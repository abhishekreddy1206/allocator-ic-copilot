"""Evaluation-scoped immutable evidence constructors and deterministic briefing."""

from app.analytics import METHODS
from app.models import Evidence, Memo, MemoClaim, uid
from sqlalchemy.orm import Session


def evidence_key(run_id: str, fund_id: str, metric: str) -> str:
    return f"{run_id}:METRIC-{fund_id}-{metric.upper()}"


def add_evidence(
    session: Session,
    run_id: str,
    key: str,
    type_: str,
    label: str,
    value,
    unit: str,
    source: str,
    identifier: str,
    period: str,
    methodology: str,
    provenance: dict,
    status: str,
) -> str:
    eid = f"{run_id}:{key}"
    session.add(
        Evidence(
            id=eid,
            run_id=run_id,
            type=type_,
            label=label,
            value={"value": value},
            unit=unit,
            source=source,
            source_identifier=identifier,
            observation_period=period,
            methodology=methodology,
            provenance=provenance,
            live_or_cached=status,
        )
    )
    return eid


def fund_evidence(session: Session, run_id: str, fund: dict, provenance: dict, status: str) -> dict[str, str]:
    refs = {}
    m = fund["metrics"]
    period = f"{m['period_start']} → {m['period_end']}"
    percent = {
        "annualized_return",
        "cumulative_return",
        "annualized_volatility",
        "maximum_drawdown",
        "alpha",
        "excess_return",
        "tracking_error",
        "best_month",
        "worst_month",
        "positive_month_pct",
        "factor_alpha",
    }
    for metric, methodology in METHODS.items():
        if metric not in m:
            continue
        refs[metric] = add_evidence(
            session,
            run_id,
            f"METRIC-{fund['id']}-{metric.upper()}",
            "computed_metric",
            f"{fund['canonical_name']} · {metric.replace('_', ' ')}",
            m[metric],
            "decimal fraction" if metric in percent else "capture percent" if "capture" in metric else "ratio",
            "Deterministic Python analytics",
            fund["id"],
            period,
            methodology,
            {
                **provenance,
                "observation_count": m["observation_count"],
                "benchmark_observation_count": m["benchmark_observation_count"],
                "risk_free_observation_count": m["risk_free_observation_count"],
                "contiguous": m["contiguous"],
            },
            status,
        )
    for field in ["liquidity", "strategy", "management_fee", "performance_fee", "qualitative_notes"]:
        refs[field] = add_evidence(
            session,
            run_id,
            f"SOURCE-{fund['id']}-{field.upper()}",
            "qualitative_note" if field == "qualitative_notes" else "source_field",
            f"{fund['canonical_name']} · {field.replace('_', ' ')}",
            fund[field],
            "decimal fraction" if "fee" in field else "text",
            "Uploaded CSV",
            fund["source_file"],
            period,
            "Canonical source field; no qualitative verification performed.",
            {"source_row": fund["source_row"], "upload_id": fund["source_file"], "synthetic": fund["synthetic"]},
            "source",
        )
    for name, beta in fund["factors"]["betas"].items():
        refs[f"factor_{name}"] = add_evidence(
            session,
            run_id,
            f"FACTOR-{fund['id']}-{name}",
            "factor_estimate",
            f"{fund['canonical_name']} · {name} beta",
            beta,
            "beta",
            "NumPy OLS",
            name,
            fund["factors"]["period"],
            "Fund excess returns regressed on FF5 + momentum; classical t statistics, not robust/HAC.",
            {**provenance, "regression": fund["factors"]},
            status,
        )
    for name, item in fund["regimes"].items():
        refs[f"regime_{name}"] = add_evidence(
            session,
            run_id,
            f"REGIME-{fund['id']}-{name}",
            "computed_metric",
            f"{fund['canonical_name']} · {name}",
            item["average_return"],
            "decimal fraction",
            "Deterministic regime filter",
            name,
            period,
            "Arithmetic mean in exact overlapping months: equity-down SPY<0; high VIX>=25; rates rising/falling by DGS10 monthly change.",
            {**provenance, **item},
            status,
        )
    for symbol, correlation in fund["diversification"].items():
        refs[f"diversification_{symbol}"] = add_evidence(
            session,
            run_id,
            f"CORRELATION-{fund['id']}-{symbol}",
            "computed_metric",
            f"{fund['canonical_name']} · {symbol} correlation",
            correlation,
            "ratio",
            "Deterministic exact-month correlation",
            symbol,
            period,
            METHODS["benchmark_correlation"],
            {**provenance, "benchmark": symbol, "benchmark_evidence_ids": provenance["all_benchmark_evidence_ids"].get(symbol, [])},
            status,
        )
    return refs


def briefing_sections(result: dict) -> dict:
    """A truthful no-key artifact, explicitly rules-based. Never masquerades as AI."""
    eligible = [f for f in result["funds"] if f["eligible"]][:5]
    sections = []
    if not eligible:
        return {
            "sections": [
                {
                    "title": "Recommendation",
                    "claims": [
                        {
                            "text": "No manager meets all hard constraints. Resolve data gaps or revise the mandate before shortlisting.",
                            "claim_type": "decision",
                            "confidence": "deterministic",
                            "evidence_ids": [result["mandate_evidence"]],
                        }
                    ],
                }
            ]
        }
    top = eligible[0]
    refs = top["evidence_ids"]

    def claim(text, ids, kind="fact"):
        return {"text": text, "claim_type": kind, "confidence": "deterministic" if kind != "diligence" else "question", "evidence_ids": ids}

    sections.append(
        {
            "title": "Executive Summary",
            "claims": [
                claim(
                    f"{top['canonical_name']} ranks first under the current transparent decision methodology. This is a diligence shortlist, not an allocation recommendation.",
                    [top["decision_evidence"]],
                )
            ],
        }
    )
    sections.append(
        {
            "title": "Mandate",
            "claims": [
                claim(
                    f"{result['mandate']['profile']} sleeve · {result['mandate']['benchmark']} benchmark · {result['mandate']['liquidity_requirement']} liquidity · minimum {result['mandate']['minimum_track_record_months']} months.",
                    [result["mandate_evidence"]],
                )
            ],
        }
    )
    sections.append(
        {
            "title": "Recommendation",
            "claims": [
                claim(
                    f"Advance {top['canonical_name']} for manager diligence under the current mandate; validate source concerns before any allocation.",
                    [top["decision_evidence"], refs["qualitative_notes"]],
                    "decision",
                )
            ],
        }
    )
    sections.append(
        {
            "title": "Ranked Shortlist",
            "claims": [
                claim(
                    f"#{f['rank']} {f['canonical_name']} — score {f['total_score']:.1f}/100; all configured hard constraints passed.", [f["decision_evidence"]]
                )
                for f in eligible
            ],
        }
    )
    sections.append(
        {
            "title": "Investment Rationale",
            "claims": [
                claim(
                    f"Observed annualized return {top['metrics']['annualized_return']:.1%}, Sharpe {top['metrics']['sharpe_ratio']:.2f}, and maximum drawdown {top['metrics']['maximum_drawdown']:.1%}.",
                    [refs["annualized_return"], refs["sharpe_ratio"], refs["maximum_drawdown"]],
                )
            ]
            if top["metrics"]["sharpe_ratio"] is not None
            else [claim("Risk-free coverage is incomplete; Sharpe is unavailable.", [refs["sharpe_ratio"]])],
        }
    )
    factor_text = (
        "Factor R² is unavailable."
        if top["factors"]["r_squared"] is None
        else f"Explanatory factor R² is {top['factors']['r_squared']:.1%}. An unexplained residual is not proof of repeatable alpha."
    )
    sections.append(
        {
            "title": "Diversification / Factor Analysis",
            "claims": [
                claim(
                    f"Benchmark correlation is {top['metrics']['benchmark_correlation']:.2f}. {factor_text}",
                    [refs["benchmark_correlation"], refs["factor_r_squared"]],
                )
            ],
        }
    )
    sections.append({"title": "Key Risks", "claims": [claim(f"Unverified source note: {top['qualitative_notes']}", [refs["qualitative_notes"]])]})
    sections.append(
        {
            "title": "Manager-Specific Diligence Questions",
            "claims": [
                claim(
                    "Can the administrator independently verify performance, redemption terms, capacity and the concerns in the source note?",
                    [refs["qualitative_notes"], refs["liquidity"]],
                    "diligence",
                )
            ],
        }
    )
    excluded = [f for f in result["funds"] if not f["eligible"]][:3]
    sections.append(
        {
            "title": "Alternatives Considered",
            "claims": [claim(f"{f['canonical_name']}: " + " ".join(x["reason"] for x in f["failed_constraints"]), [f["decision_evidence"]]) for f in excluded],
        }
    )
    sections.append(
        {
            "title": "Data Appendix",
            "claims": [
                claim(
                    f"History {top['metrics']['period_start']} → {top['metrics']['period_end']}; {top['metrics']['observation_count']} observed months. Source status: {result['market_status']}. Manager data is synthetic only where explicitly marked.",
                    [refs["annualized_return"], result["mandate_evidence"]],
                )
            ],
        }
    )
    return {"sections": sections}


def persist_memo(session: Session, run, payload: dict, kind: str, metadata: dict) -> Memo:
    memo = Memo(
        id=uid(),
        run_id=run.id,
        mandate_id=run.mandate_id,
        kind=kind,
        recommendation=payload.get("recommended_fund_id"),
        structured_sections=payload,
        model_metadata=metadata,
    )
    session.add(memo)
    session.flush()
    for section in payload["sections"]:
        for claim in section["claims"]:
            session.add(
                MemoClaim(
                    memo_id=memo.id, text=claim["text"], claim_type=claim["claim_type"], confidence=claim["confidence"], evidence_ids=claim["evidence_ids"]
                )
            )
    return memo
