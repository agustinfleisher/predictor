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
- Sign up: `POST /auth/signup` with `{ "username": "...", "email": "...", "password": "..." }` → returns bearer token.
- Login: `POST /auth/login` with `{ "identifier": "<username or email>", "password": "..." }` → returns bearer token.
- Forgot password: `POST /auth/forgot_password` with `{ "identifier": "<username or email>" }` (sends a reset token via SMTP if configured; otherwise logs token to stdout).
- Reset password: `POST /auth/reset_password` with `{ "token": "...", "new_password": "..." }`.
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
- CORS is open (`*`) for local development. For production, restrict origins.
- Optional SMTP: set `APP_SMTP_HOST`, `APP_SMTP_PORT`, `APP_SMTP_USERNAME`, `APP_SMTP_PASSWORD`, `APP_SMTP_FROM` to send real reset emails; otherwise tokens are logged to stdout.

Frontend (simple static)
------------------------
- A lightweight HTML/JS frontend lives in `frontend/`.
- Start the API (separate terminal):
  ```bash
  cd /Users/ag/stock_pipeline
  uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
- Serve the frontend (another terminal):
  ```bash
  cd /Users/ag/stock_pipeline/frontend
  python3 -m http.server 5173
  ```
  Then open http://127.0.0.1:5173 in your browser.
- Flow in the UI: sign up or log in, then submit a job (tickers/dates), then view results (summary, equity curve head, trades head).
