import numpy as np
import pandas as pd
import pytest
from app.analytics import compute_metrics, factor_regression, wealth_drawdown, regime_metrics


def series(values, start="2020-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M").astype(str), dtype=float)


def test_compounding_and_annualization_hand_fixture():
    r = series([0.02, -0.01] * 6)
    b = series([0.01, -0.02] * 6)
    rf = series([0.001] * 12)
    m = compute_metrics(r, b, rf)
    growth = (1.02 * 0.99) ** 6 - 1
    assert m["cumulative_return"] == pytest.approx(growth)
    assert m["annualized_return"] == pytest.approx(growth)
    sigma = np.sqrt((6 * 0.015**2 + 6 * 0.015**2) / 11)
    assert m["annualized_volatility"] == pytest.approx(sigma * np.sqrt(12))
    assert m["sharpe_ratio"] == pytest.approx(0.004 / sigma * np.sqrt(12))
    assert m["sortino_ratio"] == pytest.approx(0.004 / np.sqrt(6 * 0.011**2 / 12) * np.sqrt(12))
    assert m["maximum_drawdown"] == pytest.approx(-0.01)
    assert m["calmar_ratio"] == pytest.approx(growth / 0.01)
    assert m["best_month"] == 0.02 and m["worst_month"] == -0.01
    assert m["positive_month_pct"] == 0.5


def test_drawdown_includes_initial_wealth():
    _, dd = wealth_drawdown(series([-0.10, 0.05, -0.20]))
    assert dd.iloc[0] == pytest.approx(-0.10)
    assert dd.min() == pytest.approx(0.9 * 1.05 * 0.8 - 1)


def test_relative_metrics_exact_known_beta_and_captures():
    b = series([0.01, -0.02, 0.03, -0.01] * 3)
    r = 2 * b + 0.001
    m = compute_metrics(r, b, series([0] * 12))
    assert m["beta"] == pytest.approx(2)
    assert m["benchmark_correlation"] == pytest.approx(1)
    assert m["alpha"] == pytest.approx(0.012)
    assert m["tracking_error"] == pytest.approx(b.std(ddof=1) * np.sqrt(12))
    assert m["information_ratio"] == pytest.approx((r - b).mean() * 12 / m["tracking_error"])
    up = b > 0
    down = b < 0
    for key, mask in [("upside_capture", up), ("downside_capture", down)]:
        assert m[key] == pytest.approx(((1 + r[mask]).prod() ** (1 / mask.sum()) - 1) / ((1 + b[mask]).prod() ** (1 / mask.sum()) - 1) * 100)


def test_gaps_suppressed_and_no_overlap():
    r = series([0.01] * 13).drop("2020-06")
    m = compute_metrics(r, series([0.02] * 12, start="2010-01"), series([0] * 13))
    assert not m["contiguous"]
    assert m["annualized_return"] is None
    assert m["maximum_drawdown"] is None
    assert m["sharpe_ratio"] is None
    assert m["benchmark_observation_count"] == 0
    assert m["beta"] is None


def test_zero_denominators_and_missing_risk_free():
    r = series([0.01] * 24)
    m = compute_metrics(r, series([0] * 24), series([0] * 24))
    for key in ["sharpe_ratio", "sortino_ratio", "calmar_ratio", "beta", "benchmark_correlation", "upside_capture", "downside_capture"]:
        assert m[key] is None
    m = compute_metrics(series([0.01, -0.01] * 12), series([0.02, -0.02] * 12), series([0] * 12))
    assert m["sharpe_ratio"] is None
    assert m["risk_free_observation_count"] == 12


def test_factor_regression_known_coefficients_and_alignment():
    rng = np.random.default_rng(5)
    index = pd.period_range("2020-01", periods=48, freq="M").astype(str)
    x = pd.DataFrame(rng.uniform(-0.03, 0.03, (48, 3)), index=index, columns=["Mkt-RF", "SMB", "Mom"])
    rf = pd.Series(0.001, index=index)
    fund = rf + 0.002 + x["Mkt-RF"] * 0.7 - x.SMB * 0.2 + x.Mom * 0.3
    out = factor_regression(fund, x.iloc[5:], rf)
    assert out["observations"] == 43
    assert out["betas"] == pytest.approx({"Mkt-RF": 0.7, "SMB": -0.2, "Mom": 0.3})
    assert out["alpha"] == pytest.approx(0.024)
    assert out["r_squared"] == pytest.approx(1)
    assert factor_regression(fund.iloc[:12], x, rf)["r_squared"] is None
    assert factor_regression(fund, x.assign(SMB=x["Mkt-RF"]), rf)["status"] == "rank-deficient factor matrix"


def test_regimes_use_exact_month_masks():
    r = series([0.01, -0.02, 0.03])
    out = regime_metrics(r, series([0.01, -0.01, -0.01]), series([15, 28, 26]), series([3, 4, 3]))
    assert out["equity_down"]["average_return"] == pytest.approx(0.005)
    assert out["rates_rising"]["average_return"] == -0.02
    assert out["rates_falling"]["average_return"] == 0.03


def test_log_compounding_survives_long_high_growth_history():
    r = series([9.0] * 400)
    m = compute_metrics(r, series([0.01, -0.01] * 200), series([0] * 400))
    assert m["annualized_return"] == pytest.approx(10**12 - 1)
    assert m["cumulative_return"] is None  # beyond representable floating point, never infinity
    assert m["maximum_drawdown"] == 0
    assert m["calmar_ratio"] is None
