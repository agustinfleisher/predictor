const API_BASE = "http://127.0.0.1:8000";

let accessToken = null;
let lastJobId = null;

const statusEl = document.getElementById("status");
const tokenStatusEl = document.getElementById("tokenStatus");
const jobIdEl = document.getElementById("jobId");
const summaryEl = document.getElementById("summary");
const equityEl = document.getElementById("equity");
const tradesEl = document.getElementById("trades");

function setStatus(msg, type = "info") {
  statusEl.textContent = msg;
  statusEl.style.color = type === "error" ? "#f87171" : "#4ade80";
}

function setToken(token) {
  accessToken = token;
  tokenStatusEl.textContent = token ? "Authenticated" : "Not authenticated";
  tokenStatusEl.style.color = token ? "#4ade80" : "#94a3b8";
}

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  if (opts.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (err) {
    /* ignore parse error */
  }
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : text || "Request failed";
    throw new Error(detail);
  }
  return data;
}

async function signup() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !password) {
    setStatus("Email and password required.", "error");
    return;
  }
  try {
    const data = await api("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    setStatus("Signed up and logged in.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !password) {
    setStatus("Email and password required.", "error");
    return;
  }
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    setStatus("Logged in.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function defaultDates() {
  const endInput = document.getElementById("end");
  const startInput = document.getElementById("start");
  const today = new Date();
  const endStr = today.toISOString().slice(0, 10);
  const past = new Date();
  past.setFullYear(past.getFullYear() - 2);
  const startStr = past.toISOString().slice(0, 10);
  if (!endInput.value) endInput.value = endStr;
  if (!startInput.value) startInput.value = startStr;
}

async function submitJob() {
  if (!accessToken) {
    setStatus("Log in first.", "error");
    return;
  }
  const tickersRaw = document.getElementById("tickers").value;
  const tickers = tickersRaw.split(",").map((t) => t.trim()).filter(Boolean);
  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  const task = document.getElementById("task").value;
  const model_kind = document.getElementById("model_kind").value;
  const horizon = parseInt(document.getElementById("horizon").value || "1", 10);
  const entry_threshold = parseFloat(document.getElementById("entry_threshold").value || "0");

  const payload = {
    tickers,
    start,
    end,
    task,
    model_kind,
    horizon,
    entry_threshold,
  };

  try {
    setStatus("Running job...");
    const data = await api("/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    lastJobId = data.job_id;
    jobIdEl.textContent = `Job ID: ${lastJobId}`;
    setStatus("Job finished. Fetching results...");
    await fetchJobDetail(lastJobId);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function fetchJobs() {
  if (!accessToken) {
    setStatus("Log in first.", "error");
    return;
  }
  try {
    const data = await api("/jobs");
    setStatus(`Found ${data.length} job(s).`);
    if (data.length) {
      lastJobId = data[0].id;
      jobIdEl.textContent = `Latest Job ID: ${lastJobId}`;
      await fetchJobDetail(lastJobId);
    }
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function fetchJobDetail(jobId) {
  if (!jobId) {
    setStatus("No job id to fetch.", "error");
    return;
  }
  try {
    const data = await api(`/jobs/${jobId}`);
    summaryEl.textContent = JSON.stringify(data.summary, null, 2);
    equityEl.textContent = JSON.stringify(data.equity_curve.slice(0, 20), null, 2);
    tradesEl.textContent = JSON.stringify(data.trades_head.slice(0, 20), null, 2);
    setStatus("Results loaded.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

document.getElementById("signup").addEventListener("click", signup);
document.getElementById("login").addEventListener("click", login);
document.getElementById("submitJob").addEventListener("click", submitJob);
document.getElementById("refreshJobs").addEventListener("click", fetchJobs);

defaultDates();
setToken(null);
setStatus("Ready.");
