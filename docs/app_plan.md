App plan (stockpredictor)
=========================

Goals & audience
----------------
- Audience: you + invited users who want to run/inspect the pipeline via a browser (no coding required).
- Core tasks: sign up / log in; choose data source (live yfinance for supported tickers or upload CSV); configure horizons/features/regimes; run a backtest; view metrics/equity/trades; download results.
- Constraints: small-to-medium jobs (limit tickers/date ranges) with reasonable latency; protect against heavy loads.

UX: key screens/flows
---------------------
1) Landing/login/signup
   - Simple hero + CTA to log in or create an account.
   - Email/password auth; password reset link (future).
2) Home / run setup
   - Select data source: live (ticker, start/end) or upload CSV (OHLCV).
   - Choose target/horizon (next-day direction/return), features, regimes, and ensemble choice.
   - Job guardrails: max tickers, max date span, max rows for uploads.
   - Run button → starts job and shows “processing” status.
3) Results dashboard
   - Summary metrics (validation + walk-forward), trade stats, equity curve, and trades/predictions table.
   - Download CSV/JSON of results; link to rerun with same config.
4) Job history (per user)
   - Recent runs with timestamp, status, config hash, and quick view/download.

Stack & architecture
--------------------
- Back end: FastAPI (Python) wrapping existing pipeline. Endpoints for auth, job submission, job status/results.
- Front end: Vite + React (or Next.js if you prefer SSR); talk to API via HTTPS.
- Auth: email/password with hashed storage; JWT access + refresh stored in httpOnly cookies.
- Persistence: SQLite to start (users, jobs, job results metadata). Results payloads can be stored as JSON blobs or on disk with pointers in DB.
- Job execution: initial synchronous path for small jobs; optionally upgrade to background jobs (e.g., FastAPI background tasks) if latency grows.

API surface (initial)
---------------------
- `POST /auth/signup` {email, password} → create user.
- `POST /auth/login` {email, password} → set access/refresh cookies.
- `POST /auth/refresh` → rotate access token.
- `POST /auth/logout` → clear cookies.
- `POST /jobs` → submit run (tickers/date range or CSV upload ref, target/feature/regime choices).
- `GET /jobs/{job_id}` → status + summary metrics.
- `GET /jobs/{job_id}/results` → equity/trades/metrics payload (paged for tables).

Data & models
-------------
- Data sources: yfinance for supported tickers; CSV upload for offline use.
- Feature/regime choices: expose a safe subset (limit custom code); use existing feature/regime builders.
- Models: offer baseline registry (logistic, RF, GBDT, MLP) and ensemble options; constrain hyperparams to avoid long runs.

Security & limits
-----------------
- Auth required for all job endpoints.
- Rate limits per user; guardrails on tickers/date span and upload size; block overly large jobs.
- Store passwords hashed (e.g., argon2 or bcrypt); short-lived access tokens with refresh.

Deployment
----------
- Back end: containerized FastAPI (Fly.io/Render/Heroku or similar).
- Front end: Vercel/Netlify or served by back end for simplicity.
- Env config: yfinance allowed; no secrets in the repo; use env vars for keys/tokens.

Testing & observability
-----------------------
- Unit tests for API/auth and a smoke test for a small job.
- Logging: structured logs for requests and job lifecycle; capture errors with trace IDs.
- Simple metrics: job counts, durations, failures.

Near-term build steps
---------------------
1) Scaffold FastAPI app with auth (JWT in cookies) + SQLite users table.
2) Add job submission endpoint that calls existing pipeline synchronously with tight limits.
3) Front end: basic React UI for login/signup, job form, and results view with charts/tables.
4) Add job history per user; optional background job execution if needed.
