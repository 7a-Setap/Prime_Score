/* =========================
   CONFIG
========================= */
const API_BASE = "http://localhost:5000";

/* =========================
   HELPERS
========================= */
async function apiFetch(url, options = {}) {
  const res = await fetch(API_BASE + url, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }

  return res.json();
}

const qs = id => document.getElementById(id);

/* =========================
   NAVIGATION
========================= */
function navigateTo(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));

  qs(page + "Page")?.classList.add("active");
  document.querySelector(`[data-page="${page}"]`)?.classList.add("active");
}

/* =========================
   AUTH
========================= */
async function handleLogin(e) {
  e.preventDefault();

  const username = qs("loginUsername").value;
  const password = qs("loginPassword").value;

  try {
    const data = await apiFetch("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });

    qs("usernameDisplay").textContent = data.username;
    qs("welcomeName").textContent = data.username;

    if (data.first_time_user) {
      qs("firstTimeMessage").style.display = "block";
    }

    loadHome();
    navigateTo("home");
  } catch (err) {
    qs("loginError").textContent = "Invalid login";
  }
}

async function handleRegister(e) {
  e.preventDefault();

  const username = qs("registerUsername").value;
  const password = qs("registerPassword").value;

  try {
    await apiFetch("/api/register", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });

    alert("Registered! Please login.");
  } catch (err) {
    qs("registerError").textContent = err.message;
  }
}

async function logout() {
  await apiFetch("/api/logout", { method: "POST" });
  location.reload();
}

/* =========================
   HOME
========================= */
async function loadHome() {
  const data = await apiFetch("/api/home-screen");

  renderMatches(data.live_matches, "liveMatchesHome");
  renderMatches(data.upcoming_fixtures, "upcomingFixturesHome");
  renderMatches(data.recent_results, "recentResultsHome");
}

/* =========================
   MATCHES
========================= */
function renderMatches(matches, containerId) {
  const el = qs(containerId);
  if (!el) return;

  el.innerHTML = "";

  if (!matches || matches.length === 0) {
    el.innerHTML = "<p>No data available</p>";
    return;
  }

  matches.forEach(m => {
    const card = document.createElement("div");
    card.className = "match-card";
    card.innerHTML = `
      <strong>${m.home_team} vs ${m.away_team}</strong>
      <p>${m.status}</p>
    `;
    card.onclick = () => openMatchModal(m.match_id);
    el.appendChild(card);
  });
}

/* =========================
   LIVE / FIXTURES / RESULTS
========================= */
async function loadLiveMatches() {
  const data = await apiFetch("/api/matches/live");
  renderMatches(data.matches, "liveMatchesList");
}

async function loadFixtures() {
  const data = await apiFetch("/api/fixtures");
  renderMatches(data.fixtures, "fixturesList");
}

async function loadResults() {
  const data = await apiFetch("/api/results");
  renderMatches(data.results, "resultsList");
}

/* =========================
   MODAL
========================= */
async function openMatchModal(id) {
  const m = await apiFetch(`/api/matches/${id}`);

  qs("matchDetailContent").innerHTML = `
    <h3>${m.home_team} vs ${m.away_team}</h3>
    <p>Status: ${m.status}</p>
    <p>Score: ${m.home_score} - ${m.away_score}</p>
  `;

  qs("matchModal").classList.add("show");
}

function closeMatchModal() {
  qs("matchModal").classList.remove("show");
}

/* =========================
   INIT
========================= */
document.addEventListener("DOMContentLoaded", () => {
  qs("loginForm")?.addEventListener("submit", handleLogin);
  qs("registerForm")?.addEventListener("submit", handleRegister);
  qs("logoutBtn")?.addEventListener("click", logout);

  navigateTo("login");
});
