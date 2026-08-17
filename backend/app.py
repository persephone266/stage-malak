import os
import secrets
import calendar
import shutil
import glob
from datetime import datetime, date, timedelta
from collections import Counter

from flask import Flask, request, jsonify, session, send_file, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import (
    db, User, Patient, Appointment, Consultation, Prescription, Medicine,
    Analysis, Invoice, Payment, MedicalCertificate, MedicalRecord, Notification
)
from utils import (
    login_required, roles_required, generate_dossier_number, generate_invoice_number,
    generate_prescription_pdf, generate_invoice_pdf, generate_certificate_pdf,
    CERTIFICATE_TYPES
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
# DATA_DIR permet de pointer la base de données, les fichiers uploadés et les
# sauvegardes vers un disque persistant en production (ex: Render Disk).
# Par défaut (usage local), tout reste dans le dossier backend/ comme avant.
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
INSTANCE_DIR = os.path.join(DATA_DIR, "instance")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


def get_or_create_secret_key():
    """
    Utilise SECRET_KEY définie en variable d'environnement si présente (recommandé en production).
    Sinon, génère une clé aléatoire unique à la première exécution et la réutilise ensuite
    (stockée localement, jamais codée en dur dans le code source).
    """
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_file = os.path.join(INSTANCE_DIR, "secret_key.txt")
    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            return f.read().strip()
    new_key = secrets.token_hex(32)
    with open(key_file, "w") as f:
        f.write(new_key)
    return new_key


app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["SECRET_KEY"] = get_or_create_secret_key()
DB_PATH = os.path.join(DATA_DIR, "cabinet.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo
IS_SQLITE = DATABASE_URL.startswith("sqlite")

db.init_app(app)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =====================================================================
# FRONTEND (fichiers statiques)
# =====================================================================
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


# =====================================================================
# AUTHENTIFICATION
# =====================================================================
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Identifiant ou mot de passe incorrect"}), 401
    if not user.is_active:
        return jsonify({"error": "Compte désactivé"}), 403
    session["user_id"] = user.id
    session["role"] = user.role
    session["full_name"] = user.full_name
    return jsonify({"user": user.to_dict()})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Déconnexion réussie"})


@app.route("/api/auth/me", methods=["GET"])
@login_required
def me():
    user = User.query.get(session["user_id"])
    return jsonify({"user": user.to_dict()})


@app.route("/api/auth/change-password", methods=["PUT"])
@login_required
def change_password():
    data = request.get_json(force=True)
    user = User.query.get(session["user_id"])
    if not check_password_hash(user.password_hash, data.get("current_password", "")):
        return jsonify({"error": "Mot de passe actuel incorrect"}), 400
    new_pw = data.get("new_password", "")
    if len(new_pw) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    return jsonify({"message": "Mot de passe mis à jour"})


# =====================================================================
# DASHBOARD
# =====================================================================
@app.route("/api/dashboard/summary", methods=["GET"])
@login_required
def dashboard_summary():
    today = date.today()
    total_patients = Patient.query.count()
    today_appts = Appointment.query.filter_by(appointment_date=today).count()
    today_consults = Consultation.query.filter(
        db.func.date(Consultation.consultation_date) == today
    ).count()

    first_of_month = today.replace(day=1)
    monthly_payments = Payment.query.filter(
        Payment.payment_date >= first_of_month, Payment.payment_status == "Payé"
    ).all()
    monthly_income = sum(float(p.amount) for p in monthly_payments)

    upcoming = Appointment.query.filter(
        Appointment.appointment_date >= today, Appointment.status == "Planifié"
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(6).all()

    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(6).all()

    return jsonify({
        "total_patients": total_patients,
        "today_appointments": today_appts,
        "today_consultations": today_consults,
        "monthly_income": monthly_income,
        "upcoming_appointments": [a.to_dict() for a in upcoming],
        "recent_patients": [p.to_dict() for p in recent_patients],
    })


@app.route("/api/dashboard/charts", methods=["GET"])
@login_required
def dashboard_charts():
    today = date.today()
    months_labels, consultations_data, revenue_data, new_patients_data = [], [], [], []

    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        end_day = calendar.monthrange(y, m)[1]
        end = date(y, m, end_day)

        months_labels.append(start.strftime("%b %Y"))
        consultations_data.append(
            Consultation.query.filter(
                db.func.date(Consultation.consultation_date) >= start,
                db.func.date(Consultation.consultation_date) <= end,
            ).count()
        )
        payments = Payment.query.filter(
            Payment.payment_date >= start, Payment.payment_date <= end,
            Payment.payment_status == "Payé"
        ).all()
        revenue_data.append(sum(float(p.amount) for p in payments))
        new_patients_data.append(
            Patient.query.filter(
                db.func.date(Patient.created_at) >= start,
                db.func.date(Patient.created_at) <= end,
            ).count()
        )

    male = Patient.query.filter_by(gender="Homme").count()
    female = Patient.query.filter_by(gender="Femme").count()

    return jsonify({
        "months": months_labels,
        "consultations": consultations_data,
        "revenue": revenue_data,
        "new_patients": new_patients_data,
        "gender_distribution": {"Homme": male, "Femme": female},
    })


# =====================================================================
# PATIENTS
# =====================================================================
@app.route("/api/patients", methods=["GET"])
@login_required
def list_patients():
    q = request.args.get("search", "").strip()
    insured = request.args.get("insured", "").strip()
    query = Patient.query
    if insured == "1":
        query = query.filter(Patient.insurance_type.isnot(None),
                             Patient.insurance_type != "Aucune")
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(like), Patient.last_name.ilike(like),
                Patient.dossier_number.ilike(like), Patient.cin.ilike(like),
                Patient.phone.ilike(like), Patient.insurance_number.ilike(like),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).all()
    return jsonify([p.to_dict() for p in patients])


@app.route("/api/patients", methods=["POST"])
@login_required
def create_patient():
    data = request.get_json(force=True)
    last = db.session.query(db.func.max(Patient.id)).scalar() or 0
    patient = Patient(
        dossier_number=generate_dossier_number(last + 1),
        first_name=data["first_name"], last_name=data["last_name"],
        cin=data.get("cin"), phone=data.get("phone"), email=data.get("email"),
        address=data.get("address"),
        date_of_birth=datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date() if data.get("date_of_birth") else None,
        gender=data["gender"], blood_group=data.get("blood_group"),
        emergency_contact=data.get("emergency_contact"),
        allergies=data.get("allergies"), chronic_diseases=data.get("chronic_diseases"),
        previous_surgeries=data.get("previous_surgeries"),
        vaccination_notes=data.get("vaccination_notes"), medical_notes=data.get("medical_notes"),
        visit_type=data.get("visit_type"),
        insurance_type=data.get("insurance_type", "Aucune"),
        insurance_number=data.get("insurance_number"),
        insurance_expiration=datetime.strptime(data["insurance_expiration"], "%Y-%m-%d").date() if data.get("insurance_expiration") else None,
        insurance_status=data.get("insurance_status", "Active"),
    )
    db.session.add(patient)
    db.session.commit()
    return jsonify(patient.to_dict(detailed=True)), 201


@app.route("/api/patients/<int:pid>", methods=["GET"])
@login_required
def get_patient(pid):
    patient = Patient.query.get_or_404(pid)
    return jsonify(patient.to_dict(detailed=True))


@app.route("/api/patients/<int:pid>", methods=["PUT"])
@login_required
def update_patient(pid):
    patient = Patient.query.get_or_404(pid)
    data = request.get_json(force=True)
    for field in ["first_name", "last_name", "cin", "phone", "email", "address",
                  "gender", "blood_group", "emergency_contact", "allergies",
                  "chronic_diseases", "previous_surgeries", "vaccination_notes",
                  "medical_notes", "insurance_type", "insurance_number", "insurance_status",
                  "visit_type"]:
        if field in data:
            setattr(patient, field, data[field])
    if data.get("date_of_birth"):
        patient.date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
    if data.get("insurance_expiration"):
        patient.insurance_expiration = datetime.strptime(data["insurance_expiration"], "%Y-%m-%d").date()
    db.session.commit()
    return jsonify(patient.to_dict(detailed=True))


@app.route("/api/patients/<int:pid>", methods=["DELETE"])
@roles_required("medecin")
def delete_patient(pid):
    patient = Patient.query.get_or_404(pid)
    db.session.delete(patient)
    db.session.commit()
    return jsonify({"message": "Patient supprimé"})


@app.route("/api/patients/<int:pid>/certificate/<cert_type>/pdf", methods=["GET"])
@login_required
def patient_certificate_pdf(pid, cert_type):
    if cert_type not in CERTIFICATE_TYPES:
        return jsonify({"error": "Type de certificat inconnu"}), 404
    patient = Patient.query.get_or_404(pid)
    doctor = User.query.filter_by(role="medecin").first()
    try:
        buf = generate_certificate_pdf(cert_type, patient.to_dict(),
                                       doctor.to_dict() if doctor else {})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501

    certificate = MedicalCertificate(
        patient_id=patient.id,
        doctor_id=doctor.id if doctor else session["user_id"],
        content=CERTIFICATE_TYPES[cert_type]["title"],
    )
    db.session.add(certificate)
    db.session.commit()
    _add_medical_record(patient.id, "Certificat", certificate.id,
                        CERTIFICATE_TYPES[cert_type]["title"])
    db.session.commit()

    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"certificat_{cert_type}_{patient.dossier_number}.pdf")


@app.route("/api/patients/<int:pid>/medical-record", methods=["GET"])
@login_required
def patient_medical_record(pid):
    Patient.query.get_or_404(pid)
    records = MedicalRecord.query.filter_by(patient_id=pid).order_by(MedicalRecord.record_date.desc()).all()
    detailed = []
    for r in records:
        entry = r.to_dict()
        if r.record_type == "Consultation":
            c = Consultation.query.get(r.reference_id)
            entry["details"] = c.to_dict() if c else None
        elif r.record_type == "Ordonnance":
            p = Prescription.query.get(r.reference_id)
            entry["details"] = p.to_dict() if p else None
        elif r.record_type == "Analyse":
            a = Analysis.query.get(r.reference_id)
            entry["details"] = a.to_dict() if a else None
        detailed.append(entry)
    return jsonify(detailed)


# =====================================================================
# RENDEZ-VOUS
# =====================================================================
@app.route("/api/appointments", methods=["GET"])
@login_required
def list_appointments():
    query = Appointment.query
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    status = request.args.get("status")
    if date_from:
        query = query.filter(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.filter(Appointment.appointment_date <= date_to)
    if status:
        query = query.filter_by(status=status)
    appts = query.order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    return jsonify([a.to_dict() for a in appts])


@app.route("/api/appointments", methods=["POST"])
@login_required
def create_appointment():
    data = request.get_json(force=True)
    appt = Appointment(
        patient_id=data["patient_id"], doctor_id=data.get("doctor_id") or _default_doctor_id(),
        appointment_date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
        appointment_time=datetime.strptime(data["time"], "%H:%M").time(),
        reason=data.get("reason"), status=data.get("status", "Planifié"),
    )
    db.session.add(appt)
    db.session.commit()
    if appt.appointment_date == date.today() + timedelta(days=1):
        _add_notification("Rendez-vous", f"Rendez-vous demain avec {appt.patient.first_name} {appt.patient.last_name} à {appt.appointment_time.strftime('%H:%M')}", appt.id)
    return jsonify(appt.to_dict()), 201


@app.route("/api/appointments/<int:aid>", methods=["PUT"])
@login_required
def update_appointment(aid):
    appt = Appointment.query.get_or_404(aid)
    data = request.get_json(force=True)
    if "patient_id" in data:
        appt.patient_id = data["patient_id"]
    if "date" in data:
        appt.appointment_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    if "time" in data:
        appt.appointment_time = datetime.strptime(data["time"], "%H:%M").time()
    if "reason" in data:
        appt.reason = data["reason"]
    if "status" in data:
        appt.status = data["status"]
    db.session.commit()
    return jsonify(appt.to_dict())


@app.route("/api/appointments/<int:aid>", methods=["DELETE"])
@login_required
def delete_appointment(aid):
    appt = Appointment.query.get_or_404(aid)
    db.session.delete(appt)
    db.session.commit()
    return jsonify({"message": "Rendez-vous supprimé"})


def _default_doctor_id():
    doc = User.query.filter_by(role="medecin").first()
    return doc.id if doc else None


# =====================================================================
# CONSULTATIONS
# =====================================================================
@app.route("/api/consultations", methods=["GET"])
@login_required
def list_consultations():
    query = Consultation.query
    patient_id = request.args.get("patient_id")
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    consults = query.order_by(Consultation.consultation_date.desc()).all()
    return jsonify([c.to_dict() for c in consults])


@app.route("/api/consultations", methods=["POST"])
@roles_required("medecin")
def create_consultation():
    data = request.get_json(force=True)
    consult = Consultation(
        patient_id=data["patient_id"], doctor_id=session["user_id"],
        appointment_id=data.get("appointment_id"),
        symptoms=data.get("symptoms"), diagnosis=data.get("diagnosis"),
        clinical_observations=data.get("clinical_observations"),
        treatment=data.get("treatment"),
        follow_up_date=datetime.strptime(data["follow_up_date"], "%Y-%m-%d").date() if data.get("follow_up_date") else None,
    )
    db.session.add(consult)
    if data.get("appointment_id"):
        appt = Appointment.query.get(data["appointment_id"])
        if appt:
            appt.status = "Terminé"
    db.session.commit()

    patient = Patient.query.get(data["patient_id"])
    _add_medical_record(patient.id, "Consultation", consult.id, f"Consultation - {data.get('diagnosis') or 'Sans diagnostic'}")
    if consult.follow_up_date:
        _add_notification("Suivi", f"Suivi prévu pour {patient.first_name} {patient.last_name} le {consult.follow_up_date}", consult.id)
    db.session.commit()
    return jsonify(consult.to_dict()), 201


@app.route("/api/consultations/<int:cid>", methods=["GET"])
@login_required
def get_consultation(cid):
    return jsonify(Consultation.query.get_or_404(cid).to_dict())


@app.route("/api/consultations/<int:cid>", methods=["PUT"])
@roles_required("medecin")
def update_consultation(cid):
    consult = Consultation.query.get_or_404(cid)
    data = request.get_json(force=True)
    for field in ["symptoms", "diagnosis", "clinical_observations", "treatment"]:
        if field in data:
            setattr(consult, field, data[field])
    if data.get("follow_up_date"):
        consult.follow_up_date = datetime.strptime(data["follow_up_date"], "%Y-%m-%d").date()
    db.session.commit()
    return jsonify(consult.to_dict())


# =====================================================================
# ORDONNANCES (PRESCRIPTIONS)
# =====================================================================
@app.route("/api/prescriptions", methods=["GET"])
@login_required
def list_prescriptions():
    query = Prescription.query
    patient_id = request.args.get("patient_id")
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    prescriptions = query.order_by(Prescription.created_at.desc()).all()
    return jsonify([p.to_dict() for p in prescriptions])


@app.route("/api/prescriptions", methods=["POST"])
@roles_required("medecin")
def create_prescription():
    data = request.get_json(force=True)
    prescription = Prescription(
        consultation_id=data.get("consultation_id"), patient_id=data["patient_id"],
        doctor_id=session["user_id"], instructions=data.get("instructions"),
    )
    for med in data.get("medicines", []):
        prescription.medicines.append(Medicine(
            name=med["name"], dosage=med.get("dosage"),
            duration=med.get("duration"), instructions=med.get("instructions"),
        ))
    db.session.add(prescription)
    db.session.commit()
    _add_medical_record(prescription.patient_id, "Ordonnance", prescription.id,
                         "Ordonnance - " + ", ".join(m.name for m in prescription.medicines))
    db.session.commit()
    return jsonify(prescription.to_dict()), 201


@app.route("/api/prescriptions/<int:pid>", methods=["GET"])
@login_required
def get_prescription(pid):
    return jsonify(Prescription.query.get_or_404(pid).to_dict())


@app.route("/api/prescriptions/<int:pid>/pdf", methods=["GET"])
@login_required
def prescription_pdf(pid):
    prescription = Prescription.query.get_or_404(pid)
    patient = prescription.patient
    doctor = prescription.doctor
    try:
        buf = generate_prescription_pdf(prescription.to_dict(), patient.to_dict(), doctor.to_dict())
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                      download_name=f"ordonnance_{patient.dossier_number}_{prescription.id}.pdf")


# =====================================================================
# ANALYSES DE LABORATOIRE
# =====================================================================
@app.route("/api/analyses", methods=["GET"])
@login_required
def list_analyses():
    query = Analysis.query
    patient_id = request.args.get("patient_id")
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    analyses = query.order_by(Analysis.created_at.desc()).all()
    return jsonify([a.to_dict() for a in analyses])


@app.route("/api/analyses", methods=["POST"])
@login_required
def create_analysis():
    patient_id = request.form.get("patient_id") or (request.get_json(silent=True) or {}).get("patient_id")
    if request.content_type and "multipart/form-data" in request.content_type:
        name = request.form.get("analysis_name")
        result = request.form.get("result")
        comments = request.form.get("comments")
        consultation_id = request.form.get("consultation_id") or None
        file_path = None
        file = request.files.get("file")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
            file.save(os.path.join(UPLOAD_DIR, filename))
            file_path = filename
    else:
        data = request.get_json(force=True)
        name = data.get("analysis_name")
        result = data.get("result")
        comments = data.get("comments")
        consultation_id = data.get("consultation_id")
        file_path = None

    analysis = Analysis(
        patient_id=patient_id, consultation_id=consultation_id or None,
        analysis_name=name, result=result, comments=comments, file_path=file_path,
    )
    db.session.add(analysis)
    db.session.commit()
    _add_medical_record(analysis.patient_id, "Analyse", analysis.id, f"Analyse - {name}")
    db.session.commit()
    return jsonify(analysis.to_dict()), 201


@app.route("/api/analyses/<int:aid>/file", methods=["GET"])
@login_required
def get_analysis_file(aid):
    analysis = Analysis.query.get_or_404(aid)
    if not analysis.file_path:
        return jsonify({"error": "Aucun fichier joint"}), 404
    return send_from_directory(UPLOAD_DIR, analysis.file_path)


# =====================================================================
# PAIEMENTS & FACTURES
# =====================================================================
@app.route("/api/payments", methods=["GET"])
@login_required
def list_payments():
    query = Payment.query
    patient_id = request.args.get("patient_id")
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    payments = query.order_by(Payment.payment_date.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@app.route("/api/payments", methods=["POST"])
@login_required
def create_payment():
    data = request.get_json(force=True)
    last = db.session.query(db.func.max(Invoice.id)).scalar() or 0
    invoice = Invoice(
        invoice_number=generate_invoice_number(last + 1, date.today().year),
        patient_id=data["patient_id"], amount=data["amount"],
        status="Payée" if data.get("status", "Payé") == "Payé" else "En attente",
    )
    db.session.add(invoice)
    db.session.flush()
    payment = Payment(
        patient_id=data["patient_id"], consultation_id=data.get("consultation_id"),
        invoice_id=invoice.id, amount=data["amount"],
        payment_method=data.get("method", "Espèces"),
        payment_status=data.get("status", "Payé"),
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify(payment.to_dict()), 201


@app.route("/api/invoices/<int:iid>/pdf", methods=["GET"])
@login_required
def invoice_pdf(iid):
    invoice = Invoice.query.get_or_404(iid)
    doctor = User.query.filter_by(role="medecin").first()
    try:
        buf = generate_invoice_pdf(invoice.to_dict(), invoice.patient.to_dict(), doctor.to_dict() if doctor else {})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                      download_name=f"facture_{invoice.invoice_number}.pdf")


# =====================================================================
# NOTIFICATIONS
# =====================================================================
@app.route("/api/notifications", methods=["GET"])
@login_required
def list_notifications():
    _refresh_notifications()
    notifs = Notification.query.order_by(Notification.notif_date.desc()).limit(30).all()
    return jsonify([n.to_dict() for n in notifs])


@app.route("/api/notifications/<int:nid>/read", methods=["PUT"])
@login_required
def mark_notification_read(nid):
    n = Notification.query.get_or_404(nid)
    n.is_read = True
    db.session.commit()
    return jsonify({"message": "OK"})


def _add_notification(ntype, message, related_id=None):
    db.session.add(Notification(type=ntype, message=message, related_id=related_id))


def _add_medical_record(patient_id, record_type, reference_id, title):
    db.session.add(MedicalRecord(patient_id=patient_id, record_type=record_type,
                                  reference_id=reference_id, title=title))


def _refresh_notifications():
    """Génère les alertes automatiques : RDV demain, assurances expirées, suivis à venir."""
    tomorrow = date.today() + timedelta(days=1)
    appts_tomorrow = Appointment.query.filter_by(appointment_date=tomorrow, status="Planifié").all()
    for a in appts_tomorrow:
        exists = Notification.query.filter_by(type="Rendez-vous", related_id=a.id).first()
        if not exists:
            _add_notification("Rendez-vous", f"Rendez-vous demain avec {a.patient.first_name} {a.patient.last_name} à {a.appointment_time.strftime('%H:%M')}", a.id)

    expired = Patient.query.filter(
        Patient.insurance_expiration != None, Patient.insurance_expiration < date.today()
    ).all()
    for p in expired:
        if p.insurance_status != "Expirée":
            p.insurance_status = "Expirée"
        exists = Notification.query.filter_by(type="Assurance", related_id=p.id).first()
        if not exists:
            _add_notification("Assurance", f"Assurance {p.insurance_type} expirée pour {p.first_name} {p.last_name}", p.id)

    upcoming_followups = Consultation.query.filter(
        Consultation.follow_up_date != None,
        Consultation.follow_up_date >= date.today(),
        Consultation.follow_up_date <= date.today() + timedelta(days=3),
    ).all()
    for c in upcoming_followups:
        exists = Notification.query.filter_by(type="Suivi", related_id=c.id).first()
        if not exists:
            _add_notification("Suivi", f"Suivi prévu pour {c.patient.first_name} {c.patient.last_name} le {c.follow_up_date}", c.id)

    db.session.commit()


# =====================================================================
# RECHERCHE GLOBALE
# =====================================================================
@app.route("/api/search", methods=["GET"])
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    like = f"%{q}%"
    patients = Patient.query.filter(
        db.or_(
            Patient.first_name.ilike(like), Patient.last_name.ilike(like),
            Patient.dossier_number.ilike(like), Patient.cin.ilike(like),
            Patient.phone.ilike(like), Patient.insurance_number.ilike(like),
        )
    ).limit(15).all()
    return jsonify([p.to_dict() for p in patients])


# =====================================================================
# STATISTIQUES
# =====================================================================
@app.route("/api/statistics", methods=["GET"])
@login_required
def statistics():
    today = date.today()
    months_labels, consultations_data, revenue_data, new_patients_data = [], [], [], []
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        end_day = calendar.monthrange(y, m)[1]
        end = date(y, m, end_day)
        months_labels.append(start.strftime("%b %Y"))
        consultations_data.append(Consultation.query.filter(
            db.func.date(Consultation.consultation_date) >= start,
            db.func.date(Consultation.consultation_date) <= end).count())
        payments = Payment.query.filter(
            Payment.payment_date >= start, Payment.payment_date <= end,
            Payment.payment_status == "Payé").all()
        revenue_data.append(sum(float(p.amount) for p in payments))
        new_patients_data.append(Patient.query.filter(
            db.func.date(Patient.created_at) >= start,
            db.func.date(Patient.created_at) <= end).count())

    diagnoses = [c.diagnosis for c in Consultation.query.filter(Consultation.diagnosis != None).all() if c.diagnosis]
    common_diseases = Counter(diagnoses).most_common(6)

    ages = [p.age for p in Patient.query.all() if p.age is not None]
    age_groups = {"0-17": 0, "18-35": 0, "36-50": 0, "51-65": 0, "66+": 0}
    for age in ages:
        if age <= 17:
            age_groups["0-17"] += 1
        elif age <= 35:
            age_groups["18-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["66+"] += 1

    male = Patient.query.filter_by(gender="Homme").count()
    female = Patient.query.filter_by(gender="Femme").count()

    return jsonify({
        "months": months_labels, "consultations": consultations_data,
        "revenue": revenue_data, "new_patients": new_patients_data,
        "common_diseases": {k: v for k, v in common_diseases} if common_diseases else {},
        "age_groups": age_groups,
        "gender_distribution": {"Homme": male, "Femme": female},
    })


# =====================================================================
# PARAMÈTRES
# =====================================================================
@app.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    user = User.query.filter_by(role="medecin").first()
    return jsonify(user.to_dict() if user else {})


@app.route("/api/settings", methods=["PUT"])
@roles_required("medecin")
def update_settings():
    user = User.query.get(session["user_id"])
    data = request.get_json(force=True)
    for field in ["full_name", "email", "phone", "specialite", "clinic_name",
                  "clinic_address", "clinic_phone"]:
        if field in data:
            setattr(user, field, data[field])
    if "consultation_fee" in data:
        user.consultation_fee = data["consultation_fee"]
    db.session.commit()
    return jsonify(user.to_dict())


# =====================================================================
# SAUVEGARDE DE LA BASE DE DONNÉES
# =====================================================================
MAX_BACKUPS = 30  # conserve les 30 dernières sauvegardes automatiques


def create_backup(reason="auto"):
    """Crée une copie horodatée et cohérente de la base SQLite dans backend/backups/."""
    if not IS_SQLITE or not os.path.exists(DB_PATH):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"cabinet_{reason}_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    try:
        import sqlite3
        src = sqlite3.connect(DB_PATH)
        dest = sqlite3.connect(backup_path)
        src.backup(dest)   # copie cohérente même si la base est en cours d'utilisation
        dest.close()
        src.close()
    except Exception:
        shutil.copy2(DB_PATH, backup_path)  # solution de secours

    if reason == "auto":
        autos = sorted(glob.glob(os.path.join(BACKUP_DIR, "cabinet_auto_*.db")))
        while len(autos) > MAX_BACKUPS:
            os.remove(autos.pop(0))
    return backup_path


def should_run_daily_backup():
    """Vérifie si une sauvegarde automatique a déjà été faite aujourd'hui."""
    today = date.today().isoformat()
    marker = os.path.join(INSTANCE_DIR, "last_backup.txt")
    if os.path.exists(marker):
        with open(marker, "r") as f:
            if f.read().strip() == today:
                return False
    with open(marker, "w") as f:
        f.write(today)
    return True


def run_daily_backup_if_needed():
    if IS_SQLITE and should_run_daily_backup():
        create_backup("auto")


@app.route("/api/backup/list", methods=["GET"])
@roles_required("medecin")
def list_backups():
    if not IS_SQLITE:
        return jsonify({"error": "La sauvegarde automatique n'est disponible qu'avec SQLite. Pour MySQL, utilisez mysqldump."}), 400
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db")), reverse=True)
    backups = [{
        "filename": os.path.basename(f),
        "size_kb": round(os.path.getsize(f) / 1024, 1),
        "date": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
    } for f in files]
    return jsonify(backups)


@app.route("/api/backup/create", methods=["POST"])
@roles_required("medecin")
def manual_backup():
    if not IS_SQLITE:
        return jsonify({"error": "La sauvegarde automatique n'est disponible qu'avec SQLite. Pour MySQL, utilisez mysqldump."}), 400
    path = create_backup("manuel")
    if not path:
        return jsonify({"error": "Aucune base de données à sauvegarder pour le moment."}), 400
    return jsonify({"message": "Sauvegarde créée avec succès", "filename": os.path.basename(path)})


@app.route("/api/backup/download/<path:filename>", methods=["GET"])
@roles_required("medecin")
def download_backup(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(path):
        return jsonify({"error": "Sauvegarde introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=safe_name)


@app.route("/api/backup/download-now", methods=["GET"])
@roles_required("medecin")
def download_fresh_backup():
    """Génère une sauvegarde à l'instant et la télécharge directement."""
    path = create_backup("manuel")
    if not path:
        return jsonify({"error": "Aucune base de données à sauvegarder pour le moment."}), 400
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


# =====================================================================
# INITIALISATION / SEED
# =====================================================================
def _ensure_columns():
    """Ajoute les colonnes manquantes aux bases créées avant leur introduction."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    existing = {c["name"] for c in inspector.get_columns("patients")}
    if "visit_type" not in existing:
        db.session.execute(text("ALTER TABLE patients ADD COLUMN visit_type VARCHAR(255)"))
        db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        _ensure_columns()
        if User.query.count() == 0:
            from seed import seed_data
            seed_data(db)
        run_daily_backup_if_needed()


init_db()  # s'exécute aussi bien avec "python app.py" qu'avec Gunicorn/Render

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
