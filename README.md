# Cabinet Médical – Dr Chaima Ouled Bouallala

Application complète de gestion de cabinet médical.
**Backend :** Python (Flask + SQLAlchemy) — **Frontend :** HTML / CSS / JavaScript — **Base de données :** MySQL (script fourni), fonctionne aussi en SQLite en local sans configuration.

## 📁 Structure du projet

```
cabinet-medical/
├── database/
│   └── schema.sql          → Script complet MySQL (tables, contraintes, données d'exemple)
├── backend/
│   ├── app.py              → Application Flask (toutes les routes API + serveur du frontend)
│   ├── models.py           → Modèles SQLAlchemy
│   ├── utils.py            → Authentification, décorateurs, génération PDF
│   ├── seed.py             → Données de démonstration
│   ├── requirements.txt
│   └── uploads/            → Fichiers joints des analyses (créé automatiquement)
└── frontend/
    ├── index.html          → Page de connexion
    ├── dashboard.html / patients.html / appointments.html / consultations.html
    ├── prescriptions.html / analyses.html / payments.html / statistiques.html / parametres.html
    ├── css/style.css
    └── js/…
```

## 🚀 Installation et démarrage (mode rapide – SQLite)

Aucune installation de MySQL n'est requise pour tester l'application immédiatement :

```bash
cd cabinet-medical/backend
pip install -r requirements.txt
python3 app.py
```

Ouvrez ensuite : **http://localhost:5000**

Au premier démarrage, la base de données `cabinet.db` (SQLite) est créée automatiquement avec des données de démonstration.

### 🔑 Comptes de démonstration
| Rôle        | Identifiant  | Mot de passe   |
|-------------|--------------|----------------|
| Médecin     | `dr.chaima`  | `password123`  |
| Secrétaire  | `secretaire` | `password123`  |

## 🐬 Utiliser MySQL (production)

1. Créez la base avec le script fourni :
   ```bash
   mysql -u root -p < database/schema.sql
   ```
2. Définissez la variable d'environnement avant de lancer le serveur :
   ```bash
   export DATABASE_URL="mysql+pymysql://utilisateur:motdepasse@localhost/cabinet_medical"
   python3 app.py
   ```
   (Le pilote `PyMySQL` est déjà dans `requirements.txt`.)

Le schéma SQL contient les tables : `users`, `patients`, `medical_records`, `consultations`,
`appointments`, `prescriptions`, `medicines`, `analyses`, `payments`, `invoices`,
`medical_certificates`, `notifications` — avec clés primaires, clés étrangères, contraintes et données d'exemple.

## ✨ Fonctionnalités incluses

- **Authentification** : connexion/déconnexion sécurisée, mots de passe chiffrés (scrypt), rôles Médecin / Secrétaire
- **Tableau de bord** : statistiques clés, graphiques (consultations, revenus, nouveaux patients, genre), alertes
- **Patients** : CRUD complet, recherche, dossier détaillé (infos personnelles, médicales, assurance)
- **Dossier médical** : historique chronologique unifié (consultations, ordonnances, analyses)
- **Rendez-vous** : vue tableau + vue calendrier, statuts (Planifié / Terminé / Annulé)
- **Consultations** : symptômes, diagnostic, observations, traitement, suivi — liées automatiquement au dossier patient
- **Ordonnances** : création multi-médicaments, impression / export PDF professionnel
- **Analyses de laboratoire** : résultats, commentaires, upload de fichiers (PDF/images)
- **Paiements & factures** : enregistrement des paiements, génération automatique de factures PDF
- **Notifications** : RDV du lendemain, assurances expirées, suivis à venir
- **Recherche globale** : par nom, numéro de dossier, CIN, téléphone, numéro d'assurance
- **Statistiques avancées** : maladies fréquentes, tranches d'âge, répartition par genre
- **Paramètres** : profil du médecin, informations du cabinet, frais de consultation, changement de mot de passe

## 🎨 Interface

Design médical moderne : palette blanc / bleu médical / vert clair / gris clair, entièrement en français,
responsive (ordinateur, tablette, mobile).

## 🛡️ Sécurité & Sauvegarde

- **Clé secrète** : générée automatiquement et de façon unique à la première exécution (stockée dans `backend/instance/secret_key.txt`, jamais codée en dur). Vous pouvez la remplacer par la vôtre via la variable d'environnement `SECRET_KEY`.
- **Sauvegarde automatique** : une copie complète de la base de données est créée chaque jour au démarrage de l'application, dans `backend/backups/` (les 30 dernières sont conservées).
- **Sauvegarde manuelle** : dans **Paramètres** (compte médecin), bouton "Télécharger une sauvegarde maintenant" + historique des sauvegardes téléchargeables.
- **Restauration** : pour restaurer une sauvegarde, arrêtez le serveur, remplacez `backend/cabinet.db` par le fichier de sauvegarde téléchargé (renommé `cabinet.db`), puis relancez `python app.py`.
- ⚠️ La sauvegarde automatique fonctionne uniquement avec SQLite (mode par défaut). Avec MySQL, utilisez `mysqldump` pour vos sauvegardes.

## ⚠️ Notes

- Le serveur de développement Flask (`python3 app.py`) ne doit pas être utilisé tel quel en production ; utilisez Gunicorn/uWSGI derrière un reverse proxy (Nginx) avec HTTPS.
- Changez la valeur de `SECRET_KEY` dans `app.py` (ou via la variable d'environnement `SECRET_KEY`) avant toute mise en production.
