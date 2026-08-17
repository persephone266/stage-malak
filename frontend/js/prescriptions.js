let medRowCount = 0;

(async () => {
  await renderLayout("prescriptions.html", "Ordonnances médicales");
  const content = document.getElementById("content");
  const isDoctor = window.CURRENT_USER?.role === "medecin";

  content.innerHTML = `
    <div class="table-toolbar">
      <div class="field" style="margin:0;">
        <select id="filterPatient" style="min-width:260px;"><option value="">Tous les patients</option></select>
      </div>
      ${isDoctor ? `<button class="btn btn-primary" onclick="openPrescModal()">+ Nouvelle ordonnance</button>` : ""}
    </div>
    <div class="card"><div id="prescList"></div></div>
    ${isDoctor ? prescModalHtml() : ""}
  `;

  const patients = await apiFetch("/patients");
  const sel = document.getElementById("filterPatient");
  sel.innerHTML += patients.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
  if (isDoctor) document.getElementById("f_p_patient").innerHTML = patients.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  const preselect = new URLSearchParams(window.location.search).get("patient_id");
  if (preselect) {
    sel.value = preselect;
    if (isDoctor) { openPrescModal(); document.getElementById("f_p_patient").value = preselect; }
  }

  sel.addEventListener("change", loadPrescriptions);
  document.getElementById("prescForm")?.addEventListener("submit", savePrescription);
  loadPrescriptions();
})();

async function loadPrescriptions() {
  const pid = document.getElementById("filterPatient").value;
  try {
    const list = await apiFetch(`/prescriptions${pid ? "?patient_id=" + pid : ""}`);
    const el = document.getElementById("prescList");
    if (!list.length) {
      el.innerHTML = `<div class="empty-state"><div class="ic">💊</div>Aucune ordonnance enregistrée</div>`;
      return;
    }
    el.innerHTML = list.map(p => `
      <div class="list-row" style="align-items:flex-start;">
        <div class="avatar">💊</div>
        <div class="info">
          <div class="t1">${p.patient_name} <span style="color:#6B7280;font-weight:400;">— ${fmtDate(p.date)}</span></div>
          <div class="t2" style="margin-top:4px;">${p.medicines.map(m => `${m.name} (${m.dosage || "-"}, ${m.duration || "-"})`).join(" · ")}</div>
        </div>
        <a class="btn btn-outline btn-sm" href="/api/prescriptions/${p.id}/pdf" target="_blank">🖨️ Imprimer / PDF</a>
      </div>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

function prescModalHtml() {
  return `
  <div class="modal-overlay" id="prescModal">
    <div class="modal modal-lg">
      <div class="modal-header"><h2>Nouvelle ordonnance</h2><button class="modal-close" onclick="closeModal('prescModal')">✕</button></div>
      <form id="prescForm">
        <div class="modal-body">
          <div class="field full" style="margin-bottom:16px;"><label>Patient *</label><select id="f_p_patient" required></select></div>
          <label style="font-size:13px;font-weight:600;">Médicaments</label>
          <div id="medicinesContainer" style="margin-top:10px;"></div>
          <button type="button" class="btn btn-outline btn-sm" onclick="addMedicineRow()">+ Ajouter un médicament</button>
          <div class="field full" style="margin-top:16px;"><label>Instructions générales</label><textarea id="f_p_instructions" rows="2"></textarea></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('prescModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Créer l'ordonnance</button>
        </div>
      </form>
    </div>
  </div>`;
}

function openPrescModal() {
  document.getElementById("prescForm").reset();
  document.getElementById("medicinesContainer").innerHTML = "";
  addMedicineRow();
  openModal("prescModal");
}

function addMedicineRow() {
  medRowCount++;
  const div = document.createElement("div");
  div.className = "medicine-row";
  div.id = `medrow-${medRowCount}`;
  div.innerHTML = `
    <input type="text" placeholder="Nom du médicament *" class="med-name" required>
    <input type="text" placeholder="Posologie" class="med-dosage">
    <input type="text" placeholder="Durée" class="med-duration">
    <input type="text" placeholder="Instructions" class="med-instructions">
    <button type="button" class="btn btn-danger btn-sm" onclick="document.getElementById('medrow-${medRowCount}').remove()">✕</button>
  `;
  document.getElementById("medicinesContainer").appendChild(div);
}

async function savePrescription(e) {
  e.preventDefault();
  const rows = document.querySelectorAll(".medicine-row");
  const medicines = Array.from(rows).map(r => ({
    name: r.querySelector(".med-name").value,
    dosage: r.querySelector(".med-dosage").value,
    duration: r.querySelector(".med-duration").value,
    instructions: r.querySelector(".med-instructions").value,
  })).filter(m => m.name.trim());

  if (!medicines.length) { toast("Ajoutez au moins un médicament", "error"); return; }

  const params = new URLSearchParams(window.location.search);
  const payload = {
    patient_id: document.getElementById("f_p_patient").value,
    consultation_id: params.get("consultation_id") || null,
    instructions: document.getElementById("f_p_instructions").value,
    medicines,
  };
  try {
    const created = await apiFetch("/prescriptions", { method: "POST", body: JSON.stringify(payload) });
    toast("Ordonnance créée");
    closeModal("prescModal");
    loadPrescriptions();
    window.open(`/api/prescriptions/${created.id}/pdf`, "_blank");
  } catch (e) { toast(e.message, "error"); }
}
