#!/usr/bin/env python
"""
Example CLI to run the modular pipeline end-to-end.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from stock_pipeline import data, features, training


def parse_args() -> argparse.Namespace:
    today = date.today()
    default_start = today - timedelta(days=365 * 2)
    parser = argparse.ArgumentParser(description="Train daily stock prediction models.")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated tickers (e.g., AAPL,MSFT).")
    parser.add_argument("--start", type=str, default=str(default_start), help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=str(today), help="End date YYYY-MM-DD")
    parser.add_argument("--task", choices=["classification", "regression"], default="classification")
    parser.add_argument("--model", type=str, default="logistic", help="Model kind: logistic, rf, gboost, mlp, linear")
    parser.add_argument("--horizon", type=int, default=1, help="Prediction horizon in days (next-day=1)")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction for hold-out test set")
    parser.add_argument("--include-vix", action="store_true", help="Fetch VIX and merge as market regime feature.")
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        raise SystemExit("No tickers provided.")

    print(f"Fetching {tickers} from {args.start} to {args.end} ...")
    prices = data.download_ohlcv(tickers, start=args.start, end=args.end)

    if prices.empty:
        raise SystemExit("No price data returned.")

    if args.include_vix:
        vix = data.download_vix(start=args.start, end=args.end)
        prices = data.merge_market_regime(prices, vix)

    print("Engineering features...")
    feat_df = features.build_feature_matrix(prices, drop_na=True)

    print(f"Training {args.model} for task={args.task} ...")
    model, metrics = training.train_evaluate(
        feat_df, model_kind=args.model, task=args.task, test_size=args.test_size, horizon=args.horizon
    )

    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    # Optional: persist model placeholder
    model_path = Path("trained_model.pkl")
    try:
        import joblib

        joblib.dump(model, model_path)
        print(f"Saved model to {model_path.resolve()}")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not save model ({exc}). Install joblib to enable persistence.")


if __name__ == "__main__":
    main()
