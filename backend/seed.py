from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash

from models import (
    User, Patient, Appointment, Consultation, Prescription, Medicine,
    Analysis, Invoice, Payment, MedicalRecord, Notification
)


def seed_data(db):
    doctor = User(
        username="dr.chaima",
        password_hash=generate_password_hash("password123"),
        full_name="Dr Chaima Ouled Bouallala",
        role="medecin",
        email="chaima.doctor@cabinet.ma",
        phone="+212 6 00 11 22 33",
        specialite="Médecine Générale",
        consultation_fee=200.00,
        clinic_name="Cabinet Médical - Dr Chaima Ouled Bouallala",
        clinic_address="12 Avenue Mohammed V, Marrakech",
        clinic_phone="+212 5 24 00 00 00",
    )
    secretary = User(
        username="secretaire",
        password_hash=generate_password_hash("password123"),
        full_name="Fatima Zahra Idrissi",
        role="secretaire",
        email="secretariat@cabinet.ma",
        phone="+212 6 22 33 44 55",
    )
    db.session.add_all([doctor, secretary])
    db.session.commit()

    patients_data = [
        dict(dossier_number="DM-0001", first_name="Youssef", last_name="El Amrani", cin="BE452178",
             phone="+212 6 61 23 45 67", email="youssef.elamrani@mail.ma", address="Rue Ibn Sina, Marrakech",
             date_of_birth=date(1988, 4, 12), gender="Homme", blood_group="O+",
             emergency_contact="Aicha El Amrani - +212 6 12 34 56 78", allergies="Aucune",
             chronic_diseases="Hypertension", previous_surgeries="Appendicectomie (2010)",
             vaccination_notes="À jour", medical_notes="Patient suivi régulièrement",
             insurance_type="CNSS", insurance_number="CNSS-778541",
             insurance_expiration=date(2026, 11, 30), insurance_status="Active"),
        dict(dossier_number="DM-0002", first_name="Salma", last_name="Bennani", cin="K548712",
             phone="+212 6 65 87 65 43", email="salma.bennani@mail.ma", address="Avenue Hassan II, Marrakech",
             date_of_birth=date(1995, 9, 23), gender="Femme", blood_group="A+",
             emergency_contact="Karim Bennani - +212 6 98 76 54 32", allergies="Pénicilline",
             chronic_diseases="Aucune", previous_surgeries="Aucune", vaccination_notes="À jour",
             medical_notes="RAS", insurance_type="AMO", insurance_number="AMO-334521",
             insurance_expiration=date(2025, 1, 15), insurance_status="Expirée"),
        dict(dossier_number="DM-0003", first_name="Omar", last_name="Tazi", cin="J221459",
             phone="+212 6 71 22 33 44", email="omar.tazi@mail.ma", address="Quartier Gueliz, Marrakech",
             date_of_birth=date(1979, 1, 5), gender="Homme", blood_group="B+",
             emergency_contact="Nadia Tazi - +212 6 55 44 33 22", allergies="Aucune",
             chronic_diseases="Diabète type 2", previous_surgeries="Aucune", vaccination_notes="À jour",
             medical_notes="Contrôle glycémie mensuel", insurance_type="CNOPS",
             insurance_number="CNOPS-119873", insurance_expiration=date(2027, 3, 1), insurance_status="Active"),
        dict(dossier_number="DM-0004", first_name="Imane", last_name="Cherkaoui", cin="BH119873",
             phone="+212 6 44 55 66 77", email="imane.cherkaoui@mail.ma", address="Route de Casablanca, Marrakech",
             date_of_birth=date(2001, 6, 18), gender="Femme", blood_group="AB+",
             emergency_contact="Hicham Cherkaoui - +212 6 33 22 11 00", allergies="Latex",
             chronic_diseases="Asthme", previous_surgeries="Aucune", vaccination_notes="À jour",
             medical_notes="Utilise inhalateur", insurance_type="Assurance Privée",
             insurance_number="PRIV-556231", insurance_expiration=date(2026, 8, 20), insurance_status="Active"),
        dict(dossier_number="DM-0005", first_name="Hamza", last_name="Fassi", cin="A778541",
             phone="+212 6 12 98 76 54", email="hamza.fassi@mail.ma", address="Hay Riad, Marrakech",
             date_of_birth=date(1965, 11, 30), gender="Homme", blood_group="O-",
             emergency_contact="Sara Fassi - +212 6 44 33 22 11", allergies="Aucune",
             chronic_diseases="Cardiopathie", previous_surgeries="Pontage coronarien (2018)",
             vaccination_notes="À jour", medical_notes="Suivi cardiologique", insurance_type="Aucune",
             insurance_number=None, insurance_expiration=None, insurance_status="Active"),
    ]
    patients = [Patient(**pd) for pd in patients_data]
    db.session.add_all(patients)
    db.session.commit()

    today = date.today()
    appts = [
        Appointment(patient_id=patients[0].id, doctor_id=doctor.id, appointment_date=today,
                    appointment_time=datetime.strptime("09:00", "%H:%M").time(),
                    reason="Contrôle tension artérielle", status="Planifié"),
        Appointment(patient_id=patients[1].id, doctor_id=doctor.id, appointment_date=today,
                    appointment_time=datetime.strptime("10:30", "%H:%M").time(),
                    reason="Consultation générale", status="Planifié"),
        Appointment(patient_id=patients[2].id, doctor_id=doctor.id, appointment_date=today,
                    appointment_time=datetime.strptime("14:00", "%H:%M").time(),
                    reason="Suivi diabète", status="Planifié"),
        Appointment(patient_id=patients[3].id, doctor_id=doctor.id, appointment_date=today + timedelta(days=1),
                    appointment_time=datetime.strptime("09:30", "%H:%M").time(),
                    reason="Contrôle asthme", status="Planifié"),
        Appointment(patient_id=patients[4].id, doctor_id=doctor.id, appointment_date=today - timedelta(days=3),
                    appointment_time=datetime.strptime("11:00", "%H:%M").time(),
                    reason="Consultation cardiologique", status="Terminé"),
    ]
    db.session.add_all(appts)
    db.session.commit()

    consult = Consultation(
        patient_id=patients[4].id, doctor_id=doctor.id, appointment_id=appts[4].id,
        symptoms="Douleurs thoraciques légères, fatigue", diagnosis="Angine stable",
        clinical_observations="TA 130/85, FC 78 bpm, auscultation normale",
        treatment="Poursuite du traitement bêtabloquant",
        follow_up_date=today + timedelta(days=30),
    )
    db.session.add(consult)
    db.session.commit()

    prescription = Prescription(consultation_id=consult.id, patient_id=patients[4].id, doctor_id=doctor.id,
                                 instructions="À prendre après les repas. Contrôle dans 1 mois.")
    prescription.medicines.append(Medicine(name="Bisoprolol 5mg", dosage="1 comprimé/jour", duration="30 jours", instructions="Le matin"))
    prescription.medicines.append(Medicine(name="Aspirine 100mg", dosage="1 comprimé/jour", duration="30 jours", instructions="Le soir"))
    db.session.add(prescription)
    db.session.commit()

    analysis = Analysis(patient_id=patients[4].id, consultation_id=consult.id,
                         analysis_name="Bilan lipidique", result="LDL: 1.4 g/L, HDL: 0.45 g/L",
                         comments="Légèrement au-dessus de la normale, à recontrôler")
    db.session.add(analysis)
    db.session.commit()

    invoice = Invoice(invoice_number="INV-2026-0001", patient_id=patients[4].id, amount=200.00, status="Payée")
    db.session.add(invoice)
    db.session.commit()

    payment = Payment(patient_id=patients[4].id, consultation_id=consult.id, invoice_id=invoice.id,
                       amount=200.00, payment_method="Carte Bancaire", payment_status="Payé")
    db.session.add(payment)

    db.session.add_all([
        MedicalRecord(patient_id=patients[4].id, record_type="Consultation", reference_id=consult.id, title="Consultation cardiologique"),
        MedicalRecord(patient_id=patients[4].id, record_type="Ordonnance", reference_id=prescription.id, title="Ordonnance - Bisoprolol, Aspirine"),
        MedicalRecord(patient_id=patients[4].id, record_type="Analyse", reference_id=analysis.id, title="Bilan lipidique"),
    ])

    db.session.add_all([
        Notification(type="Rendez-vous", message=f"Rendez-vous demain avec {patients[3].first_name} {patients[3].last_name} à 09:30", related_id=appts[3].id),
        Notification(type="Assurance", message=f"Assurance AMO expirée pour {patients[1].first_name} {patients[1].last_name}", related_id=patients[1].id),
        Notification(type="Suivi", message=f"Suivi cardiologique prévu pour {patients[4].first_name} {patients[4].last_name}", related_id=consult.id),
    ])

    db.session.commit()
    print("✔ Données de démonstration insérées avec succès.")
    print("  Médecin  -> identifiant: dr.chaima   mot de passe: password123")
    print("  Secrétaire -> identifiant: secretaire  mot de passe: password123")
