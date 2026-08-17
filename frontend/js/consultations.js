let patientsCache = [];

(async () => {
  await renderLayout("consultations.html", "Consultations médicales");
  const content = document.getElementById("content");
  const isDoctor = window.CURRENT_USER?.role === "medecin";

  content.innerHTML = `
    <div class="table-toolbar">
      <div class="field" style="margin:0;">
        <input type="text" id="searchPatient" placeholder="🔍 Rechercher un patient..." style="min-width:260px;">
      </div>
      <div class="field" style="margin:0;">
        <select id="filterPatient" style="min-width:260px;"><option value="">Tous les patients</option></select>
      </div>
      ${isDoctor ? `<button class="btn btn-primary" onclick="openConsultModal()">+ Nouvelle consultation</button>` :
        `<span class="chip chip-gray">Lecture seule (secrétariat)</span>`}
    </div>
    <div class="card">
      <div id="consultList"></div>
    </div>
    ${consultModalHtml()}
  `;

  patientsCache = await apiFetch("/patients");
  const sel = document.getElementById("filterPatient");
  sel.innerHTML += patientsCache.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
  if (isDoctor) {
    document.getElementById("f_c_patient").innerHTML = patientsCache.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");
  }

  const preselect = new URLSearchParams(window.location.search).get("patient_id");
  if (preselect) {
    sel.value = preselect;
    if (isDoctor) { openConsultModal(); document.getElementById("f_c_patient").value = preselect; }
  }

  const searchInput = document.getElementById("searchPatient");
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = patientsCache.filter(p =>
      p.full_name.toLowerCase().includes(query) ||
      p.dossier_number.toLowerCase().includes(query)
    );
    sel.innerHTML = `<option value="">Tous les patients</option>` +
      filtered.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
  });

  sel.addEventListener("change", loadConsultations);
  document.getElementById("consultForm")?.addEventListener("submit", saveConsult);
  loadConsultations();
})();

async function loadConsultations() {
  const pid = document.getElementById("filterPatient").value;
  try {
    const consults = await apiFetch(`/consultations${pid ? "?patient_id=" + pid : ""}`);
    const el = document.getElementById("consultList");
    if (!consults.length) {
      el.innerHTML = `<div class="empty-state"><div class="ic">🩺</div>Aucune consultation enregistrée</div>`;
      return;
    }
    el.innerHTML = consults.map(c => `
      <div class="list-row" style="align-items:flex-start;">
        <div class="avatar">🩺</div>
        <div class="info">
          <div class="t1">${c.patient_name} <span style="color:#6B7280;font-weight:400;">— ${fmtDateTime(c.date)}</span></div>
          <div class="t2" style="margin-top:4px;line-height:1.6;">
            <strong>Symptômes:</strong> ${c.symptoms || "-"}<br>
            <strong>Diagnostic:</strong> ${c.diagnosis || "-"}<br>
            <strong>Traitement:</strong> ${c.treatment || "-"}
            ${c.follow_up_date ? `<br><strong>Suivi prévu:</strong> ${fmtDate(c.follow_up_date)}` : ""}
          </div>
        </div>
        <a class="btn btn-outline btn-sm" href="prescriptions.html?patient_id=${c.patient_id}&consultation_id=${c.id}">+ Ordonnance</a>
      </div>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

function consultModalHtml() {
  if (window.CURRENT_USER?.role !== "medecin") return "";
  return `
  <div class="modal-overlay" id="consultModal">
    <div class="modal modal-lg">
      <div class="modal-header"><h2>Nouvelle consultation</h2><button class="modal-close" onclick="closeModal('consultModal')">✕</button></div>
      <form id="consultForm">
        <div class="modal-body">
          <div class="form-grid">
            <div class="field full">
              <label>Rechercher un patient</label>
              <input type="text" id="searchModalPatient" placeholder="🔍 Tapez le nom ou numéro de dossier...">
            </div>
            <div class="field full"><label>Patient *</label><select id="f_c_patient" required></select></div>
            <div class="field full"><label>Symptômes</label><textarea id="f_c_symptoms" rows="2"></textarea></div>
            <div class="field full"><label>Diagnostic</label><textarea id="f_c_diagnosis" rows="2"></textarea></div>
            <div class="field full"><label>Observations cliniques</label><textarea id="f_c_obs" rows="2" placeholder="TA, FC, température..."></textarea></div>
            <div class="field full"><label>Traitement</label><textarea id="f_c_treatment" rows="2"></textarea></div>
            <div class="field"><label>Date de suivi</label><input type="date" id="f_c_followup"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('consultModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Enregistrer la consultation</button>
        </div>
      </form>
    </div>
  </div>`;
}

function openConsultModal() {
  document.getElementById("consultForm").reset();
  const patientSelect = document.getElementById("f_c_patient");
  patientSelect.innerHTML = patientsCache.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  const searchInput = document.getElementById("searchModalPatient");
  searchInput.value = "";
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = patientsCache.filter(p =>
      p.full_name.toLowerCase().includes(query) ||
      p.dossier_number.toLowerCase().includes(query)
    );
    patientSelect.innerHTML = filtered.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");
  });

  openModal("consultModal");
}

async function saveConsult(e) {
  e.preventDefault();
  const payload = {
    patient_id: document.getElementById("f_c_patient").value,
    symptoms: document.getElementById("f_c_symptoms").value,
    diagnosis: document.getElementById("f_c_diagnosis").value,
    clinical_observations: document.getElementById("f_c_obs").value,
    treatment: document.getElementById("f_c_treatment").value,
    follow_up_date: document.getElementById("f_c_followup").value || null,
  };
  try {
    await apiFetch("/consultations", { method: "POST", body: JSON.stringify(payload) });
    toast("Consultation enregistrée et liée au dossier du patient");
    closeModal("consultModal");
    loadConsultations();
  } catch (e) { toast(e.message, "error"); }
}
