(async () => {
  await renderLayout("parametres.html", "Paramètres");
  const content = document.getElementById("content");
  const isDoctor = window.CURRENT_USER?.role === "medecin";

  content.innerHTML = `
    <div class="grid-2">
      <div class="card">
        <h3>Profil & Informations du cabinet</h3>
        <form id="settingsForm">
          <div class="form-grid">
            <div class="field"><label>Nom complet</label><input type="text" id="s_full_name" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Email</label><input type="email" id="s_email" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Téléphone</label><input type="text" id="s_phone" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Spécialité</label><input type="text" id="s_specialite" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Frais de consultation (MAD)</label><input type="number" step="0.01" id="s_fee" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Nom du cabinet</label><input type="text" id="s_clinic_name" ${isDoctor ? "" : "disabled"}></div>
            <div class="field full"><label>Adresse du cabinet</label><input type="text" id="s_clinic_address" ${isDoctor ? "" : "disabled"}></div>
            <div class="field"><label>Téléphone du cabinet</label><input type="text" id="s_clinic_phone" ${isDoctor ? "" : "disabled"}></div>
          </div>
          ${isDoctor ? `<button type="submit" class="btn btn-primary" style="margin-top:18px;">Enregistrer les modifications</button>` :
            `<p style="margin-top:14px;color:#6B7280;font-size:13px;">Seul le médecin peut modifier ces informations.</p>`}
        </form>
      </div>
      <div class="card">
        <h3>Changer le mot de passe</h3>
        <form id="pwForm">
          <div class="field"><label>Mot de passe actuel</label><input type="password" id="pw_current" required></div>
          <div class="field"><label>Nouveau mot de passe</label><input type="password" id="pw_new" required minlength="6"></div>
          <div class="field"><label>Confirmer le nouveau mot de passe</label><input type="password" id="pw_confirm" required minlength="6"></div>
          <button type="submit" class="btn btn-primary" style="width:100%;">Mettre à jour le mot de passe</button>
        </form>
      </div>
    </div>

    ${isDoctor ? `
    <div class="card" style="margin-top:18px;">
      <h3>💾 Sauvegarde des données</h3>
      <p style="font-size:13px;color:#6B7280;margin-bottom:16px;">
        Une sauvegarde automatique de la base de données est effectuée une fois par jour à l'ouverture de l'application
        (les 30 dernières sont conservées). Vous pouvez aussi créer et télécharger une sauvegarde manuelle à tout moment.
      </p>
      <button class="btn btn-primary" id="btnDownloadNow">⬇️ Télécharger une sauvegarde maintenant</button>
      <div style="margin-top:20px;">
        <h3 style="font-size:14px;">Historique des sauvegardes</h3>
        <div id="backupList" class="table-wrap"></div>
      </div>
    </div>` : ""}
  `;

  try {
    const s = await apiFetch("/settings");
    document.getElementById("s_full_name").value = s.full_name || "";
    document.getElementById("s_email").value = s.email || "";
    document.getElementById("s_phone").value = s.phone || "";
    document.getElementById("s_specialite").value = s.specialite || "";
    document.getElementById("s_fee").value = s.consultation_fee || "";
    document.getElementById("s_clinic_name").value = s.clinic_name || "";
    document.getElementById("s_clinic_address").value = s.clinic_address || "";
    document.getElementById("s_clinic_phone").value = s.clinic_phone || "";
  } catch (e) { toast(e.message, "error"); }

  if (isDoctor) {
    document.getElementById("settingsForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        full_name: document.getElementById("s_full_name").value,
        email: document.getElementById("s_email").value,
        phone: document.getElementById("s_phone").value,
        specialite: document.getElementById("s_specialite").value,
        consultation_fee: parseFloat(document.getElementById("s_fee").value) || 0,
        clinic_name: document.getElementById("s_clinic_name").value,
        clinic_address: document.getElementById("s_clinic_address").value,
        clinic_phone: document.getElementById("s_clinic_phone").value,
      };
      try {
        await apiFetch("/settings", { method: "PUT", body: JSON.stringify(payload) });
        toast("Paramètres mis à jour");
      } catch (e) { toast(e.message, "error"); }
    });
  }

  document.getElementById("pwForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const newPw = document.getElementById("pw_new").value;
    const confirmPw = document.getElementById("pw_confirm").value;
    if (newPw !== confirmPw) { toast("Les mots de passe ne correspondent pas", "error"); return; }
    try {
      await apiFetch("/auth/change-password", {
        method: "PUT",
        body: JSON.stringify({ current_password: document.getElementById("pw_current").value, new_password: newPw }),
      });
      toast("Mot de passe mis à jour");
      document.getElementById("pwForm").reset();
    } catch (e) { toast(e.message, "error"); }
  });

  if (isDoctor) {
    document.getElementById("btnDownloadNow").addEventListener("click", () => {
      window.open("/api/backup/download-now", "_blank");
      toast("Sauvegarde en cours de téléchargement...");
      setTimeout(loadBackups, 1200);
    });
    loadBackups();
  }
})();

async function loadBackups() {
  const el = document.getElementById("backupList");
  if (!el) return;
  try {
    const backups = await apiFetch("/backup/list");
    if (!backups.length) {
      el.innerHTML = `<div class="empty-state">Aucune sauvegarde pour le moment</div>`;
      return;
    }
    el.innerHTML = `
      <table>
        <thead><tr><th>Fichier</th><th>Date</th><th>Taille</th><th></th></tr></thead>
        <tbody>
          ${backups.map(b => `
            <tr>
              <td>${b.filename}</td>
              <td>${fmtDateTime(b.date)}</td>
              <td>${b.size_kb} Ko</td>
              <td><a class="btn btn-outline btn-sm" href="/api/backup/download/${encodeURIComponent(b.filename)}" target="_blank">⬇️ Télécharger</a></td>
            </tr>`).join("")}
        </tbody>
      </table>`;
  } catch (e) { el.innerHTML = `<div class="empty-state">${e.message}</div>`; }
}
