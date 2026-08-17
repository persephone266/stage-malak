(async () => {
  await renderLayout("dashboard.html", "Tableau de bord");
  const content = document.getElementById("content");

  content.innerHTML = `
    <div class="stat-grid">
      <div class="stat-card">
        <div class="top"><div class="icon icon-blue">🧑‍🤝‍🧑</div></div>
        <div class="value" id="statPatients">-</div>
        <div class="label">Total patients</div>
      </div>
      <div class="stat-card">
        <div class="top"><div class="icon icon-green">📅</div></div>
        <div class="value" id="statAppts">-</div>
        <div class="label">Rendez-vous aujourd'hui</div>
      </div>
      <div class="stat-card">
        <div class="top"><div class="icon icon-orange">🩺</div></div>
        <div class="value" id="statConsults">-</div>
        <div class="label">Consultations aujourd'hui</div>
      </div>
      <div class="stat-card">
        <div class="top"><div class="icon icon-purple">💰</div></div>
        <div class="value" id="statIncome">-</div>
        <div class="label">Revenu du mois (MAD)</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>Rendez-vous à venir <a href="appointments.html">Voir tout →</a></h3>
        <div id="upcomingList"></div>
      </div>
      <div class="card" id="notifications">
        <h3>Alertes & Notifications</h3>
        <div id="notifList"></div>
      </div>
    </div>

    <div class="grid-charts">
      <div class="card"><h3>Consultations mensuelles</h3><canvas id="chartConsults" height="180"></canvas></div>
      <div class="card"><h3>Revenu mensuel (MAD)</h3><canvas id="chartRevenue" height="180"></canvas></div>
    </div>
    <div class="grid-charts">
      <div class="card"><h3>Nouveaux patients</h3><canvas id="chartNewPatients" height="180"></canvas></div>
      <div class="card"><h3>Répartition par genre</h3><canvas id="chartGender" height="180"></canvas></div>
    </div>

    <div class="card">
      <h3>Patients récents <a href="patients.html">Voir tout →</a></h3>
      <div id="recentPatients"></div>
    </div>
  `;

  try {
    const summary = await apiFetch("/dashboard/summary");
    document.getElementById("statPatients").textContent = summary.total_patients;
    document.getElementById("statAppts").textContent = summary.today_appointments;
    document.getElementById("statConsults").textContent = summary.today_consultations;
    document.getElementById("statIncome").textContent = summary.monthly_income.toLocaleString("fr-FR", { minimumFractionDigits: 2 });

    const upcomingList = document.getElementById("upcomingList");
    upcomingList.innerHTML = summary.upcoming_appointments.length ? summary.upcoming_appointments.map(a => `
      <div class="list-row">
        <div class="avatar">${initials(a.patient_name?.split(" ")[0], a.patient_name?.split(" ")[1])}</div>
        <div class="info">
          <div class="t1">${a.patient_name}</div>
          <div class="t2">${fmtDate(a.date)} à ${a.time} — ${a.reason || "Consultation"}</div>
        </div>
        ${statusChip(a.status)}
      </div>`).join("") : `<div class="empty-state"><div class="ic">📅</div>Aucun rendez-vous à venir</div>`;

    const recent = document.getElementById("recentPatients");
    recent.innerHTML = summary.recent_patients.length ? summary.recent_patients.map(p => `
      <div class="list-row">
        <div class="avatar">${initials(p.first_name, p.last_name)}</div>
        <div class="info">
          <div class="t1">${p.full_name}</div>
          <div class="t2">${p.dossier_number} · ${p.phone || "N/A"}</div>
        </div>
        <a class="btn btn-outline btn-sm" href="patient_profile.html?id=${p.id}">Voir profil</a>
      </div>`).join("") : `<div class="empty-state"><div class="ic">🧑‍🤝‍🧑</div>Aucun patient</div>`;

    const notifs = await apiFetch("/notifications");
    const notifList = document.getElementById("notifList");
    const icons = { "Rendez-vous": "📅", "Assurance": "🛡️", "Suivi": "🔁" };
    notifList.innerHTML = notifs.length ? notifs.slice(0, 8).map(n => `
      <div class="list-row">
        <div class="avatar" style="background:${n.is_read ? '#F4F6F9' : '#E8F0FE'};">${icons[n.type] || "🔔"}</div>
        <div class="info">
          <div class="t1">${n.message}</div>
          <div class="t2">${fmtDateTime(n.date)}</div>
        </div>
      </div>`).join("") : `<div class="empty-state"><div class="ic">🔔</div>Aucune alerte</div>`;

    const charts = await apiFetch("/dashboard/charts");
    if (typeof Chart === "undefined") {
      document.querySelectorAll(".grid-charts .card").forEach(c => {
        c.innerHTML += `<div class="empty-state">⚠️ Impossible de charger la librairie de graphiques (js/vendor/chart.umd.js manquant)</div>`;
      });
      refreshNotifBadge();
      return;
    }
    const chartOpts = { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } };

    new Chart(document.getElementById("chartConsults"), {
      type: "bar",
      data: { labels: charts.months, datasets: [{ data: charts.consultations, backgroundColor: "#1668E3", borderRadius: 6 }] },
      options: chartOpts,
    });
    new Chart(document.getElementById("chartRevenue"), {
      type: "line",
      data: { labels: charts.months, datasets: [{ data: charts.revenue, borderColor: "#3BC896", backgroundColor: "rgba(59,200,150,0.15)", fill: true, tension: 0.35 }] },
      options: chartOpts,
    });
    new Chart(document.getElementById("chartNewPatients"), {
      type: "bar",
      data: { labels: charts.months, datasets: [{ data: charts.new_patients, backgroundColor: "#8B5CF6", borderRadius: 6 }] },
      options: chartOpts,
    });
    new Chart(document.getElementById("chartGender"), {
      type: "doughnut",
      data: {
        labels: ["Homme", "Femme"],
        datasets: [{ data: [charts.gender_distribution.Homme, charts.gender_distribution.Femme], backgroundColor: ["#1668E3", "#F5A623"] }],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });

    refreshNotifBadge();
  } catch (e) {
    toast(e.message, "error");
  }
})();
