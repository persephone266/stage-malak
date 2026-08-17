const params = new URLSearchParams(window.location.search);
const patientId = params.get("id");

(async () => {
  await renderLayout("patients.html", "Profil du patient");
  const content = document.getElementById("content");
  if (!patientId) { content.innerHTML = `<div class="empty-state">Patient introuvable</div>`; return; }

  try {
    const p = await apiFetch(`/patients/${patientId}`);
    content.innerHTML = `
      <div class="card" style="margin-bottom:18px;">
        <div class="profile-header">
          <div class="avatar">${initials(p.first_name, p.last_name)}</div>
          <div style="flex:1;">
            <h2>${p.full_name}</h2>
            <p>Dossier ${p.dossier_number} · ${p.age ?? "-"} ans · ${p.gender} ${p.blood_group ? "· " + p.blood_group : ""}</p>
          </div>
          <button class="btn btn-outline" onclick="editPatientRedirect()">✏️ Modifier</button>
          <a class="btn btn-primary" href="consultations.html?patient_id=${p.id}">+ Nouvelle consultation</a>
        </div>
      </div>

      <div class="tabs">
        <button type="button" class="tab-btn active" data-ptab="tabInfo">Informations</button>
        <button type="button" class="tab-btn" data-ptab="tabDossier">Dossier médical</button>
        <button type="button" class="tab-btn" data-ptab="tabAssurance">Assurance</button>
      </div>

      <div class="tab-content active" id="tabInfo">
        <div class="card">
          <h3>Informations personnelles</h3>
          <div class="info-grid">
            <div class="info-item"><div class="k">CIN</div><div class="v">${p.cin || "-"}</div></div>
            <div class="info-item"><div class="k">Téléphone</div><div class="v">${p.phone || "-"}</div></div>
            <div class="info-item"><div class="k">Email</div><div class="v">${p.email || "-"}</div></div>
            <div class="info-item"><div class="k">Date de naissance</div><div class="v">${fmtDate(p.date_of_birth)}</div></div>
            <div class="info-item"><div class="k">Adresse</div><div class="v">${p.address || "-"}</div></div>
            <div class="info-item"><div class="k">Contact d'urgence</div><div class="v">${p.emergency_contact || "-"}</div></div>
          </div>
        </div>
        <div class="card" style="margin-top:18px;">
          <h3>Informations médicales</h3>
          <div class="info-grid">
            <div class="info-item"><div class="k">Type de visite</div><div class="v">${p.visit_type || "-"}</div></div>
            <div class="info-item"><div class="k">Allergies</div><div class="v">${p.allergies || "Aucune"}</div></div>
            <div class="info-item"><div class="k">Maladies chroniques</div><div class="v">${p.chronic_diseases || "Aucune"}</div></div>
            <div class="info-item"><div class="k">Chirurgies antérieures</div><div class="v">${p.previous_surgeries || "Aucune"}</div></div>
            <div class="info-item"><div class="k">Vaccination</div><div class="v">${p.vaccination_notes || "-"}</div></div>
            <div class="info-item full" style="grid-column:1/-1;"><div class="k">Notes médicales</div><div class="v">${p.medical_notes || "-"}</div></div>
          </div>
        </div>
        ${certificatesCardHtml(p)}
      </div>

      <div class="tab-content" id="tabDossier">
        <div class="card">
          <h3>Historique chronologique</h3>
          <div class="timeline" id="timeline"><div class="empty-state">Chargement...</div></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:14px;">
          <a class="btn btn-outline" href="prescriptions.html?patient_id=${p.id}">💊 Nouvelle ordonnance</a>
          <a class="btn btn-outline" href="analyses.html?patient_id=${p.id}">🧪 Ajouter une analyse</a>
          <a class="btn btn-outline" href="payments.html?patient_id=${p.id}">💳 Enregistrer un paiement</a>
        </div>
      </div>

      <div class="tab-content" id="tabAssurance">
        <div class="card">
          <h3>Informations d'assurance</h3>
          <div class="info-grid">
            <div class="info-item"><div class="k">Type d'assurance</div><div class="v">${p.insurance_type}</div></div>
            <div class="info-item"><div class="k">Numéro</div><div class="v">${p.insurance_number || "-"}</div></div>
            <div class="info-item"><div class="k">Date d'expiration</div><div class="v">${fmtDate(p.insurance_expiration)}</div></div>
            <div class="info-item"><div class="k">Statut</div><div class="v">${statusChip(p.insurance_status)}</div></div>
          </div>
        </div>
      </div>
    `;

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.ptab).classList.add("active");
      });
    });

    loadTimeline(p.id);
  } catch (e) {
    content.innerHTML = `<div class="empty-state">Erreur : ${e.message}</div>`;
  }
})();

async function loadTimeline(id) {
  try {
    const records = await apiFetch(`/patients/${id}/medical-record`);
    const el = document.getElementById("timeline");
    if (!records.length) {
      el.innerHTML = `<div class="empty-state"><div class="ic">📋</div>Aucun élément dans le dossier médical</div>`;
      return;
    }
    const icons = { "Consultation": "🩺", "Ordonnance": "💊", "Analyse": "🧪", "Certificat": "📄" };
    el.innerHTML = records.map(r => {
      let desc = "";
      if (r.type === "Consultation" && r.details) {
        desc = `Symptômes: ${r.details.symptoms || "-"}<br>Diagnostic: ${r.details.diagnosis || "-"}<br>Traitement: ${r.details.treatment || "-"}`;
      } else if (r.type === "Ordonnance" && r.details) {
        desc = r.details.medicines.map(m => `${m.name} — ${m.dosage || ""}`).join("<br>");
      } else if (r.type === "Analyse" && r.details) {
        desc = `Résultat: ${r.details.result || "-"}<br>Commentaire: ${r.details.comments || "-"}`;
      }
      return `
        <div class="timeline-item">
          <div class="date">${fmtDateTime(r.date)}</div>
          <div class="title">${icons[r.type] || "📌"} ${r.title || r.type}</div>
          ${desc ? `<div class="desc">${desc}</div>` : ""}
        </div>`;
    }).join("");
  } catch (e) { toast(e.message, "error"); }
}

function certificatesCardHtml(p) {
  const certs = certificatesForVisitType(p.visit_type);
  return `
    <div class="card" style="margin-top:18px;">
      <h3>Certificats à imprimer</h3>
      <p style="color:#6B7280;font-size:13px;margin:4px 0 12px;">
        Le PDF s'ouvre pré-rempli (nom, date de naissance, docteur), prêt à imprimer.
      </p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        ${certs.map(c => `
          <button class="btn ${c.suggested ? "btn-primary" : "btn-outline"}"
                  onclick="openCertificate(${p.id}, '${c.type}')">
            📄 ${c.label}${c.suggested ? " ★" : ""}
          </button>`).join("")}
      </div>
    </div>`;
}

function editPatientRedirect() {
  window.location.href = `patients.html?edit=${patientId}`;
}
