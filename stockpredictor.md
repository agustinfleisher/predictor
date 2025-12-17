Project summary (stockpredictor)
================================

Purpose
-------
Build a modular daily stock prediction toolkit with data loading, feature engineering, model factories/ensembles, and walk-forward backtesting, plus an end-to-end example (`main.py`).

How the purpose is fulfilled
----------------------------
This project is organized as a small, composable pipeline that turns raw market time series into (1) a predictive signal and (2) a realistic evaluation of that signal using time-series-safe validation.

At a high level the workflow is:
1) **Load and align data** (`stock_pipeline/data.py`): download OHLCV for one or more tickers, clean/normalize columns, align dates, and optionally merge external series like VIX.
2) **Describe market regimes** (`stock_pipeline/regimes.py`): label each date with regime features (e.g., VIX level buckets or realized-vol z-score buckets) and optionally one-hot encode them for modeling.
3) **Engineer predictive features** (`stock_pipeline/features.py`): compute standard technical/seasonality inputs (returns, vol, RSI, Bollinger bands, calendar effects, VIX-derived features) in a way that preserves time ordering.
4) **Build a modeling dataset** (`stock_pipeline/datasets.py`): define targets (e.g., next-day return or next-day direction), select features, and create train/validation splits that respect chronology to avoid leakage.
5) **Instantiate models consistently** (`stock_pipeline/base_models.py`, `stock_pipeline/models.py`): provide a registry/factory layer so models can be swapped without changing pipeline code.
6) **Combine models when helpful** (`stock_pipeline/ensemble.py`): support simple blends (weighted averaging / voting) and regime-aware gating to make the signal more robust than a single estimator.
7) **Evaluate with walk-forward testing** (`stock_pipeline/backtesting.py`, `stock_pipeline/backtester.py`, `stock_pipeline/metrics.py`): run a fold-by-fold walk-forward loop that retrains over time and simulates a simple trading rule (thresholded entries, transaction costs), returning metrics, an equity curve, and a trade/prediction ledger.

`main.py` stitches these parts together into a runnable reference that demonstrates the intended “happy path” from data → features → model/ensemble → walk-forward backtest → printed summary outputs.

Key files/modules
-----------------
- `main.py`: end-to-end script (load prices, add VIX/realized-vol regimes, build features, train simple blend, run walk-forward backtest, print metrics/equity/trades head).
- `stock_pipeline/data.py`: yfinance loader, cleaning, alignment, optional manual adjustment, VIX merge.
- `stock_pipeline/features.py`: price/volume/volatility/RSI/Bollinger/calendar and VIX-based regime features.
- `stock_pipeline/regimes.py`: regime labeling from VIX or realized vol (levels/z-scores) with optional one-hot.
- `stock_pipeline/datasets.py`: target creation (next-day return/direction), feature selection, time-series split.
- `stock_pipeline/base_models.py`: untrained factories (logistic, RF, gradient boosting, MLP).
- `stock_pipeline/models.py`: registry-based model maker and selector.
- `stock_pipeline/ensemble.py`: weighted averaging, majority vote, regime gating, simple meta-blender.
- `stock_pipeline/backtesting.py`: walk-forward backtest with costs, entry threshold, positions, metrics.
- `stock_pipeline/backtester.py`: class wrapper returning trades + metrics summary.
- `stock_pipeline/metrics.py`: classification/regression metric helpers.
- `README.md`: usage examples for features, ensembling, backtesting, backtester.
- `scripts/run_pipeline.py`: older CLI-style runner (separate from `main.py`).
- `requirements.txt`: minimal dependencies for the project.

What’s been done
----------------
- Implemented all modules above and wired `__init__.py`.
- Added `main.py` demonstrating end-to-end workflow with console summaries and basic error handling for missing data.
- Installed dependencies via `requirements.txt` in `/Users/ag/stock_pipeline` and via venv in `/Users/ag/predictor`.
- Initialized git repo in `/Users/ag/stock_pipeline` and committed the full project. Remote currently set to `git@github.com:agustinfleisher/predictor.git`.
- Debugged and fixed multiple pipeline blockers:
  - yfinance MultiIndex output handling is now robust (handles both `(ticker, field)` and `(field, ticker)` column layouts).
  - VIX merge now drops duplicate dates before reindexing to avoid `ValueError: cannot reindex on an axis with duplicate labels`.
  - Avoided column collisions by renaming VIX volume to `vix_volume` before merging into equity OHLCV.
  - Fixed realized-vol regime calculation to align indices (`group_keys=False`) to avoid `TypeError: incompatible index of inserted column with frame index`.

Known issues / blockers
-----------------------
- In this Codex CLI sandbox, outbound network/DNS may be blocked unless commands are run with “escalated permissions”. Symptoms looked like DNS failures (e.g., `Could not resolve host: github.com` / `guce.yahoo.com`).
- When network access is allowed, `main.py` runs end-to-end and downloads data via yfinance successfully.
- `git push` requires authentication:
  - HTTPS: needs GitHub username + Personal Access Token (PAT); non-interactive pushes can fail with `could not read Username... terminal prompts disabled`.
  - SSH: requires your public key to be added to GitHub; otherwise you’ll see `Permission denied (publickey)`.
- Repo status note: project is committed locally; remaining step is configuring GitHub auth and pushing.

Next steps
----------
1) Push to GitHub (after DNS/network works in your terminal and you have auth set up):
   - SSH (current remote): add `~/.ssh/id_ed25519.pub` to GitHub, then `git push -u origin main`
   - or HTTPS: `git remote set-url origin https://github.com/agustinfleisher/predictor.git` then `git push -u origin main` (use a PAT when prompted)
2) If you want to run fully offline, add a CSV loader and point `main.py` at local OHLCV CSVs (the feature/backtest pipeline is already modular for that).

How to run (with network)
-------------------------
```bash
cd /Users/ag/stock_pipeline
python3 main.py
```
It prints tickers/date range, validation/backtest metrics, and heads of equity/trades.

Typical `main.py` output
------------------------
`main.py` prints:
- Ticketers + date range + task/horizon
- Validation metrics for a simple blended baseline
- Walk-forward fold-averaged metrics + trading metrics
- `head()` of the equity curve and the trades/predictions DataFrame

Notes on environments
---------------------
- `/Users/ag/stock_pipeline` uses system Python (pip3 already installed deps).
- `/Users/ag/predictor` is a separate venv demo; activate with `source .venv/bin/activate` and install needed libs there if you want to run scripts in that folder.
