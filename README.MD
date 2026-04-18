# Dermatology Department Management System

This is a Flask and PostgreSQL based dermatology workflow application designed to help clinics manage patient records, clinical visits, lab requests, radiology requests, admissions, bed allocation, follow-ups, and discharge summaries from one place.

It is built for practical use in a dermatology department where doctors need fast access to clinical history, patients need organized follow-up care, and staff need a simple system for monitoring ongoing treatment.

## Why This Application Matters

Dermatology care is often long-running and visually driven. A patient may need repeated visits, photo tracking, test reports, medication changes, and follow-up review over time. This application solves that by keeping the full patient journey in one system.

It improves:

- Patient monitoring across multiple visits and treatment stages.
- Doctor access to complete and current clinical information.
- Clinical decision-making through history, images, prescriptions, and test results.
- Coordination between doctors, nurses, and administrative staff.
- Continuity of care when patients return after days or weeks.

## Clinical Importance

Dermatology treatment depends heavily on visual comparison, documentation, and follow-up timing. Missing a prior image, lab result, or medication history can affect diagnosis and outcomes. This system supports:

- Tracking skin changes over time.
- Comparing previous and current clinical images.
- Recording diagnosis, complaints, exam findings, and treatment plans.
- Monitoring admitted patients and their daily progress.
- Detecting missed follow-ups before a condition worsens.
- Producing discharge summaries that preserve the treatment story.

## Core Requirements

The application is intended for clinics and hospitals that need:

- A secure login system for different user roles.
- A patient registration and search workflow.
- A centralized clinical record for each patient.
- Lab and radiology request management.
- In-patient bed assignment and progress tracking.
- Follow-up monitoring and missed follow-up review.
- Prescription creation and printable medical records.
- A PostgreSQL-backed database for structured storage.

## Advanced Features

### For Patient Monitoring

- Complete patient profile with demographic and contact details.
- Historical visit records for comparison over time.
- Clinical gallery for photos and diagnostic files.
- Follow-up visit tracking.
- Missed follow-up reporting.
- Admission and discharge lifecycle tracking.

### For Doctor Efficiency

- Fast access to patient history from a single dashboard.
- Clinical notes, diagnosis, treatment plan, and medications in one workflow.
- Easy prescription management with multiple medications.
- Quick viewing of lab reports and patient images.
- Less time spent searching across paper files or separate tools.

### For Staff and Administration

- Role-based access control.
- Bed management for admitted patients.
- Daily progress note entry.
- Discharge summary generation.
- Data export for reports and analysis.
- User activity logging for accountability.

### For Mobile and Remote Access

- Mobile-friendly upload page for clinical media.
- QR-code based access for patient uploads.
- Web-based interface that can be exposed for remote access when needed.

## Benefits

### Benefits For Patients

- Better continuity of care.
- Fewer missed follow-ups.
- Easier photo-based monitoring of skin progress.
- Faster clinical review when returning for repeat visits.
- Better documentation of treatment changes and response.

### Benefits For Doctors

- One-screen access to the patient journey.
- Less manual tracking across notebooks or separate files.
- Better visibility into prior diagnosis and response to treatment.
- Faster decisions based on clinical history and supporting reports.
- Easier handoff when multiple doctors are involved.

### Benefits For the Clinic

- Organized records for active and discharged patients.
- Better workflow for outpatient and inpatient dermatology care.
- Improved auditability and reporting.
- Reduced risk of missing important clinical information.
- Easier scaling of the department as patient volume grows.

## How The Application Was Made

The application is built using a simple but practical layered structure:

- `app.py` contains the main Flask application, routes, authentication, dashboard logic, and patient workflows.
- `lab_api.py` handles lab request operations.
- `radiology_api.py` handles radiology scan requests and image capture.
- `init_db.py` creates the PostgreSQL database and loads the schema from `init_db.sql`.
- `init_db.sql` defines the tables used for patients, users, visits, reports, prescriptions, beds, notes, and activity logs.
- `templates/` contains the HTML pages for the user interface.
- `static/` contains CSS, JavaScript, and UI assets.

The system uses PostgreSQL because the data is structured, relational, and clinically important. That makes it suitable for preserving patient history, linking visits to prescriptions, connecting lab results to patients, and tracking admissions over time.

## Technology Stack

- Backend: Flask (Python)
- Database: PostgreSQL
- Frontend: HTML, CSS, JavaScript
- Visualization: Chart.js
- HTTP integration: Requests

## Main Features

- Role-based authentication for Admin, Doctor, and Staff.
- Patient registration and search.
- Patient visit and follow-up history.
- Lab report requests and uploads.
- Radiology request handling and image storage.
- Patient image gallery.
- Bed management and inpatient workflow.
- Daily progress notes.
- Discharge summaries.
- Prescription creation and printing.
- Dashboard analytics and reporting.
- Missed follow-up tracking.
- Mobile upload support.

## Installation Requirements

Before running the project, make sure you have:

- Python 3.7 or newer.
- PostgreSQL installed and running.
- Pip installed.

## Setup Instructions

1. Clone the repository.

2. Create and activate a virtual environment.

3. Install the dependencies.

4. Update the database credentials in the Python files if your PostgreSQL user or password is different.

5. Run the database initializer once:

   ```bash
   python init_db.py
   ```

   This script creates `dermatology_db` only if it does not already exist, then creates the required tables.

6. Start the application:

   ```bash
   python app.py
   ```

## First-Time Use

When the application starts with an empty database, the login page will redirect to the first user registration flow. The first account should be created as the admin account. After that, the admin can create and manage other users.

## Mobile Upload Workflow

The mobile upload page is useful when a patient or staff member needs to send an image from a phone. To expose the local server publicly during testing, use a tunnel tool such as ngrok and generate a QR code for the upload URL.

## Data Model Overview

The system stores core clinical entities such as:

- Users and roles.
- Patients.
- Visit and follow-up data.
- Prescriptions and prescription items.
- Lab reports.
- Patient images.
- Bed assignments.
- Daily progress notes.
- Discharge summaries.
- User activity logs.

## Summary

This application is a clinic-focused dermatology information system built to improve patient monitoring, doctor access, clinical documentation, and workflow efficiency. It is especially useful where repeated visits, skin image tracking, prescriptions, lab reports, and follow-up care need to stay connected in one place.