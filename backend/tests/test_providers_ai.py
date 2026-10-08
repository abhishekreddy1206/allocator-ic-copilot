from io import BytesIO
from zipfile import ZipFile
import pytest
from app.providers import CachedDemoProvider, MarketSeries, with_fallback, FrenchFactorProvider
from app.ai import MemoOutput, SectionOutput, ClaimOutput, validate_output, generate_verified


def test_provider_success_and_honest_fallback():
    cached = CachedDemoProvider()

    class Success:
        def fetch(self, identifier):
            result = cached.fetch(identifier)
            return MarketSeries(result.values, {**result.lineage, "live_or_cached": "live", "synthetic": False})

    class Failure:
        def fetch(self, identifier):
            raise TimeoutError("unavailable")

    assert with_fallback(Success(), "SPY", cached).lineage["live_or_cached"] == "live"
    fallback = with_fallback(Failure(), "SPY", cached)
    assert fallback.lineage["synthetic"] and fallback.lineage["live_or_cached"] == "cached"
    assert fallback.lineage["fallback_reason"] == "TimeoutError"


def test_french_zip_percent_conversion_and_missing_values():
    content = BytesIO()
    with ZipFile(content, "w") as z:
        z.writestr("factor.csv", "Research data\n,Mkt-RF,SMB,HML,RMW,CMA,RF\n202001,1,2,-99.99,4,5,.1\n202002,-2,1,0,3,2,.1\nAnnual Factors\n2020,1,2,3,4,5,6")
    frame = FrenchFactorProvider.parse_zip(content.getvalue())
    assert list(frame.index) == ["2020-01", "2020-02"]
    assert frame.loc["2020-01", "Mkt-RF"] == 0.01
    assert frame.loc["2020-01", "HML"] != frame.loc["2020-01", "HML"]


def context():
    return {
        "kind": "memo",
        "engine_top_id": "A",
        "funds": [{"id": "A", "eligible": True, "canonical_name": "Atlas Macro", "manager_name": "Atlas Partners"}],
        "evidence": [{"id": "E", "fund_id": "A"}],
    }


def output(text="Source notes suggest leadership continuity deserves diligence.", refs=None, fund="A"):
    return MemoOutput(
        recommended_fund_id="A",
        sections=[
            SectionOutput(title=t, claims=[ClaimOutput(fund_id=fund, text=text, evidence_ids=refs or ["E"], confidence="medium", claim_type="interpretation")])
            for t in ["Executive Summary", "Investment Rationale", "Key Risks", "Manager-Specific Diligence Questions", "Alternatives Considered"]
        ],
    )


@pytest.mark.parametrize(
    "bad",
    [
        output(refs=["UNKNOWN"]),
        output(text="Sharpe is 1.42."),
        output(fund="INVENTED"),
        output(text="This manager is eligible."),
        output(text="Atlas Macro deserves consideration."),
        output(text="An allocation to InventedFund could be preferable."),
    ],
)
def test_unknown_evidence_numbers_funds_and_eligibility_rejected(bad):
    with pytest.raises(ValueError):
        validate_output(bad, context())


def test_recommendation_and_cross_fund_evidence_rejected():
    bad = output()
    bad.recommended_fund_id = "B"
    with pytest.raises(ValueError):
        validate_output(bad, context())
    c = context()
    c["evidence"][0]["fund_id"] = "B"
    with pytest.raises(ValueError):
        validate_output(output(), c)


def test_one_validation_retry_and_persistent_failure():
    class Provider:
        calls = 0

        def generate(self, context, feedback=""):
            self.calls += 1
            return output(refs=["UNKNOWN"] if self.calls == 1 else ["E"]), {"model": "test stub"}

    p = Provider()
    payload, meta = generate_verified(p, context())
    assert p.calls == 2 and meta["validation_attempts"] == 2
    assert payload["recommended_fund_id"] == "A"

    class Bad:
        def generate(self, context, feedback=""):
            return output(refs=["UNKNOWN"]), {}

    with pytest.raises(ValueError):
        generate_verified(Bad(), context())


def test_momentum_explanatory_text_is_not_a_csv_header():
    content = BytesIO()
    with ZipFile(content, "w") as z:
        z.writestr("momentum.csv", "Research data\nMom    is the average of the returns on two portfolios\n, Mom   \n202001,1.5\n202002,-2.0\n")
    frame = FrenchFactorProvider.parse_zip(content.getvalue())
    assert frame.columns.tolist() == ["Mom"]
    assert frame.loc["2020-01", "Mom"] == 0.015
