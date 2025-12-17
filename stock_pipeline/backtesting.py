"""
Walk-forward backtesting with position sizing, costs, and portfolio aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Callable, Dict, Iterable, List, Literal, Tuple

import numpy as np
import pandas as pd

from . import datasets, models

Task = Literal["classification", "regression"]


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    daily_returns: pd.Series
    metrics: Dict[str, float]


def default_position_sizer(
    task: Task,
    pred: np.ndarray,
    proba: np.ndarray | None = None,
    return_scale: float = 0.02,
    max_size: float = 1.0,
) -> np.ndarray:
    """
    Turn model outputs into signed position sizes in [-max_size, max_size].

    Classification: size scales with distance of probability from 0.5.
    Regression: size scales with predicted return divided by return_scale.
    """
    if task == "classification":
        if proba is None:
            conf = 1.0
            side = np.where(pred == 1, 1, -1)
        else:
            if proba.ndim > 1:
                p_up = proba[:, -1]
            else:
                p_up = proba
            conf = np.clip(np.abs(p_up - 0.5) * 2, 0.0, 1.0)
            side = np.where(p_up >= 0.5, 1, -1)
        size = conf * side
        return np.clip(size, -max_size, max_size)

    # Regression
    size = pred / return_scale
    return np.clip(size, -max_size, max_size)


def performance_metrics(daily_returns: pd.Series, trades: pd.DataFrame, freq: int = 252) -> Dict[str, float]:
    """
    Compute high-level portfolio metrics.
    """
    if daily_returns.empty:
        return {}
    equity = (1 + daily_returns).cumprod()
    ann_return = (1 + daily_returns.mean()) ** freq - 1
    ann_vol = daily_returns.std(ddof=0) * sqrt(freq)
    sharpe = ann_return / ann_vol if ann_vol > 0 else np.nan
    max_dd = (equity / equity.cummax() - 1).min()
    hit_rate = (trades["net_return"] > 0).mean()
    avg_trade = trades["net_return"].mean()
    exposure = trades["position"].abs().mean()
    total_cost = trades["cost"].sum()
    turnover = trades["position"].diff().abs().mean() if not trades.empty else 0.0
    return {
        "cumulative_return": equity.iloc[-1] - 1,
        "annualized_return": ann_return,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "hit_rate": hit_rate,
        "avg_trade_return": avg_trade,
        "avg_abs_position": exposure,
        "turnover": turnover,
        "total_cost": total_cost,
    }


def _date_windows(
    unique_dates: List[pd.Timestamp],
    train_window: int,
    test_window: int,
    step: int,
    expanding: bool,
) -> Iterable[Tuple[List[pd.Timestamp], List[pd.Timestamp]]]:
    total = len(unique_dates)
    idx = train_window
    while idx + test_window <= total:
        if expanding:
            train_dates = unique_dates[:idx]
        else:
            train_dates = unique_dates[idx - train_window : idx]
        test_dates = unique_dates[idx : idx + test_window]
        yield train_dates, test_dates
        idx += step


def walk_forward_backtest(
    labeled_features: pd.DataFrame,
    model_kind: str,
    task: Task,
    horizon: int = 1,
    train_window: int = 252 * 2,
    test_window: int = 63,
    step: int | None = None,
    expanding: bool = True,
    cost_perc: float = 0.0005,
    slippage_perc: float = 0.0005,
    position_sizer: Callable[..., np.ndarray] | None = None,
    entry_threshold: float = 0.0,
) -> BacktestResult:
    """
    Run walk-forward backtest with rolling/expanding windows.

    labeled_features must contain:
      - date, ticker, target_return (and target for classification)
      - feature columns (numeric)
    """
    df = labeled_features.copy()
    if "target_return" not in df:
        df = datasets.add_targets(df, horizon=horizon, task=task)
    df = df.dropna(subset=["target_return"])
    feature_cols = datasets.select_feature_columns(df)

    df = df.sort_values("date").reset_index(drop=True)
    dates = sorted(df["date"].unique())
    if step is None:
        step = test_window

    sizer = position_sizer or default_position_sizer
    all_trades: List[pd.DataFrame] = []
    fold_idx = 0

    for train_dates, test_dates in _date_windows(dates, train_window, test_window, step, expanding):
        train_df = df[df["date"].isin(train_dates)]
        test_df = df[df["date"].isin(test_dates)]
        if train_df.empty or test_df.empty:
            continue

        X_train, y_train = datasets.build_xy(train_df, feature_columns=feature_cols, target_column="target")
        X_test, y_test = datasets.build_xy(test_df, feature_columns=feature_cols, target_column="target")

        model = models.make_model(model_kind, task=task)
        model.fit(X_train, y_train)

        proba_up = None

        if task == "classification":
            proba = model.predict_proba(X_test) if hasattr(model, "predict_proba") else None
            preds = (proba[:, -1] >= 0.5).astype(int) if proba is not None else model.predict(X_test)
            if entry_threshold > 0 and proba is not None:
                edge = np.abs(proba[:, -1] - 0.5) * 2
                mask = edge < entry_threshold
                preds = preds.copy()
                preds[mask] = 0  # flatten to no-trade when confidence low
                proba = proba.copy()
                proba[mask, -1] = 0.5
            if proba is not None:
                proba_up = proba[:, -1]
            positions = sizer(task, preds, proba=proba)
            gross = positions * test_df["target_return"].to_numpy()
        else:
            preds = model.predict(X_test)
            if entry_threshold > 0:
                mask = np.abs(preds) < entry_threshold
                preds = preds.copy()
                preds[mask] = 0.0
            positions = sizer(task, preds, proba=None)
            gross = positions * test_df["target_return"].to_numpy()

        round_trip_cost = cost_perc * 2 + slippage_perc
        costs = np.abs(positions) * round_trip_cost
        net = gross - costs

        trades = test_df[["date", "ticker"]].copy()
        trades["prediction"] = preds
        trades["target"] = test_df["target"].to_numpy()
        trades["position"] = positions
        trades["target_return"] = test_df["target_return"].to_numpy()
        trades["gross_return"] = gross
        trades["cost"] = costs
        trades["net_return"] = net
        trades["fold"] = fold_idx
        if proba_up is not None:
            trades["proba_up"] = proba_up
        all_trades.append(trades)
        fold_idx += 1

    if not all_trades:
        return BacktestResult(trades=pd.DataFrame(), daily_returns=pd.Series(dtype=float), metrics={})

    trades_df = pd.concat(all_trades, axis=0).sort_values("date").reset_index(drop=True)
    daily_returns = trades_df.groupby("date")["net_return"].mean()
    metrics = performance_metrics(daily_returns, trades_df)
    return BacktestResult(trades=trades_df, daily_returns=daily_returns, metrics=metrics)
