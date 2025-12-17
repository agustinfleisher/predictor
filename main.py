"""
End-to-end daily-return prediction example using the stock_pipeline package.

Flow:
- Configure tickers/dates/horizon.
- Load prices and add regimes (VIX + realized volatility).
- Engineer features and label next-day direction.
- Train simple baselines and blend on validation.
- Configure and run walk-forward backtest.
"""

from __future__ import annotations

from datetime import date, timedelta
import sys

from stock_pipeline import (
    backtester,
    base_models,
    data,
    datasets,
    ensemble,
    features,
    metrics,
    regimes,
)


def build_dataset(tickers: list[str], start: str, end: str):
    try:
        prices = data.load_prices(tickers, start=start, end=end, auto_adjust=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to load prices ({exc}).")
        return None
    if prices is None or prices.empty:
        return None
    try:
        vix = data.download_vix(start, end)
        prices = data.merge_market_regime(prices, vix)
        prices = regimes.add_vix_regime(prices, method="level", low=15, high=25, one_hot=True)
        prices = regimes.add_realized_vol_regime(prices, window=20, low=0.015, high=0.03, one_hot=True)
        feat = features.build_feature_matrix(prices, drop_na=True)
        labeled = datasets.add_targets(feat, horizon=1, task="classification")
        labeled = labeled.dropna(subset=["target"]).reset_index(drop=True)
        return labeled
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to prepare dataset ({exc}).")
        return None


def simple_train_val_split(labeled, test_size=0.2):
    train_df, val_df = datasets.time_series_split(labeled, test_size=test_size)
    X_train, y_train = datasets.build_xy(train_df, target_column="target")
    X_val, y_val = datasets.build_xy(val_df, target_column="target")
    return X_train, y_train, X_val, y_val


def fit_and_blend(X_train, y_train, X_val):
    logit = base_models.make_logistic()
    rf = base_models.make_random_forest(task="classification")
    logit.fit(X_train, y_train)
    rf.fit(X_train, y_train)
    proba_logit = logit.predict_proba(X_val)
    proba_rf = rf.predict_proba(X_val)
    preds_blend, proba_blend = ensemble.average_predictions(
        [proba_logit, proba_rf], task="classification", weights=[0.6, 0.4]
    )
    return preds_blend, proba_blend


def run_backtest(labeled):
    cfg = backtester.BacktestConfig(
        model_kind="random_forest",  # uses stock_pipeline.models under the hood
        task="classification",
        horizon=1,
        train_window=252,   # 1-year train
        test_window=63,     # 1-quarter test
        cost_perc=0.0005,
        slippage_perc=0.0005,
        entry_threshold=0.05,  # skip low-confidence signals
    )
    wf = backtester.WalkForwardBacktester(labeled_features=labeled, config=cfg)
    trades, summary = wf.run()
    return trades, summary


def main():
    tickers = ["AAPL", "MSFT"]
    end = date.today()
    start = end - timedelta(days=365 * 2)
    horizon = 1

    # Load data and build labeled feature set
    labeled = build_dataset(tickers, start=str(start), end=str(end))
    if labeled is None or labeled.empty:
        print("Warning: No data returned for the requested tickers/date range.")
        sys.exit(0)

    # Train/validation split and simple blend of two base models
    X_train, y_train, X_val, y_val = simple_train_val_split(labeled, test_size=0.2)
    preds_blend, proba_blend = fit_and_blend(X_train, y_train, X_val)
    val_metrics = metrics.classification_metrics(y_val, preds_blend, y_proba=proba_blend)

    # Walk-forward backtest configuration and execution
    trades, summary = run_backtest(labeled)
    equity = trades[["date", "equity"]].drop_duplicates("date").set_index("date")["equity"]

    # Console summary
    print("\n=== Backtest Summary ===")
    print(f"Tickers: {tickers}")
    print(f"Date range: {start} to {end}")
    print(f"Task: classification, Horizon: {horizon} day")
    print("Validation metrics (blend):", val_metrics)
    print("Walk-forward mean metrics:", summary["mean_metrics"])
    print("Trading metrics:", summary["trading_metrics"])

    print("\nEquity curve head:")
    print(equity.head())

    print("\nTrades head:")
    print(trades.head())


if __name__ == "__main__":
    main()
