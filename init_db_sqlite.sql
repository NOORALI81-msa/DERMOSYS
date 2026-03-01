-- init_db_sqlite.sql (SQLite Version)

-- Drop tables if they exist
DROP TABLE IF EXISTS AdditionalVitals;
DROP TABLE IF EXISTS Vitals;
DROP TABLE IF EXISTS FollowUpVisit;
DROP TABLE IF EXISTS PatientImage;
DROP TABLE IF EXISTS LabReport;
DROP TABLE IF EXISTS DailyProgressNote;
DROP TABLE IF EXISTS DischargeSummary;
DROP TABLE IF EXISTS BedAssignment;
DROP TABLE IF EXISTS ConsultationRequest;
DROP TABLE IF EXISTS PrescriptionItem;
DROP TABLE IF EXISTS Prescription;
DROP TABLE IF EXISTS Medication;
DROP TABLE IF EXISTS Bed;
DROP TABLE IF EXISTS Patient;
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Roles;

-- Roles for users
CREATE TABLE Roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Users table
CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (role_id) REFERENCES Roles(id)
);

-- Patient table
CREATE TABLE Patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code TEXT UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    mobile_number TEXT,
    email TEXT,
    date_of_registration DATE NOT NULL,
    is_admitted BOOLEAN DEFAULT 0,
    treatment_course_duration TEXT,
    treatment_start_date DATE,
    complaints TEXT,
    examination_findings TEXT,
    diagnosis TEXT,
    past_medical_history TEXT,
    initial_treatment_plan TEXT,
    initial_blood_pressure TEXT,
    initial_temperature REAL,
    blood_sugar REAL,
    initial_pulse_rate INTEGER,
    initial_weight REAL,
    initial_height REAL,
    initial_bmi REAL,
    initial_bsa REAL,
    affected_bsa_percentage REAL,
    registered_by_doctor_id INTEGER,
    FOREIGN KEY (registered_by_doctor_id) REFERENCES Users(id)
);

-- Bed table
CREATE TABLE Bed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bed_number TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'Available'
);

-- Bed Assignment table
CREATE TABLE BedAssignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    bed_id INTEGER NOT NULL,
    admission_date TEXT NOT NULL,
    discharge_date TEXT,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (bed_id) REFERENCES Bed(id)
);

-- Daily Progress Notes table
CREATE TABLE DailyProgressNote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    note_date TEXT NOT NULL,
    notes TEXT NOT NULL,
    doctor_id INTEGER NOT NULL,
    FOREIGN KEY (assignment_id) REFERENCES BedAssignment(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Discharge Summary table
CREATE TABLE DischargeSummary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER UNIQUE NOT NULL,
    summary_date TEXT NOT NULL,
    final_diagnosis TEXT,
    treatment_summary TEXT,
    follow_up_instructions TEXT,
    doctor_id INTEGER NOT NULL,
    FOREIGN KEY (assignment_id) REFERENCES BedAssignment(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Consultation Request table
CREATE TABLE ConsultationRequest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    requesting_doctor_id INTEGER NOT NULL,
    referral_department TEXT NOT NULL,
    reason_for_referral TEXT NOT NULL,
    priority TEXT DEFAULT 'Normal',
    request_date TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (requesting_doctor_id) REFERENCES Users(id)
);

-- Medication table
CREATE TABLE Medication (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    formulation TEXT
);

-- Prescription table
CREATE TABLE Prescription (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    visit_id INTEGER,
    prescription_date TEXT NOT NULL,
    condition_notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- PrescriptionItem table
CREATE TABLE PrescriptionItem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    medication_name TEXT NOT NULL,
    dosage TEXT,
    frequency TEXT,
    duration TEXT,
    notes TEXT,
    FOREIGN KEY (prescription_id) REFERENCES Prescription(id) ON DELETE CASCADE
);

-- Follow-up visits table
CREATE TABLE FollowUpVisit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    disease_status TEXT,
    updated_complaints TEXT,
    updated_examination TEXT,
    medication_change TEXT,
    updated_treatment_plan TEXT,
    doctor_id INTEGER NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Vitals table
CREATE TABLE Vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_id INTEGER,
    visit_date DATE NOT NULL,
    blood_pressure TEXT,
    temperature REAL,
    pulse_rate INTEGER,
    weight REAL,
    height REAL,
    bmi REAL,
    bsa REAL,
    recorded_by_staff_id INTEGER,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by_staff_id) REFERENCES Users(id)
);

-- PatientImage table
CREATE TABLE PatientImage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    image_filename TEXT NOT NULL,
    upload_date DATE NOT NULL,
    notes TEXT,
    image_type TEXT DEFAULT 'Clinical',
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
);

-- LabReport table
CREATE TABLE LabReport (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    report_date DATE NOT NULL,
    report_summary TEXT,
    file_path TEXT,
    image_id INTEGER,
    status TEXT DEFAULT 'Pending',
    requested_by_doctor_id INTEGER,
    department TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_doctor_id) REFERENCES Users(id),
    FOREIGN KEY (image_id) REFERENCES PatientImage(id) ON DELETE SET NULL
);

-- AdditionalVitals table
CREATE TABLE AdditionalVitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    vital_name TEXT NOT NULL,
    vital_value TEXT NOT NULL,
    record_date DATE NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
);

-- Insert default data
INSERT INTO Roles (name) VALUES ('admin'), ('doctor'), ('staff'), ('Health Worker'), ('IT Executive');
INSERT INTO Bed (bed_number) VALUES ('A-101'), ('A-102');
INSERT INTO Medication (name, formulation) VALUES ('Isotretinoin', 'Capsule'), ('Clindamycin', 'Gel');
