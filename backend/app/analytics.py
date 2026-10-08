"""Monthly decimal returns. No imputation, no LLM calculations, no look-ahead filling."""

import numpy as np
import pandas as pd

METHODS = {
    "cumulative_return": "Product(1 + monthly return) - 1; observed months only.",
    "annualized_return": "Product(1+r)^(12/n)-1; unavailable for gaps or fewer than 12 months.",
    "annualized_volatility": "Sample standard deviation of monthly returns × sqrt(12); contiguous history only.",
    "sharpe_ratio": "Mean monthly excess return / sample standard deviation of monthly excess return × sqrt(12); exact RF month join.",
    "sortino_ratio": "Mean monthly excess return × 12 / (sqrt(mean(min(excess,0)^2)) × sqrt(12)); all aligned months in denominator.",
    "maximum_drawdown": "Minimum wealth / running peak - 1, including initial wealth of 1; unavailable for gapped history.",
    "calmar_ratio": "Geometric annualized return / absolute maximum drawdown; null at zero drawdown.",
    "benchmark_correlation": "Pearson correlation of exact-month inner-joined fund and benchmark returns; minimum 12 observations.",
    "beta": "Sample covariance(fund,benchmark) / sample variance(benchmark); minimum 12 matched months.",
    "alpha": "OLS monthly excess intercept × 12 (arithmetic estimate), benchmark excess regression; exact RF join.",
    "tracking_error": "Sample standard deviation(fund - benchmark) × sqrt(12) on exact matched months.",
    "information_ratio": "Mean active monthly return × 12 / annualized tracking error.",
    "excess_return": "Annualized geometric fund growth minus benchmark growth on the same contiguous matched window.",
    "upside_capture": "Geometric mean fund return / geometric mean benchmark return in positive benchmark months × 100.",
    "downside_capture": "Geometric mean fund return / geometric mean benchmark return in negative benchmark months × 100.",
    "best_month": "Maximum observed monthly decimal return.",
    "worst_month": "Minimum observed monthly decimal return.",
    "positive_month_pct": "Fraction of observed returns strictly greater than zero.",
    "skew": "pandas unbiased sample skewness; minimum 3 observations.",
    "kurtosis": "pandas unbiased excess kurtosis; minimum 4 observations.",
    "factor_r_squared": "OLS R² of fund excess returns against six explanatory factors; exact-month alignment, minimum 24 months.",
    "factor_alpha": "OLS intercept × 12, arithmetic explanatory estimate, not proof of skill.",
}


def finite(value: float | None) -> float | None:
    return float(value) if value is not None and np.isfinite(value) else None


def divide(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b):
        return None
    return finite(a / b) if abs(b) > 1e-12 else None


def contiguous(s: pd.Series) -> bool:
    if s.empty:
        return False
    idx = pd.PeriodIndex(s.index, freq="M").sort_values()
    return idx.is_unique and len(idx) == idx[-1].ordinal - idx[0].ordinal + 1


def wealth_drawdown(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    log_wealth = np.log1p(s).cumsum()
    log_peak = log_wealth.cummax().clip(lower=0)
    with np.errstate(over="ignore"):
        wealth = np.exp(log_wealth)
    return wealth, np.expm1(log_wealth - log_peak)


def compute_metrics(returns: pd.Series, benchmark: pd.Series, rf: pd.Series) -> dict:
    r = returns.dropna().sort_index().astype(float)
    if r.index.has_duplicates or (r <= -1).any() or not np.isfinite(r).all():
        raise ValueError("Returns must be finite, unique monthly observations greater than -100%.")
    n = len(r)
    out = dict.fromkeys(METHODS)
    out.update(observation_count=n, period_start=str(r.index.min()) if n else "", period_end=str(r.index.max()) if n else "", contiguous=contiguous(r))
    if not n:
        return out
    wealth, dd = wealth_drawdown(r)
    out.update(
        cumulative_return=finite(wealth.iloc[-1] - 1),
        best_month=finite(r.max()),
        worst_month=finite(r.min()),
        positive_month_pct=float((r > 0).mean()),
        skew=finite(r.skew()) if n >= 3 else None,
        kurtosis=finite(r.kurt()) if n >= 4 else None,
    )
    if contiguous(r):
        out["maximum_drawdown"] = finite(dd.min())
        if n >= 12:
            out["annualized_return"] = finite(np.expm1(np.log1p(r).mean() * 12))
            out["annualized_volatility"] = finite(r.std(ddof=1) * np.sqrt(12))
            out["calmar_ratio"] = divide(out["annualized_return"], abs(out["maximum_drawdown"]))
    risk = pd.concat([r.rename("r"), rf.rename("rf")], axis=1, join="inner").dropna()
    out["risk_free_observation_count"] = len(risk)
    if len(risk) == n and n >= 12 and contiguous(r):
        excess = risk.r - risk.rf
        out["sharpe_ratio"] = divide(excess.mean() * np.sqrt(12), excess.std(ddof=1))
        out["sortino_ratio"] = divide(excess.mean() * np.sqrt(12), np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))
    aligned = pd.concat([r.rename("r"), benchmark.rename("b")], axis=1, join="inner").dropna()
    out["benchmark_observation_count"] = len(aligned)
    out["benchmark_period"] = f"{aligned.index.min()} → {aligned.index.max()}" if len(aligned) else "No overlap"
    out["rolling_correlation"] = []
    if len(aligned) >= 12:
        a, b = aligned.r, aligned.b
        if a.std() > 1e-12 and b.std() > 1e-12:
            out["benchmark_correlation"] = finite(a.corr(b))
        out["beta"] = divide(a.cov(b), b.var(ddof=1))
        active = a - b
        out["tracking_error"] = finite(active.std(ddof=1) * np.sqrt(12))
        out["information_ratio"] = divide(active.mean() * 12, out["tracking_error"])
        if contiguous(a):
            out["excess_return"] = finite(np.expm1(np.log1p(a).mean() * 12) - np.expm1(np.log1p(b).mean() * 12))
        for label, mask in [("upside_capture", b > 0), ("downside_capture", b < 0)]:
            if mask.sum():
                out[label] = divide(np.expm1(np.log1p(a[mask]).mean()), np.expm1(np.log1p(b[mask]).mean()))
                if out[label] is not None:
                    out[label] *= 100
        alpha_data = aligned.join(rf.rename("rf"), how="inner").dropna()
        if len(alpha_data) >= 12 and (alpha_data.b - alpha_data.rf).var() > 1e-12:
            x = alpha_data.b - alpha_data.rf
            y = alpha_data.r - alpha_data.rf
            out["alpha"] = finite((y.mean() - x.mean() * y.cov(x) / x.var()) * 12)
        # Windows must represent 12 calendar months, never 12 discontinuous observations.
        for i in range(11, len(aligned)):
            w = aligned.iloc[i - 11 : i + 1]
            out["rolling_correlation"].append(
                {"period": str(w.index[-1]), "value": finite(w.r.corr(w.b)) if contiguous(w.r) and w.b.std() > 1e-12 and w.r.std() > 1e-12 else None}
            )
    return out


def factor_regression(returns: pd.Series, factors: pd.DataFrame, rf: pd.Series) -> dict:
    joined = pd.concat([returns.rename("fund"), rf.rename("rf"), factors], axis=1, join="inner").dropna()
    names = list(factors.columns)
    empty = {"betas": {}, "t_stats": {}, "r_squared": None, "alpha": None, "observations": len(joined), "period": "", "status": "insufficient observations"}
    if len(joined) < max(24, len(names) * 3):
        return empty
    x = np.column_stack([np.ones(len(joined)), joined[names].values])
    y = (joined.fund - joined.rf).values
    if np.linalg.matrix_rank(x) < x.shape[1]:
        return {**empty, "status": "rank-deficient factor matrix"}
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ coef
    sse = residual @ residual
    tss = np.sum((y - y.mean()) ** 2)
    cov = (sse / (len(y) - x.shape[1])) * np.linalg.inv(x.T @ x)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    return {
        "betas": {name: finite(coef[i + 1]) for i, name in enumerate(names)},
        "t_stats": {name: divide(coef[i + 1], se[i + 1]) for i, name in enumerate(names)},
        "r_squared": finite(1 - sse / tss) if tss > 1e-12 else None,
        "alpha": finite(coef[0] * 12),
        "observations": len(joined),
        "period": f"{joined.index.min()} → {joined.index.max()}",
        "status": "explanatory OLS; not evidence of skill",
    }


def chart_series(returns: pd.Series, benchmark: pd.Series) -> list[dict]:
    """Break charts at missing months; drawdowns across gaps are not asserted."""
    if returns.empty:
        return []
    index = pd.period_range(returns.index.min(), returns.index.max(), freq="M").astype(str)
    frame = pd.DataFrame(index=index).join(returns.rename("r")).join(benchmark.rename("b"))
    w, dd = wealth_drawdown(frame.r.dropna())
    bw, _ = wealth_drawdown(frame.b.dropna())
    has_gaps = not contiguous(returns)
    return [
        {
            "period": str(p),
            "fund": finite((w.get(p) - 1) * 100) if p in w else None,
            "benchmark": finite((bw.get(p) - 1) * 100) if p in bw else None,
            "drawdown": finite(dd.get(p) * 100) if p in dd and not has_gaps else None,
        }
        for p in index
    ]


def regime_metrics(returns: pd.Series, spy: pd.Series, vix: pd.Series, rates: pd.Series) -> dict:
    data = pd.concat([returns.rename("r"), spy.rename("spy"), vix.rename("vix"), rates.diff().rename("rate_change")], axis=1, join="inner").dropna()
    masks = {"equity_down": data.spy < 0, "high_vix": data.vix >= 25, "rates_rising": data.rate_change > 0, "rates_falling": data.rate_change < 0}
    return {
        key: {
            "average_return": finite(data.loc[mask, "r"].mean()) if mask.any() else None,
            "observations": int(mask.sum()),
            "periods": data.index[mask].tolist(),
        }
        for key, mask in masks.items()
    }
