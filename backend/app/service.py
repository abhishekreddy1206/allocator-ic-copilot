"""Small orchestration boundary: database inputs → pure computations → immutable run."""

import hashlib
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.models import (
    Fund,
    MonthlyReturn,
    BenchmarkReturn,
    FactorReturn,
    MacroObservation,
    Mandate,
    Run,
    MetricSnapshot,
    Evaluation,
    FactorExposure,
    Upload,
    DataQualityIssue,
    uid,
)
from app.providers import market_bundle
from app.analytics import compute_metrics, factor_regression, chart_series, regime_metrics
from app.mandates import MandateInput, PROFILES, rank_funds, decision_diff
from app.evidence import fund_evidence, add_evidence
from app.ingestion import ingest_csv
from app.demo import demo_csv


def store_market(session: Session, live: bool = False) -> dict:
    bundle = market_bundle(live)
    for model, key, field in [(BenchmarkReturn, "benchmarks", "symbol"), (FactorReturn, "factors", "factor"), (MacroObservation, "macro", "series_id")]:
        # The run's evidence snapshots all values and lineage before future refreshes.
        session.execute(delete(model))
        for identifier, series in bundle[key].items():
            for period, value in series.values.items():
                session.add(
                    model(
                        **{
                            field: identifier,
                            "period": str(period),
                            "value" if model == MacroObservation else "return_value": float(value),
                            "lineage": series.lineage,
                        }
                    )
                )
    session.flush()
    return {k: {s: v.lineage for s, v in b.items()} for k, b in bundle.items()}


def seed_demo(session: Session) -> dict:
    summary = ingest_csv(session, "synthetic_managers.csv", demo_csv())
    if not session.scalar(select(BenchmarkReturn.id).limit(1)):
        store_market(session)
    session.flush()
    return summary


def evaluate(session: Session, mandate: MandateInput, previous_run_id: str | None = None) -> Run:
    sources = {}
    series = {"benchmarks": {}, "factors": {}, "macro": {}}
    market_rows = []
    for model, group, name, value in [
        (BenchmarkReturn, "benchmarks", "symbol", "return_value"),
        (FactorReturn, "factors", "factor", "return_value"),
        (MacroObservation, "macro", "series_id", "value"),
    ]:
        records = session.scalars(select(model).order_by(model.period)).all()
        for r in records:
            identifier = getattr(r, name)
            series[group].setdefault(identifier, {})[r.period] = getattr(r, value)
            sources[f"{group}:{identifier}"] = r.lineage
            market_rows.append((group, identifier, r))
    if mandate.benchmark not in series["benchmarks"]:
        raise ValueError("Selected benchmark unavailable. Load demo data or refresh sources.")
    ss = {g: {k: pd.Series(v, dtype=float).sort_index() for k, v in data.items()} for g, data in series.items()}
    rf = ss["macro"].get("TB3MS", pd.Series(dtype=float)) / 1200
    factors = pd.DataFrame(ss["factors"])
    returns = session.scalars(select(MonthlyReturn).order_by(MonthlyReturn.period)).all()
    by_fund = {}
    for r in returns:
        by_fund.setdefault(r.fund_id, []).append(r)
    uploads = {u.id: u for u in session.scalars(select(Upload))}
    dq_counts = {}
    for issue in session.scalars(select(DataQualityIssue)):
        if issue.fund_id:
            dq_counts[issue.fund_id] = dq_counts.get(issue.fund_id, 0) + 1
    raw_funds = []
    demo_hash = hashlib.sha256(demo_csv().encode()).hexdigest()
    for f in session.scalars(select(Fund).order_by(Fund.id)):
        obs = by_fund.get(f.id, [])
        if not obs:
            continue
        r = pd.Series({x.period: x.return_value for x in obs}, dtype=float).sort_index()
        m = compute_metrics(r, ss["benchmarks"][mandate.benchmark], rf)
        factor = factor_regression(r, factors, rf)
        m.update(factor_r_squared=factor["r_squared"], factor_alpha=factor["alpha"])
        fund = {
            c: getattr(f, c)
            for c in [
                "id",
                "canonical_name",
                "manager_name",
                "strategy",
                "liquidity",
                "management_fee",
                "performance_fee",
                "qualitative_notes",
                "source_file",
                "source_row",
            ]
        }
        fund.update(
            metrics=m,
            factors=factor,
            charts=chart_series(r, ss["benchmarks"][mandate.benchmark]),
            regimes=regime_metrics(
                r,
                ss["benchmarks"].get("SPY", pd.Series(dtype=float)),
                ss["macro"].get("VIXCLS", pd.Series(dtype=float)),
                ss["macro"].get("DGS10", pd.Series(dtype=float)),
            ),
            diversification={s: compute_metrics(r, b, rf)["benchmark_correlation"] for s, b in ss["benchmarks"].items()},
            data_quality_flags=dq_counts.get(f.id, 0),
            synthetic=uploads[f.source_file].sha256 == demo_hash,
        )
        raw_funds.append(fund)
    params = mandate.model_dump()
    mand = Mandate(id=uid(), name=mandate.name, parameters=params)
    session.add(mand)
    session.flush()
    run = Run(id=uid(), mandate_id=mand.id, result={})
    session.add(run)
    session.flush()
    statuses = {v["live_or_cached"] for v in sources.values()}
    market_status = "LIVE" if statuses == {"live"} else "CACHED DEMO DATA" if statuses == {"cached"} else "MIXED LIVE / CACHED DEMO DATA"
    ranked = rank_funds(raw_funds, mandate)
    market_refs = {"benchmarks": {}, "macro": {}, "factors": {}}
    for group, identifier, row in market_rows:
        eid = add_evidence(
            session,
            run.id,
            f"{group.upper()}-{identifier}-{row.period}",
            "benchmark_observation" if group == "benchmarks" else "macro_observation" if group == "macro" else "factor_observation",
            f"{identifier} · {row.period}",
            getattr(row, "return_value", getattr(row, "value", None)),
            "annual percent" if identifier in ["TB3MS", "DGS10"] else "index level" if identifier == "VIXCLS" else "decimal fraction",
            row.lineage["provider"],
            identifier,
            row.period,
            row.lineage["transformation"],
            {**row.lineage, "database_observation_id": row.id},
            row.lineage["live_or_cached"],
        )
        market_refs[group].setdefault(identifier, []).append(eid)
    mandate_ref = add_evidence(
        session,
        run.id,
        "MANDATE",
        "mandate",
        mandate.name,
        params,
        "configuration",
        "User-defined mandate",
        mand.id,
        "Evaluation time",
        "Hard gates first; bounded fixed-scale scores; explicit profile weights. Subjective decision aid.",
        {"weights": mandate.weights or PROFILES[mandate.profile], "market_status": market_status},
        "source",
    )
    for f in ranked:
        obs = by_fund[f["id"]]
        prov = {
            "return_sources": [
                {
                    "id": x.id,
                    "upload_id": x.source_file,
                    "source_row": x.source_row,
                    "period": x.period,
                    "return_value": x.return_value,
                    "normalization": x.normalization_metadata,
                }
                for x in obs
            ],
            "benchmark": mandate.benchmark,
            "benchmark_evidence_ids": market_refs["benchmarks"][mandate.benchmark],
            "macro_evidence_ids": market_refs["macro"],
            "all_benchmark_evidence_ids": market_refs["benchmarks"],
            "risk_free_series": "TB3MS / 1200",
            "risk_free_evidence_ids": market_refs["macro"].get("TB3MS", []),
            "factor_evidence_ids": market_refs["factors"],
            "source_status": sources,
        }
        refs = fund_evidence(session, run.id, f, prov, market_status)
        f["evidence_ids"] = refs
        f["decision_evidence"] = add_evidence(
            session,
            run.id,
            f"DECISION-{f['id']}",
            "validation_result",
            f"{f['canonical_name']} · mandate decision",
            {k: f[k] for k in ["eligible", "rank", "failed_constraints", "total_score", "component_scores", "preference_bonus"]},
            "decision",
            "Deterministic mandate / ranking engine",
            f["id"],
            f"{f['metrics']['period_start']} → {f['metrics']['period_end']}",
            "Hard constraints exclude first. Eligible-only weighted score; tie broken by canonical identifier.",
            {"mandate_evidence": mandate_ref, "metric_evidence": refs},
            "computed",
        )
        session.add(
            MetricSnapshot(
                fund_id=f["id"],
                run_id=run.id,
                evaluation_period=f"{f['metrics']['period_start']} → {f['metrics']['period_end']}",
                observation_count=f["metrics"]["observation_count"],
                metrics=f["metrics"],
                methodology={"metric_evidence": refs},
            )
        )
        session.add(
            Evaluation(
                fund_id=f["id"],
                run_id=run.id,
                mandate_id=mand.id,
                **{k: f[k] for k in ["eligible", "failed_constraints", "component_scores", "total_score", "rank"]},
            )
        )
        for name, beta in f["factors"]["betas"].items():
            session.add(
                FactorExposure(
                    fund_id=f["id"], run_id=run.id, factor_name=name, beta=beta, t_stat=f["factors"]["t_stats"][name], methodology_metadata=f["factors"]
                )
            )
    previous = session.get(Run, previous_run_id) if previous_run_id else None
    if previous_run_id and previous is None:
        raise ValueError("Previous evaluation does not exist")
    changes = decision_diff(previous.result["funds"], ranked, previous.result["mandate"], params) if previous else []
    run.result = {
        "run_id": run.id,
        "mandate": params,
        "mandate_evidence": mandate_ref,
        "weights": mandate.weights or PROFILES[mandate.profile],
        "funds": ranked,
        "changes": changes,
        "sources": sources,
        "market_status": market_status,
        "created_at": run.created_at.isoformat(),
    }
    session.flush()
    return run
