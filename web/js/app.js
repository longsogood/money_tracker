const API = "";
let passcode = sessionStorage.getItem("passcode") || "";
let currentYear, currentMonth;
let pieChart = null, barChart = null;

const today = new Date();
currentYear = today.getFullYear();
currentMonth = today.getMonth() + 1;

const fmtMoney = v => new Intl.NumberFormat("vi-VN").format(Math.round(v)) + "đ";

function showApp() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app-screen").classList.remove("hidden");
  loadSummary();
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

  renderPie(data.by_category);
  renderDailyBar(data.transactions);
  renderList(data.transactions);
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
    const thumb = t.image_url ? `<img class="thumb" src="${t.image_url}" onclick="openLightbox('${t.image_url}')" alt="hóa đơn">` : "";
    return `<div class="tx-item">
      ${thumb}
      <div class="info">
        <div class="cat">${cat}</div>
        <div class="note">${t.note || ""}</div>
        <div class="date">${t.occurred_at}</div>
      </div>
      <div class="amount ${cls}">${sign}${fmtMoney(Number(t.amount))}</div>
    </div>`;
  }).join("");
}

function openLightbox(url) {
  const lb = document.createElement("div");
  lb.id = "lightbox";
  lb.innerHTML = `<img src="${url}">`;
  lb.addEventListener("click", () => lb.remove());
  document.body.appendChild(lb);
}
