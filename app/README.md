FastAPI app (stockpredictor)
============================

Quickstart
----------
```bash
cd /Users/ag/stock_pipeline
python3 -m venv .venv && source .venv/bin/activate  # optional
pip install -r requirements-app.txt
uvicorn app.main:app --reload
```

Auth flow
---------
- Sign up: `POST /auth/signup` with `{ "email": "...", "password": "..." }` → returns bearer token.
- Login: `POST /auth/login` → returns bearer token.
- Use the token in `Authorization: Bearer <token>` for job endpoints.

Job flow (sync)
---------------
- Submit: `POST /jobs` with body:
  ```json
  {
    "tickers": ["AAPL", "MSFT"],
    "start": "2022-01-01",
    "end": "2023-12-31",
    "task": "classification",
    "horizon": 1,
    "model_kind": "random_forest",
    "entry_threshold": 0.05
  }
  ```
  Returns `{"job_id": "..."}` once the run finishes (synchronous for now).
- List jobs: `GET /jobs`
- Get results: `GET /jobs/{job_id}` → summary metrics, equity curve, and trades head.

Notes and limits
----------------
- Guardrails: max tickers = 5, max date span = 5 years (configurable via env vars).
- Data source: yfinance (live) only for now; CSV uploads can be added later.
- Tokens use a dev default secret; set `APP_SECRET_KEY` in production.
