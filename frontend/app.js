const API_BASE = "http://127.0.0.1:8000";

let accessToken = null;
let lastJobId = null;
let currentUser = null;

const statusEl = document.getElementById("status");
const accountDisplayEl = document.getElementById("accountDisplay");
const jobIdEl = document.getElementById("jobId");
const summaryEl = document.getElementById("summary");
const equityEl = document.getElementById("equity");
const tradesEl = document.getElementById("trades");

const tabSignup = document.getElementById("tabSignup");
const tabLogin = document.getElementById("tabLogin");
const tabForgot = document.getElementById("tabForgot");
const signupForm = document.getElementById("signupForm");
const loginForm = document.getElementById("loginForm");
const forgotForm = document.getElementById("forgotForm");
const openSignupBtn = document.getElementById("openSignup");
const openLoginBtn = document.getElementById("openLogin");
const jobSection = document.getElementById("jobSection");
const resultsSection = document.getElementById("resultsSection");
const authGate = document.getElementById("authGate");
const submitBtn = document.getElementById("submitJob");
const refreshBtn = document.getElementById("refreshJobs");

function setStatus(msg, type = "info") {
  statusEl.textContent = msg;
  statusEl.style.color = type === "error" ? "#f87171" : "#4ade80";
}

function setToken(token, user = null) {
  accessToken = token;
  currentUser = user;
  if (token && user) {
    accountDisplayEl.textContent = user.username || user.email || "Account";
    accountDisplayEl.classList.remove("muted");
  } else {
    accountDisplayEl.textContent = "Not signed in";
    accountDisplayEl.classList.add("muted");
  }
  toggleAuthState(!!token);
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
  const username = document.getElementById("su_username").value.trim();
  const email = document.getElementById("su_email").value.trim();
  const password = document.getElementById("su_password").value;
  if (!username || !email || !password) {
    setStatus("Username, email, and password required.", "error");
    return;
  }
  try {
    const data = await api("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
    setToken(data.access_token, { username, email });
    setStatus("Signed up and logged in.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function login() {
  const identifier = document.getElementById("li_identifier").value.trim();
  const password = document.getElementById("li_password").value;
  if (!identifier || !password) {
    setStatus("Username/email and password required.", "error");
    return;
  }
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    });
    setToken(data.access_token, { username: identifier, email: identifier });
    setStatus("Logged in.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function forgotPassword() {
  const identifier = document.getElementById("fp_identifier").value.trim();
  if (!identifier) {
    setStatus("Username or email required.", "error");
    return;
  }
  try {
    await api("/auth/forgot_password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
    setStatus("If the account exists, a reset token was sent.");
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
document.getElementById("forgot").addEventListener("click", forgotPassword);
document.getElementById("submitJob").addEventListener("click", submitJob);
document.getElementById("refreshJobs").addEventListener("click", fetchJobs);

openSignupBtn.addEventListener("click", () => activateTab("signup"));
openLoginBtn.addEventListener("click", () => activateTab("login"));
tabSignup.addEventListener("click", () => activateTab("signup"));
tabLogin.addEventListener("click", () => activateTab("login"));
tabForgot.addEventListener("click", () => activateTab("forgot"));

function activateTab(name) {
  tabSignup.classList.toggle("active", name === "signup");
  tabLogin.classList.toggle("active", name === "login");
  tabForgot.classList.toggle("active", name === "forgot");
  signupForm.classList.toggle("hidden", name !== "signup");
  loginForm.classList.toggle("hidden", name !== "login");
  forgotForm.classList.toggle("hidden", name !== "forgot");
}

function toggleAuthState(isAuthed) {
  if (isAuthed) {
    jobSection.classList.remove("locked");
    resultsSection.classList.remove("locked");
    submitBtn.disabled = false;
    refreshBtn.disabled = false;
    authGate.classList.add("hidden");
  } else {
    jobSection.classList.add("locked");
    resultsSection.classList.add("locked");
    submitBtn.disabled = true;
    refreshBtn.disabled = true;
    authGate.classList.remove("hidden");
  }
}

defaultDates();
setToken(null, null);
setStatus("Ready.");
activateTab("signup");
