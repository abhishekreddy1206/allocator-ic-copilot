"""Network boundaries carry explicit provenance; fallback is synthetic, never live."""

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Protocol
from zipfile import ZipFile
import re
import httpx
import numpy as np
import pandas as pd

SYMBOLS = ["SPY", "QQQ", "AGG", "HYG", "IWM", "TLT", "GLD"]
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
PERIODS = pd.period_range("2021-10", "2026-09", freq="M").astype(str)


@dataclass
class MarketSeries:
    values: pd.Series
    lineage: dict


def lineage(provider: str, identifier: str, transformation: str, cached: bool = False) -> dict:
    return {
        "provider": provider,
        "identifier": identifier,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "live_or_cached": "cached" if cached else "live",
        "synthetic": cached,
        "transformation": transformation,
    }


class BenchmarkDataProvider(Protocol):
    def fetch(self, identifier: str) -> MarketSeries: ...


class RiskFreeRateProvider(Protocol):
    def fetch(self, identifier: str) -> MarketSeries: ...


class FactorDataProvider(Protocol):
    def fetch(self) -> dict[str, MarketSeries]: ...


class MacroDataProvider(Protocol):
    def fetch(self, identifier: str) -> MarketSeries: ...


class CachedDemoProvider:
    def __init__(self):
        rng = np.random.default_rng(417)
        t = np.arange(60)
        # Student-t innovations, serial cycles, and synchronized stress regimes.
        equity = 0.008 + 0.021 * np.sin(t * 0.7) + rng.standard_t(5, 60) * 0.020
        equity[[5, 8, 11, 29, 46]] = [-0.065, -0.082, -0.094, -0.071, -0.058]
        rates = 1.2 + 3.5 / (1 + np.exp(-(t - 15) / 4)) - 0.018 * np.maximum(t - 38, 0)
        duration = 0.002 - 0.013 * np.diff(rates, prepend=rates[0]) + rng.standard_t(6, 60) * 0.012
        momentum = 0.003 + 0.017 * np.sin(t * 0.45) + rng.standard_t(5, 60) * 0.013
        self.data = {
            "SPY": equity,
            "QQQ": 1.25 * equity + rng.standard_t(6, 60) * 0.01,
            "AGG": duration,
            "HYG": 0.002 + 0.30 * equity + 0.3 * duration + rng.standard_t(6, 60) * 0.005,
            "IWM": 1.12 * equity + rng.standard_t(6, 60) * 0.012,
            "TLT": 2.4 * duration,
            "GLD": 0.005 - 0.12 * equity + rng.standard_t(5, 60) * 0.024,
            "TB3MS": rates,
            "VIXCLS": 16 + 160 * np.maximum(-equity, 0) + rng.uniform(0, 4, 60),
            "DGS10": rates + 0.7 + 0.3 * np.sin(t * 0.2),
            "Mkt-RF": equity - rates / 1200,
            "Mom": momentum,
        }
        for name in ["SMB", "HML", "RMW", "CMA"]:
            self.data[name] = rng.standard_t(6, 60) * 0.012 + 0.002 * np.sin(t * 0.4)

    def fetch(self, identifier: str) -> MarketSeries:
        return MarketSeries(
            pd.Series(self.data[identifier], index=PERIODS, dtype=float),
            lineage("CachedDemoProvider", identifier, "Seed 417 synthetic regime fixture; not public historical market data", True),
        )


class YahooBenchmarkProvider:
    def fetch(self, identifier: str) -> MarketSeries:
        import yfinance as yf

        prices = yf.download(
            identifier, start="2021-09-01", end=datetime.now(timezone.utc).strftime("%Y-%m-%d"), auto_adjust=True, progress=False, timeout=12, threads=False
        )
        if prices.empty:
            raise ValueError("Yahoo returned no prices")
        close = prices["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        # Drop current incomplete month before aggregation.
        last_complete = pd.Period(datetime.now(timezone.utc).date(), freq="M") - 1
        monthly = close.groupby(close.index.to_period("M")).last()
        monthly = monthly[monthly.index <= last_complete]
        returns = monthly.pct_change(fill_method=None).dropna()
        returns.index = returns.index.astype(str)
        if returns.empty:
            raise ValueError("Yahoo returned no completed monthly returns")
        return MarketSeries(
            returns,
            lineage(
                "Yahoo / yfinance",
                identifier,
                "auto_adjust=True close; last trading close each completed month; pct_change; dividend/split-adjusted approximation",
            ),
        )


class FredMacroProvider:
    def fetch(self, identifier: str) -> MarketSeries:
        url = f"https://fred.stlouisfed.org/graph/?g=1&cosd=2021-09-01&coed={datetime.now(timezone.utc):%Y-%m-%d}&id={identifier}"
        # Public CSV endpoint needs no FRED API key.
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={identifier}&cosd=2021-09-01"
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        dates = pd.to_datetime(df.iloc[:, 0], errors="coerce")
        vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        series = pd.Series(vals.values, index=dates.dt.to_period("M")).dropna().groupby(level=0).mean()
        last_complete = pd.Period(datetime.now(timezone.utc).date(), freq="M") - 1
        series = series[series.index <= last_complete]
        series.index = series.index.astype(str)
        if series.empty:
            raise ValueError("FRED returned no usable observations")
        return MarketSeries(
            series,
            lineage(
                "FRED", identifier, "Monthly mean of available observations; TB3MS annual percent / 1200 is monthly RF proxy, not an investable total return"
            ),
        )


class FredRiskFreeRateProvider:
    def fetch(self, identifier: str = "TB3MS") -> MarketSeries:
        result = FredMacroProvider().fetch(identifier)
        result.values = result.values / 1200
        result.lineage["transformation"] = "TB3MS annual discount-basis percent / 100 / 12; monthly risk-free proxy"
        return result


class FrenchFactorProvider:
    @staticmethod
    def parse_zip(content: bytes) -> pd.DataFrame:
        with ZipFile(BytesIO(content)) as archive:
            text = archive.read(archive.namelist()[0]).decode("utf-8-sig")
        lines = text.splitlines()
        header = next(line for line in lines if re.match(r"^\s*,\s*(Mkt-RF|Mom)\b", line))
        data = [line for line in lines if re.match(r"^\s*\d{6}\s*,", line)]
        frame = pd.read_csv(StringIO(header + "\n" + "\n".join(data)), index_col=0)
        frame.columns = frame.columns.str.strip()
        frame.index = pd.to_datetime(frame.index.astype(str), format="%Y%m").to_period("M").astype(str)
        frame = frame.apply(pd.to_numeric, errors="coerce")
        frame = frame.mask(frame <= -99) / 100  # published missing-value sentinel
        return frame

    def fetch(self) -> dict[str, MarketSeries]:
        base = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        frames = []
        for filename in ["F-F_Research_Data_5_Factors_2x3_CSV.zip", "F-F_Momentum_Factor_CSV.zip"]:
            r = httpx.get(base + filename, timeout=20, follow_redirects=True)
            r.raise_for_status()
            frames.append(self.parse_zip(r.content))
        frame = frames[0].join(frames[1], how="inner")
        frame = frame.loc[frame.index >= "2021-10"]
        if frame.empty:
            raise ValueError("No French factor overlap")
        return {
            name: MarketSeries(
                frame[name].dropna(),
                lineage("Kenneth French Data Library", name, "Monthly published percent / 100; FF five factors plus momentum, explanatory analysis"),
            )
            for name in FACTORS
        }


def with_fallback(provider: BenchmarkDataProvider | MacroDataProvider, identifier: str, cached: CachedDemoProvider) -> MarketSeries:
    try:
        result = provider.fetch(identifier)
        if result.values.empty or not np.isfinite(result.values).all():
            raise ValueError("Provider returned invalid observations")
        return result
    except Exception as exc:
        result = cached.fetch(identifier)
        result.lineage["fallback_reason"] = type(exc).__name__
        return result


def market_bundle(live: bool = False) -> dict[str, dict[str, MarketSeries]]:
    cached = CachedDemoProvider()
    benchmarks = {s: with_fallback(YahooBenchmarkProvider(), s, cached) if live else cached.fetch(s) for s in SYMBOLS}
    macro = {s: with_fallback(FredMacroProvider(), s, cached) if live else cached.fetch(s) for s in ["TB3MS", "VIXCLS", "DGS10"]}
    factors = {s: cached.fetch(s) for s in FACTORS}
    if live:
        try:
            factors = FrenchFactorProvider().fetch()
        except Exception as exc:
            for value in factors.values():
                value.lineage["fallback_reason"] = type(exc).__name__
    return {"benchmarks": benchmarks, "macro": macro, "factors": factors}
