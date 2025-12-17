"""
Market regime utilities (e.g., volatility-based states from VIX or realized vol).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

PriceFrame = pd.DataFrame
RegimeLabel = Literal["low", "mid", "high"]


def classify_regime_from_levels(series: pd.Series, low: float, high: float) -> pd.Series:
    """
    Label regimes based on absolute thresholds.
    """
    def _label(x):
        if pd.isna(x):
            return np.nan
        if x < low:
            return "low"
        if x > high:
            return "high"
        return "mid"

    return series.apply(_label)


def classify_regime_from_zscore(series: pd.Series, window: int = 20, low_z: float = -0.5, high_z: float = 0.5) -> pd.Series:
    """
    Label regimes using rolling z-scores of the input series.
    """
    mean = series.rolling(window, min_periods=window).mean()
    std = series.rolling(window, min_periods=window).std()
    z = (series - mean) / std
    return classify_regime_from_levels(z, low=low_z, high=high_z)


def _one_hot(regimes: pd.Series) -> pd.DataFrame:
    dummy = pd.get_dummies(regimes, prefix="regime")
    for col in ["regime_low", "regime_mid", "regime_high"]:
        if col not in dummy:
            dummy[col] = 0
    return dummy


def add_vix_regime(
    prices: PriceFrame,
    vix_col: str = "vix_close",
    method: Literal["level", "zscore"] = "level",
    low: float = 15.0,
    high: float = 25.0,
    z_window: int = 20,
    z_low: float = -0.5,
    z_high: float = 0.5,
    one_hot: bool = True,
) -> PriceFrame:
    """
    Add VIX-based regime labels (and optional one-hot flags) to the price frame.
    """
    if vix_col not in prices:
        return prices.copy()

    df = prices.copy()
    if method == "level":
        regimes = classify_regime_from_levels(df[vix_col], low=low, high=high)
    elif method == "zscore":
        regimes = classify_regime_from_zscore(df[vix_col], window=z_window, low_z=z_low, high_z=z_high)
    else:
        raise ValueError(f"Unknown regime method: {method}")

    df["regime"] = regimes
    df["regime_code"] = df["regime"].map({"low": 0, "mid": 1, "high": 2})
    if one_hot:
        df = pd.concat([df, _one_hot(df["regime"])], axis=1)
    return df


def add_realized_vol_regime(
    prices: PriceFrame,
    window: int = 20,
    low: float = 0.015,
    high: float = 0.03,
    one_hot: bool = True,
) -> PriceFrame:
    """
    Label regimes using realized volatility of returns.
    """
    df = prices.sort_values(["ticker", "date"]).reset_index(drop=True)
    returns = df.groupby("ticker")["adj_close"].pct_change()
    realized = returns.groupby(df["ticker"], group_keys=False).apply(lambda s: s.rolling(window, min_periods=window).std())
    df["realized_vol"] = realized
    df["realized_vol_regime"] = classify_regime_from_levels(df["realized_vol"], low=low, high=high)
    df["realized_vol_code"] = df["realized_vol_regime"].map({"low": 0, "mid": 1, "high": 2})
    if one_hot:
        df = pd.concat([df, _one_hot(df["realized_vol_regime"]).rename(columns=lambda c: c.replace("regime_", "realized_"))], axis=1)
    return df
