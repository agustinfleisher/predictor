"""
Feature engineering utilities for daily equity data.

All functions operate on tidy DataFrames with columns:
date, ticker, open, high, low, close, adj_close, volume, [optional VIX cols]
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

PriceFrame = pd.DataFrame


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def add_price_features(
    prices: PriceFrame,
    return_windows: Sequence[int] = (1, 5, 10),
    ma_windows: Sequence[int] = (5, 10, 20),
    vol_windows: Sequence[int] = (10, 20),
    rsi_period: int = 14,
    bollinger_windows: Sequence[int] = (20,),
    atr_window: int = 14,
    volume_zscore_windows: Sequence[int] = (20,),
) -> PriceFrame:
    """
    Add momentum, mean-reversion, volatility, volume, moving-average, RSI, and range features.
    """
    df = prices.sort_values(["ticker", "date"]).reset_index(drop=True)

    def by_ticker(series: pd.Series, func):
        return series.groupby(df["ticker"], group_keys=False).apply(func)

    # Momentum/returns
    for win in return_windows:
        df[f"ret_{win}d"] = by_ticker(df["adj_close"], lambda s: s.pct_change(win))
    df["ret_1d_log"] = by_ticker(df["adj_close"], lambda s: np.log(s) - np.log(s.shift(1)))

    # Moving averages and distance-to-mean (mean reversion signal)
    for win in ma_windows:
        df[f"sma_{win}"] = by_ticker(df["adj_close"], lambda s: s.rolling(win, min_periods=win).mean())
        df[f"ema_{win}"] = by_ticker(df["adj_close"], lambda s: s.ewm(span=win, adjust=False).mean())
        df[f"dist_sma_{win}"] = (df["adj_close"] - df[f"sma_{win}"]) / df[f"sma_{win}"]
        df[f"ma_crossover_{win}"] = (df["adj_close"] > df[f"sma_{win}"]).astype(int)

    # Volatility
    for win in vol_windows:
        df[f"volatility_{win}d"] = by_ticker(
            df["adj_close"].pct_change(), lambda s: s.rolling(win, min_periods=win).std()
        )
        df[f"return_z_{win}d"] = df["ret_1d_log"] / by_ticker(df["ret_1d_log"], lambda s: s.rolling(win, min_periods=win).std())

    # Bollinger-style z-scores
    for win in bollinger_windows:
        mean = by_ticker(df["adj_close"], lambda s: s.rolling(win, min_periods=win).mean())
        std = by_ticker(df["adj_close"], lambda s: s.rolling(win, min_periods=win).std())
        df[f"boll_z_{win}"] = (df["adj_close"] - mean) / std

    # Volume ratios and z-scores
    for win in ma_windows:
        df[f"volume_avg_{win}"] = by_ticker(df["volume"], lambda s: s.rolling(win, min_periods=win).mean())
        df[f"volume_ratio_{win}"] = df["volume"] / df[f"volume_avg_{win}"]
    for win in volume_zscore_windows:
        vol_mean = by_ticker(df["volume"], lambda s: s.rolling(win, min_periods=win).mean())
        vol_std = by_ticker(df["volume"], lambda s: s.rolling(win, min_periods=win).std())
        df[f"volume_z_{win}"] = (df["volume"] - vol_mean) / vol_std

    # RSI
    df["rsi"] = by_ticker(df["adj_close"], lambda s: _rsi(s, period=rsi_period))

    # Range/ATR features
    prev_close = by_ticker(df["adj_close"], lambda s: s.shift(1))
    high_low = df["high"] - df["low"]
    high_prev = (df["high"] - prev_close).abs()
    low_prev = (df["low"] - prev_close).abs()
    true_range = pd.concat([high_low, high_prev, low_prev], axis=1).max(axis=1)
    df["atr"] = by_ticker(true_range, lambda s: s.rolling(atr_window, min_periods=atr_window).mean())
    df["range_pct"] = high_low / df["adj_close"]
    df["gap_pct"] = (df["open"] - prev_close) / prev_close

    return df


def add_calendar_features(prices: PriceFrame) -> PriceFrame:
    """Append calendar-derived features."""
    df = prices.copy()
    df["day_of_week"] = df["date"].dt.weekday
    df["month"] = df["date"].dt.month
    df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    return df


def add_market_regime_features(prices: PriceFrame) -> PriceFrame:
    """
    Add market regime indicators derived from VIX if present on the frame.
    """
    df = prices.copy()
    if "vix_close" not in df:
        return df
    vix_series = (
        df[["date", "vix_close"]]
        .drop_duplicates(subset="date")
        .sort_values("date")
        .assign(vix_change_1d=lambda s: s["vix_close"].pct_change())
        .assign(vix_trend_5d=lambda s: s["vix_close"].pct_change(5))
    )
    # VIX z-score over 20d window
    vix_series["vix_mean_20d"] = vix_series["vix_close"].rolling(20, min_periods=20).mean()
    vix_series["vix_std_20d"] = vix_series["vix_close"].rolling(20, min_periods=20).std()
    vix_series["vix_z_20d"] = (vix_series["vix_close"] - vix_series["vix_mean_20d"]) / vix_series["vix_std_20d"]
    df = df.merge(vix_series, on=["date", "vix_close"], how="left")
    df["vix_level"] = df["vix_close"]
    return df


def build_feature_matrix(
    prices: PriceFrame,
    drop_na: bool = True,
    **kwargs,
) -> PriceFrame:
    """
    Compose feature engineering steps and return a feature-enriched frame.
    """
    df = add_price_features(prices, **kwargs)
    df = add_calendar_features(df)
    df = add_market_regime_features(df)
    df = df.replace([np.inf, -np.inf], np.nan)
    if drop_na:
        df = df.dropna().reset_index(drop=True)
    return df
