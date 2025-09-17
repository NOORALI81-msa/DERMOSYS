# Dermatology Department Management System

A comprehensive, web-based Hospital Management System (HMS) built with Flask and PostgreSQL, specifically tailored for the needs of a dermatology department. This application manages the complete patient lifecycle, from initial registration and clinical examination to in-patient bed management, daily progress tracking, and final discharge.

## Features

- [cite_start]**Role-Based Authentication**: Secure login system for Admins, Doctors, and Staff with different permission levels[cite: 1].
- [cite_start]**Comprehensive Patient Records**: A centralized system to register new patients and search for existing ones by name, code, or mobile number[cite: 1].
- **Clinical Workflow**:
    - [cite_start]**Patient Visit Management**: Record initial visit details upon registration and log all subsequent follow-up visits[cite: 1].
    - [cite_start]**Picture & Report Gallery**: Upload and view clinical images and diagnostic reports for each patient in a dedicated gallery[cite: 1].
    - [cite_start]**Lab Investigation Management**: Doctors can request various lab tests, and staff can upload the results (PDFs or images) and update their status[cite: 1].
    - [cite_start]**Mobile-Friendly Uploads**: A simple, dedicated page for patients or staff to upload images directly from a mobile device using a unique link[cite: 1].
- **In-Patient Management**:
    - [cite_start]**Bed Management**: A visual interface to view bed status, add/remove beds, assign patients to available beds, and track admissions[cite: 1].
    - [cite_start]**Daily Progress Notes**: Doctors can add daily updates for admitted patients[cite: 1].
    - [cite_start]**Discharge Summaries**: Automatically generate and store a final summary upon patient discharge based on daily notes[cite: 1].
- [cite_start]**Prescription Management**: Create, view, print, and delete prescriptions with multiple medications and detailed instructions[cite: 1].
- **Advanced Analytics & Reporting**:
    - [cite_start]**Analytics Dashboard**: A high-level overview of key metrics like patient counts, bed occupancy, disease frequency, and user activity[cite: 1].
    - [cite_start]**Missed Follow-up Tracking**: A dedicated page to monitor patients who have missed their scheduled follow-up dates[cite: 1].
    - [cite_start]**Data Export**: Admins can download a detailed CSV report of all patient data for analysis[cite: 1].
- [cite_start]**API Endpoints**: Provides several API endpoints to fetch patient data and analytics, allowing for integration with other systems[cite: 1].

## Technology Stack

- [cite_start]**Backend**: Flask (Python) [cite: 1]
- [cite_start]**Database**: PostgreSQL [cite: 1]
- [cite_start]**Frontend**: HTML, CSS, JavaScript [cite: 1]
- [cite_start]**Libraries**: Chart.js for data visualization, Requests for API communication[cite: 1].

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- [cite_start]Python (3.7 or newer) [cite: 1]
- [cite_start]PostgreSQL [cite: 1]
- [cite_start]Pip (Python Package Installer) [cite: 1]

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
    - [cite_start]Create a new database named `dermatology_db`[cite: 1].
    - [cite_start]Open `app.py` and `init_db.py` and update the `DB_CONFIG` dictionary with your PostgreSQL password[cite: 1].

5.  **Initialize the Database**
    Run the following command to create all the necessary tables. **Note: This will erase any existing data.**
    ```bash
    python init_db.py
    ```

## Running the Application

1.  **Start the Flask Server**
    ```bash
    python app.py
    ```
    [cite_start]The application will be available at `http://127.0.0.1:5001`[cite: 1].

2.  **First-Time Admin Setup**
    - [cite_start]When you run the application for the first time, the database will be empty[cite: 1].
    - Navigate to `http://127.0.0.1:5001/login`. [cite_start]The system will detect that no users exist and automatically redirect you to the registration page[cite: 1].
    - Create the first user account on this page. [cite_start]This account will be automatically assigned the **Admin** role[cite: 1].
    - Once created, you will be redirected to the login page. You can now log in with your new admin account. [cite_start]All subsequent user registrations must be done by an Admin via the dashboard[cite: 1].

## Using the Mobile Upload & QR Code Feature

For the `/mobile_upload` feature to work from any device (like a patient's phone on a mobile network), you need to expose your local server to the internet. The easiest way to do this is with **ngrok**.

1.  **Download ngrok**: If you haven't already, download ngrok from the official website and follow their setup instructions.

2.  **Start the Flask App**: Run your application as usual. [cite_start]It will be running on port `5001`[cite: 1].
    ```bash
    python app.py
    ```

3.  [cite_start]**Start ngrok**: Open a **new, separate terminal window** and run the following command to create a public URL for your application[cite: 1].
    ```bash
    ngrok http 5001
    ```

4.  [cite_start]**Get the Public URL**: Ngrok will display a public "Forwarding" URL that looks something like `https://random-string.ngrok.io`[cite: 1].

5.  **Create the QR Code**: Use this public ngrok URL to create the full link for the mobile upload page (e.g., `https://random-string.ngrok.io/mobile_upload/123`). You can then use any online QR code generator to turn this link into a QR code that patients or staff can scan from any device on any network.