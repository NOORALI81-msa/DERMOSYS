# Dermatology Department Management System

A comprehensive, web-based Hospital Management System (HMS) built with Flask and PostgreSQL, specifically tailored for the needs of a dermatology department. This application manages the complete patient lifecycle, from initial registration and clinical examination to in-patient bed management, daily progress tracking, and final discharge.

## Features

- **Role-Based Authentication**: Secure login system for Admins, Doctors, and Staff with different permission levels.
- **Patient Records**: Centralized system to register new patients and search for existing ones by name, code, or mobile number.
- **Clinical Workflow**:
    - **Patient Visit Management**: A unified form for staff to record vitals and for doctors to add clinical notes.
    - **Picture Analysis**: Upload and view clinical images for each patient in a dedicated gallery.
    - **Lab Report Management**: Doctors can request lab tests, and staff can upload the results (PDFs or images).
- **In-Patient Management**:
    - **Bed Management**: A visual interface to view bed status, assign patients to available beds, and track admissions.
    - **Daily Progress Notes**: Doctors can add daily updates for admitted patients.
    - **Discharge Summaries**: Generate and store a final summary upon patient discharge.
- **Prescription Management**: Create, view, and manage prescriptions with multiple medications and detailed instructions.
- **Inter-Departmental Referrals**: A system for requesting consultations from other departments.
- **Analytics Dashboard**: A high-level overview of key metrics like patient counts, bed occupancy, and disease frequency.

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Libraries**: Chart.js for data visualization

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- Python (3.7 or newer)
- PostgreSQL
- Pip (Python Package Installer)

## Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd <your-project-folder>
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate it (Windows)
    venv\Scripts\activate

    # Activate it (macOS/Linux)
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up the PostgreSQL Database**
    - Open `pgAdmin` or `psql`.
    - Create a new database named `dermatology_db`.
    - Open `app.py` and `init_db.py` and update the `DB_CONFIG` dictionary with your PostgreSQL password.

5.  **Initialize the Database**
    Run the following command to create all the necessary tables. **Note: This will erase any existing data.**
    ```bash
    python init_db.py
    ```

## Running the Application

1.  **Start the Flask Server**
    ```bash
    python app.py or py app.py
    ```
    The application will be available at `http://127.0.0.1:5001`.

2.  **First-Time Admin Setup**
    - The first time you run the application, there are no users. You must create an admin account.
    - Temporarily comment out the security check inside the `register_user` function in `app.py`.
    - Go to `http://127.0.0.1:5001/register_user`, create a user, and assign them the "Admin" role.
    - **Important**: Stop the server and un-comment the security lines in `app.py` to secure the registration page again.
    - You can now log in with your new admin account.
