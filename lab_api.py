from flask import Blueprint, request, session, flash, redirect, url_for
from datetime import date
import psycopg2
import psycopg2.extras

# --- Blueprint Setup for Lab ---
lab_bp = Blueprint('lab_api', __name__)

# --- Database Configuration ---
DB_CONFIG = {
    'dbname': 'dermatology_db', 'user': 'postgres', 'password': 'Noor@818',
    'host': 'localhost', 'port': '5432', 'sslmode': 'disable'
}

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes a new database connection."""
    return psycopg2.connect(**DB_CONFIG)

# --- Main Route for Lab Test Requests ---
@lab_bp.route('/request_test', methods=['POST'])
def request_lab_test():
    """Handles the creation of a standard lab test request."""
    if 'user_id' not in session:
        flash("Please log in to make a request.", "danger")
        return redirect(url_for('login'))

    patient_id = request.form.get('patient_id')
    report_type = request.form.get('lab_test_name')
    department = request.form.get('lab_department', 'Pathology') # Default department

    if not all([patient_id, report_type]):
        flash("Missing required fields for lab test request.", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    db_conn = None
    try:
        db_conn = get_db_connection()
        with db_conn.cursor() as cursor:
            sql = """
                INSERT INTO LabReport (patient_id, requested_by_doctor_id, report_type,
                                       department, report_date, status)
                VALUES (%s, %s, %s, %s, %s, 'Pending')
            """
            cursor.execute(sql, (patient_id, session['user_id'], report_type, department, date.today()))
            db_conn.commit()
        flash(f"Lab test '{report_type}' requested successfully.", 'success')
    except Exception as e:
        if db_conn: db_conn.rollback()
        flash(f"Database error while requesting lab test: {e}", "danger")
    finally:
        if db_conn:
            db_conn.close()

    return redirect(url_for('patient_detail', patient_id=patient_id))