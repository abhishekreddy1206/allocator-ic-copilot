"""CSV → schema mapping → explicit normalization → quarantine → persistence."""

import csv
import hashlib
from io import StringIO
import re
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Upload, Fund, MonthlyReturn, DataQualityIssue, uid

STRATEGIES = {
    "global macro": "Global Macro",
    "macro": "Global Macro",
    "cta": "CTA / Managed Futures",
    "managed futures": "CTA / Managed Futures",
    "cta / managed futures": "CTA / Managed Futures",
    "equity l/s": "Equity Long/Short",
    "equity long/short": "Equity Long/Short",
    "relative value": "Relative Value",
    "rv": "Relative Value",
    "credit": "Credit",
    "multi-strategy": "Multi-Strategy",
    "multi strategy": "Multi-Strategy",
    "event driven": "Event Driven",
    "event-driven": "Event Driven",
    "market neutral": "Market Neutral",
    "market-neutral": "Market Neutral",
}
ALIASES = {
    "fund_identifier": "fund_id",
    "identifier": "fund_id",
    "fund": "fund_name",
    "name": "fund_name",
    "manager": "manager_name",
    "date": "period",
    "month": "period",
    "return": "monthly_return",
    "monthly_returns": "monthly_return",
    "notes": "qualitative_notes",
    "management_fee_pct": "management_fee",
    "performance_fee_pct": "performance_fee",
}


def identifier(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def name_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def number(value: str, fee: bool = False) -> tuple[float | None, str | None]:
    if not value.strip():
        return None, None
    text = value.strip().replace(",", "")
    percent = text.endswith("%")
    val = float(text.rstrip("%"))
    if not (-float("inf") < val < float("inf")):
        raise ValueError("Non-finite numeric value")
    action = "percent string divided by 100" if percent else None
    if percent:
        val /= 100
    elif fee and val >= 1:
        val /= 100
        action = "fee percentage points divided by 100 (explicit fee-field convention)"
    elif not fee and abs(val) >= 1:
        raise ValueError("Ambiguous bare return >= 1; provide explicit % or decimal")
    if fee and not 0 <= val <= 1:
        raise ValueError("Fee must be between 0 and 100%")
    if not fee and val <= -1:
        raise ValueError("Monthly return must exceed -100%")
    if not fee and val > 10:
        raise ValueError("Return above 1000% requires source/unit review; quarantined")
    return val, action


def month(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"\d{4}[-/]\d{2}([-/]\d{2})?", value):
        raise ValueError("Use unambiguous YYYY-MM or YYYY-MM-DD dates")
    date = pd.to_datetime(value.replace("/", "-"), errors="raise")
    return str(date.to_period("M"))


def ingest_csv(session: Session, filename: str, content: str, identity_context: str = "") -> dict:
    digest = hashlib.sha256((content + identity_context).encode()).hexdigest()
    previous = session.scalar(select(Upload).where(Upload.sha256 == digest))
    if previous:
        return {**previous.summary, "already_imported": True, "upload_id": previous.id}
    reader = csv.DictReader(StringIO(content.lstrip("\ufeff")))
    if not reader.fieldnames or len(reader.fieldnames) > 60:
        raise ValueError("CSV header required; at most 60 columns")
    mapping = {h: ALIASES.get(re.sub(r"\s+", "_", h.strip().lower()), re.sub(r"\s+", "_", h.strip().lower())) for h in reader.fieldnames}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Columns map to conflicting canonical names")
    required = {"fund_id", "fund_name", "strategy", "liquidity", "period", "monthly_return"}
    if missing := required - set(mapping.values()):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    upload = Upload(id=uid(), filename=filename[:200], sha256=digest, raw_csv=content, summary={})
    session.add(upload)
    session.flush()
    count, valid, warnings, errors, actions = 0, 0, 0, 0, 0
    affected = set()
    existing = {f.id: f for f in session.scalars(select(Fund))}
    touched = set()
    seen = {(r.fund_id, r.period): r.return_value for r in session.scalars(select(MonthlyReturn))}

    def issue(kind: str, description: str, row: int | None, fund_id: str | None, severity: str = "warning", resolution: str | None = None):
        nonlocal warnings, errors, actions
        if severity == "error":
            errors += 1
        elif severity == "info":
            actions += 1
        else:
            warnings += 1
        if fund_id:
            affected.add(fund_id)
        session.add(
            DataQualityIssue(
                severity=severity,
                issue_type=kind,
                fund_id=fund_id,
                source_file=upload.id,
                source_row=row,
                description=description,
                inferred_resolution=resolution,
                status="resolved" if resolution else "open",
            )
        )

    for source_row, raw in enumerate(reader, 2):
        count += 1
        if count > 50000:
            raise ValueError("Upload exceeds 50,000 rows")
        if None in raw or any(v is None for v in raw.values()):
            issue("malformed_row", "Row column count differs from header", source_row, None, "error")
            continue
        row = {mapping[k]: v.strip() for k, v in raw.items()}
        fid = identifier(row["fund_id"])
        linked = fid if fid in existing else None
        try:
            if not fid or len(fid) > 80 or not row["fund_name"]:
                raise ValueError("Fund identifier and name are required")
            strategy = STRATEGIES.get(row["strategy"].lower())
            if not strategy:
                raise ValueError("Unknown strategy; review mapping")
            liq = row["liquidity"].lower().replace(" ", "")
            liq = {"month": "monthly", "quarter": "quarterly", "yearly": "annual", "annual": "annual", "illiquid": "locked"}.get(liq, liq)
            if liq not in {"daily", "monthly", "quarterly", "annual", "locked"}:
                raise ValueError("Unknown liquidity; cannot infer redemption terms")
            period = month(row["period"])
            if pd.Period(period, freq="M") >= pd.Period(pd.Timestamp.now(tz="UTC").date(), freq="M"):
                raise ValueError("Future or incomplete monthly observation")
            value, unit_action = number(row["monthly_return"])
            if value is None:
                raise ValueError("Missing monthly return; not imputed")
            management, ma = number(row.get("management_fee", ""), fee=True)
            performance, pa = number(row.get("performance_fee", ""), fee=True)
            manager = row.get("manager_name", "").strip()
            notes = row.get("qualitative_notes", "")[:5000]
            if fid in existing:
                f = existing[fid]
                if name_key(row["fund_name"]) != name_key(f.canonical_name) or (manager and name_key(manager) != name_key(f.manager_name)):
                    issue("identifier_conflict", f"Identifier {fid} conflicts with existing fund/manager identity; row quarantined", source_row, fid, "error")
                    continue
                if (
                    strategy != f.strategy
                    or liq != f.liquidity
                    or (management is not None and management != f.management_fee)
                    or (performance is not None and performance != f.performance_fee)
                    or (notes and notes != f.qualitative_notes)
                ):
                    issue("metadata_conflict", "Conflicting strategy/liquidity/fee/note under one identifier; row quarantined", source_row, fid, "error")
                    continue
                if row["fund_name"] != f.canonical_name:
                    issue(
                        "name_variant",
                        f"Name '{row['fund_name']}' mapped to '{f.canonical_name}'",
                        source_row,
                        fid,
                        "info",
                        "Case/punctuation-insensitive name match under exact normalized identifier",
                    )
            else:
                f = Fund(
                    id=fid,
                    external_identifier=fid,
                    canonical_name=" ".join(row["fund_name"].split()),
                    manager_name=manager or "Not supplied",
                    strategy=strategy,
                    liquidity=liq,
                    management_fee=management,
                    performance_fee=performance,
                    qualitative_notes=notes,
                    source_file=upload.id,
                    source_row=source_row,
                )
                session.add(f)
                session.flush()
                existing[fid] = f
                linked = fid
                if not manager or management is None or performance is None:
                    issue("missing_optional", "Optional manager/fee fields absent; no values inferred", source_row, fid)
            linked = fid
            changes = {}
            for field, normalized in [("fund_id", fid), ("strategy", strategy), ("liquidity", liq), ("period", period)]:
                original = raw[next(k for k, v in mapping.items() if v == field)]
                if original != normalized:
                    changes[field] = {"raw": original, "normalized": normalized}
            for field, action, val in [("monthly_return", unit_action, value), ("management_fee", ma, management), ("performance_fee", pa, performance)]:
                if action:
                    changes[field] = {"raw": row.get(field), "normalized": val, "action": action}
            if changes:
                issue("normalization", str(changes), source_row, fid, "info", "Applied explicit field conventions; original raw CSV retained")
            key = (fid, period)
            if key in seen:
                identical = abs(seen[key] - value) < 1e-12
                issue(
                    "duplicate_observation" if identical else "conflicting_observation",
                    f"{fid} {period}: " + ("identical duplicate excluded" if identical else "conflicting return quarantined; existing observation retained"),
                    source_row,
                    fid,
                    "warning" if identical else "error",
                    "Kept first identical observation" if identical else None,
                )
                continue
            if abs(value) > 0.25:
                issue("extreme_return", f"{value:.1%} monthly return; retained, requires source verification", source_row, fid)
            session.add(
                MonthlyReturn(
                    fund_id=fid,
                    period=period,
                    return_value=value,
                    source_file=upload.id,
                    source_row=source_row,
                    normalization_metadata={"changes": changes, "raw_return": row["monthly_return"]},
                )
            )
            seen[key] = value
            valid += 1
            touched.add(fid)
        except (ValueError, TypeError, OverflowError) as exc:
            issue("invalid_row", str(exc), source_row, linked, "error")
    for fid in sorted(touched):
        periods = sorted(p for f, p in seen if f == fid)
        missing = sorted(set(pd.period_range(periods[0], periods[-1], freq="M").astype(str)) - set(periods))
        if missing:
            issue("missing_month", "Missing months: " + ", ".join(missing), None, fid)
        if len(periods) < 36:
            issue("insufficient_history", f"{len(periods)} months; default mandate requires 36", None, fid)
    if touched:
        ranges = {(min(p for f, p in seen if f == fid), max(p for f, p in seen if f == fid)) for fid in touched}
        if len(ranges) > 1:
            issue("inconsistent_ranges", "Funds have different observation ranges; analytics use exact-month alignment", None, None)
    summary = {
        "total_rows": count,
        "valid_rows": valid,
        "rejected_rows": count - valid,
        "warnings": warnings,
        "errors": errors,
        "normalization_actions": actions,
        "funds_affected": len(affected),
        "filename": filename,
        "upload_id": upload.id,
    }
    upload.summary = summary
    session.flush()
    return summary
