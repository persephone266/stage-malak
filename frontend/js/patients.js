let editingPatientId = null;
let loadedPatients = [];
let insuredOnly = false;

const VISIT_TYPES = [
  "Consultation",
  "Contrôle",
  "Certificat médical",
  "Certificat de repos",
  "Certificat prénuptial",
  "Suivi de grossesse",
  "Autre",
];

(async () => {
  await renderLayout("patients.html", "Gestion des patients");
  const content = document.getElementById("content");

  content.innerHTML = `
    <div class="table-toolbar">
      <div class="search-box">
        <span class="ic">🔍</span>
        <input type="text" id="tableSearch" placeholder="Nom, N° dossier, CIN, téléphone...">
      </div>
      <div class="view-toggle">
        <button id="btnAllPatients" class="active" onclick="switchInsuranceFilter(false)">👥 Tous</button>
        <button id="btnInsuredPatients" onclick="switchInsuranceFilter(true)">🛡️ Avec assurance</button>
      </div>
      <button class="btn btn-primary" onclick="openPatientModal()">+ Ajouter un patient</button>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Dossier</th><th>Nom complet</th><th>Âge</th><th>Genre</th>
            <th>Téléphone</th><th>Assurance</th><th>Statut</th><th></th>
          </tr></thead>
          <tbody id="patientsBody"></tbody>
        </table>
      </div>
      <div id="emptyPatients"></div>
    </div>

    ${patientModalHtml()}
  `;

  document.getElementById("tableSearch").addEventListener("input", debounce(loadPatients, 300));
  loadPatients();
  document.getElementById("patientForm").addEventListener("submit", savePatient);

  const editId = new URLSearchParams(window.location.search).get("edit");
  if (editId) editPatient(editId);
})();

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

async function loadPatients() {
  const q = document.getElementById("tableSearch").value.trim();
  const params = new URLSearchParams();
  if (q) params.set("search", q);
  if (insuredOnly) params.set("insured", "1");
  try {
    const patients = await apiFetch(`/patients${params.toString() ? "?" + params : ""}`);
    loadedPatients = patients;
    const body = document.getElementById("patientsBody");
    const empty = document.getElementById("emptyPatients");
    if (!patients.length) {
      body.innerHTML = "";
      empty.innerHTML = `<div class="empty-state"><div class="ic">🧑‍🤝‍🧑</div>${
        insuredOnly ? "Aucun patient avec assurance" : "Aucun patient trouvé"}</div>`;
      return;
    }
    empty.innerHTML = "";
    body.innerHTML = patients.map(p => `
      <tr>
        <td><strong>${p.dossier_number}</strong></td>
        <td>
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="avatar">${initials(p.first_name, p.last_name)}</div>
            <div>${p.full_name}</div>
          </div>
        </td>
        <td>${p.age ?? "-"}</td>
        <td>${p.gender}</td>
        <td>${p.phone || "-"}</td>
        <td>${p.insurance_type}</td>
        <td>${statusChip(p.insurance_status)}</td>
        <td style="white-space:nowrap;">
          <button class="btn btn-outline btn-sm" title="Imprimer un certificat"
                  onclick="chooseCertificate(${p.id})">📄</button>
          <a class="btn btn-outline btn-sm" href="patient_profile.html?id=${p.id}">Voir</a>
          <button class="btn btn-outline btn-sm" onclick="editPatient(${p.id})">Modifier</button>
          <button class="btn btn-danger btn-sm" onclick="deletePatient(${p.id})">Suppr.</button>
        </td>
      </tr>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

function switchInsuranceFilter(onlyInsured) {
  insuredOnly = onlyInsured;
  document.getElementById("btnAllPatients").classList.toggle("active", !onlyInsured);
  document.getElementById("btnInsuredPatients").classList.toggle("active", onlyInsured);
  loadPatients();
}

function patientModalHtml() {
  return `
  <div class="modal-overlay" id="patientModal">
    <div class="modal modal-lg">
      <div class="modal-header">
        <h2 id="patientModalTitle">Ajouter un patient</h2>
        <button class="modal-close" onclick="closeModal('patientModal')">✕</button>
      </div>
      <form id="patientForm">
        <div class="modal-body">
          <div class="tabs">
            <button type="button" class="tab-btn active" data-tab="tabPerso">Informations personnelles</button>
            <button type="button" class="tab-btn" data-tab="tabMed">Informations médicales</button>
            <button type="button" class="tab-btn" data-tab="tabAssur">Assurance</button>
          </div>

          <div class="tab-content active" id="tabPerso">
            <div class="form-grid">
              <div class="field"><label>Prénom *</label><input type="text" id="f_first_name" required></div>
              <div class="field"><label>Nom *</label><input type="text" id="f_last_name" required></div>
              <div class="field"><label>CIN</label><input type="text" id="f_cin"></div>
              <div class="field"><label>Téléphone</label><input type="text" id="f_phone"></div>
              <div class="field"><label>Email</label><input type="email" id="f_email"></div>
              <div class="field"><label>Date de naissance</label><input type="date" id="f_dob"></div>
              <div class="field"><label>Genre *</label>
                <select id="f_gender" required><option value="Homme">Homme</option><option value="Femme">Femme</option></select>
              </div>
              <div class="field"><label>Groupe sanguin</label>
                <select id="f_blood"><option value="">-</option>${["A+","A-","B+","B-","AB+","AB-","O+","O-"].map(b=>`<option>${b}</option>`).join("")}</select>
              </div>
              <div class="field full"><label>Adresse</label><input type="text" id="f_address"></div>
              <div class="field full"><label>Contact d'urgence</label><input type="text" id="f_emergency" placeholder="Nom - Téléphone"></div>
            </div>
          </div>

          <div class="tab-content" id="tabMed">
            <div class="form-grid">
              <div class="field full">
                <label>Type de visite</label>
                <div class="checkbox-grid" id="f_visit_type">
                  ${VISIT_TYPES.map(t => `
                    <label class="checkbox-item">
                      <input type="checkbox" name="visit_type" value="${t}"> <span>${t}</span>
                    </label>`).join("")}
                </div>
                <input type="text" id="f_visit_other" class="mt-8" placeholder="Préciser (si Autre)">
              </div>
              <div class="field full"><label>Allergies</label><textarea id="f_allergies" rows="2"></textarea></div>
              <div class="field full"><label>Maladies chroniques</label><textarea id="f_chronic" rows="2"></textarea></div>
              <div class="field full"><label>Chirurgies antérieures</label><textarea id="f_surgeries" rows="2"></textarea></div>
              <div class="field full"><label>Notes de vaccination</label><textarea id="f_vaccination" rows="2"></textarea></div>
              <div class="field full"><label>Notes médicales</label><textarea id="f_notes" rows="2"></textarea></div>
            </div>
          </div>

          <div class="tab-content" id="tabAssur">
            <div class="form-grid">
              <div class="field"><label>Type d'assurance</label>
                <select id="f_ins_type">
                  ${["Aucune","CNSS","AMO","CNOPS","Assurance Privée"].map(t=>`<option>${t}</option>`).join("")}
                </select>
              </div>
              <div class="field"><label>Numéro d'assurance</label><input type="text" id="f_ins_number"></div>
              <div class="field"><label>Date d'expiration</label><input type="date" id="f_ins_exp"></div>
              <div class="field"><label>Statut</label>
                <select id="f_ins_status"><option>Active</option><option>Expirée</option></select>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('patientModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Enregistrer</button>
        </div>
      </form>
    </div>
  </div>`;
}

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("tab-btn")) {
    const parent = e.target.closest(".modal-body");
    parent.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    parent.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    e.target.classList.add("active");
    parent.querySelector("#" + e.target.dataset.tab).classList.add("active");
  }
});

function getVisitType() {
  const checked = [...document.querySelectorAll('#f_visit_type input:checked')].map(i => i.value);
  const other = document.getElementById("f_visit_other").value.trim();
  if (other) {
    const i = checked.indexOf("Autre");
    if (i !== -1) checked[i] = `Autre : ${other}`;
    else checked.push(`Autre : ${other}`);
  }
  return checked.join(", ");
}

function setVisitType(value) {
  const parts = (value || "").split(",").map(s => s.trim()).filter(Boolean);
  const other = parts.find(p => p.startsWith("Autre :"));
  document.getElementById("f_visit_other").value = other ? other.slice(7).trim() : "";
  document.querySelectorAll('#f_visit_type input').forEach(cb => {
    cb.checked = parts.includes(cb.value) || (cb.value === "Autre" && Boolean(other));
  });
}

function openPatientModal() {
  editingPatientId = null;
  document.getElementById("patientModalTitle").textContent = "Ajouter un patient";
  document.getElementById("patientForm").reset();
  openModal("patientModal");
}

async function editPatient(id) {
  try {
    const p = await apiFetch(`/patients/${id}`);
    editingPatientId = id;
    document.getElementById("patientModalTitle").textContent = "Modifier le patient";
    document.getElementById("f_first_name").value = p.first_name || "";
    document.getElementById("f_last_name").value = p.last_name || "";
    document.getElementById("f_cin").value = p.cin || "";
    document.getElementById("f_phone").value = p.phone || "";
    document.getElementById("f_email").value = p.email || "";
    document.getElementById("f_dob").value = p.date_of_birth || "";
    document.getElementById("f_gender").value = p.gender;
    document.getElementById("f_blood").value = p.blood_group || "";
    document.getElementById("f_address").value = p.address || "";
    document.getElementById("f_emergency").value = p.emergency_contact || "";
    setVisitType(p.visit_type);
    document.getElementById("f_allergies").value = p.allergies || "";
    document.getElementById("f_chronic").value = p.chronic_diseases || "";
    document.getElementById("f_surgeries").value = p.previous_surgeries || "";
    document.getElementById("f_vaccination").value = p.vaccination_notes || "";
    document.getElementById("f_notes").value = p.medical_notes || "";
    document.getElementById("f_ins_type").value = p.insurance_type || "Aucune";
    document.getElementById("f_ins_number").value = p.insurance_number || "";
    document.getElementById("f_ins_exp").value = p.insurance_expiration || "";
    document.getElementById("f_ins_status").value = p.insurance_status || "Active";
    openModal("patientModal");
  } catch (e) { toast(e.message, "error"); }
}

async function savePatient(e) {
  e.preventDefault();
  const payload = {
    first_name: document.getElementById("f_first_name").value,
    last_name: document.getElementById("f_last_name").value,
    cin: document.getElementById("f_cin").value,
    phone: document.getElementById("f_phone").value,
    email: document.getElementById("f_email").value,
    date_of_birth: document.getElementById("f_dob").value || null,
    gender: document.getElementById("f_gender").value,
    blood_group: document.getElementById("f_blood").value,
    address: document.getElementById("f_address").value,
    emergency_contact: document.getElementById("f_emergency").value,
    visit_type: getVisitType(),
    allergies: document.getElementById("f_allergies").value,
    chronic_diseases: document.getElementById("f_chronic").value,
    previous_surgeries: document.getElementById("f_surgeries").value,
    vaccination_notes: document.getElementById("f_vaccination").value,
    medical_notes: document.getElementById("f_notes").value,
    insurance_type: document.getElementById("f_ins_type").value,
    insurance_number: document.getElementById("f_ins_number").value,
    insurance_expiration: document.getElementById("f_ins_exp").value || null,
    insurance_status: document.getElementById("f_ins_status").value,
  };
  try {
    if (editingPatientId) {
      await apiFetch(`/patients/${editingPatientId}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("Patient mis à jour");
    } else {
      await apiFetch("/patients", { method: "POST", body: JSON.stringify(payload) });
      toast("Patient ajouté");
    }
    closeModal("patientModal");
    loadPatients();
  } catch (e) { toast(e.message, "error"); }
}

function chooseCertificate(id) {
  const p = loadedPatients.find(x => x.id === id);
  if (p) openCertificateChooser(p.id, p.full_name, p.visit_type);
}

async function deletePatient(id) {
  if (!confirm("Supprimer définitivement ce patient et tout son dossier médical ?")) return;
  try {
    await apiFetch(`/patients/${id}`, { method: "DELETE" });
    toast("Patient supprimé");
    loadPatients();
  } catch (e) { toast(e.message, "error"); }
}
