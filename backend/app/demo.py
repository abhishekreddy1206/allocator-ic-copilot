"""Structured, reproducible synthetic manager behaviors; no hardcoded analytics/ranks."""

import csv
from io import StringIO
import numpy as np
from app.providers import CachedDemoProvider, PERIODS

PERSONAS = [
    ("ATLAS", "Atlas Global Macro", "Global Macro", "quarterly", "Discretionary macro; concentrated policy trades and episodic losses."),
    (
        "MERIDIAN",
        "Meridian Systematic",
        "CTA / Managed Futures",
        "monthly",
        "Systematic trend; founder controls research and two senior researchers departed. Validate succession and IP ownership.",
    ),
    (
        "CEDAR",
        "Cedar Market Neutral",
        "Market Neutral",
        "monthly",
        "Low-return diversifier; capacity constrained. Review crowding and prime broker concentration.",
    ),
    (
        "BASTION",
        "Bastion Relative Value",
        "Relative Value",
        "annual",
        "Stable carry; annual redemptions and possible gates. Asset/liability mismatch deserves diligence.",
    ),
    ("NOVA", "Nova Emerging", "Multi-Strategy", "monthly", "New manager; limited independently verified performance history."),
    (
        "HORIZON",
        "Horizon Equity Opportunities",
        "Equity Long/Short",
        "monthly",
        "High headline returns; concentrated equity exposure may explain most performance.",
    ),
    ("HARBOR", "Harbor Defensive", "Global Macro", "monthly", "Defensive hedges reduce equity-down losses at the cost of upside participation."),
    ("SUMMIT", "Summit Carry", "Credit", "quarterly", "Steady carry in calm markets; short-volatility profile and severe stress losses."),
    ("ORION", "Orion Convex", "CTA / Managed Futures", "quarterly", "Convex trend capture; quarterly redemption schedule. Confirm live versus backtest split."),
    ("ALPINE", "Alpine Long Short", "Equity Long/Short", "monthly", "Balanced equity book; sector concentration and crowded shorts."),
    ("JUNIPER", "Juniper Credit", "Credit", "quarterly", "Structured credit; valuation lag and financing dependence."),
    ("LANTERN", "Lantern Event Driven", "Event Driven", "quarterly", "Deal spreads; litigation and failed merger tail risk."),
    ("VECTOR", "Vector Statistical", "Market Neutral", "daily", "High-turnover statistical arbitrage; transaction cost and capacity risk."),
    ("DELTA", "Delta Multi Strategy", "Multi-Strategy", "quarterly", "Diversified sleeves; leverage, centralized risk and transparency need review."),
    ("AURORA", "Aurora Macro", "Global Macro", "monthly", "Cross-asset carry and trend; one month absent from source file."),
    ("STONE", "Stonebridge Value", "Relative Value", "quarterly", "Moderate carry; historical window precedes current market fixtures."),
    ("PULSE", "Pulse Tactical", "Global Macro", "monthly", "Aggressive tactical positions; one extreme gain requires administrator confirmation."),
    ("NORTH", "Northstar Futures", "CTA / Managed Futures", "monthly", "Shorter track record; trend portfolio concentrated in commodities."),
]


def demo_csv() -> str:
    p = CachedDemoProvider()
    e, mom = p.data["SPY"], p.data["Mom"]
    rng = np.random.default_rng(91)
    # Non-Gaussian noise and strategy-specific stress/carry/nonlinear responses.
    noise = rng.standard_t(6, (18, 60)) * 0.004
    series = [
        0.010 + 0.10 * e + 0.50 * mom + noise[0],
        0.004 + 0.06 * e + 0.85 * mom + noise[1],
        0.003 + 0.02 * e + noise[2] * 0.55,
        0.006 + 0.08 * e + noise[3] * 0.5,
        0.006 + 0.25 * e + noise[4],
        0.004 + 1.45 * e + noise[5],
        0.004 + 0.06 * e - 0.25 * np.minimum(e, 0) + noise[6] * 0.6,
        0.008 + 0.04 * e + noise[7] * 0.4 - 0.095 * (e < -0.05),
        0.008 + 0.03 * e + 0.60 * mom + noise[8] * 0.8,
        0.006 + 0.48 * e + noise[9] * 1.5,
        0.006 + 0.30 * e + noise[10] - 0.045 * (e < -0.06),
        0.004 + 0.18 * e + noise[11] - 0.020 * (e < -0.07),
        0.004 - 0.02 * e + noise[12] * 0.55,
        0.006 + 0.25 * e + 0.20 * mom + noise[13],
        0.004 + 0.08 * e + 0.50 * mom + noise[14],
        0.005 + 0.12 * e + noise[15],
        0.006 + 0.1 * e + noise[16] * 2,
        0.003 + 0.08 * e + 0.60 * mom + noise[17],
    ]
    # Episodic event sequence guarantees a genuine drawdown gate transition.
    series[0][26:29] = [-0.040, -0.042, -0.016]
    series[16][33] = 0.36
    out = StringIO()
    columns = [
        "fund_id",
        "fund_name",
        "manager_name",
        "strategy",
        "liquidity",
        "management_fee",
        "performance_fee",
        "period",
        "monthly_return",
        "qualitative_notes",
    ]
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for i, (fid, name, strategy, liq, notes) in enumerate(PERSONAS):
        for j, period in enumerate(PERIODS):
            if (fid == "NOVA" and j < 42) or (fid == "NORTH" and j < 30) or (fid == "AURORA" and j == 18):
                continue
            if fid == "STONE":
                period = str(__import__("pandas").Period("2015-01", freq="M") + j)
            row = dict(
                fund_id=fid.lower() if j % 7 == 0 else fid,
                fund_name=name if j % 9 != 1 else "  " + name.upper() + "  ",
                manager_name=fid.title() + " Partners",
                strategy={"CTA / Managed Futures": "managed futures", "Equity Long/Short": "equity l/s"}.get(strategy, strategy.lower()),
                liquidity=liq.title() if j % 3 else " " + liq + " ",
                management_fee="1.5%" if j % 2 else "0.015",
                performance_fee="20" if j % 2 else "20%",
                period=period if j % 2 else period + "-01",
                monthly_return=f"{series[i][j] * 100:.6f}%" if j % 3 else f"{series[i][j]:.8f}",
                qualitative_notes="SYNTHETIC. " + notes,
            )
            if fid == "CEDAR":
                row["performance_fee"] = ""
            writer.writerow(row)
            if fid == "ATLAS" and j == 15:
                writer.writerow(row)
            if fid == "DELTA" and j == 10:
                writer.writerow({**row, "fund_name": "Unrelated Duplicate Fund"})
    writer.writerow(
        {
            "fund_id": "ATLA5",
            "fund_name": "Atlas Global Macro",
            "strategy": "macro",
            "liquidity": "quarterly",
            "period": "2024-04",
            "monthly_return": "ambiguous",
            "qualitative_notes": "Identifier typo; must not fuzzy merge.",
        }
    )
    return out.getvalue()
