"""
Class-based wrapper around walk-forward backtesting utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from . import backtesting, metrics

Task = Literal["classification", "regression"]


@dataclass
class BacktestConfig:
    model_kind: str = "gboost"
    task: Task = "classification"
    horizon: int = 1
    train_window: int = 252 * 2
    test_window: int = 63
    step: Optional[int] = None
    expanding: bool = True
    cost_perc: float = 0.0005
    slippage_perc: float = 0.0005
    entry_threshold: float = 0.0
    position_sizer: Optional[Callable[..., np.ndarray]] = None


class WalkForwardBacktester:
    """
    Runs walk-forward evaluation over labeled features using the config provided.
    """

    def __init__(self, labeled_features: pd.DataFrame, config: BacktestConfig):
        self.labeled_features = labeled_features
        self.config = config

    def _fold_metrics(self, trades: pd.DataFrame) -> Tuple[list[dict], dict]:
        """
        Compute per-fold and mean metrics using centralized metric helpers.
        """
        fold_metrics: list[dict] = []
        task = self.config.task
        for fold_id, g in trades.groupby("fold"):
            y_true = g["target"]
            y_pred = g["prediction"]
            if task == "classification":
                proba = g["proba_up"].to_numpy() if "proba_up" in g else None
                proba_full = None
                if proba is not None:
                    proba_full = np.column_stack([1 - proba, proba])
                m = metrics.classification_metrics(y_true, y_pred, y_proba=proba_full)
            else:
                m = metrics.regression_metrics(y_true, y_pred)
            fold_metrics.append({"fold": fold_id, **m})

        mean_metrics: Dict[str, float] = {}
        if fold_metrics:
            metric_keys = [k for k in fold_metrics[0].keys() if k != "fold"]
            for key in metric_keys:
                vals = [fm[key] for fm in fold_metrics if key in fm]
                mean_metrics[key] = float(np.mean(vals))
        return fold_metrics, mean_metrics

    def run(self) -> Tuple[pd.DataFrame, Dict]:
        cfg = self.config
        result = backtesting.walk_forward_backtest(
            labeled_features=self.labeled_features,
            model_kind=cfg.model_kind,
            task=cfg.task,
            horizon=cfg.horizon,
            train_window=cfg.train_window,
            test_window=cfg.test_window,
            step=cfg.step,
            expanding=cfg.expanding,
            cost_perc=cfg.cost_perc,
            slippage_perc=cfg.slippage_perc,
            position_sizer=cfg.position_sizer,
            entry_threshold=cfg.entry_threshold,
        )

        trades = result.trades.copy()
        equity_curve = (1 + result.daily_returns).cumprod()
        if not trades.empty and "date" in trades.columns:
            trades = trades.merge(equity_curve.rename("equity"), left_on="date", right_index=True, how="left")
        else:
            trades["equity"] = None

        fold_metrics, mean_metrics = self._fold_metrics(trades)
        summary = {
            "mean_metrics": mean_metrics,
            "fold_metrics": fold_metrics,
            "trading_metrics": result.metrics,
        }

        return trades, summary
