(async () => {
  await renderLayout("analyses.html", "Analyses de laboratoire");
  const content = document.getElementById("content");

  content.innerHTML = `
    <div class="table-toolbar">
      <div class="field" style="margin:0;">
        <select id="filterPatient" style="min-width:260px;"><option value="">Tous les patients</option></select>
      </div>
      <button class="btn btn-primary" onclick="openAnalysisModal()">+ Ajouter une analyse</button>
    </div>
    <div class="card"><div id="analysisList"></div></div>
    ${analysisModalHtml()}
  `;

  const patients = await apiFetch("/patients");
  const sel = document.getElementById("filterPatient");
  sel.innerHTML += patients.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
  document.getElementById("f_an_patient").innerHTML = patients.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  const preselect = new URLSearchParams(window.location.search).get("patient_id");
  if (preselect) { sel.value = preselect; openAnalysisModal(); document.getElementById("f_an_patient").value = preselect; }

  sel.addEventListener("change", loadAnalyses);
  document.getElementById("analysisForm").addEventListener("submit", saveAnalysis);
  loadAnalyses();
})();

async function loadAnalyses() {
  const pid = document.getElementById("filterPatient").value;
  try {
    const list = await apiFetch(`/analyses${pid ? "?patient_id=" + pid : ""}`);
    const el = document.getElementById("analysisList");
    if (!list.length) {
      el.innerHTML = `<div class="empty-state"><div class="ic">🧪</div>Aucune analyse enregistrée</div>`;
      return;
    }
    el.innerHTML = list.map(a => `
      <div class="list-row" style="align-items:flex-start;">
        <div class="avatar">🧪</div>
        <div class="info">
          <div class="t1">${a.analysis_name} — ${a.patient_name} <span style="color:#6B7280;font-weight:400;">(${fmtDate(a.date)})</span></div>
          <div class="t2" style="margin-top:4px;"><strong>Résultat:</strong> ${a.result || "-"} ${a.comments ? "· " + a.comments : ""}</div>
        </div>
        ${a.file_path ? `<a class="btn btn-outline btn-sm" href="/api/analyses/${a.id}/file" target="_blank">📎 Voir fichier</a>` : ""}
      </div>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

function analysisModalHtml() {
  return `
  <div class="modal-overlay" id="analysisModal">
    <div class="modal">
      <div class="modal-header"><h2>Ajouter une analyse</h2><button class="modal-close" onclick="closeModal('analysisModal')">✕</button></div>
      <form id="analysisForm" enctype="multipart/form-data">
        <div class="modal-body">
          <div class="form-grid">
            <div class="field full"><label>Patient *</label><select id="f_an_patient" required></select></div>
            <div class="field full"><label>Nom de l'analyse *</label><input type="text" id="f_an_name" required placeholder="ex: Bilan lipidique"></div>
            <div class="field full"><label>Résultat</label><textarea id="f_an_result" rows="2"></textarea></div>
            <div class="field full"><label>Commentaires</label><textarea id="f_an_comments" rows="2"></textarea></div>
            <div class="field full"><label>Fichier joint (PDF / Image)</label><input type="file" id="f_an_file" accept=".pdf,.png,.jpg,.jpeg,.gif"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('analysisModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Enregistrer</button>
        </div>
      </form>
    </div>
  </div>`;
}

function openAnalysisModal() {
  document.getElementById("analysisForm").reset();
  openModal("analysisModal");
}

async function saveAnalysis(e) {
  e.preventDefault();
  const fd = new FormData();
  fd.append("patient_id", document.getElementById("f_an_patient").value);
  fd.append("analysis_name", document.getElementById("f_an_name").value);
  fd.append("result", document.getElementById("f_an_result").value);
  fd.append("comments", document.getElementById("f_an_comments").value);
  const file = document.getElementById("f_an_file").files[0];
  if (file) fd.append("file", file);
  try {
    await apiFetch("/analyses", { method: "POST", body: fd });
    toast("Analyse enregistrée");
    closeModal("analysisModal");
    loadAnalyses();
  } catch (e) { toast(e.message, "error"); }
}
