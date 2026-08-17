let currentView = "table";
let calMonth = new Date().getMonth();
let calYear = new Date().getFullYear();
let allAppointments = [];
let allPatientsCache = [];
let editingApptId = null;

(async () => {
  await renderLayout("appointments.html", "Gestion des rendez-vous");
  const content = document.getElementById("content");
  content.innerHTML = `
    <div class="table-toolbar">
      <div class="field" style="margin:0;">
        <input type="text" id="searchPatient" placeholder="🔍 Rechercher un patient..." style="min-width:260px;">
      </div>
      <div class="field" style="margin:0;">
        <select id="filterPatient" style="min-width:200px;"><option value="">Tous les patients</option></select>
      </div>
      <div class="view-toggle">
        <button id="btnTableView" class="active" onclick="switchView('table')">📋 Tableau</button>
        <button id="btnCalView" onclick="switchView('calendar')">📅 Calendrier</button>
      </div>
      <button class="btn btn-primary" onclick="openApptModal()">+ Nouveau rendez-vous</button>
    </div>
    <div class="card" id="tableView">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Patient</th><th>Date</th><th>Heure</th><th>Motif</th><th>Statut</th><th></th></tr></thead>
          <tbody id="apptBody"></tbody>
        </table>
      </div>
      <div id="emptyAppts"></div>
    </div>
    <div class="card" id="calendarView" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <button class="btn btn-outline btn-sm" onclick="changeMonth(-1)">← Précédent</button>
        <h3 id="calLabel" style="margin:0;"></h3>
        <button class="btn btn-outline btn-sm" onclick="changeMonth(1)">Suivant →</button>
      </div>
      <div class="calendar-grid" id="calendarGrid"></div>
    </div>

    ${apptModalHtml()}
  `;
  allPatientsCache = await apiFetch("/patients");
  document.getElementById("f_a_patient").innerHTML = allPatientsCache.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  const filterSel = document.getElementById("filterPatient");
  filterSel.innerHTML += allPatientsCache.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");

  const searchInput = document.getElementById("searchPatient");
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = allPatientsCache.filter(p =>
      p.full_name.toLowerCase().includes(query) ||
      p.dossier_number.toLowerCase().includes(query)
    );
    filterSel.innerHTML = `<option value="">Tous les patients</option>` +
      filtered.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
    filterAppointments();
  });

  filterSel.addEventListener("change", filterAppointments);

  const preselect = new URLSearchParams(window.location.search).get("patient_id");
  if (preselect) { openApptModal(); document.getElementById("f_a_patient").value = preselect; }

  document.getElementById("apptForm").addEventListener("submit", saveAppt);
  loadAppointments();
})();

function switchView(v) {
  currentView = v;
  document.getElementById("btnTableView").classList.toggle("active", v === "table");
  document.getElementById("btnCalView").classList.toggle("active", v === "calendar");
  document.getElementById("tableView").style.display = v === "table" ? "block" : "none";
  document.getElementById("calendarView").style.display = v === "calendar" ? "block" : "none";
  if (v === "calendar") renderCalendar();
}

async function loadAppointments() {
  try {
    allAppointments = await apiFetch("/appointments");
    filterAppointments();
  } catch (e) { toast(e.message, "error"); }
}

function filterAppointments() {
  const filterId = document.getElementById("filterPatient").value;
  const filtered = filterId ? allAppointments.filter(a => a.patient_id == filterId) : allAppointments;
  const body = document.getElementById("apptBody");
  const empty = document.getElementById("emptyAppts");
  if (!filtered.length) {
    body.innerHTML = "";
    empty.innerHTML = `<div class="empty-state"><div class="ic">📅</div>Aucun rendez-vous</div>`;
    return;
  }
  empty.innerHTML = "";
  body.innerHTML = filtered.map(a => `
    <tr>
      <td><strong>${a.patient_name}</strong></td>
      <td>${fmtDate(a.date)}</td>
      <td>${a.time}</td>
      <td>${a.reason || "-"}</td>
      <td>${statusChip(a.status)}</td>
      <td style="white-space:nowrap;">
        <button class="btn btn-outline btn-sm" onclick="editAppt(${a.id})">Modifier</button>
        ${a.status === "Planifié" ? `<button class="btn btn-outline btn-sm" onclick="cancelAppt(${a.id})">Annuler</button>` : ""}
        <button class="btn btn-danger btn-sm" onclick="deleteAppt(${a.id})">Suppr.</button>
      </td>
    </tr>`).join("");
}

function renderCalendar() {
  const label = new Date(calYear, calMonth, 1).toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
  document.getElementById("calLabel").textContent = label.charAt(0).toUpperCase() + label.slice(1);
  const grid = document.getElementById("calendarGrid");
  const dows = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"];
  let html = dows.map(d => `<div class="dow">${d}</div>`).join("");

  const firstDay = new Date(calYear, calMonth, 1);
  let startOffset = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const todayStr = new Date().toISOString().slice(0, 10);

  for (let i = 0; i < startOffset; i++) html += `<div></div>`;
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const dayAppts = allAppointments.filter(a => a.date === dateStr);
    html += `<div class="calendar-cell ${dateStr === todayStr ? "today" : ""}">
      <div class="day-num">${d}</div>
      ${dayAppts.slice(0, 3).map(a => `<div class="appt-pill" title="${a.patient_name} - ${a.reason || ''}">${a.time} ${a.patient_name}</div>`).join("")}
      ${dayAppts.length > 3 ? `<div style="font-size:10px;color:#6B7280;">+${dayAppts.length - 3} autres</div>` : ""}
    </div>`;
  }
  grid.innerHTML = html;
}

function changeMonth(delta) {
  calMonth += delta;
  if (calMonth < 0) { calMonth = 11; calYear--; }
  if (calMonth > 11) { calMonth = 0; calYear++; }
  renderCalendar();
}

function apptModalHtml() {
  return `
  <div class="modal-overlay" id="apptModal">
    <div class="modal">
      <div class="modal-header"><h2 id="apptModalTitle">Nouveau rendez-vous</h2><button class="modal-close" onclick="closeModal('apptModal')">✕</button></div>
      <form id="apptForm">
        <div class="modal-body">
          <div class="form-grid">
            <div class="field full">
              <label>Rechercher un patient</label>
              <input type="text" id="searchModalPatient" placeholder="🔍 Tapez le nom ou numéro de dossier...">
            </div>
            <div class="field full"><label>Patient *</label><select id="f_a_patient" required></select></div>
            <div class="field"><label>Date *</label><input type="date" id="f_a_date" required></div>
            <div class="field"><label>Heure *</label><input type="time" id="f_a_time" required></div>
            <div class="field full"><label>Motif</label><input type="text" id="f_a_reason" placeholder="ex: Consultation générale"></div>
            <div class="field full"><label>Statut</label>
              <select id="f_a_status"><option>Planifié</option><option>Terminé</option><option>Annulé</option></select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('apptModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Enregistrer</button>
        </div>
      </form>
    </div>
  </div>`;
}

function openApptModal() {
  editingApptId = null;
  document.getElementById("apptModalTitle").textContent = "Nouveau rendez-vous";
  document.getElementById("apptForm").reset();
  document.getElementById("f_a_date").value = new Date().toISOString().slice(0, 10);

  const patientSelect = document.getElementById("f_a_patient");
  patientSelect.innerHTML = allPatientsCache.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  const searchInput = document.getElementById("searchModalPatient");
  searchInput.value = "";
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = allPatientsCache.filter(p =>
      p.full_name.toLowerCase().includes(query) ||
      p.dossier_number.toLowerCase().includes(query)
    );
    patientSelect.innerHTML = filtered.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");
  });

  openModal("apptModal");
}

function editAppt(id) {
  const a = allAppointments.find(x => x.id === id);
  editingApptId = id;
  document.getElementById("apptModalTitle").textContent = "Modifier le rendez-vous";
  document.getElementById("f_a_patient").value = a.patient_id;
  document.getElementById("f_a_date").value = a.date;
  document.getElementById("f_a_time").value = a.time;
  document.getElementById("f_a_reason").value = a.reason || "";
  document.getElementById("f_a_status").value = a.status;
  openModal("apptModal");
}

async function saveAppt(e) {
  e.preventDefault();
  const payload = {
    patient_id: document.getElementById("f_a_patient").value,
    date: document.getElementById("f_a_date").value,
    time: document.getElementById("f_a_time").value,
    reason: document.getElementById("f_a_reason").value,
    status: document.getElementById("f_a_status").value,
  };
  try {
    if (editingApptId) {
      await apiFetch(`/appointments/${editingApptId}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("Rendez-vous mis à jour");
    } else {
      await apiFetch("/appointments", { method: "POST", body: JSON.stringify(payload) });
      toast("Rendez-vous créé");
    }
    closeModal("apptModal");
    loadAppointments();
  } catch (e) { toast(e.message, "error"); }
}

async function cancelAppt(id) {
  try {
    await apiFetch(`/appointments/${id}`, { method: "PUT", body: JSON.stringify({ status: "Annulé" }) });
    toast("Rendez-vous annulé");
    loadAppointments();
  } catch (e) { toast(e.message, "error"); }
}

async function deleteAppt(id) {
  if (!confirm("Supprimer ce rendez-vous ?")) return;
  try {
    await apiFetch(`/appointments/${id}`, { method: "DELETE" });
    toast("Rendez-vous supprimé");
    loadAppointments();
  } catch (e) { toast(e.message, "error"); }
}
