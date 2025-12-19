const API_BASE = "http://127.0.0.1:8000";

let accessToken = null;
let lastJobId = null;
let currentUser = null;
let selectedBot = null;

const statusEl = document.getElementById("status");
const accountDisplayEl = document.getElementById("accountDisplay");
const jobIdEl = document.getElementById("jobId");
const metricsTableEl = document.getElementById("metricsTable");
const tradesTableEl = document.getElementById("tradesTable");
const authErrorEl = document.getElementById("authError");
const selectedBotEl = document.getElementById("selectedBot");
const testPanel = document.getElementById("testPanel");
const backToPicker = document.getElementById("backToPicker");

let equityChart = null;

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
const taskSelect = document.getElementById("task");
const modelSelect = document.getElementById("model_kind");
const loadingOverlay = document.getElementById("loadingOverlay");

// Model-task compatibility matrix
const MODEL_COMPATIBILITY = {
  logistic: ["classification"],
  random_forest: ["classification", "regression"],
  gboost: ["classification", "regression"],
  mlp: ["classification", "regression"],
  linear: ["regression"],
};

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

function showLoading(show) {
  if (loadingOverlay) {
    loadingOverlay.classList.toggle("hidden", !show);
  }
  if (submitBtn) {
    submitBtn.disabled = show;
    submitBtn.textContent = show ? "Running..." : "Run backtest";
  }
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
    console.error("API Error:", res.status, text);
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

async function devLogin() {
  try {
    const data = await api("/auth/dev-login", {
      method: "POST",
    });
    setToken(data.access_token, { username: "dev", email: "dev@localhost" });
    setStatus("Dev login successful.");
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
  past.setFullYear(past.getFullYear() - 4);  // 4 years for sufficient training data
  const startStr = past.toISOString().slice(0, 10);
  if (!endInput.value) endInput.value = endStr;
  if (!startInput.value) startInput.value = startStr;
}

function updateModelOptions() {
  if (!taskSelect || !modelSelect) return;

  const currentTask = taskSelect.value;
  const currentModel = modelSelect.value;

  // Clear and repopulate model options based on task compatibility
  const compatibleModels = Object.entries(MODEL_COMPATIBILITY)
    .filter(([model, tasks]) => tasks.includes(currentTask))
    .map(([model]) => model);

  modelSelect.innerHTML = "";
  compatibleModels.forEach(model => {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    if (model === currentModel && compatibleModels.includes(currentModel)) {
      opt.selected = true;
    }
    modelSelect.appendChild(opt);
  });

  // If current model is not compatible, select first compatible one
  if (!compatibleModels.includes(currentModel)) {
    modelSelect.value = compatibleModels[0] || "random_forest";
  }
}

function validateJobInputs() {
  const sel = tickerSelect ? tickerSelect.value : "";
  const custom = tickerCustom ? tickerCustom.value.trim() : "";

  // Check ticker
  if (!sel && !custom) {
    return { valid: false, error: "Please select or enter a ticker." };
  }
  if (sel === "custom" && !custom) {
    return { valid: false, error: "Please enter a custom ticker." };
  }

  // Check model-task compatibility
  const task = taskSelect ? taskSelect.value : "classification";
  const model = modelSelect ? modelSelect.value : "random_forest";

  if (!MODEL_COMPATIBILITY[model] || !MODEL_COMPATIBILITY[model].includes(task)) {
    return {
      valid: false,
      error: `Model "${model}" does not support "${task}" task. Please select a compatible model.`
    };
  }

  // Check dates
  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  if (!start || !end) {
    return { valid: false, error: "Please set start and end dates." };
  }
  if (new Date(start) >= new Date(end)) {
    return { valid: false, error: "End date must be after start date." };
  }

  return { valid: true };
}

async function submitJob() {
  if (!accessToken) {
    setStatus("Log in first.", "error");
    return;
  }

  // Validate inputs
  const validation = validateJobInputs();
  if (!validation.valid) {
    setStatus(validation.error, "error");
    return;
  }

  const sel = tickerSelect ? tickerSelect.value : "";
  const custom = tickerCustom ? tickerCustom.value.trim() : "";
  const tickers = [];
  if (sel && sel !== "custom") tickers.push(sel);
  if (sel === "custom" && custom) tickers.push(custom.toUpperCase());
  if (!sel && custom) tickers.push(custom.toUpperCase());

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

  console.log("Submitting payload:", JSON.stringify(payload, null, 2));

  try {
    showLoading(true);
    setStatus("Running backtest... This may take 30-60 seconds.");
    const data = await api("/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    lastJobId = data.job_id;
    jobIdEl.textContent = `Job ID: ${lastJobId}`;
    setStatus("Job finished. Loading results...");
    await fetchJobDetail(lastJobId);
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    showLoading(false);
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
    renderMetrics(data.summary);
    renderEquityChart(data.equity_curve);
    renderTradesTable(data.trades_head);
    setStatus("Results loaded.");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function renderMetrics(summary) {
  const trading = summary.trading_metrics || {};
  const mean = summary.mean_metrics || {};

  const metrics = [
    { label: "Cumulative Return", value: formatPercent(trading.cumulative_return) },
    { label: "Annualized Return (Arithmetic)", value: formatPercent(trading.annualized_return) },
    { label: "Annualized Volatility", value: formatPercent(trading.annualized_vol) },
    { label: "Sharpe Ratio", value: formatNumber(trading.sharpe) },
    { label: "Max Drawdown", value: formatPercent(trading.max_drawdown) },
    { label: "Hit Rate", value: formatPercent(trading.hit_rate) },
    { label: "Avg Trade Return", value: formatPercent(trading.avg_trade_return) },
    { label: "Cumulative Trading Costs", value: formatPercent(trading.total_cost) },
    { label: "Number of Trades", value: trading.num_trades || '-' },
  ];

  const html = `
    <table class="metrics-table">
      <tbody>
        ${metrics.map(m => `
          <tr>
            <td class="metric-label">${m.label}</td>
            <td class="metric-value ${getValueClass(m.value)}">${m.value}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  metricsTableEl.innerHTML = html;
}

function renderEquityChart(equityCurve) {
  const ctx = document.getElementById("equityChart").getContext("2d");

  if (equityChart) {
    equityChart.destroy();
  }

  const labels = equityCurve.map(p => p.date);
  const values = equityCurve.map(p => p.equity);

  equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Portfolio Value",
        data: values,
        borderColor: "#4ade80",
        backgroundColor: "rgba(74, 222, 128, 0.1)",
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Value: ${ctx.parsed.y.toFixed(4)}`
          }
        }
      },
      scales: {
        x: {
          display: true,
          ticks: {
            maxTicksLimit: 8,
            color: "#94a3b8"
          },
          grid: { color: "#1f2937" }
        },
        y: {
          display: true,
          ticks: { color: "#94a3b8" },
          grid: { color: "#1f2937" }
        }
      }
    }
  });
}

function renderTradesTable(trades) {
  if (!trades || trades.length === 0) {
    tradesTableEl.innerHTML = '<p class="muted-text">No trades to display</p>';
    return;
  }

  const columns = ["date", "ticker", "prediction", "target", "position", "net_return"];
  const headers = columns.map(c => `<th>${c}</th>`).join('');

  const rows = trades.slice(0, 50).map(t => `
    <tr>
      <td>${t.date || '-'}</td>
      <td>${t.ticker || '-'}</td>
      <td>${formatNumber(t.prediction)}</td>
      <td>${formatNumber(t.target)}</td>
      <td>${formatNumber(t.position)}</td>
      <td class="${t.net_return >= 0 ? 'positive' : 'negative'}">${formatPercent(t.net_return)}</td>
    </tr>
  `).join('');

  tradesTableEl.innerHTML = `
    <table class="trades-table">
      <thead><tr>${headers}</tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function formatPercent(val) {
  if (val === null || val === undefined || isNaN(val)) return '-';
  return (val * 100).toFixed(2) + '%';
}

function formatNumber(val) {
  if (val === null || val === undefined || isNaN(val)) return '-';
  return Number(val).toFixed(4);
}

function getValueClass(val) {
  if (val === '-') return '';
  const num = parseFloat(val);
  if (isNaN(num)) return '';
  if (num > 0) return 'positive';
  if (num < 0) return 'negative';
  return '';
}

document.getElementById("signup").addEventListener("click", signup);
document.getElementById("login").addEventListener("click", login);
document.getElementById("forgot").addEventListener("click", forgotPassword);
document.getElementById("devLogin").addEventListener("click", devLogin);
document.getElementById("devLoginSignup").addEventListener("click", devLogin);
document.getElementById("submitJob").addEventListener("click", submitJob);
document.getElementById("refreshJobs").addEventListener("click", fetchJobs);

// Task change updates model options
if (taskSelect) {
  taskSelect.addEventListener("change", updateModelOptions);
}

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

function backToEngines() {
  if (testPanel) testPanel.classList.add("hidden");
  selectedBot = null;
  if (selectedBotEl) selectedBotEl.textContent = "None selected";
  Array.from(botGrid.children).forEach((c) => c.classList.remove("selected"));
  setStatus("Pick an engine to continue.");
  window.scrollTo({ top: 0, behavior: "smooth" });
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
updateModelOptions(); // Initialize model options based on default task
if (backToPicker) backToPicker.addEventListener("click", backToEngines);
