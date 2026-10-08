"""Hard gates precede subjective, explicit weighted decision scores."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator

LIQUIDITY = {"daily": 0, "monthly": 1, "quarterly": 2, "annual": 3, "locked": 4}
PROFILES = {
    "Diversifier": {"correlation": 0.30, "factor_diversification": 0.20, "downside_protection": 0.15, "sharpe": 0.15, "drawdown": 0.10, "volatility_fit": 0.10},
    "Absolute Return": {"sharpe": 0.30, "sortino": 0.20, "return": 0.15, "drawdown": 0.20, "consistency": 0.15},
    "Capital Preservation": {"drawdown": 0.35, "volatility_fit": 0.25, "downside_protection": 0.25, "consistency": 0.15},
}


class MandateInput(BaseModel):
    name: str = Field(default="Core diversifier sleeve", max_length=120)
    benchmark: Literal["SPY", "QQQ", "AGG", "HYG", "IWM", "TLT", "GLD"] = "SPY"
    profile: Literal["Diversifier", "Absolute Return", "Capital Preservation"] = "Diversifier"
    target_volatility: float = Field(default=0.10, ge=0.001, le=1)
    maximum_volatility: float | None = Field(default=0.25, ge=0.001, le=2)
    maximum_drawdown: float = Field(default=0.15, ge=0, le=1, description="Positive permitted loss magnitude")
    minimum_track_record_months: int = Field(default=36, ge=12, le=240)
    maximum_benchmark_correlation: float = Field(default=0.40, ge=-1, le=1)
    liquidity_requirement: Literal["daily", "monthly", "quarterly", "annual", "locked"] = "quarterly"
    preferred_strategies: list[str] = Field(default_factory=list)
    excluded_strategies: list[str] = Field(default_factory=list)
    weights: dict[str, float] | None = None

    @model_validator(mode="after")
    def valid_weights(self):
        if self.weights is not None:
            allowed = set().union(*[set(w) for w in PROFILES.values()])
            if set(self.weights) - allowed or any(v < 0 for v in self.weights.values()) or abs(sum(self.weights.values()) - 1) > 1e-6:
                raise ValueError("Weights must be known nonnegative factors summing to 1.")
        return self


def eligibility(fund: dict, m: dict, mandate: MandateInput) -> list[dict]:
    failures = []

    def fail(key, actual, limit, message):
        failures.append({"constraint": key, "actual": actual, "limit": limit, "reason": message})

    if m["observation_count"] < mandate.minimum_track_record_months:
        fail(
            "history",
            m["observation_count"],
            mandate.minimum_track_record_months,
            f"{m['observation_count']} months is below {mandate.minimum_track_record_months} required.",
        )
    if not m.get("contiguous"):
        fail("data_coverage", False, True, "Missing months prevent a defensible drawdown/annualized risk assessment; history must be contiguous.")
    for key, limit, label, is_loss in [
        ("maximum_drawdown", mandate.maximum_drawdown, "Maximum drawdown", True),
        ("annualized_volatility", mandate.maximum_volatility, "Volatility", False),
        ("benchmark_correlation", mandate.maximum_benchmark_correlation, "Benchmark correlation", False),
    ]:
        if limit is None:
            continue
        val = m.get(key)
        if val is None:
            fail(key, None, limit, f"{label} unavailable; constraint cannot be verified.")
        elif (abs(val) if is_loss else val) > limit + 1e-12:
            message = (
                f"{label} {val:.2f} exceeds limit {limit:.2f}."
                if key == "benchmark_correlation"
                else f"{label} {val:.1%} breaches permitted {'loss ' if is_loss else ''}{limit:.1%}."
            )
            fail(key, val, limit, message)
    if fund["liquidity"] not in LIQUIDITY or LIQUIDITY[fund["liquidity"]] > LIQUIDITY[mandate.liquidity_requirement]:
        fail(
            "liquidity",
            fund["liquidity"],
            mandate.liquidity_requirement,
            f"{fund['liquidity'].title()} liquidity fails {mandate.liquidity_requirement} requirement.",
        )
    if fund["strategy"] in mandate.excluded_strategies:
        fail("strategy", fund["strategy"], mandate.excluded_strategies, f"{fund['strategy']} is excluded.")
    return failures


def clip(x: float | None, low: float, high: float, reverse: bool = False) -> float:
    if x is None:
        return 0  # unavailable analytics receive no soft credit
    score = max(0, min(1, (x - low) / (high - low))) * 100
    return 100 - score if reverse else score


def component_scores(m: dict, mandate: MandateInput) -> dict:
    return {
        "correlation": clip(m.get("benchmark_correlation"), 0, 1, True),
        "factor_diversification": clip(m.get("factor_r_squared"), 0, 1, True),
        "downside_protection": clip(m.get("downside_capture"), -50, 100, True),
        "sharpe": clip(m.get("sharpe_ratio"), 0, 2),
        "sortino": clip(m.get("sortino_ratio"), 0, 3),
        "drawdown": clip(abs(m["maximum_drawdown"]) if m.get("maximum_drawdown") is not None else None, 0, 0.20, True),
        "volatility_fit": clip(
            max(0, m["annualized_volatility"] - mandate.target_volatility) if m.get("annualized_volatility") is not None else None, 0, 0.15, True
        ),
        "return": clip(m.get("annualized_return"), 0, 0.20),
        "consistency": clip(m.get("positive_month_pct"), 0.40, 0.80),
    }


def rank_funds(funds: list[dict], mandate: MandateInput) -> list[dict]:
    weights = mandate.weights if mandate.weights is not None else PROFILES[mandate.profile]
    result = []
    for fund in funds:
        failed = eligibility(fund, fund["metrics"], mandate)
        components = component_scores(fund["metrics"], mandate) if not failed else {}
        # Strategy preference is an explicit visible bonus, capped to the 0–100 scale.
        bonus = 3.0 if fund["strategy"] in mandate.preferred_strategies and not failed else 0
        score = min(100, sum(components[k] * w for k, w in weights.items()) + bonus) if not failed else None
        result.append(
            {
                **fund,
                "eligible": not failed,
                "failed_constraints": failed,
                "component_scores": {
                    k: {"score": round(components[k], 4), "weight": w, "contribution": round(components[k] * w, 4)} for k, w in weights.items()
                }
                if not failed
                else {},
                "preference_bonus": bonus,
                "total_score": round(score, 6) if score is not None else None,
                "rank": None,
            }
        )
    result.sort(key=lambda f: (not f["eligible"], -(f["total_score"] or 0), f["id"]))
    for i, f in enumerate([f for f in result if f["eligible"]], 1):
        f["rank"] = i
    return result


def decision_diff(previous: list[dict], current: list[dict], old: dict, new: dict) -> list[dict]:
    lookup = {f["id"]: f for f in previous}
    parameter_changes = {k: {"from": old.get(k), "to": v} for k, v in new.items() if old.get(k) != v}
    changes = []
    for f in current:
        p = lookup.get(f["id"])
        if p and (p["eligible"] != f["eligible"] or p["rank"] != f["rank"]):
            reasons = (
                [c["reason"] for c in f["failed_constraints"]]
                if not f["eligible"]
                else [f"Rank recomputed among {sum(x['eligible'] for x in current)} eligible managers using {new['profile']} weights."]
            )
            changes.append(
                {
                    "fund_id": f["id"],
                    "fund": f["canonical_name"],
                    "from_rank": p["rank"],
                    "to_rank": f["rank"],
                    "from_eligible": p["eligible"],
                    "to_eligible": f["eligible"],
                    "reasons": reasons,
                    "parameter_changes": parameter_changes,
                }
            )
    return changes
