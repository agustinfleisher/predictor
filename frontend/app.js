const API_BASE = "http://127.0.0.1:8000";

let accessToken = null;
let lastJobId = null;
let currentUser = null;
let selectedBot = null;

const statusEl = document.getElementById("status");
const accountDisplayEl = document.getElementById("accountDisplay");
const jobIdEl = document.getElementById("jobId");
const summaryEl = document.getElementById("summary");
const equityEl = document.getElementById("equity");
const tradesEl = document.getElementById("trades");
const authErrorEl = document.getElementById("authError");
const selectedBotEl = document.getElementById("selectedBot");
const testPanel = document.getElementById("testPanel");
const backToPicker = document.getElementById("backToPicker");
const backToPicker = document.getElementById("backToPicker");

const tabSignup = document.getElementById("tabSignup");
const tabLogin = document.getElementById("tabLogin");
const tabForgot = document.getElementById("tabForgot");
const forms = {
  signup: document.getElementById("signupForm"),
  login: document.getElementById("loginForm"),
  forgot: document.getElementById("forgotForm"),
};
const openSignupBtn = document.getElementById("openSignup");
const openLoginBtn = document.getElementById("openLogin");
const jobSection = document.getElementById("jobSection");
const resultsSection = document.getElementById("resultsSection");
const authGate = document.getElementById("authGate");
const submitBtn = document.getElementById("submitJob");
const refreshBtn = document.getElementById("refreshJobs");
const appShell = document.getElementById("appShell");
const authOverlay = document.getElementById("authOverlay");
const botGrid = document.getElementById("botGrid");
const tickerSelect = document.getElementById("tickerSelect");
const tickerCustom = document.getElementById("tickerCustom");

const bots = [
  { name: "Nova", desc: "Mixed-model baseline for general conditions." },
  { name: "Quanta", desc: "Probability-first engine for directional calls." },
  { name: "Pulse", desc: "Lightweight, momentum-tilted scout." },
  { name: "Aegis", desc: "Defensive, risk-aware entries with tighter screens." },
  { name: "Sentinel", desc: "Pattern detector keyed to recurring regimes." },
  { name: "Archive", desc: "History-heavy recall for mean-reverting signals." },
  { name: "Vector", desc: "Momentum explorer with trend bias." },
  { name: "Covenant", desc: "Rule-based, conservative entries; fewer trades." },
  { name: "Helm", desc: "Regime-aware steering with volatility gating." },
  { name: "Aurora", desc: "Ensembles multiple views for stability." },
];

const topTickers = [
  "AAPL","MSFT","AMZN","NVDA","GOOGL","GOOG","META","TSLA","BRK.B","UNH",
  "JNJ","JPM","V","XOM","PG","MA","HD","CVX","PFE","AVGO",
  "COST","PEP","KO","ABBV","NFLX","ADBE","CRM","AMD","INTC","WMT"
];

function setStatus(msg, type = "info") {
  statusEl.textContent = msg;
  statusEl.style.color = type === "error" ? "#f87171" : "#4ade80";
}

function setAuthError(msg) {
  if (!authErrorEl) return;
  authErrorEl.textContent = msg || "";
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
    setAuthError("Username, email, and password required.");
    return;
  }
  try {
    const data = await api("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
    setToken(data.access_token, { username, email });
    setStatus("Signed up and logged in.");
    setAuthError("");
  } catch (err) {
    setStatus(err.message, "error");
    setAuthError(err.message);
  }
}

async function login() {
  const identifier = document.getElementById("li_identifier").value.trim();
  const password = document.getElementById("li_password").value;
  if (!identifier || !password) {
    setStatus("Username/email and password required.", "error");
    setAuthError("Username/email and password required.");
    return;
  }
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    });
    setToken(data.access_token, { username: identifier, email: identifier });
    setStatus("Logged in.");
    setAuthError("");
  } catch (err) {
    setStatus(err.message, "error");
    setAuthError(err.message);
  }
}

async function forgotPassword() {
  const identifier = document.getElementById("fp_identifier").value.trim();
  if (!identifier) {
    setStatus("Username or email required.", "error");
    setAuthError("Username or email required.");
    return;
  }
  try {
    await api("/auth/forgot_password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
    setStatus("If the account exists, a reset token was sent.");
    setAuthError("");
  } catch (err) {
    setStatus(err.message, "error");
    setAuthError(err.message);
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
  const sel = tickerSelect ? tickerSelect.value : "";
  const custom = tickerCustom ? tickerCustom.value.trim() : "";
  const tickers = [];
  if (sel && sel !== "custom") tickers.push(sel);
  if (sel === "custom" && custom) tickers.push(custom.toUpperCase());
  if (!tickers.length) {
    setStatus("Choose a ticker.", "error");
    return;
  }
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
  Object.entries(forms).forEach(([key, el]) => {
    if (name === key) {
      el.classList.add("active");
    } else {
      el.classList.remove("active");
    }
  });
}

function toggleAuthState(isAuthed) {
  if (isAuthed) {
    authOverlay.classList.add("hidden");
    appShell.classList.remove("hidden");
    jobSection.classList.remove("locked");
    resultsSection.classList.remove("locked");
    submitBtn.disabled = false;
    refreshBtn.disabled = false;
    authGate.classList.add("hidden");
  } else {
    authOverlay.classList.remove("hidden");
    appShell.classList.add("hidden");
    jobSection.classList.add("locked");
    resultsSection.classList.add("locked");
    submitBtn.disabled = true;
    refreshBtn.disabled = true;
    authGate.classList.remove("hidden");
  }
}

function renderBots() {
  if (!botGrid) return;
  botGrid.innerHTML = "";
  bots.forEach((b) => {
    const card = document.createElement("div");
    card.className = "bot-card";
    card.innerHTML = `<div class="bot-name">${b.name}</div><div class="bot-desc">${b.desc}</div>`;
    card.addEventListener("click", () => selectBot(b.name, card));
    botGrid.appendChild(card);
  });
}

function selectBot(name, cardEl) {
  selectedBot = name;
  if (selectedBotEl) selectedBotEl.textContent = `Selected: ${name}`;
  Array.from(botGrid.children).forEach((c) => c.classList.remove("selected"));
  if (cardEl) cardEl.classList.add("selected");
  if (testPanel) {
    testPanel.classList.remove("hidden");
    window.scrollTo({ top: testPanel.offsetTop - 40, behavior: "smooth" });
  }
  setStatus(`Selected ${name}. Choose a ticker, set dates, and run.`);
}

function renderTickers() {
  if (!tickerSelect) return;
  tickerSelect.innerHTML = "";
  const defaultOpt = document.createElement("option");
  defaultOpt.value = "";
  defaultOpt.textContent = "Choose a ticker";
  tickerSelect.appendChild(defaultOpt);
  topTickers.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    tickerSelect.appendChild(opt);
  });
  const customOpt = document.createElement("option");
  customOpt.value = "custom";
  customOpt.textContent = "Custom...";
  tickerSelect.appendChild(customOpt);
}

defaultDates();
setToken(null, null);
setStatus("Ready.");
activateTab("signup");
renderBots();
renderTickers();
if (backToPicker) backToPicker.addEventListener("click", backToEngines);
