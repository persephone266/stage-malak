-- =====================================================================
-- Cabinet Médical – Dr Chaima Ouled Bouallala
-- Script de création de la base de données MySQL
-- =====================================================================

DROP DATABASE IF EXISTS cabinet_medical;
CREATE DATABASE cabinet_medical CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cabinet_medical;

-- ---------------------------------------------------------------------
-- Table: users (Médecin / Secrétaire)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role ENUM('medecin','secretaire') NOT NULL DEFAULT 'secretaire',
    email VARCHAR(150),
    phone VARCHAR(30),
    specialite VARCHAR(150) DEFAULT 'Médecine Générale',
    consultation_fee DECIMAL(10,2) DEFAULT 200.00,
    clinic_name VARCHAR(200) DEFAULT 'Cabinet Médical - Dr Chaima Ouled Bouallala',
    clinic_address VARCHAR(255),
    clinic_phone VARCHAR(30),
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: patients
-- ---------------------------------------------------------------------
CREATE TABLE patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_number VARCHAR(20) NOT NULL UNIQUE,     -- ex: DM-0001
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    cin VARCHAR(30),
    phone VARCHAR(30),
    email VARCHAR(150),
    address VARCHAR(255),
    date_of_birth DATE,
    gender ENUM('Homme','Femme') NOT NULL,
    blood_group VARCHAR(5),
    emergency_contact VARCHAR(150),

    -- Informations médicales
    allergies TEXT,
    chronic_diseases TEXT,
    previous_surgeries TEXT,
    vaccination_notes TEXT,
    medical_notes TEXT,

    -- Assurance
    insurance_type ENUM('CNSS','AMO','CNOPS','Assurance Privée','Aucune') DEFAULT 'Aucune',
    insurance_number VARCHAR(60),
    insurance_expiration DATE,
    insurance_status ENUM('Active','Expirée') DEFAULT 'Active',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_patients_search ON patients(last_name, first_name, cin, phone);

-- ---------------------------------------------------------------------
-- Table: appointments (Rendez-vous)
-- ---------------------------------------------------------------------
CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    reason VARCHAR(255),
    status ENUM('Planifié','Terminé','Annulé') DEFAULT 'Planifié',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appt_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_appt_doctor FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: consultations
-- ---------------------------------------------------------------------
CREATE TABLE consultations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_id INT NULL,
    consultation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    symptoms TEXT,
    diagnosis TEXT,
    clinical_observations TEXT,
    treatment TEXT,
    follow_up_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_consult_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_consult_doctor FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_consult_appt FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: prescriptions
-- ---------------------------------------------------------------------
CREATE TABLE prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consultation_id INT NULL,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    prescription_date DATE DEFAULT (CURRENT_DATE),
    instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_presc_consult FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE SET NULL,
    CONSTRAINT fk_presc_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_presc_doctor FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: medicines (lignes de médicaments d'une ordonnance)
-- ---------------------------------------------------------------------
CREATE TABLE medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    dosage VARCHAR(100),
    duration VARCHAR(100),
    instructions VARCHAR(255),
    CONSTRAINT fk_med_presc FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: analyses (Analyses de laboratoire)
-- ---------------------------------------------------------------------
CREATE TABLE analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    consultation_id INT NULL,
    analysis_name VARCHAR(200) NOT NULL,
    analysis_date DATE DEFAULT (CURRENT_DATE),
    result TEXT,
    comments TEXT,
    file_path VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_analysis_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_analysis_consult FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: invoices (Factures)
-- ---------------------------------------------------------------------
CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    patient_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    invoice_date DATE DEFAULT (CURRENT_DATE),
    status ENUM('Payée','En attente','Annulée') DEFAULT 'En attente',
    CONSTRAINT fk_invoice_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: payments (Paiements)
-- ---------------------------------------------------------------------
CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    consultation_id INT NULL,
    invoice_id INT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('Espèces','Carte Bancaire','Chèque','Virement') DEFAULT 'Espèces',
    payment_status ENUM('Payé','En attente','Remboursé') DEFAULT 'Payé',
    payment_date DATE DEFAULT (CURRENT_DATE),
    CONSTRAINT fk_pay_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_pay_consult FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE SET NULL,
    CONSTRAINT fk_pay_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: medical_certificates (Certificats médicaux)
-- ---------------------------------------------------------------------
CREATE TABLE medical_certificates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    certificate_date DATE DEFAULT (CURRENT_DATE),
    content TEXT,
    CONSTRAINT fk_cert_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_cert_doctor FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: medical_records (Journal chronologique unifié du dossier patient)
-- ---------------------------------------------------------------------
CREATE TABLE medical_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    record_type ENUM('Consultation','Ordonnance','Analyse','Certificat') NOT NULL,
    reference_id INT NOT NULL,     -- id de la table correspondante
    record_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    title VARCHAR(255),
    CONSTRAINT fk_record_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: notifications
-- ---------------------------------------------------------------------
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('Rendez-vous','Assurance','Suivi') NOT NULL,
    message VARCHAR(255) NOT NULL,
    related_id INT,
    notif_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read TINYINT(1) DEFAULT 0
) ENGINE=InnoDB;

-- =====================================================================
-- DONNÉES D'EXEMPLE
-- =====================================================================

-- Mot de passe pour les deux comptes de démonstration : "password123"
-- (hash généré avec werkzeug.security.generate_password_hash, pbkdf2:sha256)
INSERT INTO users (username, password_hash, full_name, role, email, phone, specialite, consultation_fee, clinic_name, clinic_address, clinic_phone) VALUES
('dr.chaima', 'scrypt:32768:8:1$FB8ftTQq6pFkxwuB$0e45a289f0aa9f6c5ddb1df059f1256047506c09698b274eb470c3a8a26480a9bb10e5e17155b2afe6ff9c472b904fad46726c9e3c2fa8ebf6ec63e44762369b', 'Dr Chaima Ouled Bouallala', 'medecin', 'chaima.doctor@cabinet.ma', '+212 6 00 11 22 33', 'Médecine Générale', 200.00, 'Cabinet Médical - Dr Chaima Ouled Bouallala', '12 Avenue Mohammed V, Marrakech', '+212 5 24 00 00 00'),
('secretaire', 'scrypt:32768:8:1$FB8ftTQq6pFkxwuB$0e45a289f0aa9f6c5ddb1df059f1256047506c09698b274eb470c3a8a26480a9bb10e5e17155b2afe6ff9c472b904fad46726c9e3c2fa8ebf6ec63e44762369b', 'Fatima Zahra Idrissi', 'secretaire', 'secretariat@cabinet.ma', '+212 6 22 33 44 55', NULL, NULL, NULL, NULL, NULL);
-- Mot de passe en clair pour les deux comptes ci-dessus : password123

INSERT INTO patients (dossier_number, first_name, last_name, cin, phone, email, address, date_of_birth, gender, blood_group, emergency_contact, allergies, chronic_diseases, previous_surgeries, vaccination_notes, medical_notes, insurance_type, insurance_number, insurance_expiration, insurance_status) VALUES
('DM-0001','Youssef','El Amrani','BE452178','+212 6 61 23 45 67','youssef.elamrani@mail.ma','Rue Ibn Sina, Marrakech','1988-04-12','Homme','O+','Aicha El Amrani - +212 6 12 34 56 78','Aucune','Hypertension','Appendicectomie (2010)','À jour','Patient suivi régulièrement','CNSS','CNSS-778541','2026-11-30','Active'),
('DM-0002','Salma','Bennani','K548712','+212 6 65 87 65 43','salma.bennani@mail.ma','Avenue Hassan II, Marrakech','1995-09-23','Femme','A+','Karim Bennani - +212 6 98 76 54 32','Pénicilline','Aucune','Aucune','À jour','RAS','AMO','AMO-334521','2025-01-15','Expirée'),
('DM-0003','Omar','Tazi','J221459','+212 6 71 22 33 44','omar.tazi@mail.ma','Quartier Gueliz, Marrakech','1979-01-05','Homme','B+','Nadia Tazi - +212 6 55 44 33 22','Aucune','Diabète type 2','Aucune','À jour','Contrôle glycémie mensuel','CNOPS','CNOPS-119873','2027-03-01','Active'),
('DM-0004','Imane','Cherkaoui','BH119873','+212 6 44 55 66 77','imane.cherkaoui@mail.ma','Route de Casablanca, Marrakech','2001-06-18','Femme','AB+','Hicham Cherkaoui - +212 6 33 22 11 00','Latex','Asthme','Aucune','À jour','Utilise inhalateur','Assurance Privée','PRIV-556231','2026-08-20','Active'),
('DM-0005','Hamza','Fassi','A778541','+212 6 12 98 76 54','hamza.fassi@mail.ma','Hay Riad, Marrakech','1965-11-30','Homme','O-','Sara Fassi - +212 6 44 33 22 11','Aucune','Cardiopathie','Pontage coronarien (2018)','À jour','Suivi cardiologique','Aucune',NULL,NULL,'Active');

INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status) VALUES
(1,1, CURDATE(), '09:00:00', 'Contrôle tension artérielle', 'Planifié'),
(2,1, CURDATE(), '10:30:00', 'Consultation générale', 'Planifié'),
(3,1, CURDATE(), '14:00:00', 'Suivi diabète', 'Planifié'),
(4,1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:30:00', 'Contrôle asthme', 'Planifié'),
(5,1, DATE_SUB(CURDATE(), INTERVAL 3 DAY), '11:00:00', 'Consultation cardiologique', 'Terminé');

INSERT INTO consultations (patient_id, doctor_id, appointment_id, symptoms, diagnosis, clinical_observations, treatment, follow_up_date) VALUES
(5,1,5,'Douleurs thoraciques légères, fatigue','Angine stable','TA 130/85, FC 78 bpm, auscultation normale','Poursuite du traitement bêtabloquant', DATE_ADD(CURDATE(), INTERVAL 30 DAY));

INSERT INTO prescriptions (consultation_id, patient_id, doctor_id, instructions) VALUES
(1,5,1,'À prendre après les repas. Contrôle dans 1 mois.');

INSERT INTO medicines (prescription_id, name, dosage, duration, instructions) VALUES
(1,'Bisoprolol 5mg','1 comprimé/jour','30 jours','Le matin'),
(1,'Aspirine 100mg','1 comprimé/jour','30 jours','Le soir');

INSERT INTO analyses (patient_id, consultation_id, analysis_name, result, comments) VALUES
(5,1,'Bilan lipidique','LDL: 1.4 g/L, HDL: 0.45 g/L','Légèrement au-dessus de la normale, à recontrôler');

INSERT INTO invoices (invoice_number, patient_id, amount, status) VALUES
('INV-2026-0001',5,200.00,'Payée');

INSERT INTO payments (patient_id, consultation_id, invoice_id, amount, payment_method, payment_status) VALUES
(5,1,1,200.00,'Carte Bancaire','Payé');

INSERT INTO medical_records (patient_id, record_type, reference_id, title) VALUES
(5,'Consultation',1,'Consultation cardiologique'),
(5,'Ordonnance',1,'Ordonnance - Bisoprolol, Aspirine'),
(5,'Analyse',1,'Bilan lipidique');

INSERT INTO notifications (type, message, related_id) VALUES
('Rendez-vous','Rendez-vous demain avec Imane Cherkaoui à 09:30', 4),
('Assurance','Assurance AMO expirée pour Salma Bennani', 2),
('Suivi','Suivi cardiologique prévu pour Hamza Fassi', 1);
