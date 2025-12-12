Modular daily stock prediction toolkit
======================================

What this provides
------------------
- Fetch daily OHLCV from yfinance plus optional VIX regime data (`stock_pipeline/data.py`).
- Data helpers to clean, align calendars across tickers, auto-adjust for splits/dividends, and fill missing values (`download_ohlcv`, `load_prices`, `align_and_fill`).
- Manual adjustment helper if you fetch raw prices: `adjust_ohlcv` (applies adj_close ratio to OHLC).
- Engineer practical features: returns, moving averages, mean-reversion distance, volatility, volume ratios, RSI, calendar signals, and VIX-based regime indicators (`stock_pipeline/features.py`).
- Regime helpers to label low/mid/high volatility states from VIX or realized vol (`stock_pipeline/regimes.py`).
- Build supervised datasets with next-day return or direction labels, and time-ordered splits (`stock_pipeline/datasets.py`).
- Factory-created models: logistic regression, random forest, gradient boosting, MLP, and linear regression (`stock_pipeline/models.py`).
- Simple model selector to fit many candidates and keep the best (`models.select_best_model`).
- Ensembling/regime gating helpers (`stock_pipeline/ensemble.py`).
- Walk-forward backtesting with costs/slippage, position sizing, and portfolio aggregation (`stock_pipeline/backtesting.py`).
- Training/evaluation helper and an example CLI runner (`stock_pipeline/training.py`, `scripts/run_pipeline.py`).

Install deps
------------
```bash
cd stock_pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Run the example pipeline
------------------------
```bash
python scripts/run_pipeline.py \
  --tickers AAPL,MSFT \
  --include-vix \
  --task classification \
  --model logistic \
  --start 2020-01-01 \
  --end 2023-12-31
```

How to assemble your own
------------------------
1) Pull data: `prices = data.download_ohlcv(["AAPL", "MSFT"], start, end)`.
2) Add VIX if desired: `vix = data.download_vix(start, end)` then `prices = data.merge_market_regime(prices, vix)`.
3) Engineer features: `feat = features.build_feature_matrix(prices)`.
4) Create labels: `labeled = datasets.add_targets(feat, horizon=1, task="classification")`.
5) Split and train: `train_df, test_df = datasets.time_series_split(labeled)` then `model = models.make_model("gboost", "classification")` and `model.fit(...)`.
6) Evaluate with metrics in `training.evaluate_classification` or `evaluate_regression`.

Ensembling / regime switching
-----------------------------
- Average model outputs: `preds, proba = ensemble.average_predictions([proba_model1, proba_model2], task="classification")`.
- Weighted regression blend: `y_blend, _ = ensemble.average_predictions([preds1, preds2], task="regression", weights=[0.6, 0.4])`.
- Gate models by VIX (low vs high vol): `gated = ensemble.gate_by_regime(pred_low, pred_high, feat["vix_close"], threshold=20)`.
- Meta-blend (stacking): train meta on base preds -> `meta = ensemble.train_meta_blender(base_preds_train, y_train, task="classification")` then `preds, proba = ensemble.predict_meta_blend(meta, base_preds_test, task="classification")`.

Class-based backtester usage
----------------------------
```python
from stock_pipeline import data, features, datasets, backtester

tickers = ["AAPL", "MSFT"]
start, end = "2022-01-01", "2023-12-31"

# 1) Load prices and merge VIX for regime features (optional)
prices = data.load_prices(tickers, start=start, end=end, auto_adjust=True)
vix = data.download_vix(start, end)
prices = data.merge_market_regime(prices, vix)

# 2) Build features
feat = features.build_feature_matrix(prices, drop_na=True)

# 3) Label for classification (next-day direction)
labeled = datasets.add_targets(feat, horizon=1, task="classification")

# 4) Configure backtest
cfg = backtester.BacktestConfig(
    model_kind="logistic",   # or "random_forest"
    task="classification",
    horizon=1,
    train_window=252,        # 1-year train
    test_window=63,          # 1-quarter test
    cost_perc=0.0005,
    slippage_perc=0.0005,
    entry_threshold=0.0,
)

# 5) Run walk-forward backtest
wf = backtester.WalkForwardBacktester(labeled_features=labeled, config=cfg)
trades, summary = wf.run()

print("Mean metrics:", summary["mean_metrics"])
print("Trading metrics:", summary["trading_metrics"])

print("Equity curve head:")
equity = trades[["date", "equity"]].drop_duplicates("date").set_index("date")["equity"]
print(equity.head())

print("Trades preview:")
print(trades.head())
```

Walk-forward backtest
---------------------
```python
from stock_pipeline import backtesting, datasets, features

prices = data.download_ohlcv(["AAPL","MSFT"], "2020-01-01", "2023-12-31")
vix = data.download_vix("2020-01-01", "2023-12-31")
prices = data.merge_market_regime(prices, vix)
feat = features.build_feature_matrix(prices)
labeled = datasets.add_targets(feat, horizon=1, task="classification")
result = backtesting.walk_forward_backtest(
    labeled,
    model_kind="gboost",
    task="classification",
    train_window=252*2,
    test_window=63,
    cost_perc=0.0005,
    slippage_perc=0.0005,
)
print(result.metrics)
print(result.daily_returns.head())
```

Feature engineering usage
-------------------------
```python
from stock_pipeline import data, features

tickers = ["AAPL", "MSFT"]
start, end = "2023-01-01", "2023-03-31"

# Default windows
prices = data.load_prices(tickers, start=start, end=end, auto_adjust=True)
feat_default = features.build_feature_matrix(prices, drop_na=True)
print("Default columns:", feat_default.columns.tolist())
print("Head of engineered features:")
print(feat_default[["ticker", "date", "ret_1d", "sma_5", "ema_5", "rsi", "atr", "volume_ratio_5"]].head())

# Override windows (e.g., faster signals)
feat_fast = features.build_feature_matrix(
    prices,
    drop_na=True,
    return_windows=(1, 3),
    ma_windows=(3, 7),
    vol_windows=(5, 10),
    rsi_period=7,
    bollinger_windows=(10,),
)
print("Custom columns:", feat_fast.columns.tolist())
print("Head (custom windows):")
print(feat_fast[["ticker", "date", "ret_1d", "sma_3", "ema_3", "rsi", "atr", "volume_ratio_3"]].head())
```

Notes
-----
- The pipeline assumes daily bars; intraday intervals need adjustments to rolling windows.
- yfinance calls require network access; in offline mode, swap in your own CSV loader and reuse the feature/model modules unchanged.
