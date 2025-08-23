-- init_db.sql (PostgreSQL Version)

-- Drop existing tables in reverse order of dependency to avoid foreign key errors
DROP TABLE IF EXISTS AdditionalVitals CASCADE;
DROP TABLE IF EXISTS Vitals CASCADE;
DROP TABLE IF EXISTS FollowUpVisit CASCADE;
DROP TABLE IF EXISTS PatientImage CASCADE;
DROP TABLE IF EXISTS LabReport CASCADE;
DROP TABLE IF EXISTS DailyProgressNote CASCADE;
DROP TABLE IF EXISTS DischargeSummary CASCADE;
DROP TABLE IF EXISTS BedAssignment CASCADE;
DROP TABLE IF EXISTS ConsultationRequest CASCADE;
DROP TABLE IF EXISTS PrescriptionItem CASCADE;
DROP TABLE IF EXISTS Prescription CASCADE;
DROP TABLE IF EXISTS Medication CASCADE;
DROP TABLE IF EXISTS Bed CASCADE;
DROP TABLE IF EXISTS Patient CASCADE;
DROP TABLE IF EXISTS Users CASCADE;
DROP TABLE IF EXISTS Roles CASCADE;

-- Roles for users
CREATE TABLE Roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Users table
CREATE TABLE Users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (role_id) REFERENCES Roles(id)
);

-- Patient table
CREATE TABLE Patient (
    id SERIAL PRIMARY KEY,
    patient_code VARCHAR(20) UNIQUE,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    mobile_number VARCHAR(15),
    email VARCHAR(100), -- ADDED
    date_of_registration DATE NOT NULL,
    is_admitted BOOLEAN DEFAULT FALSE,
    treatment_course_duration VARCHAR(50),
    treatment_start_date DATE,
    complaints TEXT,
    examination_findings TEXT,
    diagnosis TEXT,
    past_medical_history TEXT,
    initial_treatment_plan TEXT,
    initial_blood_pressure VARCHAR(10),
    initial_temperature REAL,
    blood_sugar REAL, -- ADDED
    initial_pulse_rate INT,
    initial_weight REAL,
    initial_height REAL,
    initial_bmi REAL,
    initial_bsa REAL,
    affected_bsa_percentage REAL,
    registered_by_doctor_id INT,
    FOREIGN KEY (registered_by_doctor_id) REFERENCES Users(id)
);

-- Bed table
CREATE TABLE Bed (
    id SERIAL PRIMARY KEY,
    bed_number VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'Available'
);

-- Bed Assignment table
CREATE TABLE BedAssignment (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    bed_id INT NOT NULL,
    admission_date TIMESTAMP NOT NULL,
    discharge_date TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (bed_id) REFERENCES Bed(id)
);

-- Daily Progress Notes table
CREATE TABLE DailyProgressNote (
    id SERIAL PRIMARY KEY,
    assignment_id INT NOT NULL,
    note_date TIMESTAMP NOT NULL,
    notes TEXT NOT NULL,
    doctor_id INT NOT NULL,
    FOREIGN KEY (assignment_id) REFERENCES BedAssignment(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Discharge Summary table
CREATE TABLE DischargeSummary (
    id SERIAL PRIMARY KEY,
    assignment_id INT UNIQUE NOT NULL,
    summary_date TIMESTAMP NOT NULL,
    final_diagnosis TEXT,
    treatment_summary TEXT,
    follow_up_instructions TEXT,
    doctor_id INT NOT NULL,
    FOREIGN KEY (assignment_id) REFERENCES BedAssignment(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Consultation Request table
CREATE TABLE ConsultationRequest (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    requesting_doctor_id INT NOT NULL,
    referral_department VARCHAR(100) NOT NULL,
    reason_for_referral TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'Normal',
    request_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (requesting_doctor_id) REFERENCES Users(id)
);

-- Medication table
CREATE TABLE Medication (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    formulation VARCHAR(50)
);

-- Prescription table
CREATE TABLE Prescription (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    visit_id INT,
    prescription_date TIMESTAMP NOT NULL,
    condition_notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id),
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- PrescriptionItem table
CREATE TABLE PrescriptionItem (
    id SERIAL PRIMARY KEY,
    prescription_id INT NOT NULL,
    medication_name VARCHAR(100) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    duration VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (prescription_id) REFERENCES Prescription(id) ON DELETE CASCADE
);

-- Follow-up visits table
CREATE TABLE FollowUpVisit (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    visit_date DATE NOT NULL,
    disease_status TEXT,
    updated_complaints TEXT,
    updated_examination TEXT,
    medication_change TEXT,
    updated_treatment_plan TEXT,
    doctor_id INT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES Users(id)
);

-- Vitals table
CREATE TABLE Vitals (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    visit_id INT,
    visit_date DATE NOT NULL,
    blood_pressure VARCHAR(10),
    temperature REAL,
    pulse_rate INT,
    weight REAL,
    height REAL,
    bmi REAL,
    bsa REAL,
    recorded_by_staff_id INT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by_staff_id) REFERENCES Users(id)
);

-- PatientImage table (UPDATED)
CREATE TABLE PatientImage (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    image_filename VARCHAR(255) NOT NULL,
    upload_date DATE NOT NULL,
    notes TEXT,
    image_type VARCHAR(20) DEFAULT 'Clinical', -- 'Clinical' or 'Diagnostic'
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
);

-- LabReport table (UPDATED)
CREATE TABLE LabReport (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    report_date DATE NOT NULL,
    report_summary TEXT,
    file_path VARCHAR(255), -- For PDFs
    image_id INT, -- NEW: Links to an image in PatientImage table
    status VARCHAR(20) DEFAULT 'Pending',
    requested_by_doctor_id INT,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_doctor_id) REFERENCES Users(id),
    FOREIGN KEY (image_id) REFERENCES PatientImage(id) ON DELETE SET NULL
);

-- NEW TABLE for dynamic lab values from the patient entry form
CREATE TABLE AdditionalVitals (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    vital_name VARCHAR(100) NOT NULL,
    vital_value VARCHAR(100) NOT NULL,
    record_date DATE NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patient(id) ON DELETE CASCADE
);

-- Insert default data
INSERT INTO Roles (name) VALUES ('admin'), ('doctor'), ('staff'), ('Health Worker'), ('IT Executive');
INSERT INTO Bed (bed_number) VALUES ('A-101'), ('A-102');
INSERT INTO Medication (name, formulation) VALUES ('Isotretinoin', 'Capsule'), ('Clindamycin', 'Gel');