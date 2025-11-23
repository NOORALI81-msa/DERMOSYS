from flask import Blueprint, request, session, flash, redirect, url_for
from datetime import date
from app import get_db  # ⬅ connect using main DB config

lab_bp = Blueprint('lab_api', __name__)

@lab_bp.route('/request_test', methods=['POST'])
def request_lab_test():
    if 'user_id' not in session:
        flash("Please log in to make a request.", "danger")
        return redirect(url_for('login'))

    patient_id = request.form.get('patient_id')
    report_type = request.form.get('lab_test_name')
    department = request.form.get('lab_department', 'Pathology')

    if not all([patient_id, report_type]):
        flash("Missing required fields for lab test request.", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    db_conn = get_db()  # ⬅ USE CLOUD DB

    try:
        with db_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO LabReport (patient_id, requested_by_doctor_id, report_type,
                                       department, report_date, status)
                VALUES (%s, %s, %s, %s, %s, 'Pending')
            """, (patient_id, session['user_id'], report_type, department, date.today()))
            db_conn.commit()
        flash(f"Lab test '{report_type}' requested successfully.", 'success')
    except Exception as e:
        db_conn.rollback()
        flash(f"Database error while requesting lab test: {e}", "danger")

    return redirect(url_for('patient_detail', patient_id=patient_id))
