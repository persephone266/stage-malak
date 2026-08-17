const API = "/api";

function isOnLoginPage() {
  const p = window.location.pathname;
  return p === "/" || p === "/index.html" || p.endsWith("/index.html");
}

async function apiFetch(path, options = {}) {
  const opts = { credentials: "include", headers: {}, ...options };
  if (options.body && !(options.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(API + path, opts);
  if (res.status === 401) {
    if (!isOnLoginPage()) {
      window.location.href = "/index.html";
    }
    throw new Error("Non authentifié");
  }
  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json() : null;
  if (!res.ok) {
    throw new Error((data && data.error) || "Une erreur est survenue");
  }
  return data;
}

function toast(message, type = "success") {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.style.cssText = "position:fixed;bottom:24px;right:24px;padding:13px 20px;border-radius:10px;color:white;font-size:13.5px;font-weight:600;z-index:999;box-shadow:0 8px 24px rgba(0,0,0,.18);transition:.3s;opacity:0;transform:translateY(10px);";
    document.body.appendChild(t);
  }
  t.style.background = type === "error" ? "#E5484D" : "#3BC896";
  t.textContent = message;
  t.style.opacity = "1";
  t.style.transform = "translateY(0)";
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateY(10px)"; }, 2800);
}

function fmtDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
function fmtDateTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" }) + " à " +
         d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
function initials(first, last) {
  return ((first || "?")[0] + (last || "?")[0]).toUpperCase();
}

const NAV_ITEMS = [
  { href: "dashboard.html", icon: "📊", label: "Tableau de bord" },
  { href: "patients.html", icon: "🧑‍🤝‍🧑", label: "Patients" },
  { href: "appointments.html", icon: "📅", label: "Rendez-vous" },
  { href: "consultations.html", icon: "🩺", label: "Consultations" },
  { href: "prescriptions.html", icon: "💊", label: "Ordonnances" },
  { href: "analyses.html", icon: "🧪", label: "Analyses" },
  { href: "payments.html", icon: "💳", label: "Paiements" },
  { href: "parametres.html", icon: "⚙️", label: "Paramètres" },
];

async function renderLayout(activePage, pageTitle) {
  let user;
  try {
    const r = await apiFetch("/auth/me");
    user = r.user;
  } catch (e) { return; }

  const navHtml = NAV_ITEMS.map(item => `
    <a class="nav-item ${activePage === item.href ? "active" : ""}" href="${item.href}">
      <span class="ic">${item.icon}</span><span>${item.label}</span>
    </a>`).join("");

  document.body.insertAdjacentHTML("afterbegin", `
    <div class="app">
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
          <div class="logo">🩺</div>
          <div>
            <span class="name">${user.clinic_name ? "Cabinet Médical" : "Cabinet Médical"}</span>
            <span class="role">Dr Chaima Ouled Bouallala</span>
          </div>
        </div>
        <nav class="nav-section">${navHtml}</nav>
        <div class="sidebar-footer">
          <div class="list-row" style="border:none;padding:8px 6px;">
            <div class="avatar">${initials(user.full_name?.split(" ")[0], user.full_name?.split(" ")[1])}</div>
            <div class="info">
              <div class="t1">${user.full_name}</div>
              <div class="t2">${user.role === "medecin" ? "Médecin" : "Secrétaire"}</div>
            </div>
          </div>
          <button class="btn btn-outline btn-sm" style="width:100%;margin-top:8px;" onclick="logout()">↩ Déconnexion</button>
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <h1>${pageTitle}</h1>
          <div class="actions">
            <div class="search-box">
              <span class="ic">🔍</span>
              <input type="text" id="globalSearch" placeholder="Rechercher un patient...">
              <div class="search-results" id="searchResults"></div>
            </div>
            <button class="icon-btn" id="notifBtn" onclick="window.location.href='dashboard.html#notifications'">
              🔔<span class="badge-dot" id="notifBadge" style="display:none;">0</span>
            </button>
          </div>
        </header>
        <main class="content" id="content"></main>
      </div>
    </div>
  `);

  window.CURRENT_USER = user;
  setupGlobalSearch();
  refreshNotifBadge();
}

function setupGlobalSearch() {
  const input = document.getElementById("globalSearch");
  const box = document.getElementById("searchResults");
  if (!input) return;
  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (!q) { box.style.display = "none"; return; }
    timer = setTimeout(async () => {
      try {
        const results = await apiFetch(`/search?q=${encodeURIComponent(q)}`);
        if (!results.length) {
          box.innerHTML = `<div style="color:#6B7280;">Aucun résultat</div>`;
        } else {
          box.innerHTML = results.map(p => `
            <div onclick="window.location.href='patient_profile.html?id=${p.id}'">
              <strong>${p.full_name}</strong> — ${p.dossier_number} · ${p.phone || ""}
            </div>`).join("");
        }
        box.style.display = "block";
      } catch (e) {}
    }, 300);
  });
  document.addEventListener("click", (e) => {
    if (!box.contains(e.target) && e.target !== input) box.style.display = "none";
  });
}

async function refreshNotifBadge() {
  try {
    const notifs = await apiFetch("/notifications");
    const unread = notifs.filter(n => !n.is_read).length;
    const badge = document.getElementById("notifBadge");
    if (badge) {
      if (unread > 0) { badge.style.display = "flex"; badge.textContent = unread; }
      else badge.style.display = "none";
    }
  } catch (e) {}
}

async function logout() {
  try { await apiFetch("/auth/logout", { method: "POST" }); } catch (e) {}
  window.location.href = "/index.html";
}

const CERTIFICATE_TYPES = [
  { type: "medical", label: "Certificat médical", visit: "Certificat médical" },
  { type: "repos", label: "Certificat de repos", visit: "Certificat de repos" },
  { type: "prenuptial", label: "Certificat prénuptial", visit: "Certificat prénuptial" },
];

function certificatesForVisitType(visitType) {
  const parts = (visitType || "").split(",").map(s => s.trim());
  return CERTIFICATE_TYPES.map(c => ({ ...c, suggested: parts.includes(c.visit) }));
}

function openCertificate(patientId, certType) {
  window.open(`${API}/patients/${patientId}/certificate/${certType}/pdf`, "_blank");
  closeModal("certChoiceModal");
}

function openCertificateChooser(patientId, patientName, visitType) {
  let modal = document.getElementById("certChoiceModal");
  if (!modal) {
    document.body.insertAdjacentHTML("beforeend", `
      <div class="modal-overlay" id="certChoiceModal">
        <div class="modal">
          <div class="modal-header">
            <h2>Imprimer un certificat</h2>
            <button class="modal-close" onclick="closeModal('certChoiceModal')">✕</button>
          </div>
          <div class="modal-body" id="certChoiceBody"></div>
        </div>
      </div>`);
    modal = document.getElementById("certChoiceModal");
  }
  document.getElementById("certChoiceBody").innerHTML = `
    <p style="color:#6B7280;font-size:13px;margin:0 0 14px;">Patient : <strong>${patientName}</strong></p>
    <div style="display:flex;flex-direction:column;gap:10px;">
      ${certificatesForVisitType(visitType).map(c => `
        <button class="btn ${c.suggested ? "btn-primary" : "btn-outline"}"
                onclick="openCertificate(${patientId}, '${c.type}')">
          📄 ${c.label}${c.suggested ? " ★" : ""}
        </button>`).join("")}
    </div>`;
  openModal("certChoiceModal");
}

function openModal(id) { document.getElementById(id).classList.add("show"); }
function closeModal(id) { document.getElementById(id).classList.remove("show"); }

function statusChip(status) {
  const map = {
    "Planifié": "chip-blue", "Terminé": "chip-green", "Annulé": "chip-red",
    "Active": "chip-green", "Expirée": "chip-red",
    "Payé": "chip-green", "Payée": "chip-green", "En attente": "chip-orange", "Remboursé": "chip-gray",
  };
  return `<span class="chip ${map[status] || "chip-gray"}">${status}</span>`;
}
