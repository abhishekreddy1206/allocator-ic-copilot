"""Plain-language explanations derived only from engine results."""

LABELS = {
    "correlation": "Low benchmark correlation",
    "factor_diversification": "Low explanatory factor overlap",
    "downside_protection": "Downside protection",
    "sharpe": "Risk-adjusted performance",
    "sortino": "Downside risk-adjusted performance",
    "drawdown": "Drawdown control",
    "volatility_fit": "Volatility fit",
    "return": "Observed return",
    "consistency": "Consistency",
}


def suitability(fund, mandate):
    strengths = []
    if fund["eligible"]:
        for key, score in sorted(fund["component_scores"].items(), key=lambda item: -item[1]["contribution"])[:3]:
            strengths.append(
                dict(
                    text=f"{LABELS.get(key, key.replace('_', ' ').capitalize())} contributes {score['contribution']:.1f} points under the selected profile.",
                    evidence_ids=[fund["decision_evidence"]],
                )
            )
    concerns = [dict(text=c["reason"], evidence_ids=[fund["decision_evidence"]]) for c in fund["failed_constraints"]]
    if fund["qualitative_notes"]:
        concerns.append(dict(text="Unverified manager note: " + fund["qualitative_notes"], evidence_ids=[fund["evidence_ids"]["qualitative_notes"]]))
    missing = []
    if fund["metrics"]["sharpe_ratio"] is None:
        missing.append("Sharpe is unavailable; inspect history and risk-free coverage.")
    if fund["factors"]["r_squared"] is None:
        missing.append("Factor analysis is unavailable; inspect overlap and sample sufficiency.")
    if fund["unresolved_data_quality"]:
        missing.append(f"{fund['unresolved_data_quality']} unresolved data warnings or errors require review in Data Health.")
    return dict(
        headline=f"Passes all configured {mandate['profile']} constraints" if fund["eligible"] else "Does not meet the current mandate",
        strengths=strengths,
        concerns=concerns,
        missing_evidence=missing,
        next_step="Verify performance, redemption terms, and source concerns before an allocation."
        if fund["eligible"]
        else "Resolve the stated data issues or review the mandate. Existing observations are never overwritten.",
    )
