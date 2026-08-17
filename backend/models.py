from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="secretaire")  # medecin / secretaire
    email = db.Column(db.String(150))
    phone = db.Column(db.String(30))
    specialite = db.Column(db.String(150), default="Médecine Générale")
    consultation_fee = db.Column(db.Numeric(10, 2), default=200.00)
    clinic_name = db.Column(db.String(200), default="Cabinet Médical - Dr Chaima Ouled Bouallala")
    clinic_address = db.Column(db.String(255))
    clinic_phone = db.Column(db.String(30))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "username": self.username, "full_name": self.full_name,
            "role": self.role, "email": self.email, "phone": self.phone,
            "specialite": self.specialite,
            "consultation_fee": float(self.consultation_fee) if self.consultation_fee else None,
            "clinic_name": self.clinic_name, "clinic_address": self.clinic_address,
            "clinic_phone": self.clinic_phone,
        }


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    dossier_number = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    cin = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    address = db.Column(db.String(255))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(5))
    emergency_contact = db.Column(db.String(150))

    allergies = db.Column(db.Text)
    chronic_diseases = db.Column(db.Text)
    previous_surgeries = db.Column(db.Text)
    vaccination_notes = db.Column(db.Text)
    medical_notes = db.Column(db.Text)
    visit_type = db.Column(db.String(255))

    insurance_type = db.Column(db.String(30), default="Aucune")
    insurance_number = db.Column(db.String(60))
    insurance_expiration = db.Column(db.Date)
    insurance_status = db.Column(db.String(20), default="Active")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def to_dict(self, detailed=False):
        data = {
            "id": self.id, "dossier_number": self.dossier_number,
            "first_name": self.first_name, "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "cin": self.cin, "phone": self.phone, "email": self.email,
            "address": self.address,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age": self.age, "gender": self.gender, "blood_group": self.blood_group,
            "emergency_contact": self.emergency_contact,
            "visit_type": self.visit_type,
            "insurance_type": self.insurance_type, "insurance_number": self.insurance_number,
            "insurance_expiration": self.insurance_expiration.isoformat() if self.insurance_expiration else None,
            "insurance_status": self.insurance_status,
        }
        if detailed:
            data.update({
                "allergies": self.allergies, "chronic_diseases": self.chronic_diseases,
                "previous_surgeries": self.previous_surgeries,
                "vaccination_notes": self.vaccination_notes, "medical_notes": self.medical_notes,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            })
        return data


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Planifié")  # Planifié / Terminé / Annulé
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="appointments")
    doctor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.full_name if self.doctor else None,
            "date": self.appointment_date.isoformat() if self.appointment_date else None,
            "time": self.appointment_time.strftime("%H:%M") if self.appointment_time else None,
            "reason": self.reason, "status": self.status,
        }


class Consultation(db.Model):
    __tablename__ = "consultations"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    consultation_date = db.Column(db.DateTime, default=datetime.utcnow)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    clinical_observations = db.Column(db.Text)
    treatment = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="consultations")
    doctor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "doctor_name": self.doctor.full_name if self.doctor else None,
            "date": self.consultation_date.isoformat() if self.consultation_date else None,
            "symptoms": self.symptoms, "diagnosis": self.diagnosis,
            "clinical_observations": self.clinical_observations,
            "treatment": self.treatment,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
        }


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prescription_date = db.Column(db.Date, default=date.today)
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="prescriptions")
    doctor = db.relationship("User")
    medicines = db.relationship("Medicine", backref="prescription", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "doctor_name": self.doctor.full_name if self.doctor else None,
            "date": self.prescription_date.isoformat() if self.prescription_date else None,
            "instructions": self.instructions,
            "medicines": [m.to_dict() for m in self.medicines],
        }


class Medicine(db.Model):
    __tablename__ = "medicines"
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    instructions = db.Column(db.String(255))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "dosage": self.dosage,
                "duration": self.duration, "instructions": self.instructions}


class Analysis(db.Model):
    __tablename__ = "analyses"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    analysis_name = db.Column(db.String(200), nullable=False)
    analysis_date = db.Column(db.Date, default=date.today)
    result = db.Column(db.Text)
    comments = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="analyses")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "analysis_name": self.analysis_name,
            "date": self.analysis_date.isoformat() if self.analysis_date else None,
            "result": self.result, "comments": self.comments, "file_path": self.file_path,
        }


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    invoice_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="En attente")

    patient = db.relationship("Patient", backref="invoices")

    def to_dict(self):
        return {
            "id": self.id, "invoice_number": self.invoice_number,
            "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "amount": float(self.amount), "date": self.invoice_date.isoformat(),
            "status": self.status,
        }


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(30), default="Espèces")
    payment_status = db.Column(db.String(20), default="Payé")
    payment_date = db.Column(db.Date, default=date.today)

    patient = db.relationship("Patient", backref="payments")
    invoice = db.relationship("Invoice")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
            "amount": float(self.amount), "method": self.payment_method,
            "status": self.payment_status,
            "date": self.payment_date.isoformat() if self.payment_date else None,
            "invoice_number": self.invoice.invoice_number if self.invoice else None,
            "invoice_id": self.invoice_id,
        }


class MedicalCertificate(db.Model):
    __tablename__ = "medical_certificates"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    certificate_date = db.Column(db.Date, default=date.today)
    content = db.Column(db.Text)


class MedicalRecord(db.Model):
    """Journal chronologique unifié du dossier patient."""
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    record_type = db.Column(db.String(30), nullable=False)  # Consultation / Ordonnance / Analyse / Certificat
    reference_id = db.Column(db.Integer, nullable=False)
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id, "type": self.record_type, "reference_id": self.reference_id,
            "date": self.record_date.isoformat() if self.record_date else None,
            "title": self.title,
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), nullable=False)  # Rendez-vous / Assurance / Suivi
    message = db.Column(db.String(255), nullable=False)
    related_id = db.Column(db.Integer)
    notif_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "message": self.message,
            "date": self.notif_date.isoformat() if self.notif_date else None,
            "is_read": self.is_read,
        }
