"""FastAPI contracts; all financial semantics live in explicit backend modules."""

from contextlib import asynccontextmanager
import os
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import RateLimitError
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db import get_db, SessionLocal
from app.models import BenchmarkReturn, Upload, DataQualityIssue, Run, Evidence, Memo, MemoClaim
from app.mandates import MandateInput, PROFILES
from app.service import seed_demo, evaluate, store_market
from app.ingestion import ingest_csv
from app.evidence import briefing_sections, persist_memo
from app.ai import OpenAIResponsesProvider, generate_verified
from app.imports import read_table, preview, import_table, FIELDS, REQUIRED
from app.exports import comparison_xlsx, memo_docx
from fastapi.responses import Response
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal.begin() as session:
        if not session.scalar(select(BenchmarkReturn.id).limit(1)):
            store_market(session)
        if os.getenv("SEED_DEMO", "true").lower() == "true":
            seed_demo(session)
            if not session.scalar(select(Run.id).limit(1)):
                evaluate(session, MandateInput())
    yield


app = FastAPI(title="Allocator IC Copilot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"]
)
DB = Annotated[Session, Depends(get_db)]


@app.get("/api/health")
def health(db: DB):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {"ai_available": bool(os.getenv("OPENAI_API_KEY")), "profiles": PROFILES, "principle": "Deterministic software owns facts. AI helps interpret them."}


@app.post("/api/demo")
def demo(db: DB):
    summary = seed_demo(db)
    store_market(db, live=False)  # Explicit demo reset guarantees the offline walkthrough.
    run = evaluate(db, MandateInput())
    db.commit()
    return {"summary": summary, "result": run.result}


@app.post("/api/uploads")
async def upload(db: DB, files: list[UploadFile] = File(...)):
    if len(files) > 10:
        raise HTTPException(413, "At most 10 CSV files per upload")
    summaries = []
    for file in files:
        data = await file.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            db.rollback()
            raise HTTPException(413, "Each CSV must be under 8 MB")
        try:
            summaries.append(ingest_csv(db, file.filename or "upload.csv", data.decode("utf-8-sig")))
        except (ValueError, UnicodeError) as exc:
            db.rollback()
            raise HTTPException(422, str(exc)) from exc
    previous = db.scalar(select(Run).order_by(Run.created_at.desc()).limit(1))
    params = MandateInput(**previous.result["mandate"]) if previous else MandateInput()
    try:
        run = evaluate(db, params)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {"summaries": summaries, "result": run.result}


async def reviewed_file(file, mapping, corrections, sheet):
    data = await file.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "File must be under 8 MB")
    try:
        mapped, edits = json.loads(mapping), json.loads(corrections)
        if not isinstance(mapped, dict) or not isinstance(edits, dict):
            raise ValueError("Mapping and corrections must be objects")
        table = read_table(file.filename or "upload.csv", data, sheet)
        return data, table, mapped, edits
    except (ValueError, UnicodeError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/preview")
async def import_preview(db: DB, file: UploadFile = File(...), mapping: str = Form("{}"), corrections: str = Form("{}"), sheet: str = Form("")):
    data, table, mapped, edits = await reviewed_file(file, mapping, corrections, sheet)
    result = dict(headers=table["headers"], rows=[dict(source_row=i, values=dict(zip(table["headers"], row))) for i, row in enumerate(table["rows"][:200], 2)],
                  row_count=len(table["rows"]), sheets=table["sheets"], sheet=table["sheet"], mapping=mapped or table["suggested"], fields=FIELDS, required=REQUIRED)
    try:
        result.update(preview(db, file.filename or "upload.csv", data, table, mapped, edits))
    except ValueError as exc:
        result["validation_error"] = str(exc)
    return result


@app.post("/api/imports/commit")
async def import_commit(db: DB, file: UploadFile = File(...), mapping: str = Form("{}"), corrections: str = Form("{}"), sheet: str = Form("")):
    data, table, mapped, edits = await reviewed_file(file, mapping, corrections, sheet)
    try:
        summary = import_table(db, file.filename or "upload.csv", data, table, mapped, edits)
        previous = db.scalar(select(Run).order_by(Run.created_at.desc()).limit(1))
        run = evaluate(db, MandateInput(**previous.result["mandate"]) if previous else MandateInput())
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {"summary": summary, "result": run.result}


@app.get("/api/runs/{run_id}/comparison.xlsx")
def export_comparison(run_id: str, db: DB):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Evaluation not found")
    return Response(comparison_xlsx(run.result), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="manager-comparison-{run_id}.xlsx"'})


@app.get("/api/runs/{run_id}/memo.docx")
def export_memo(run_id: str, db: DB, memo_id: str | None = None):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Evaluation not found")
    memo = db.get(Memo, memo_id) if memo_id else None
    if memo_id and (not memo or memo.run_id != run_id):
        raise HTTPException(404, "Memo does not belong to this evaluation")
    payload = memo.structured_sections if memo else briefing_sections(run.result)
    metadata = memo.model_metadata if memo else {"provider": "Deterministic rules-based briefing"}
    evidence = {e.id: e for e in db.scalars(select(Evidence).where(Evidence.run_id == run_id))}
    return Response(memo_docx(run.result, payload, metadata, evidence), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="committee-memo-{run_id}.docx"'})


@app.get("/api/data-health")
def data_health(db: DB):
    uploads = db.scalars(select(Upload).order_by(Upload.created_at.desc())).all()
    issues = db.scalars(select(DataQualityIssue).order_by(DataQualityIssue.source_file, DataQualityIssue.source_row)).all()
    categories = {}
    for i in issues:
        categories[i.issue_type] = categories.get(i.issue_type, 0) + 1
    return {
        "uploads": [u.summary for u in uploads],
        "categories": categories,
        "issues": [
            {k: getattr(i, k) for k in ["id", "severity", "issue_type", "fund_id", "source_file", "source_row", "description", "inferred_resolution", "status"]}
            for i in issues
        ],
    }


@app.get("/api/runs/latest")
def latest(db: DB):
    run = db.scalar(select(Run).order_by(Run.created_at.desc()).limit(1))
    return run.result if run else None


class EvaluationRequest(BaseModel):
    mandate: MandateInput
    previous_run_id: str | None = None


@app.post("/api/evaluations")
def evaluation(request: EvaluationRequest, db: DB):
    try:
        run = evaluate(db, request.mandate, request.previous_run_id)
        db.commit()
        return run.result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/market/refresh")
def refresh(db: DB):
    sources = store_market(db, live=True)
    previous = db.scalar(select(Run).order_by(Run.created_at.desc()).limit(1))
    run = evaluate(db, MandateInput(**previous.result["mandate"]) if previous else MandateInput(), previous.id if previous else None)
    db.commit()
    return {"sources": sources, "result": run.result}


@app.get("/api/evidence")
def list_evidence(db: DB, run_id: str, type: str | None = None, q: str = "", limit: int = 150):
    query = select(Evidence).where(Evidence.run_id == run_id)
    if type:
        query = query.where(Evidence.type == type)
    if q:
        query = query.where(Evidence.label.ilike("%" + q[:100] + "%"))
    rows = db.scalars(query.order_by(Evidence.label).limit(max(1, min(limit, 500)))).all()
    return [{k: getattr(e, k) for k in ["id", "type", "label", "value", "unit", "source", "observation_period", "live_or_cached"]} for e in rows]


@app.get("/api/evidence/{evidence_id}")
def evidence_detail(evidence_id: str, db: DB):
    e = db.get(Evidence, evidence_id)
    if e is None:
        raise HTTPException(404, "Evidence not found")
    return {
        k: getattr(e, k)
        for k in [
            "id",
            "run_id",
            "type",
            "label",
            "value",
            "unit",
            "source",
            "source_identifier",
            "observation_period",
            "methodology",
            "provenance",
            "live_or_cached",
        ]
    }


@app.get("/api/uploads/{upload_id}/rows/{row}")
def source_row(upload_id: str, row: int, db: DB):
    import csv
    from io import StringIO

    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    metadata = upload.source_metadata or {}
    rows = list(csv.reader(StringIO(metadata.get("original_table", upload.raw_csv))))
    if row < 2 or row > len(rows):
        raise HTTPException(404, "Source row not found")
    return {"filename": upload.filename, "sha256": metadata.get("original_sha256", upload.sha256), "source_row": row, "headers": rows[0], "values": rows[row - 1], "sheet": metadata.get("sheet"), "mapping": metadata.get("mapping"), "corrections": metadata.get("corrections", {}).get(str(row), {})}


@app.get("/api/uploads/{upload_id}/original")
def original_file(upload_id: str, db: DB):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    xlsx = upload.filename.lower().endswith(".xlsx") and upload.original_file is not None
    return Response(upload.original_file if upload.original_file is not None else upload.raw_csv.encode(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if xlsx else "text/csv",
                    headers={"Content-Disposition": f'attachment; filename="original-{upload_id}.{"xlsx" if xlsx else "csv"}"'})


@app.get("/api/demo.csv")
def download_demo():
    from fastapi.responses import Response
    from app.demo import demo_csv

    return Response(demo_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=synthetic_managers.csv"})


def memo_response(memo: Memo, db: Session) -> dict:
    claims = db.scalars(select(MemoClaim).where(MemoClaim.memo_id == memo.id)).all()
    return {
        "id": memo.id,
        "run_id": memo.run_id,
        "kind": memo.kind,
        "generated_at": memo.generated_at.isoformat(),
        "payload": memo.structured_sections,
        "model_metadata": memo.model_metadata,
        "claims": [{k: getattr(c, k) for k in ["id", "text", "claim_type", "confidence", "evidence_ids"]} for c in claims],
    }


@app.get("/api/memos")
def memos(run_id: str, db: DB):
    return [memo_response(m, db) for m in db.scalars(select(Memo).where(Memo.run_id == run_id).order_by(Memo.generated_at.desc()))]


class MemoRequest(BaseModel):
    run_id: str
    kind: str = "briefing"


@app.post("/api/memos")
def create_memo(request: MemoRequest, db: DB):
    run = db.get(Run, request.run_id)
    if run is None:
        raise HTTPException(404, "Evaluation not found")
    if request.kind not in ["briefing", "memo", "challenge"]:
        raise HTTPException(422, "Unknown memo kind")
    if request.kind == "briefing":
        payload = briefing_sections(run.result)
        metadata = {"provider": "Deterministic rules-based briefing", "ai_generated": False}
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(503, "AI unavailable: OPENAI_API_KEY is not configured. The rules-based briefing remains available.")
        eligible = [f for f in run.result["funds"] if f["eligible"]]
        if not eligible:
            raise HTTPException(422, "No eligible manager; revise mandate before AI interpretation")
        selected = eligible[:5] + [f for f in run.result["funds"] if not f["eligible"]][:3]
        refs = {}
        for f in selected:
            for eid in f["evidence_ids"].values():
                e = db.get(Evidence, eid)
                refs[eid] = {
                    "id": e.id,
                    "fund_id": f["id"],
                    "type": e.type,
                    "label": e.label,
                    "value": e.value,
                    "unit": e.unit,
                    "period": e.observation_period,
                    "methodology": e.methodology,
                }
        prior = db.scalar(select(Memo).where(Memo.run_id == run.id, Memo.kind == "memo").order_by(Memo.generated_at.desc()).limit(1))
        context = {
            "kind": request.kind,
            "engine_top_id": eligible[0]["id"],
            "mandate": run.result["mandate"],
            "market_status": run.result["market_status"],
            "funds": [
                {k: f[k] for k in ["id", "canonical_name", "manager_name", "eligible", "rank", "metrics", "factors", "regimes", "qualitative_notes"]}
                for f in selected
            ],
            "evidence": list(refs.values()),
            "selected_recommendation": prior.structured_sections if prior and request.kind == "challenge" else None,
        }
        try:
            payload, metadata = generate_verified(OpenAIResponsesProvider(), context)
            metadata["ai_generated"] = True
            if request.kind == "memo":
                # Numerical facts and mandate prose are always rendered by software.
                facts = briefing_sections(run.result)["sections"]
                interpretations = {s["title"]: s["claims"] for s in payload["sections"]}
                factual_titles = {"Mandate", "Recommendation", "Ranked Shortlist", "Data Appendix"}
                payload["sections"] = [
                    {
                        "title": section["title"],
                        "claims": section["claims"] + ([] if section["title"] in factual_titles else interpretations.get(section["title"], [])),
                    }
                    for section in facts
                ]
                metadata["composition"] = "Deterministic factual briefing plus validated AI interpretations"

        except RateLimitError as exc:
            code = getattr(exc, "code", "")
            detail = (
                "OpenAI API project has exhausted credit/quota; add API credit or check project limits."
                if code in {"credit_balance_exhausted", "insufficient_quota"}
                else "OpenAI API rate limit reached; wait and try again."
            )
            raise HTTPException(503, detail + " Evaluation and rules-based briefing remain available.") from exc
        except Exception as exc:
            # Never return secrets/provider response bodies; preserve the evaluation.
            raise HTTPException(
                502, f"AI generation unavailable or failed validation ({type(exc).__name__}); evaluation and briefing remain available."
            ) from exc
    memo = persist_memo(db, run, payload, request.kind, metadata)
    db.commit()
    return memo_response(memo, db)
