(async () => {
  await renderLayout("payments.html", "Paiements & Factures");
  const content = document.getElementById("content");

  content.innerHTML = `
    <div class="table-toolbar">
      <div class="field" style="margin:0;">
        <select id="filterPatient" style="min-width:260px;"><option value="">Tous les patients</option></select>
      </div>
      <button class="btn btn-primary" onclick="openPaymentModal()">+ Enregistrer un paiement</button>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Patient</th><th>Date</th><th>Montant</th><th>Méthode</th><th>Statut</th><th>Facture</th><th></th></tr></thead>
          <tbody id="paymentsBody"></tbody>
        </table>
      </div>
      <div id="emptyPayments"></div>
    </div>
    ${paymentModalHtml()}
  `;

  const patients = await apiFetch("/patients");
  const sel = document.getElementById("filterPatient");
  sel.innerHTML += patients.map(p => `<option value="${p.id}">${p.full_name}</option>`).join("");
  document.getElementById("f_pay_patient").innerHTML = patients.map(p => `<option value="${p.id}">${p.full_name} (${p.dossier_number})</option>`).join("");

  let feeDefault = 200;
  try { const settings = await apiFetch("/settings"); feeDefault = settings.consultation_fee || 200; } catch (e) {}
  document.getElementById("f_pay_amount").value = feeDefault;

  const preselect = new URLSearchParams(window.location.search).get("patient_id");
  if (preselect) { sel.value = preselect; openPaymentModal(); document.getElementById("f_pay_patient").value = preselect; }

  sel.addEventListener("change", loadPayments);
  document.getElementById("paymentForm").addEventListener("submit", savePayment);
  loadPayments();
})();

async function loadPayments() {
  const pid = document.getElementById("filterPatient").value;
  try {
    const list = await apiFetch(`/payments${pid ? "?patient_id=" + pid : ""}`);
    const body = document.getElementById("paymentsBody");
    const empty = document.getElementById("emptyPayments");
    if (!list.length) {
      body.innerHTML = "";
      empty.innerHTML = `<div class="empty-state"><div class="ic">💳</div>Aucun paiement enregistré</div>`;
      return;
    }
    empty.innerHTML = "";
    body.innerHTML = list.map(p => `
      <tr>
        <td>${p.patient_name}</td>
        <td>${fmtDate(p.date)}</td>
        <td><strong>${p.amount.toFixed(2)} MAD</strong></td>
        <td>${p.method}</td>
        <td>${statusChip(p.status)}</td>
        <td>${p.invoice_number || "-"}</td>
        <td>${p.invoice_id ? `<a class="btn btn-outline btn-sm" href="/api/invoices/${p.invoice_id}/pdf" target="_blank">🖨️ Facture PDF</a>` : ""}</td>
      </tr>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

function paymentModalHtml() {
  return `
  <div class="modal-overlay" id="paymentModal">
    <div class="modal">
      <div class="modal-header"><h2>Enregistrer un paiement</h2><button class="modal-close" onclick="closeModal('paymentModal')">✕</button></div>
      <form id="paymentForm">
        <div class="modal-body">
          <div class="form-grid">
            <div class="field full"><label>Patient *</label><select id="f_pay_patient" required></select></div>
            <div class="field"><label>Montant (MAD) *</label><input type="number" step="0.01" id="f_pay_amount" required></div>
            <div class="field"><label>Méthode de paiement</label>
              <select id="f_pay_method">${["Espèces","Carte Bancaire","Chèque","Virement"].map(m=>`<option>${m}</option>`).join("")}</select>
            </div>
            <div class="field full"><label>Statut</label>
              <select id="f_pay_status"><option>Payé</option><option>En attente</option></select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline" onclick="closeModal('paymentModal')">Annuler</button>
          <button type="submit" class="btn btn-primary">Enregistrer & générer la facture</button>
        </div>
      </form>
    </div>
  </div>`;
}

function openPaymentModal() {
  openModal("paymentModal");
}

async function savePayment(e) {
  e.preventDefault();
  const payload = {
    patient_id: document.getElementById("f_pay_patient").value,
    amount: parseFloat(document.getElementById("f_pay_amount").value),
    method: document.getElementById("f_pay_method").value,
    status: document.getElementById("f_pay_status").value,
  };
  try {
    const created = await apiFetch("/payments", { method: "POST", body: JSON.stringify(payload) });
    toast("Paiement enregistré, facture générée");
    closeModal("paymentModal");
    loadPayments();
    if (created.invoice_id) window.open(`/api/invoices/${created.invoice_id}/pdf`, "_blank");
  } catch (e) { toast(e.message, "error"); }
}
