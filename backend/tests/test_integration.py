import csv
from io import StringIO
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.ingestion import ingest_csv, number, identifier, month
from app.models import Evidence, MonthlyReturn, DataQualityIssue, Run, Fund
from app.service import seed_demo, evaluate
from app.mandates import MandateInput
from app.evidence import briefing_sections, persist_memo
from app.main import app
from app.db import get_db


def fixture_csv(rows):
    out = StringIO()
    w = csv.DictWriter(out, fieldnames=["fund_id", "fund_name", "strategy", "liquidity", "period", "monthly_return"])
    w.writeheader()
    for r in rows:
        w.writerow({"fund_id": "a-1", "fund_name": "Alpha", "strategy": "cta", "liquidity": "month", "period": "2020-01", "monthly_return": "2%", **r})
    return out.getvalue()


def test_ingestion_normalization_duplicates_missing_periods_and_conflicts(db):
    content = fixture_csv(
        [
            {},
            {},
            {"period": "2020-03", "monthly_return": ".01"},
            {"fund_name": "Different identity", "period": "2020-04"},
            {"period": "2020-05", "monthly_return": "2.0"},
        ]
    )
    summary = ingest_csv(db, "fixture.csv", content)
    assert summary["valid_rows"] == 2 and summary["rejected_rows"] == 3
    assert db.scalar(select(Fund)).strategy == "CTA / Managed Futures"
    assert db.scalar(select(Fund)).liquidity == "monthly"
    assert db.scalar(select(MonthlyReturn).where(MonthlyReturn.period == "2020-01")).return_value == 0.02
    kinds = {x.issue_type for x in db.scalars(select(DataQualityIssue))}
    assert {"duplicate_observation", "missing_month", "identifier_conflict", "invalid_row", "insufficient_history", "normalization"} <= kinds
    assert ingest_csv(db, "fixture.csv", content)["already_imported"]
    assert identifier(" a-b_12 ") == "AB12"
    assert number("20", fee=True)[0] == 0.2
    with pytest.raises(ValueError):
        number("2")
    with pytest.raises(ValueError):
        month("01/02/2020")


def test_full_demo_transitions_evidence_and_memo_immutability(db):
    summary = seed_demo(db)
    assert summary["valid_rows"] > 900
    assert len(db.scalars(select(Fund)).all()) == 18
    base = evaluate(db, MandateInput())
    atlas = next(f for f in base.result["funds"] if f["id"] == "ATLAS")
    orion = next(f for f in base.result["funds"] if f["id"] == "ORION")
    assert atlas["eligible"] and orion["eligible"]
    original_id = atlas["evidence_ids"]["maximum_drawdown"]
    original_evidence = db.get(Evidence, original_id)
    assert original_evidence.provenance["return_sources"][0]["source_row"]
    assert original_evidence.provenance["benchmark_evidence_ids"]
    memo = persist_memo(db, base, briefing_sections(base.result), "briefing", {"ai_generated": False})
    tightened = evaluate(db, MandateInput(maximum_drawdown=0.07), base.id)
    a = next(f for f in tightened.result["funds"] if f["id"] == "ATLAS")
    assert not a["eligible"] and any(x["constraint"] == "maximum_drawdown" for x in a["failed_constraints"])
    assert next(f for f in tightened.result["funds"] if f["id"] == "ORION")["eligible"]
    monthly = evaluate(db, MandateInput(maximum_drawdown=0.07, liquidity_requirement="monthly"), tightened.id)
    o = next(f for f in monthly.result["funds"] if f["id"] == "ORION")
    assert not o["eligible"] and any(x["constraint"] == "liquidity" for x in o["failed_constraints"])
    assert any(c["fund_id"] == "ORION" for c in monthly.result["changes"])
    assert memo.run_id == base.id and db.get(Evidence, original_id).value == original_evidence.value
    for s in memo.structured_sections["sections"]:
        for c in s["claims"]:
            assert c["evidence_ids"] and all(db.get(Evidence, eid) for eid in c["evidence_ids"])
    assert db.get(Run, monthly.id).result["market_status"] == "CACHED DEMO DATA"


def test_api_no_key_flow_upload_evidence_and_ai_failure_preserves_run(db, monkeypatch):
    seed_demo(db)
    run = evaluate(db, MandateInput())
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        client = TestClient(app)
        assert client.get("/api/health").status_code == 200
        assert not client.get("/api/config").json()["ai_available"]
        result = client.post("/api/evaluations", json={"mandate": MandateInput(maximum_drawdown=0.07).model_dump(), "previous_run_id": run.id})
        assert result.status_code == 200
        r = result.json()
        assert r["changes"]
        memo = client.post("/api/memos", json={"run_id": r["run_id"], "kind": "briefing"})
        assert memo.status_code == 200 and memo.json()["model_metadata"]["ai_generated"] is False
        eid = memo.json()["claims"][0]["evidence_ids"][0]
        assert client.get("/api/evidence/" + eid).status_code == 200
        assert client.post("/api/memos", json={"run_id": r["run_id"], "kind": "memo"}).status_code == 503
        assert client.get("/api/runs/latest").json()["run_id"] == r["run_id"]
        bad = client.post("/api/uploads", files=[("files", ("bad.csv", b"wrong,columns\n1,2", "text/csv"))])
        assert bad.status_code == 422
        assert client.get("/api/runs/latest").json()["run_id"] == r["run_id"]
        source = db.scalar(select(MonthlyReturn))
        assert client.get(f"/api/uploads/{source.source_file}/rows/{source.source_row}").json()["sha256"]
        assert client.get("/api/evidence?run_id=" + r["run_id"] + "&type=factor_estimate").json()
    finally:
        app.dependency_overrides.clear()


def test_mocked_ai_api_composes_software_facts_and_challenge(db, monkeypatch):
    from app.ai import MemoOutput, SectionOutput, ClaimOutput

    seed_demo(db)
    run = evaluate(db, MandateInput())
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")

    def mocked_generate(self, context, feedback=""):
        fid = context["engine_top_id"]
        eid = next(e["id"] for e in context["evidence"] if e["fund_id"] == fid and e["type"] == "qualitative_note")
        titles = (
            ["Argument Against", "Alternative Conditions", "Unresolved Risks", "Diligence Questions"]
            if context["kind"] == "challenge"
            else ["Executive Summary", "Investment Rationale", "Key Risks", "Manager-Specific Diligence Questions", "Alternatives Considered"]
        )
        claim = ClaimOutput(
            fund_id=fid,
            text="The source note suggests capacity and portfolio construction need diligence.",
            evidence_ids=[eid],
            confidence="medium",
            claim_type="interpretation",
        )
        return MemoOutput(
            recommended_fund_id=fid, sections=[SectionOutput(title=t, claims=[claim] * 3 if t == "Diligence Questions" else [claim]) for t in titles]
        ), {"provider": "Test double (never used by application)", "model": "test"}

    monkeypatch.setattr("app.main.OpenAIResponsesProvider.generate", mocked_generate)
    try:
        client = TestClient(app)
        for kind in ["memo", "challenge"]:
            response = client.post("/api/memos", json={"run_id": run.id, "kind": kind})
            assert response.status_code == 200
            artifact = response.json()
            assert artifact["model_metadata"]["ai_generated"]
            assert all(c["evidence_ids"] for c in artifact["claims"])
            if kind == "memo":
                assert any(c["confidence"] == "deterministic" for c in artifact["claims"])
                assert len(artifact["payload"]["sections"]) == 10
            else:
                assert len(artifact["payload"]["sections"]) == 4
    finally:
        app.dependency_overrides.clear()
