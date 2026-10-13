"""Descriptive market context from an evaluation's saved monthly observations."""

import numpy as np
import pandas as pd
from app.analytics import contiguous, finite


def market_context(benchmark: str, observations: list[dict]) -> dict:
    benchmark_rows = sorted(
        [r for r in observations if r["type"] == "benchmark_observation" and r["identifier"] == benchmark],
        key=lambda r: r["period"],
    )
    returns = pd.Series({r["period"]: r["value"] for r in benchmark_rows}, dtype=float).sort_index()

    def window(months):
        if returns.empty:
            return returns
        end = pd.Period(returns.index[-1], freq="M")
        start = str(end - (months - 1))
        return returns.loc[start:str(end)]

    def valid(series):
        return not series.empty and contiguous(series) and bool(np.isfinite(series).all()) and bool((series >= -1).all())

    summaries = {}
    for months in (3, 12):
        values = window(months)
        complete = len(values) == months and valid(values)
        summaries[f"return_{months}m"] = finite((1 + values).prod() - 1) if complete else None
        if months == 12:
            summaries["volatility_12m"] = finite(values.std(ddof=1) * np.sqrt(12)) if complete else None

    chart_values = window(12)
    chart = []
    if valid(chart_values):
        chart.append({"period": str(pd.Period(chart_values.index[0], freq="M") - 1), "index": 100.0})
        chart.extend({"period": period, "index": finite(value)} for period, value in ((1 + chart_values).cumprod() * 100).items())

    indicators = []
    for identifier, title, unit in (
        ("VIXCLS", "VIX monthly average", "index points"),
        ("DGS10", "10-year Treasury monthly average", "% yield"),
        ("TB3MS", "3-month Treasury bill yield", "% yield"),
    ):
        rows = sorted([r for r in observations if r["type"] == "macro_observation" and r["identifier"] == identifier], key=lambda r: r["period"])
        latest = rows[-1] if rows else None
        previous = rows[-2] if len(rows) > 1 and pd.Period(rows[-1]["period"], freq="M") - 1 == pd.Period(rows[-2]["period"], freq="M") else None
        indicators.append({
            "identifier": identifier, "title": title, "unit": unit,
            "value": finite(latest["value"]) if latest else None,
            "period": latest["period"] if latest else None,
            "change": finite(latest["value"] - previous["value"]) if latest and previous else None,
            "source": latest["source"] if latest else None,
            "status": latest["status"] if latest else None,
            "evidence_id": latest["id"] if latest else None,
            "previous_evidence_id": previous["id"] if previous else None,
        })
    chart_start = chart_values.index[0] if not chart_values.empty else ""
    recent_rows = [r for r in benchmark_rows if r["period"] >= chart_start]
    statuses = {r["status"] for r in recent_rows}
    status = "LIVE" if statuses == {"live"} else "CACHED DEMO DATA" if statuses == {"cached"} else "MIXED DATA" if statuses else "UNAVAILABLE"
    return {
        "benchmark": benchmark, "period": returns.index[-1] if not returns.empty else None,
        "status": status, "chart": chart, "metrics": summaries, "indicators": indicators,
        "observations": [{**row, "value": finite(row["value"])} for row in recent_rows],
        "methodology": "Growth of 100 compounds monthly benchmark returns, including a starting value of 100. Period returns require all 3 or 12 consecutive months ending at the latest benchmark observation. Volatility uses 12 consecutive monthly returns, sample standard deviation × sqrt(12). Missing or invalid inputs are not filled. Macro changes compare consecutive monthly observations; yield changes are percentage points. Dates and source status apply to each series separately.",
    }
