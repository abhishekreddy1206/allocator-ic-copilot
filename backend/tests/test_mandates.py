from copy import deepcopy
import pytest
from app.mandates import MandateInput, eligibility, rank_funds, decision_diff


def fund(fid="A", **metrics):
    return {
        "id": fid,
        "canonical_name": fid,
        "liquidity": "quarterly",
        "strategy": "Global Macro",
        "metrics": {
            "observation_count": 60,
            "contiguous": True,
            "maximum_drawdown": -0.08,
            "annualized_volatility": 0.09,
            "benchmark_correlation": 0.2,
            "factor_r_squared": 0.3,
            "downside_capture": 20,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.8,
            "annualized_return": 0.10,
            "positive_month_pct": 0.7,
            **metrics,
        },
    }


@pytest.mark.parametrize(
    "change,key",
    [
        ({"maximum_drawdown": 0.07}, "maximum_drawdown"),
        ({"liquidity_requirement": "monthly"}, "liquidity"),
        ({"minimum_track_record_months": 61}, "history"),
        ({"maximum_benchmark_correlation": 0.1}, "benchmark_correlation"),
        ({"excluded_strategies": ["Global Macro"]}, "strategy"),
        ({"maximum_volatility": 0.05}, "annualized_volatility"),
    ],
)
def test_hard_constraints(change, key):
    f = fund()
    failures = eligibility(f, f["metrics"], MandateInput(**change))
    assert key in [c["constraint"] for c in failures]


def test_ranking_eligible_only_deterministic_ties_and_weights():
    a = fund("A", sharpe_ratio=1.9, benchmark_correlation=0.35, factor_r_squared=0.8)
    b = fund("B", sharpe_ratio=0.5, benchmark_correlation=0.02, factor_r_squared=0.1)
    c = fund("C", annualized_return=1, maximum_drawdown=-0.5)
    div = rank_funds([a, b, c], MandateInput())
    ar = rank_funds([a, b, c], MandateInput(profile="Absolute Return"))
    assert div[0]["id"] == "B" and ar[0]["id"] == "A"
    assert div[-1]["total_score"] is None and div[-1]["component_scores"] == {}
    assert div == rank_funds([c, b, a], MandateInput())
    tied = rank_funds([fund("Z"), fund("A")], MandateInput())
    assert tied[0]["id"] == "A"


def test_unknown_metric_fails_closed_and_diff_explains_breach():
    f = fund(benchmark_correlation=None)
    assert any(x["constraint"] == "benchmark_correlation" for x in eligibility(f, f["metrics"], MandateInput()))
    old = MandateInput()
    new = MandateInput(maximum_drawdown=0.07)
    before = rank_funds([fund()], old)
    after = rank_funds([fund()], new)
    change = decision_diff(before, after, old.model_dump(), new.model_dump())[0]
    assert change["from_rank"] == 1 and change["to_rank"] is None
    assert "8.0%" in change["reasons"][0]
    assert change["parameter_changes"]["maximum_drawdown"] == {"from": 0.15, "to": 0.07}


def test_invalid_weights_rejected_and_peer_removal_does_not_change_score():
    with pytest.raises(ValueError):
        MandateInput(weights={"sharpe": 0.9})
    a = fund()
    b = deepcopy(a)
    b["id"] = "B"
    assert rank_funds([a, b], MandateInput())[0]["total_score"] == rank_funds([a], MandateInput())[0]["total_score"]
