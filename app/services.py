"""
Service functions that bridge API requests to the stock_pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

import pandas as pd

from stock_pipeline import backtester, data, datasets, features, regimes

from . import schemas


class JobError(Exception):
    """Raised when a job fails in a controlled way."""


def _guardrails(job: schemas.JobRequest, max_tickers: int, max_days: int) -> None:
    if len(job.tickers) > max_tickers:
        raise JobError(f"Too many tickers; max {max_tickers}")
    delta_days = (job.end - job.start).days
    if delta_days > max_days:
        raise JobError(f"Date range too large; max {max_days} days")


def _to_iso(obj: Any) -> Any:
    if isinstance(obj, pd.Timestamp):
        return obj.date().isoformat()
    if isinstance(obj, datetime):
        return obj.date().isoformat()
    return obj


def run_job(job: schemas.JobRequest, max_tickers: int, max_days: int) -> Dict[str, Any]:
    _guardrails(job, max_tickers=max_tickers, max_days=max_days)
    prices = data.load_prices(job.tickers, start=str(job.start), end=str(job.end), auto_adjust=True)
    if prices is None or prices.empty:
        raise JobError("No price data returned for the given tickers/date range")

    vix = data.download_vix(str(job.start), str(job.end))
    prices = data.merge_market_regime(prices, vix)
    prices = regimes.add_vix_regime(prices, method="level", low=15, high=25, one_hot=True)
    prices = regimes.add_realized_vol_regime(prices, window=20, low=0.015, high=0.03, one_hot=True)

    feat = features.build_feature_matrix(prices, drop_na=True)
    labeled = datasets.add_targets(feat, horizon=job.horizon, task=job.task)
    labeled = labeled.dropna(subset=["target"]).reset_index(drop=True)
    if labeled.empty:
        raise JobError("No labeled data available after feature/target creation")

    cfg = backtester.BacktestConfig(
        model_kind=job.model_kind,
        task=job.task,
        horizon=job.horizon,
        train_window=job.train_window,
        test_window=job.test_window,
        step=None,
        expanding=job.expanding,
        cost_perc=job.cost_perc,
        slippage_perc=job.slippage_perc,
        entry_threshold=job.entry_threshold,
    )
    wf = backtester.WalkForwardBacktester(labeled_features=labeled, config=cfg)
    trades, summary = wf.run()

    equity = trades.groupby("date")["net_return"].mean()
    equity_curve = (1 + equity).cumprod().reset_index()
    equity_curve.columns = ["date", "equity"]
    equity_curve["date"] = equity_curve["date"].apply(_to_iso)

    trades_head = trades.head(200).copy()
    trades_head["date"] = trades_head["date"].apply(_to_iso)

    return {
        "summary": summary,
        "equity_curve": equity_curve.to_dict(orient="records"),
        "trades_head": trades_head.to_dict(orient="records"),
    }
