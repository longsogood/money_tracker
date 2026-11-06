const API = "";
let passcode = sessionStorage.getItem("passcode") || "";
let currentYear, currentMonth;
let pieChart = null, barChart = null, trendChart = null;
let categoriesCache = [];
let modalType = "expense";

const today = new Date();
currentYear = today.getFullYear();
currentMonth = today.getMonth() + 1;

const fmtMoney = v => new Intl.NumberFormat("vi-VN").format(Math.round(v)) + "đ";

// Theme
const savedTheme = localStorage.getItem("theme");
if (savedTheme === "light") document.documentElement.dataset.theme = "light";
document.getElementById("theme-toggle").addEventListener("click", () => {
  const light = document.documentElement.dataset.theme === "light";
  document.documentElement.dataset.theme = light ? "" : "light";
  localStorage.setItem("theme", light ? "dark" : "light");
  document.getElementById("theme-toggle").textContent = light ? "☀️" : "🌙";
  if (trendChart) loadTrend(); // vẽ lại với màu mới
});

function showApp() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app-screen").classList.remove("hidden");
  loadCategories();
  loadSummary();
  loadTxList();
}

document.getElementById("login-btn").addEventListener("click", tryLogin);
document.getElementById("passcode-input").addEventListener("keydown", e => {
  if (e.key === "Enter") tryLogin();
});

async function tryLogin() {
  const input = document.getElementById("passcode-input");
  const err = document.getElementById("login-error");
  try {
    const res = await fetch(`${API}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode: input.value }),
    });
    if (!res.ok) throw new Error();
    passcode = input.value;
    sessionStorage.setItem("passcode", passcode);
    showApp();
  } catch {
    err.textContent = "Sai mã truy cập";
    err.classList.remove("hidden");
  }
}

if (passcode) showApp();

document.getElementById("prev-month").addEventListener("click", () => shiftMonth(-1));
document.getElementById("next-month").addEventListener("click", () => shiftMonth(1));

function shiftMonth(delta) {
  currentMonth += delta;
  if (currentMonth > 12) { currentMonth = 1; currentYear++; }
  if (currentMonth < 1) { currentMonth = 12; currentYear--; }
  loadSummary();
}

async function loadSummary() {
  document.getElementById("month-label").textContent = `Tháng ${currentMonth}/${currentYear}`;

  const res = await fetch(`${API}/api/summary?year=${currentYear}&month=${currentMonth}&passcode=${encodeURIComponent(passcode)}`);
  const data = await res.json();

  document.getElementById("total-expense").textContent = fmtMoney(data.total_expense);
  document.getElementById("total-income").textContent = fmtMoney(data.total_income);

  renderCompare(data);
  renderBudget(data);
  renderPie(data.by_category);
  renderDailyBar(data.transactions);
  renderTopSpends(data.transactions);
  renderList(data.transactions);
  calTxByDay = new Map();
  for (const t of data.transactions) {
    if (!calTxByDay.has(t.occurred_at)) calTxByDay.set(t.occurred_at, []);
    calTxByDay.get(t.occurred_at).push(t);
  }
  renderCalendar();
  loadTrend();
}

function renderCompare(data) {
  const expEl = document.getElementById("compare-expense");
  const incEl = document.getElementById("compare-income");
  const prevExp = data.prev_total_expense || 0;
  const prevInc = data.prev_total_income || 0;

  const diffExp = data.total_expense - prevExp;
  if (prevExp === 0 && data.total_expense === 0) {
    expEl.textContent = "";
  } else if (prevExp === 0) {
    expEl.textContent = "Tháng trước: 0đ";
    expEl.className = "sub up";
  } else {
    const pct = Math.round(diffExp / prevExp * 100);
    expEl.textContent = `${diffExp >= 0 ? "▲" : "▼"} ${Math.abs(pct)}% vs tháng trước`;
    expEl.className = "sub " + (diffExp >= 0 ? "up" : "down");
  }

  const diffInc = data.total_income - prevInc;
  if (prevInc === 0 && data.total_income === 0) {
    incEl.textContent = "";
  } else if (prevInc === 0) {
    incEl.textContent = "Tháng trước: 0đ";
    incEl.className = "sub";
  } else {
    const pct = Math.round(diffInc / prevInc * 100);
    incEl.textContent = `${diffInc >= 0 ? "▲" : "▼"} ${Math.abs(pct)}% vs tháng trước`;
    incEl.className = "sub";
  }
}

function renderBudget(data) {
  const el = document.getElementById("budget-bar");
  if (!data.budget) { el.classList.add("hidden"); return; }
  el.classList.remove("hidden");
  const pct = Math.min(data.total_expense / data.budget * 100, 100);
  const fill = document.getElementById("budget-fill");
  fill.style.width = pct + "%";
  fill.className = "budget-fill" + (pct >= 100 ? " over" : pct >= 80 ? " warn" : "");
  document.getElementById("budget-label").textContent =
    `🎯 Đã chi ${fmtMoney(data.total_expense)} / ${fmtMoney(data.budget)} (${Math.round(data.total_expense / data.budget * 100)}%)`;
}

async function loadTrend() {
  const res = await fetch(`${API}/api/trend?passcode=${encodeURIComponent(passcode)}`);
  const data = await res.json();
  const ctx = document.getElementById("trend-chart").getContext("2d");
  if (trendChart) trendChart.destroy();
  const textColor = document.documentElement.dataset.theme === "light" ? "#6b6b80" : "#8a8aa5";
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.months,
      datasets: [{
        label: "Chi tiêu",
        data: data.expenses,
        borderColor: "#6c5ce7",
        backgroundColor: "rgba(108,92,231,0.15)",
        fill: true,
        tension: 0.35,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: textColor, font: { size: 10 } } },
        y: { ticks: { color: textColor, font: { size: 9 }, callback: v => v >= 1e6 ? (v / 1e6) + "tr" : v >= 1e3 ? (v / 1e3) + "k" : v } },
      },
    },
  });
}

function renderTopSpends(txs) {
  const section = document.getElementById("top-spends");
  const expenses = txs.filter(t => t.type === "expense")
    .sort((a, b) => Number(b.amount) - Number(a.amount))
    .slice(0, 5);
  if (expenses.length < 3) { section.classList.add("hidden"); return; }
  section.classList.remove("hidden");
  document.getElementById("top-items").innerHTML = expenses.map((t, i) => {
    const cat = t.categories ? `${t.categories.emoji || ""} ${t.categories.name}` : "❓ Khác";
    return `<div class="top-item">
      <span><span class="rank">#${i + 1}</span> ${cat} — ${t.note || ""}</span>
      <span class="amount expense">${fmtMoney(Number(t.amount))}</span>
    </div>`;
  }).join("");
}

const PALETTE = ["#6c5ce7", "#ff6b6b", "#4ecdc4", "#feca57", "#ff9ff3", "#54a0ff", "#5f27cd", "#1dd1a1"];

function renderPie(byCategory) {
  const ctx = document.getElementById("pie-chart").getContext("2d");
  if (pieChart) pieChart.destroy();
  if (!byCategory.length) {
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    return;
  }
  pieChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: byCategory.map(([c]) => c),
      datasets: [{
        data: byCategory.map(([, v]) => v),
        backgroundColor: byCategory.map((_, i) => PALETTE[i % PALETTE.length]),
        borderColor: "#16213e",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#e8e8f0", boxWidth: 12, font: { size: 11 } } },
      },
    },
  });
}

function renderDailyBar(txs) {
  const ctx = document.getElementById("bar-chart").getContext("2d");
  if (barChart) barChart.destroy();

  const days = new Map();
  for (const t of txs) {
    if (t.type !== "expense") continue;
    const day = t.occurred_at.slice(8, 10);
    days.set(day, (days.get(day) || 0) + Number(t.amount));
  }

  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  const labels = Array.from({ length: daysInMonth }, (_, i) => String(i + 1).padStart(2, "0"));
  const values = labels.map(d => days.get(d) || 0);

  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Chi theo ngày",
        data: values,
        backgroundColor: "#6c5ce7",
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8a8aa5", font: { size: 9 }, maxTicksLimit: 10 } },
        y: { ticks: { color: "#8a8aa5", font: { size: 9 } } },
      },
    },
  });
}

function renderList(txs) {
  const el = document.getElementById("tx-items");
  if (!txs.length) {
    el.innerHTML = '<div class="empty">Chưa có giao dịch nào trong tháng này</div>';
    return;
  }
  el.innerHTML = txs.map(t => {
    const cat = t.categories ? `${t.categories.emoji || ""} ${t.categories.name}` : "❓ Khác";
    const sign = t.type === "income" ? "+" : "-";
    const cls = t.type;
    const badge = `<span class="badge ${cls}">${t.type === "income" ? "THU" : "CHI"}</span>`;
    const thumb = t.image_url ? `<img class="thumb" src="${t.image_url}" onclick="openLightbox('${t.image_url}')" alt="hóa đơn">` : "";
    return `<div class="tx-item">
      ${thumb}
      <div class="info">
        <div class="cat">${badge}${cat}</div>
        <div class="note">${t.note || ""}</div>
        <div class="date">${t.occurred_at}</div>
      </div>
      <div class="amount ${cls}">${sign}${fmtMoney(Number(t.amount))}</div>
      <button class="delete-btn" onclick="deleteTx('${t.id}')">🗑️</button>
    </div>`;
  }).join("");
}

async function deleteTx(id) {
  if (!confirm("Xóa giao dịch này?")) return;
  await fetch(`${API}/api/transactions/${id}?passcode=${encodeURIComponent(passcode)}`, { method: "DELETE" });
  loadSummary();
  loadTxList();
}

// ---------- Filter & search ----------
let searchTimer;
document.getElementById("search-input").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadTxList, 300);
});
document.getElementById("category-filter").addEventListener("change", loadTxList);

async function loadTxList() {
  const q = document.getElementById("search-input").value.trim();
  const cat = document.getElementById("category-filter").value;
  const params = new URLSearchParams({ passcode, limit: 100 });
  if (q) params.set("q", q);
  if (cat) params.set("category", cat);
  const res = await fetch(`${API}/api/transactions?${params}`);
  const data = await res.json();
  renderList(data.data);
}

async function loadCategories() {
  const res = await fetch(`${API}/api/categories?passcode=${encodeURIComponent(passcode)}`);
  const data = await res.json();
  categoriesCache = data.data;
  const filterEl = document.getElementById("category-filter");
  const modalEl = document.getElementById("modal-category");
  filterEl.innerHTML = '<option value="">Tất cả nhóm</option>' +
    data.data.map(c => `<option value="${c.id}">${c.emoji || ""} ${c.name}</option>`).join("");
  modalEl.innerHTML = '<option value="">Chưa phân loại</option>' +
    data.data.map(c => `<option value="${c.id}">${c.emoji || ""} ${c.name}</option>`).join("");
}

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
  document.getElementById("tab-" + btn.dataset.tab).classList.remove("hidden");
  if (btn.dataset.tab === "calendar") renderCalendar();
  window.scrollTo(0, 0);
}));

// ---------- Calendar view ----------
let calTxByDay = null;

const fmtShort = v => {
  if (v >= 1e6) return (v / 1e6).toFixed(v % 1e6 ? 1 : 0) + "tr";
  if (v >= 1e3) return Math.round(v / 1e3) + "k";
  return Math.round(v);
};

function renderCalendar() {
  if (!calTxByDay) return;
  const grid = document.getElementById("cal-grid");
  const firstDay = new Date(currentYear, currentMonth - 1, 1);
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  // thứ 2 = index 0
  let startOffset = (firstDay.getDay() + 6) % 7;
  const todayStr = new Date().toISOString().slice(0, 10);

  let html = "";
  for (let i = 0; i < startOffset; i++) html += '<div class="cal-day empty"></div>';

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const txs = calTxByDay.get(dateStr) || [];
    const hasExpense = txs.some(t => t.type === "expense");
    const hasIncome = txs.some(t => t.type === "income");
    const dayTx = txs[0]; // ảnh đầu tiên của ngày làm nền

    let cls = "cal-day";
    if (dateStr === todayStr) cls += " today";
    if (dayTx && dayTx.image_url) cls += " has-img";

    let style = "";
    if (dayTx && dayTx.image_url) style = ` style="--bg-img:url('${dayTx.image_url}')"`;

    let amounts = "";
    if (hasExpense) {
      const total = txs.filter(t => t.type === "expense").reduce((s, t) => s + Number(t.amount), 0);
      amounts += `<span class="cal-exp">-${fmtShort(total)}</span>`;
    }
    if (hasIncome) {
      const total = txs.filter(t => t.type === "income").reduce((s, t) => s + Number(t.amount), 0);
      amounts += `<span class="cal-inc">+${fmtShort(total)}</span>`;
    }

    html += `<div class="${cls}"${style}>
      <span class="day-num">${d}</span>
      <div class="cal-amounts">${amounts}</div>
    </div>`;
  }
  grid.innerHTML = html;
}
document.getElementById("add-btn").addEventListener("click", () => {
  document.getElementById("modal-date").value = `${currentYear}-${String(currentMonth).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;
  document.getElementById("add-modal").classList.remove("hidden");
});
document.getElementById("modal-cancel").addEventListener("click", () => {
  document.getElementById("add-modal").classList.add("hidden");
});
document.querySelectorAll(".seg").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".seg").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  modalType = btn.dataset.type;
}));
document.getElementById("modal-save").addEventListener("click", async () => {
  const amount = parseFloat(document.getElementById("modal-amount").value);
  if (!amount || amount <= 0) { alert("Nhập số tiền hợp lệ"); return; }
  await fetch(`${API}/api/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      passcode,
      amount,
      type: modalType,
      note: document.getElementById("modal-note").value.trim(),
      category_id: document.getElementById("modal-category").value || null,
      occurred_at: document.getElementById("modal-date").value || null,
    }),
  });
  document.getElementById("add-modal").classList.add("hidden");
  document.getElementById("modal-amount").value = "";
  document.getElementById("modal-note").value = "";
  loadSummary();
  loadTxList();
});

function openLightbox(url) {
  const lb = document.createElement("div");
  lb.id = "lightbox";
  lb.innerHTML = `<img src="${url}">`;
  lb.addEventListener("click", () => lb.remove());
  document.body.appendChild(lb);
}
