"""
Data acquisition helpers for daily OHLCV prices and market regime proxies.

The functions use yfinance for convenience. They return tidy DataFrames
indexed by date/ticker so downstream feature code can stay simple.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Literal, Sequence

import numpy as np
import pandas as pd
import yfinance as yf

PriceFrame = pd.DataFrame
FillMethod = Literal["ffill", "bfill", "drop", None]


def _normalize_tickers(tickers: Iterable[str] | str) -> list[str]:
    if isinstance(tickers, str):
        tickers = [tickers]
    return sorted({t.strip().upper() for t in tickers if t})


def _stack_by_ticker(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Stack a yfinance MultiIndex column frame into rows keyed by ticker.

    yfinance can return columns shaped as (ticker, field) or (field, ticker)
    depending on the `group_by` parameter. This normalizes to (ticker, field)
    and stacks tickers into the index.
    """
    known_fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    if not isinstance(raw.columns, pd.MultiIndex):
        raise TypeError("Expected MultiIndex columns.")

    level0 = set(map(str, raw.columns.get_level_values(0)))
    if level0 & known_fields:
        raw = raw.swaplevel(0, 1, axis=1)

    raw = raw.sort_index(axis=1)
    try:
        return raw.stack(level=0, future_stack=True)
    except TypeError:
        return raw.stack(level=0)


def _tidy_from_yfinance(raw: pd.DataFrame, tickers: Sequence[str]) -> PriceFrame:
    """Convert yfinance output to tidy (date, ticker) indexed frame."""
    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"])

    if isinstance(raw.columns, pd.MultiIndex):
        df = _stack_by_ticker(raw).rename_axis(index=["date", "ticker"]).reset_index()
    else:
        df = raw.rename_axis(index="date").reset_index()
        df["ticker"] = tickers[0] if tickers else ""

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename_map)

    # If adj_close missing, fall back to close.
    if "adj_close" not in df:
        df["adj_close"] = df.get("close")

    wanted = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    for col in wanted:
        if col not in df:
            df[col] = pd.NA

    df["date"] = pd.to_datetime(df["date"])
    df = df[wanted].sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


def download_ohlcv(
    tickers: Iterable[str] | str,
    start: str | datetime,
    end: str | datetime,
    interval: str = "1d",
    auto_adjust: bool = True,
) -> PriceFrame:
    """
    Download OHLCV data for the given tickers from yfinance.

    Returns a tidy DataFrame with columns:
    date, ticker, open, high, low, close, adj_close, volume
    """
    tickers_list = _normalize_tickers(tickers)
    raw = yf.download(
        tickers_list,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    return _tidy_from_yfinance(raw, tickers_list)


def download_vix(
    start: str | datetime,
    end: str | datetime,
    symbol: str = "^VIX",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch VIX (or alternate) levels for the date range."""
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=True,
        group_by="ticker",
    )
    tidy = _tidy_from_yfinance(raw, [symbol])
    tidy = tidy.rename(columns={"close": "vix_close", "adj_close": "vix_adj_close"})
    tidy = tidy.rename(columns={"volume": "vix_volume"})
    return tidy[["date", "vix_close", "vix_adj_close", "vix_volume"]]


def merge_market_regime(prices: PriceFrame, vix: pd.DataFrame) -> PriceFrame:
    """
    Merge VIX levels into the per-ticker price frame on date.

    The VIX series is forward filled to align with equity trading days.
    """
    if vix.empty:
        return prices.copy()
    vix_sorted = vix.sort_values("date").drop_duplicates(subset=["date"], keep="last").set_index("date")
    vix_sorted = vix_sorted.reindex(prices["date"].sort_values().unique()).ffill().reset_index()
    merged = prices.merge(vix_sorted, how="left", left_on="date", right_on="date")
    return merged


def clean_prices(prices: PriceFrame) -> PriceFrame:
    """
    Basic cleaning: drop bad rows, deduplicate, sort.
    """
    df = prices.copy()
    df = df.dropna(subset=["date", "ticker"])
    df = df.drop_duplicates(subset=["date", "ticker"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


def _adjustment_factor(prices: PriceFrame) -> pd.Series:
    """Compute adjustment factor from adj_close/close, forward/back-filling per ticker."""
    ratio = (prices["adj_close"].astype(float) / prices["close"].astype(float)).replace([np.inf, -np.inf], np.nan)
    ratio = ratio.groupby(prices["ticker"], group_keys=False).apply(lambda s: s.ffill().bfill())
    ratio = ratio.fillna(1.0)
    return ratio


def adjust_ohlcv(prices: PriceFrame) -> PriceFrame:
    """
    Adjust open/high/low/close using the adj_close ratio (splits/dividends).

    Safe to call even if data already adjusted (ratio will be ~1).
    """
    df = clean_prices(prices)
    if "adj_close" not in df or "close" not in df:
        return df
    factor = _adjustment_factor(df)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float) * factor
    df["adj_close"] = df["close"]
    return df


def align_and_fill(prices: PriceFrame, method: FillMethod = "ffill", limit: int | None = None) -> PriceFrame:
    """
    Align tickers to a common date calendar and handle missing values.

    method:
      - "ffill": forward-fill within each ticker
      - "bfill": back-fill within each ticker
      - "drop": drop rows with missing numeric values
      - None: leave missing as-is
    """
    df = clean_prices(prices)
    if df.empty:
        return df
    all_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="B")
    frames = []
    for ticker, g in df.groupby("ticker"):
        g = g.set_index("date").reindex(all_dates)
        g["ticker"] = ticker
        if method == "drop":
            g = g.dropna()
        elif method in {"ffill", "bfill"}:
            g = g.ffill(limit=limit) if method == "ffill" else g.bfill(limit=limit)
        g = g.reset_index().rename(columns={"index": "date"})
        frames.append(g)
    aligned = pd.concat(frames, axis=0).sort_values(["ticker", "date"]).reset_index(drop=True)
    return aligned


def load_prices(
    tickers: Iterable[str] | str,
    start: str | datetime,
    end: str | datetime,
    interval: str = "1d",
    fill_method: FillMethod = "ffill",
    fill_limit: int | None = None,
    auto_adjust: bool = True,
    adjust_manually: bool = False,
) -> PriceFrame:
    """
    Fetch, clean, align, and fill missing values for multiple tickers.

    By default, yfinance auto_adjust is used; set adjust_manually=True to adjust
    OHLC using adj_close after download (useful when auto_adjust=False).
    """
    raw = download_ohlcv(tickers, start=start, end=end, interval=interval, auto_adjust=auto_adjust)
    clean = clean_prices(raw)
    adjusted = adjust_ohlcv(clean) if adjust_manually else clean
    aligned = align_and_fill(adjusted, method=fill_method, limit=fill_limit)
    return aligned
