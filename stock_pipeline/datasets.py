"""
Dataset preparation helpers for supervised learning on daily prices.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import pandas as pd


def add_targets(
    features: pd.DataFrame,
    horizon: int = 1,
    task: str = "regression",
) -> pd.DataFrame:
    """
    Add next-period return targets (regression) or direction labels (classification).
    """
    df = features.sort_values(["ticker", "date"]).reset_index(drop=True)
    future_price = df.groupby("ticker")["adj_close"].shift(-horizon)
    df["target_return"] = (future_price - df["adj_close"]) / df["adj_close"]

    if task == "classification":
        df["target"] = (df["target_return"] > 0).astype(int)
    else:
        df["target"] = df["target_return"]
    return df


def select_feature_columns(df: pd.DataFrame, exclude: Iterable[str] | None = None) -> list[str]:
    """
    Return numeric feature column names, excluding identifiers/targets.
    """
    exclude = set(exclude or [])
    identifier_cols = {"target", "target_return", "date", "ticker"}
    exclude = exclude.union(identifier_cols)

    numeric_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
    return numeric_cols


def build_xy(
    df: pd.DataFrame,
    feature_columns: Iterable[str] | None = None,
    target_column: str = "target",
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Split a prepared frame into X (features) and y (target).
    """
    features = list(feature_columns) if feature_columns is not None else select_feature_columns(df, exclude=[target_column])
    X = df[features]
    y = df[target_column]
    return X, y


def time_series_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Time-ordered train/test split to avoid look-ahead bias.
    """
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")
    df_sorted = df.sort_values("date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - test_size))
    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()
    return train_df, test_df
