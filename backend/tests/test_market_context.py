import pandas as pd
import pytest
from app.market_context import market_context


def observations(periods, value=0.01):
    return [dict(id=f"SPY-{p}", type="benchmark_observation", identifier="SPY", period=p, value=value, source="Fixture", status="cached") for p in periods]


def test_market_compounding_includes_initial_wealth_and_correct_windows():
    rows = observations([str(p) for p in pd.period_range("2024-01", periods=12, freq="M")])
    context = market_context("SPY", rows)
    assert context["metrics"]["return_3m"] == pytest.approx(1.01 ** 3 - 1)
    assert context["metrics"]["return_12m"] == pytest.approx(1.01 ** 12 - 1)
    assert context["metrics"]["volatility_12m"] == pytest.approx(0, abs=1e-12)
    assert context["chart"][0] == {"period": "2023-12", "index": 100.0}
    assert context["chart"][-1]["index"] == pytest.approx(100 * 1.01 ** 12)
    assert len(context["observations"]) == 12


def test_market_gaps_short_history_and_invalid_values_are_not_filled():
    periods = [str(p) for p in pd.period_range("2024-01", periods=12, freq="M")]
    rows = observations([p for p in periods if p != "2024-06"])
    context = market_context("SPY", rows)
    assert context["metrics"]["return_12m"] is None
    assert context["metrics"]["volatility_12m"] is None
    assert context["metrics"]["return_3m"] == pytest.approx(1.01 ** 3 - 1)
    assert context["chart"] == []
    assert market_context("QQQ", rows)["status"] == "UNAVAILABLE"
    invalid = market_context("SPY", observations(["2024-12"], float("nan")))
    assert invalid["chart"] == [] and invalid["observations"][0]["value"] is None
    assert market_context("SPY", observations(periods[-3:], -1.1))["metrics"]["return_3m"] is None


def test_macro_changes_require_adjacent_months_and_keep_independent_dates():
    rows = observations(["2024-10", "2024-11", "2024-12"])
    rows += [dict(id=f"yield-{p}", type="macro_observation", identifier="DGS10", period=p, value=v, source="FRED", status="live") for p, v in [("2024-10", 4.1), ("2024-11", 4.3)]]
    context = market_context("SPY", rows)
    yield_ = next(i for i in context["indicators"] if i["identifier"] == "DGS10")
    assert yield_["period"] == "2024-11" and context["period"] == "2024-12"
    assert yield_["change"] == pytest.approx(0.2)
    assert yield_["status"] == "live" and context["status"] == "CACHED DEMO DATA"
    rows[-2]["period"] = "2024-09"
    yield_ = next(i for i in market_context("SPY", rows)["indicators"] if i["identifier"] == "DGS10")
    assert yield_["change"] is None and yield_["previous_evidence_id"] is None
