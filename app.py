# app.py (Final Version with All Fixes)
import os
import math
import logging
import time
import io
import csv
from datetime import datetime, date
from functools import wraps
from collections import Counter, defaultdict

import psycopg2
import psycopg2.extras
import requests
from flask import (Flask, render_template, request, redirect, url_for, g,
                   flash, session, jsonify, send_from_directory, make_response)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename



# --- App Configuration & Setup ---
app = Flask(__name__)
app.secret_key = 'a-very-secure-and-random-secret-key-for-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'dcm'}

RADIOLOGY_API_HOST = "http://127.0.0.1:5000"

import ssl

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'JpnE0HopPAcKwZIP',
    'host': 'db.vlufplbgthtxntlismdx.supabase.co',
    'port': '5432',
    
}

def get_db():
    if 'db' not in g:
        ssl_context = ssl.create_default_context()
        g.db = psycopg2.connect(**DB_CONFIG, sslmode='require', ssl=ssl_context)
    return g.db


import tempfile

# Use temporary writable directory on Vercel
DOWNLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()


logging.basicConfig(level=logging.INFO)




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# This dictionary contains the detailed lab test structure.
TEST_CATEGORIES = {
    'biochemistry': {
        'Kidney Function': ['GLU', 'UREA', 'CREATININE'],
        'Liver Function': ['SGOT', 'SGPT', 'ALBUMIN', 'TOTAL_BILIRUBIN'],
        'Thyroid Function': ['TSH', 'T3', 'T4'],
        'Cardiac Markers': ['TROPONIN_I'],
        'Lipid Profile': ['TOTAL_CHOLESTEROL', 'HDL', 'LDL'],
        'Electrolytes': ['SODIUM', 'POTASSIUM']
    },
    'microbiology': {
        'Wet Mount & Staining': ['GRAM_STAIN', 'HANGING_DROP', 'INDIA_INK', 'STOOL_OVA', 'KOH_MOUNT', 'ZN_STAIN'],
        'Culture & Sensitivity': ['BLOOD_CULTURE', 'URINE_CULTURE', 'SPUTUM_CULTURE', 'WOUND_CULTURE', 'THROAT_CULTURE', 'CSF_CULTURE'],
        'Fungal Culture': ['FUNGAL_CULTURE', 'FUNGAL_ID', 'ANTIFUNGAL_SENS'],
        'Serology': ['WIDAL', 'TYPHIDOT', 'DENGUE_NS1', 'MALARIA_AG', 'HIV_ELISA', 'HBSAG']
    },
    'pathology': {
        'Histopathology': ['BIOPSY_HISTOPATHOLOGY', 'SURGICAL_PATHOLOGY'],
        'Hematology': ['CBC', 'PERIPHERAL_SMEAR', 'BONE_MARROW', 'COAGULATION'],
        'Immunohistochemistry': ['IHC_MARKERS', 'SPECIAL_STAINS', 'MOLECULAR_PATH']
    }
}




@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role_id') != 1:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Main Landing & Auth Routes ---
@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/patient/<int:patient_id>/request_investigation', methods=['POST'])
@login_required
def request_investigation(patient_id):
    """
    This single route handles both Radiology and Lab requests based on
    the 'request_type' from the dynamic modal.
    """
    request_type = request.form.get('request_type')
    db_conn = get_db()

    # --- Section for handling Radiology requests ---
    if request_type == 'radiology':
        uhid = request.form.get('uhid')
        scan_type = request.form.get('radiology_scan_type')
        body_part = request.form.get('radiology_body_part')

        if not all([uhid, scan_type, body_part]):
            flash("Missing fields for radiology scan request.", "danger")
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        # Call the function from the radiology_api.py blueprint
        filename, error = perform_radiology_request(db_conn, patient_id, uhid, scan_type, body_part)
        
        if error:
            flash(f"Radiology request failed: {error}", "danger")
        else:
            flash(f"Radiology scan '{filename}' successfully requested and added to patient gallery.", "success")

    # --- Section for handling Lab requests ---
    elif request_type == 'lab':
        # Get a list of tests from checkboxes, not a single text field
        requested_tests = request.form.getlist('lab_tests')
        department = request.form.get('lab_department', 'Pathology')

        # Check if the list is empty
        if not requested_tests:
            flash("You must select at least one lab test.", "danger")
            return redirect(url_for('patient_detail', patient_id=patient_id))
        
        try:
            with db_conn.cursor() as cursor:
                # Loop through the selected tests and create a record for each one
                for test_name in requested_tests:
                    sql = "INSERT INTO LabReport (patient_id, requested_by_doctor_id, report_type, department, report_date, status) VALUES (%s, %s, %s, %s, %s, 'Pending')"
                    cursor.execute(sql, (patient_id, session['user_id'], test_name, department, date.today()))
                db_conn.commit()
            flash(f"Lab tests requested successfully.", 'success')
        except Exception as e:
            db_conn.rollback()
            flash(f"Database error requesting lab test: {e}", "danger")
    
    # --- Fallback for invalid request types ---
    else:
        flash("Invalid request type submitted.", "warning")

    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(id) FROM Users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        flash('No administrator account found. Please register the first user.', 'info')
        return redirect(url_for('register'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role_id'] = user['role_id']
            
            log_cursor = db.cursor()
            log_cursor.execute(
                "INSERT INTO UserActivityLog (user_id, login_time) VALUES (%s, %s) RETURNING id",
                (user['id'], datetime.now())
            )
            log_id = log_cursor.fetchone()[0]
            session['log_id'] = log_id
            db.commit()
            log_cursor.close()

            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    cursor.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'log_id' in session:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE UserActivityLog SET logout_time = %s WHERE id = %s",
            (datetime.now(), session['log_id'])
        )
        db.commit()
        cursor.close()

    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(id) FROM Users")
    user_count = cursor.fetchone()[0]
    
    if user_count > 0 and 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role_id = 1
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO Users (username, password_hash, role_id) VALUES (%s, %s, %s)',
                           (username, hashed_password, role_id))
            db.commit()
            flash('Administrator account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            db.rollback()
            flash(f"Username '{username}' already exists. Please choose a different one.", 'danger')
        finally:
            cursor.close()
        
    return render_template('register_user.html', initial_setup=True)


@app.route('/register_user', methods=['GET', 'POST'])
@login_required
@admin_required
def register_user():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role_id = request.form['role_id']
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO Users (username, password_hash, role_id) VALUES (%s, %s, %s)',
                           (username, generate_password_hash(password), role_id))
            db.commit()
            flash('User created successfully!', 'success')
        except psycopg2.IntegrityError:
            db.rollback()
            flash(f"Username '{username}' already exists.", 'danger')
        finally:
            cursor.close()
        return redirect(url_for('dashboard'))
    return render_template('register_user.html', initial_setup=False)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('forgot_password'))

        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (hashed_password, user['id']))
            db.commit()
            flash('Password has been reset successfully. Please log in.', 'success')
            cursor.close()
            return redirect(url_for('login'))
        else:
            flash('Username not found.', 'danger')
            cursor.close()
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# --- Dashboard & Analytics ---
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # --- 1. PATIENT LIST SEARCH & PAGINATION LOGIC (NEWLY ADDED) ---
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 15 # Or your preferred number of patients per page

    # Get search parameters from the form
    search_name = request.args.get('name', '').strip()
    search_patient_code = request.args.get('patient_code', '').strip()
    search_mobile = request.args.get('mobile_number', '').strip()
    search_status = request.args.get('status', '').strip()

    # Dynamically build the WHERE clause for searching
    where_clauses = []
    params = []
    if search_name:
        where_clauses.append("name ILIKE %s")
        params.append(f"%{search_name}%")
    if search_patient_code:
        where_clauses.append("patient_code ILIKE %s")
        params.append(f"%{search_patient_code}%")
    if search_mobile:
        where_clauses.append("mobile_number ILIKE %s")
        params.append(f"%{search_mobile}%")
    if search_status == 'admitted':
        where_clauses.append("is_admitted = TRUE")
    elif search_status == 'discharged':
        where_clauses.append("is_admitted = FALSE")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
    # Get the total count of patients for pagination
    count_sql = f"SELECT COUNT(*) FROM Patient {where_sql}"
    cursor.execute(count_sql, tuple(params))
    total_patients_count = cursor.fetchone()[0]
    total_pages = math.ceil(total_patients_count / PER_PAGE)
    offset = (page - 1) * PER_PAGE

    # Fetch the paginated list of patients
    patient_query_params = list(params)
    patient_query_params.extend([PER_PAGE, offset])
    # *** FIX: Calculate age from 'dob' column instead of selecting a non-existent 'age' column ***
    patients_sql = f"""
        SELECT id, patient_code, name, DATE_PART('year', AGE(dob)) as age, gender, diagnosis, is_admitted 
        FROM Patient 
        {where_sql}
        ORDER BY id DESC 
        LIMIT %s OFFSET %s
    """
    cursor.execute(patients_sql, tuple(patient_query_params))
    patients = cursor.fetchall()
    
    # --- 2. EXISTING STATS AND USER LOGIC (Unchanged) ---
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM Patient")
    stats['total_patients'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Bed WHERE status = 'Occupied'")
    stats['occupied_beds'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Bed")
    stats['total_beds'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM LabReport WHERE status = 'Pending'")
    stats['pending_reports'] = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM Patient p
        JOIN (
            SELECT patient_id, MAX(next_follow_up_date) as last_follow_up_due
            FROM Prescription
            WHERE next_follow_up_date IS NOT NULL
            GROUP BY patient_id
        ) latest_prescription ON p.id = latest_prescription.patient_id
        LEFT JOIN FollowUpVisit fv ON p.id = fv.patient_id AND fv.visit_date > latest_prescription.last_follow_up_due
        WHERE latest_prescription.last_follow_up_due < CURRENT_DATE AND fv.id IS NULL;
    """)
    stats['missed_follow_ups'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM Prescription WHERE next_follow_up_date IS NOT NULL")
    stats['total_follow_ups_scheduled'] = cursor.fetchone()[0]

    cursor.execute("SELECT diagnosis FROM Patient WHERE diagnosis IS NOT NULL AND diagnosis != ''")
    diagnoses = [row['diagnosis'].strip() for row in cursor.fetchall()]
    disease_counts = Counter(diagnoses)
    cursor.execute("SELECT gender FROM Patient")
    genders = [row['gender'] for row in cursor.fetchall()]
    gender_counts = Counter(genders)

    employee_summary = {}
    all_users = []
    if session.get('role_id') == 1:
        sql_users = """
            SELECT
                u.id, u.username, u.is_active, r.name as role_name,
                COALESCE(SUM(
                    EXTRACT(EPOCH FROM (
                        COALESCE(log.logout_time, NOW()) - log.login_time
                    ))
                ), 0) as active_seconds_today
            FROM Users u
            JOIN Roles r ON u.role_id = r.id
            LEFT JOIN UserActivityLog log ON u.id = log.user_id AND log.login_time::date = CURRENT_DATE
            GROUP BY u.id, r.name
            ORDER BY u.is_active DESC, u.username;
        """
        cursor.execute(sql_users)
        all_users_raw = cursor.fetchall()

        for user in all_users_raw:
            user_dict = dict(user)
            seconds = int(user_dict['active_seconds_today'])
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            user_dict['active_time_str'] = f"{hours:02}:{minutes:02}:{seconds:02}"
            all_users.append(user_dict)
            
        if all_users:
            employee_summary['total'] = len(all_users)
            employee_summary['active'] = sum(1 for u in all_users if u['is_active'])
            employee_summary['inactive'] = employee_summary['total'] - employee_summary['active']
            employee_summary['doctors'] = sum(1 for u in all_users if u['role_name'].lower() == 'doctor')
            employee_summary['staff'] = sum(1 for u in all_users if u['role_name'].lower() == 'staff')

    cursor.execute("""
        SELECT 
            p.id, p.patient_code, p.name, p.mobile_number,
            latest_prescription.last_follow_up_due,
            (CURRENT_DATE - latest_prescription.last_follow_up_due) as days_overdue
        FROM Patient p
        JOIN (
            SELECT patient_id, MAX(next_follow_up_date) as last_follow_up_due
            FROM Prescription
            WHERE next_follow_up_date IS NOT NULL
            GROUP BY patient_id
        ) latest_prescription ON p.id = latest_prescription.patient_id
        LEFT JOIN FollowUpVisit fv ON p.id = fv.patient_id AND fv.visit_date > latest_prescription.last_follow_up_due
        WHERE latest_prescription.last_follow_up_due < CURRENT_DATE AND fv.id IS NULL
        ORDER BY days_overdue DESC;
    """)
    missed_follow_up_patients = cursor.fetchall()
    
    cursor.close()
    
    # --- 3. PASS ALL VARIABLES (OLD AND NEW) TO THE TEMPLATE ---
    return render_template('dashboard.html', 
                            stats=stats, 
                            disease_data=disease_counts, 
                            gender_data=gender_counts,
                            all_users=all_users,
                            employee_summary=employee_summary,
                            missed_follow_up_patients=missed_follow_up_patients,
                            # Add the new variables for the patient list
                            patients=patients,
                            total_pages=total_pages,
                            page=page)

# --- CORRECTED and ROBUST Patient Registration Route ---
@app.route('/register_patient', methods=['GET', 'POST'])
@login_required
def register_patient():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        try:
            # Check if a patient_id was submitted from the form
            patient_id = request.form.get('patient_id')

            # --- Fetch all form data (this is your existing helper logic) ---
            def get_form_value(key, value_type=str, default=None):
                val = request.form.get(key)
                if val is None or val.strip() == '': return default
                try: return value_type(val)
                except (ValueError, TypeError): return default

            # Core Info
            name = request.form.get('name')
            dob = get_form_value('dob')
            gender = request.form.get('gender')
            mobile_number = get_form_value('phone_number')
            email = get_form_value('email')
            address = get_form_value('address')
            city = get_form_value('city')
            state = get_form_value('state')
            pincode = get_form_value('pincode')

            # Vitals and Clinical Info (these get updated on every visit)
            temp = get_form_value('temp', float)
            bp_sys = get_form_value('bp_sys', int)
            bp_dia = get_form_value('bp_dia', int)
            blood_pressure = f"{bp_sys}/{bp_dia}" if bp_sys and bp_dia else None
            heart_rate = get_form_value('heart_rate', int)
            sugar = get_form_value('sugar', int)
            height_cm = get_form_value('height', float)
            weight_kg = get_form_value('weight', float)
            affected_bsa_percent = get_form_value('affected_bsa', float)
            complaints = get_form_value('complaints')
            diagnosis = get_form_value('diagnosis')
            initial_treatment_plan = get_form_value('initial_treatment_plan')
            
            # Combine Past History with new concerns
            concerns_list = request.form.getlist('concerns')
            concerns_details = [f"{c}: {request.form.get(f'concern_details_{c.lower().replace(" ", "_")}', '')}" if request.form.get(f'concern_details_{c.lower().replace(" ", "_")}', '') else c for c in concerns_list]
            past_history = request.form.get('past_medical_history', '')
            full_history = past_history
            if concerns_details:
                full_history += "\n\nPatient Concerns (from this visit):\n- " + "\n- ".join(concerns_details)

            # Auto-calculate BMI and BSA
            bmi = bsa = None
            if height_cm and weight_kg:
                bmi = round(weight_kg / ((height_cm / 100) ** 2), 2)
                bsa = round(math.sqrt((height_cm * weight_kg) / 3600), 2)

            if patient_id:
                # --- UPDATE LOGIC ---
                # Updates the existing patient record with new visit information
                sql_update = """
                    UPDATE Patient SET 
                        name = %s, dob = %s, gender = %s, mobile_number = %s, email = %s,
                        address = %s, city = %s, state = %s, pincode = %s,
                        initial_temperature = %s, initial_blood_pressure = %s, initial_pulse_rate = %s,
                        blood_sugar = %s, initial_height = %s, initial_weight = %s, 
                        initial_bmi = %s, initial_bsa = %s, complaints = %s, 
                        past_medical_history = %s, diagnosis = %s, initial_treatment_plan = %s,
                        affected_bsa_percentage = %s
                    WHERE id = %s
                """
                cursor.execute(sql_update, (
                    name, dob, gender, mobile_number, email, address, city, state, pincode,
                    temp, blood_pressure, heart_rate, sugar, height_cm, weight_kg, bmi, bsa,
                    complaints, full_history, diagnosis, initial_treatment_plan,
                    affected_bsa_percent, patient_id
                ))
                flash(f'Patient {name} updated successfully!', 'success')
                redirect_url = url_for('patient_detail', patient_id=patient_id)

            else:
                # --- CREATE LOGIC (Your original code) ---
                sql_insert = """
                    INSERT INTO Patient (
                        name, dob, gender, mobile_number, email, date_of_registration, address, city, state, pincode,
                        initial_temperature, initial_blood_pressure, initial_pulse_rate, blood_sugar,
                        initial_height, initial_weight, initial_bmi, initial_bsa, complaints,
                        past_medical_history, diagnosis, initial_treatment_plan, affected_bsa_percentage,
                        registered_by_doctor_id, external_patient_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """
                cursor.execute(sql_insert, (
                    name, dob, gender, mobile_number, email, date.today(), address, city, state, pincode,
                    temp, blood_pressure, heart_rate, sugar, height_cm, weight_kg, bmi, bsa,
                    complaints, full_history, diagnosis, initial_treatment_plan, affected_bsa_percent,
                    session.get('user_id'), get_form_value('external_patient_id')
                ))
                new_patient_id = cursor.fetchone()[0]
                
                patient_code = f"DERM-{new_patient_id:05d}"
                cursor.execute("UPDATE Patient SET patient_code = %s WHERE id = %s", (patient_code, new_patient_id))
                
                flash(f'New patient {name} registered successfully!', 'success')
                redirect_url = url_for('patient_detail', patient_id=new_patient_id)

            db.commit()
            return redirect(redirect_url)

        except Exception as e:
            db.rollback()
            logging.error(f"Error during patient save/update: {e}")
            flash('An error occurred. Please check the data.', 'danger')
        finally:
            cursor.close()

    # For a GET request, show a blank form for a new patient
    return render_template('register_patient.html', patient=None, is_editing=False)


# --- Patient Routes ---
@app.route('/patients', methods=['GET'])
@login_required
def list_patients():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 15

    # Get search parameters
    search_name = request.args.get('name', '').strip()
    search_patient_code = request.args.get('patient_code', '').strip()
    search_mobile = request.args.get('mobile_number', '').strip()
    search_status = request.args.get('status', '').strip()

    where_clauses = []
    params = []
    if search_name:
        where_clauses.append("name ILIKE %s")
        params.append(f"%{search_name}%")
    if search_patient_code:
        where_clauses.append("patient_code ILIKE %s")
        params.append(f"%{search_patient_code}%")
    if search_mobile:
        where_clauses.append("mobile_number ILIKE %s")
        params.append(f"%{search_mobile}%")
    if search_status == 'admitted':
        where_clauses.append("is_admitted = TRUE")
    elif search_status == 'discharged':
        where_clauses.append("is_admitted = FALSE")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
    count_sql = f"SELECT COUNT(*) FROM Patient {where_sql}"
    cursor.execute(count_sql, tuple(params))
    total_patients_count = cursor.fetchone()[0]
    total_pages = math.ceil(total_patients_count / PER_PAGE)
    offset = (page - 1) * PER_PAGE

    patient_query_params = list(params)
    patient_query_params.extend([PER_PAGE, offset])
    patients_sql = f"""
        SELECT id, patient_code, name, DATE_PART('year', AGE(dob)) as age, gender, diagnosis, is_admitted 
        FROM Patient 
        {where_sql}
        ORDER BY id DESC 
        LIMIT %s OFFSET %s
    """
    cursor.execute(patients_sql, tuple(patient_query_params))
    patients = cursor.fetchall()
    cursor.close()
        
    return render_template('patients.html', 
                           patients=patients, 
                           total_pages=total_pages,
                           page=page,
                           search_params=request.args)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT *, date_part('year', age(dob)) as age FROM Patient WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('list_patients'))

    # Check for CURRENT admission
    current_admission = None
    daily_notes = []
    if patient['is_admitted']:
        cursor.execute("""
            SELECT ba.id, ba.admission_date, b.bed_number 
            FROM BedAssignment ba
            JOIN Bed b ON ba.bed_id = b.id
            WHERE ba.patient_id = %s AND ba.discharge_date IS NULL
        """, (patient_id,))
        current_admission = cursor.fetchone()
        
        if current_admission:
            cursor.execute("""
                SELECT dpn.*, u.username as doctor_name
                FROM DailyProgressNote dpn JOIN Users u ON dpn.doctor_id = u.id
                WHERE dpn.assignment_id = %s ORDER BY dpn.note_date DESC
            """, (current_admission['id'],))
            daily_notes = cursor.fetchall()

    # NEW: Fetch PAST, discharged admission history
    cursor.execute("""
        SELECT ba.id, ba.admission_date, ba.discharge_date, ba.discharge_summary, b.bed_number
        FROM BedAssignment ba
        JOIN Bed b ON ba.bed_id = b.id
        WHERE ba.patient_id = %s AND ba.discharge_date IS NOT NULL
        ORDER BY ba.discharge_date DESC
    """, (patient_id,))
    admission_history = cursor.fetchall()
    
    # Fetch other patient details as before
    cursor.execute("SELECT fv.*, u.username as doctor_name FROM FollowUpVisit fv JOIN Users u ON fv.doctor_id = u.id WHERE fv.patient_id = %s ORDER BY fv.visit_date DESC", (patient_id,))
    followup_visits = cursor.fetchall()
    
    cursor.execute("SELECT p.*, u.username as doctor_name FROM Prescription p JOIN Users u ON p.doctor_id = u.id WHERE p.patient_id = %s ORDER BY p.prescription_date DESC", (patient_id,))
    prescriptions_raw = cursor.fetchall()
    prescriptions_with_items = []
    for p in prescriptions_raw:
        cursor.execute("SELECT * FROM PrescriptionItem WHERE prescription_id = %s", (p['id'],))
        items = cursor.fetchall()
        prescriptions_with_items.append({'prescription': p, 'items': items})

    cursor.execute("SELECT * FROM PatientImage WHERE patient_id = %s ORDER BY upload_date DESC", (patient_id,))
    images = cursor.fetchall()

    cursor.execute("SELECT * FROM LabReport WHERE patient_id = %s ORDER BY report_date DESC", (patient_id,))
    lab_reports = cursor.fetchall()
    
    cursor.close()
    
    return render_template('patient_detail.html', 
                           patient=patient, 
                           followup_visits=followup_visits,
                           prescriptions=prescriptions_with_items,
                           lab_reports=lab_reports,
                           images=images, 
                           now=datetime.now(),
                           admission=current_admission,
                           daily_notes=daily_notes,
                           admission_history=admission_history,  # Pass history to template
                           lab_test_categories=TEST_CATEGORIES)

# In app.py, add this new function

@app.route('/assignment/<int:assignment_id>/add_note', methods=['POST'])
@login_required
def add_daily_note(assignment_id):
    notes = request.form.get('notes')
    doctor_id = session.get('user_id')
    
    if not notes:
        flash('Note cannot be empty.', 'danger')
        # We need the patient_id to redirect back, so we have to query it
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT patient_id FROM BedAssignment WHERE id = %s", (assignment_id,))
        assignment = cursor.fetchone()
        cursor.close()
        if assignment:
            return redirect(url_for('patient_detail', patient_id=assignment['patient_id']))
        return redirect(url_for('dashboard')) # Fallback redirect

    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Get patient_id for the redirect before we do anything else
        cursor.execute("SELECT patient_id FROM BedAssignment WHERE id = %s", (assignment_id,))
        assignment = cursor.fetchone()
        
        # Insert the new progress note
        cursor.execute(
            "INSERT INTO DailyProgressNote (assignment_id, note_date, notes, doctor_id) VALUES (%s, %s, %s, %s)",
            (assignment_id, datetime.now(), notes, doctor_id)
        )
        db.commit()
        flash('Progress note added successfully.', 'success')
        
        if assignment:
            return redirect(url_for('patient_detail', patient_id=assignment['patient_id']))

    except (Exception, psycopg2.Error) as e:
        db.rollback()
        flash(f'Error adding note: {e}', 'danger')
        # Try to redirect back even if there's an error
        if 'assignment' in locals() and assignment:
            return redirect(url_for('patient_detail', patient_id=assignment['patient_id']))
    finally:
        cursor.close()

    return redirect(url_for('dashboard'))

# In app.py

@app.route('/patient/<int:patient_id>/edit', methods=['GET'])
@login_required
def edit_patient(patient_id):
    """
    This route now ONLY displays the registration form pre-filled
    with an existing patient's data.
    """
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT * FROM Patient WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()
    cursor.close()
    
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('list_patients'))
        
    # It renders your existing registration form in "edit mode"
    return render_template('register_patient.html', patient=patient, is_editing=True)



@app.route('/patient/<int:patient_id>/upload_image', methods=['POST'])
@login_required
def upload_patient_image(patient_id):
    if 'patient_image' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    file = request.files['patient_image']
    if file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        cursor = db.cursor()
        # Corrected to use 'image_filename' and 'notes'
        cursor.execute(
            "INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes) VALUES (%s, %s, %s, %s)",
            (patient_id, filename, date.today(), 'Clinical Photo')
        )
        db.commit()
        cursor.close()
        flash('Image uploaded successfully', 'success')
    else:
        flash('Invalid file type or no file selected.', 'danger')
    return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Follow-up Visits ---
@app.route('/patient/<int:patient_id>/add_visit', methods=['GET', 'POST'])
@login_required
def add_follow_up_visit(patient_id):
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        try:
            sql = """
                INSERT INTO FollowUpVisit (patient_id, doctor_id, visit_date, complaints, 
                                           examination_findings, diagnosis, treatment_plan, notes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                patient_id, session['user_id'], date.today(),
                request.form.get('complaints'), request.form.get('examination_findings'),
                request.form.get('diagnosis'), request.form.get('updated_treatment_plan'),
                request.form.get('notes')
            ))
            db.commit()
            flash('Follow-up visit recorded successfully.', 'success')
        except Exception as e:
            db.rollback()
            logging.error(f"Error adding follow-up visit: {e}")
            flash('Error adding follow-up visit.', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('patient_detail', patient_id=patient_id))
        
    return render_template('add_follow_up_visit.html', patient_id=patient_id)
    
@app.route('/follow_ups')
@login_required
def list_follow_up_visits():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT fv.*, p.name as patient_name, p.patient_code, u.username as doctor_name
        FROM FollowUpVisit fv
        JOIN Patient p ON fv.patient_id = p.id
        JOIN Users u ON fv.doctor_id = u.id
        ORDER BY fv.visit_date DESC
    """)
    visits = cursor.fetchall()
    cursor.close()
    return render_template('follow_ups.html', visits=visits)
    
# --- Prescriptions ---
@app.route('/prescriptions/new', methods=['GET', 'POST'])
@login_required
def create_prescription():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, patient_code, name FROM Patient ORDER BY name")
    patients = cursor.fetchall()
    cursor.execute("SELECT name FROM Medication ORDER BY name")
    medications = cursor.fetchall()
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        condition_notes = request.form.get('condition_notes')
        next_follow_up_str = request.form.get('next_follow_up_date')
        
        next_follow_up_date = None
        if next_follow_up_str:
            try:
                next_follow_up_date = datetime.strptime(next_follow_up_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for next follow-up. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('create_prescription'))

        sql_presc = """
            INSERT INTO Prescription 
            (patient_id, doctor_id, prescription_date, condition_notes, next_follow_up_date) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
        cursor.execute(sql_presc, (patient_id, session['user_id'], datetime.now(), condition_notes, next_follow_up_date))
        prescription_id = cursor.fetchone()['id']
        med_index = 0
        while f'med_name_{med_index}' in request.form:
            med_name = request.form.get(f'med_name_{med_index}')
            if med_name:
                sql_item = "INSERT INTO PrescriptionItem (prescription_id, medication_name, dosage, frequency, duration, notes) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(sql_item, (prescription_id, med_name, request.form.get(f'med_dosage_{med_index}'), request.form.get(f'med_frequency_{med_index}'), request.form.get(f'med_duration_{med_index}'), request.form.get(f'med_notes_{med_index}')))
            med_index += 1
        db.commit()
        flash('Prescription created.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    cursor.close()
    return render_template('create_prescription.html', patients=patients, medications=medications)

@app.route('/prescription/<int:prescription_id>/print')
@login_required
def print_prescription(prescription_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT pr.*, p.name as patient_name, p.patient_code, p.dob, p.gender, u.username as doctor_name
        FROM Prescription pr
        JOIN Patient p ON pr.patient_id = p.id
        JOIN Users u ON pr.doctor_id = u.id
        WHERE pr.id = %s
    """, (prescription_id,))
    prescription = cursor.fetchone()
    cursor.execute("SELECT * FROM PrescriptionItem WHERE prescription_id = %s", (prescription_id,))
    items = cursor.fetchall()
    cursor.close()
    
    age = None
    if prescription and prescription['dob']:
        today = date.today()
        born = prescription['dob']
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    return render_template('print_prescription.html', prescription=prescription, items=items, age=age)

# --- Lab Reports ---
@app.route('/lab_reports', methods=['GET'])
@login_required
def list_lab_reports():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT lr.*, p.name as patient_name, p.patient_code, u.username as doctor_name
        FROM LabReport lr
        JOIN Patient p ON lr.patient_id = p.id
        LEFT JOIN Users u ON lr.requested_by_doctor_id = u.id
        ORDER BY lr.department, lr.report_date DESC
    """)
    reports_list = cursor.fetchall()
    cursor.close()

    # Group the reports by department for better display
    grouped_reports = defaultdict(list)
    for report in reports_list:
        grouped_reports[report['department']].append(report)

    # Pass the grouped dictionary to the template
    return render_template('lab_reports.html', grouped_reports=grouped_reports)

@app.route('/lab_report/<int:report_id>/update_status', methods=['POST'])
@login_required
def update_lab_report_status(report_id):
    new_status = request.form.get('status')
    if new_status:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE LabReport SET status = %s WHERE id = %s", (new_status, report_id))
        db.commit()
        cursor.close()
        flash('Report status updated.', 'success')
    return redirect(url_for('list_lab_reports'))
    
@app.route('/lab_report/<int:report_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_lab_report(report_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        if 'report_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['report_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            cursor.execute("UPDATE LabReport SET file_path = %s, status = 'Completed' WHERE id = %s", (filename, report_id))
            db.commit()
            flash('Report file uploaded successfully', 'success')
            cursor.close()
            return redirect(url_for('list_lab_reports'))
            
    cursor.execute("SELECT lr.*, p.name as patient_name FROM LabReport lr JOIN Patient p ON lr.patient_id = p.id WHERE lr.id = %s", (report_id,))
    report = cursor.fetchone()
    cursor.close()
    return render_template('upload_lab_report.html', report=report)


# --- Bed Management ---
@app.route('/bed_management')
@login_required
def bed_management():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch all beds and their current assignment details if occupied
    cursor.execute("""
        SELECT b.id as bed_id, b.bed_number, b.status, ba.id as assignment_id, p.name as patient_name, p.patient_code, ba.admission_date
        FROM Bed b
        LEFT JOIN BedAssignment ba ON b.id = ba.bed_id AND ba.discharge_date IS NULL
        LEFT JOIN Patient p ON ba.patient_id = p.id
        ORDER BY b.bed_number
    """)
    beds = cursor.fetchall()
    
    # Fetch patients who are not currently admitted
    cursor.execute("""
        SELECT id, patient_code, name FROM Patient 
        WHERE id NOT IN (SELECT patient_id FROM BedAssignment WHERE discharge_date IS NULL)
        ORDER BY name
    """)
    unassigned_patients = cursor.fetchall()
    
    cursor.close()
    return render_template('bed_management.html', beds=beds, unassigned_patients=unassigned_patients)

@app.route('/bed/add', methods=['POST'])
@login_required
@admin_required
def add_bed():
    db = get_db()
    cursor = db.cursor()
    try:
        prefix = request.form['bed_prefix']
        start = int(request.form['start_number'])
        end = int(request.form['end_number'])
        for i in range(start, end + 1):
            bed_number = f"{prefix}{i}"
            cursor.execute("INSERT INTO Bed (bed_number) VALUES (%s) ON CONFLICT (bed_number) DO NOTHING", (bed_number,))
        db.commit()
        flash(f'Beds from {prefix}{start} to {prefix}{end} added or already exist.', 'success')
    except (Exception, psycopg2.Error) as e:
        db.rollback()
        flash(f'Error adding beds: {e}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('bed_management'))

# In app.py, add this new function

@app.route('/bed/<int:bed_id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_bed(bed_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Check if the bed is occupied before deleting
        cursor.execute("SELECT status FROM Bed WHERE id = %s", (bed_id,))
        bed = cursor.fetchone()
        if bed and bed[0] == 'Occupied':
            flash('Cannot remove an occupied bed.', 'danger')
            return redirect(url_for('bed_management'))

        # If available, proceed with deletion
        cursor.execute("DELETE FROM Bed WHERE id = %s", (bed_id,))
        db.commit()
        flash('Bed removed successfully.', 'success')
    except (Exception, psycopg2.Error) as e:
        db.rollback()
        flash(f'Error removing bed: {e}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('bed_management'))

@app.route('/bed/<int:bed_id>/assign', methods=['POST'])
@login_required
def assign_bed(bed_id):
    patient_id = request.form['patient_id']
    db = get_db()
    cursor = db.cursor()
    try:
        # Create a new assignment
        cursor.execute("INSERT INTO BedAssignment (patient_id, bed_id, admission_date) VALUES (%s, %s, %s)", (patient_id, bed_id, datetime.now()))
        # Update bed status
        cursor.execute("UPDATE Bed SET status = 'Occupied' WHERE id = %s", (bed_id,))
        # Update patient admission status
        cursor.execute("UPDATE Patient SET is_admitted = TRUE WHERE id = %s", (patient_id,))
        db.commit()
        flash('Bed assigned successfully.', 'success')
    except (Exception, psycopg2.Error) as e:
        db.rollback()
        flash(f'Error assigning bed: {e}', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('bed_management'))


# --- User Management (Admin) ---
@app.route('/user/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT is_active FROM Users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        new_status = not user['is_active']
        cursor.execute("UPDATE Users SET is_active = %s WHERE id = %s", (new_status, user_id))
        db.commit()
        flash(f"User status updated to {'Active' if new_status else 'Inactive'}.", 'success')
    else:
        flash("User not found.", 'danger')
    cursor.close()
    return redirect(url_for('dashboard'))

# --- API Endpoints ---
@app.route('/api/weekly_registrations')
@login_required
def weekly_registrations():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    query = """
    SELECT 
        d.day::date, 
        COUNT(p.id) as count
    FROM 
        generate_series(
            (CURRENT_DATE - INTERVAL '6 days'), 
            CURRENT_DATE, 
            '1 day'
        ) AS d(day)
    LEFT JOIN 
        Patient p ON p.date_of_registration = d.day::date
    GROUP BY 
        d.day
    ORDER BY 
        d.day;
    """
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    
    # Format data for Chart.js
    labels = [row['day'].strftime('%a, %b %d') for row in data]
    values = [row['count'] for row in data]
    
    return jsonify(labels=labels, values=values)
    
# app.py

# In app.py

@app.route('/api/user_activity/<int:user_id>')
@login_required
@admin_required
def get_user_activity(user_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    all_activities = []

    try:
        # --- The existing queries for patient activities remain the same ---
        # Patient Registrations
        cursor.execute("""
            SELECT 'Patient Registration' as type, p.name, p.id as patient_id, 
                   p.date_of_registration::timestamp as activity_date 
            FROM Patient p WHERE p.registered_by_doctor_id = %s
        """, (user_id,))
        for reg in cursor.fetchall(): all_activities.append(dict(reg))

        # Follow-up Visits
        cursor.execute("""
            SELECT 'Follow-up Visit' as type, p.name, p.id as patient_id, 
                   fv.visit_date::timestamp as activity_date 
            FROM FollowUpVisit fv JOIN Patient p ON fv.patient_id = p.id WHERE fv.doctor_id = %s
        """, (user_id,))
        for followup in cursor.fetchall(): all_activities.append(dict(followup))

        # Prescriptions
        cursor.execute("""
            SELECT 'Prescription Created' as type, p.name, p.id as patient_id, 
                   pr.prescription_date as activity_date 
            FROM Prescription pr JOIN Patient p ON pr.patient_id = p.id WHERE pr.doctor_id = %s
        """, (user_id,))
        for prescription in cursor.fetchall(): all_activities.append(dict(prescription))

        # --- NEW: Query for Login and Logout Events ---
        # Get all login times
        cursor.execute("""
            SELECT 'Login' as type, login_time as activity_date 
            FROM UserActivityLog WHERE user_id = %s
        """, (user_id,))
        for login in cursor.fetchall():
            all_activities.append({'type': 'Login', 'name': 'System Access', 'patient_id': None, 'activity_date': login['activity_date']})

        # Get all logout times
        cursor.execute("""
            SELECT 'Logout' as type, logout_time as activity_date 
            FROM UserActivityLog WHERE user_id = %s AND logout_time IS NOT NULL
        """, (user_id,))
        for logout in cursor.fetchall():
            all_activities.append({'type': 'Logout', 'name': 'System Access', 'patient_id': None, 'activity_date': logout['activity_date']})
        # --- END NEW SECTION ---
        
    except Exception as e:
        logging.error(f"Error fetching user activity for user {user_id}: {e}")
        return jsonify({"error": "Failed to fetch user activity"}), 500
    finally:
        cursor.close()

    # Sort all activities together by date (newest first)
    all_activities.sort(key=lambda x: x['activity_date'], reverse=True)
    
    return jsonify(all_activities)
    
@app.route('/api/patient/<string:uhid>', methods=['GET'])
def get_dermatology_data(uhid):
    """
    API endpoint for easy browser access. It first checks for dummy data,
    then queries the live database. NO API KEY IS REQUIRED.
    """
    DUMMY_API_DATA = {
        "DERM001": {
            "department": "Dermatology Department",
            "medical_records": {
                "diagnosis": "Chronic Plaque Psoriasis",
                "record_date": "2025-08-29",
                "record_id": "REC-73451",
                "follow_up_visit_count": 0, # dummy value
                "test_results": {
                    "bsa": 1.85,
                    "affected_bsa_percent": 12.5,
                    "skin_examination": "Erythematous plaques with well-defined borders and silvery scales on elbows, knees, and scalp."
                },
                "lab_reports": [
                    {
                        "report_name": "Skin Biopsy",
                        "result": "Consistent with psoriasis, showing parakeratosis and Munro's microabscesses."
                    }
                ],
                "prescription": [
                    {
                        "name": "Clobetasol Propionate Cream", "dosage": "0.05%",
                        "frequency": "Twice daily", "duration": "4 weeks"
                    }
                ],
                "treatment_summary": "Combination topical therapy with high-potency corticosteroids and vitamin D analogues. Phototherapy recommended if no improvement."
            }
        },
        "DERM002": {
            "department": "Dermatology Department",
            "medical_records": {
                "diagnosis": "Nodulocystic Acne",
                "record_date": "2025-07-15",
                "record_id": "REC-73109",
                "follow_up_visit_count": 2, # dummy value
                "test_results": {
                    "bsa": 1.60,
                    "affected_bsa_percent": 4.0,
                    "skin_examination": "Multiple inflammatory nodules and cysts on the face, neck, and upper back. Significant scarring present."
                },
                "lab_reports": [
                    { "report_name": "Hormone Panel", "result": "Within normal limits." }
                ],
                "prescription": [
                    { "name": "Isotretinoin", "dosage": "40mg", "frequency": "Once daily with food", "duration": "6 months" }
                ],
                "treatment_summary": "Systemic therapy with oral isotretinoin initiated due to severity and scarring. Patient counseled on side effects."
            }
        }
    }

    if uhid in DUMMY_API_DATA:
        return jsonify(DUMMY_API_DATA[uhid])

    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("SELECT * FROM Patient WHERE patient_code = %s", (uhid,))
    patient = cursor.fetchone()
    if not patient:
        cursor.close()
        return jsonify({"error": f"Patient with UHID '{uhid}' not found"}), 404

    # Fetch latest prescription
    cursor.execute("""
        SELECT pi.medication_name, pi.dosage, pi.frequency, pi.duration
        FROM PrescriptionItem pi
        JOIN Prescription p ON pi.prescription_id = p.id
        WHERE p.patient_id = %s ORDER BY p.prescription_date DESC
    """, (patient['id'],))
    prescriptions_db = cursor.fetchall()
    prescription_list = [
        {"name": item['medication_name'], "dosage": item['dosage'], 
         "frequency": item['frequency'], "duration": item['duration']}
        for item in prescriptions_db
    ]

    # Fetch lab reports
    cursor.execute("SELECT report_type, file_path FROM LabReport WHERE patient_id = %s", (patient['id'],))
    lab_reports_db = cursor.fetchall()
    lab_reports_list = [
        {"report_name": report['report_type'], "result": f"Report available at {report['file_path']}" if report['file_path'] else "Pending"}
        for report in lab_reports_db
    ]
    cursor.execute("SELECT COUNT(id) as visit_count FROM FollowUpVisit WHERE patient_id = %s", (patient['id'],))
    visit_count_result = cursor.fetchone()
    visit_count = visit_count_result['visit_count'] if visit_count_result else 0

    response = {
        "department": "Dermatology Department",
        "medical_records": {
            "diagnosis": patient['diagnosis'],
            "record_date": patient['date_of_registration'].strftime('%Y-%m-%d') if patient['date_of_registration'] else None,
            "record_id": f"REC-{patient['id']}",
            "follow_up_visit_count": visit_count,  # Placeholder; implement actual count if needed
            "test_results": {
                "bsa": patient['initial_bsa'],
                "affected_bsa_percent": patient['affected_bsa_percentage'],
                "skin_examination": patient['complaints']
            },
            "lab_reports": lab_reports_list,
            "prescription": prescription_list,
            "treatment_summary": patient['initial_treatment_plan']
        }
    }
    cursor.close()
    return jsonify(response)
    
@app.route('/missed_follow_ups')
@login_required
def missed_follow_ups():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("""
        SELECT 
            p.id, p.patient_code, p.name, p.mobile_number,
            latest_prescription.last_follow_up_due,
            (CURRENT_DATE - latest_prescription.last_follow_up_due) as days_overdue
        FROM Patient p
        JOIN (
            SELECT patient_id, MAX(next_follow_up_date) as last_follow_up_due
            FROM Prescription
            WHERE next_follow_up_date IS NOT NULL
            GROUP BY patient_id
        ) latest_prescription ON p.id = latest_prescription.patient_id
        LEFT JOIN FollowUpVisit fv ON p.id = fv.patient_id AND fv.visit_date > latest_prescription.last_follow_up_due
        WHERE latest_prescription.last_follow_up_due < CURRENT_DATE AND fv.id IS NULL
        ORDER BY days_overdue DESC;
    """)
    
    missed_patients = cursor.fetchall()
    cursor.close()
    
    return render_template('missed_follow_ups.html', patients=missed_patients)


# --- Diagnostic Center (Image Gallery) ---
@app.route('/diagnostic_center')
@login_required
def diagnostic_center():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch all patients for the dropdown
    cursor.execute("SELECT id, patient_code, name FROM Patient ORDER BY name")
    patients = cursor.fetchall()
    
    # CORRECTED: Changed pi.file_path to pi.image_filename and pi.caption to pi.notes
    cursor.execute("""
        SELECT pi.id, pi.image_filename, pi.notes, pi.upload_date, p.id as patient_id, p.patient_code, p.name as patient_name
        FROM PatientImage pi
        JOIN Patient p ON pi.patient_id = p.id
        ORDER BY pi.upload_date DESC
    """)
    images = cursor.fetchall()
    cursor.close()
    
    # Split images into two lists based on type for the tabs in the template
    clinical_notes = ['Clinical Photo', 'Uploaded via mobile']
    diagnostic_reports = [img for img in images if img['notes'] not in clinical_notes]
    clinical_photos = [img for img in images if img['notes'] in clinical_notes]
    return render_template('diagnostic_center.html', 
                           diagnostic_reports=diagnostic_reports, 
                           clinical_photos=clinical_photos)

@app.route('/diagnostic_center/upload', methods=['POST'])
@login_required
def diagnostic_center_upload():
    patient_id = request.form.get('patient_id')
    caption = request.form.get('caption', '')
    
    if 'diagnostic_image' not in request.files or not patient_id:
        flash('Patient and file are required.', 'danger')
        return redirect(url_for('diagnostic_center'))
        
    file = request.files['diagnostic_image']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('diagnostic_center'))
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO PatientImage (patient_id, file_path, upload_date, caption) VALUES (%s, %s, %s, %s)",
            (patient_id, filename, datetime.now(), caption)
        )
        db.commit()
        cursor.close()
        flash('Image uploaded and linked to patient successfully.', 'success')
    else:
        flash('File type not allowed.', 'danger')
        
    return redirect(url_for('diagnostic_center'))

# In app.py, replace your existing delete_images function with this corrected version.



# --- ADD THIS NEW FUNCTION to app.py ---



@app.route('/patients/download')
@login_required
@admin_required  # <-- ADD THIS DECORATOR
def download_patient_data():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # This advanced query joins patient data with their latest follow-up and all their prescriptions
    query = """
        SELECT 
            p.id, p.patient_code, p.name, p.gender, p.diagnosis,
            to_char(p.date_of_registration, 'YYYY-MM-DD') as date_of_registration,
            CASE 
                WHEN p.dob IS NULL OR p.dob = 'infinity'::date OR p.dob = '-infinity'::date THEN NULL
                ELSE date_part('year', age(p.dob))
            END as age,
            p.mobile_number, p.email, p.address, p.city, p.state, p.pincode,
            p.initial_treatment_plan,
            latest_follow_up.visit_date as last_follow_up_date,
            prescriptions.all_medications
        FROM 
            Patient p
        LEFT JOIN (
            SELECT patient_id, MAX(visit_date) as visit_date
            FROM FollowUpVisit
            GROUP BY patient_id
        ) latest_follow_up ON p.id = latest_follow_up.patient_id
        LEFT JOIN (
            SELECT pr.patient_id, STRING_AGG(pi.medication_name || ' (' || pi.dosage || ')', '; ') as all_medications
            FROM Prescription pr
            JOIN PrescriptionItem pi ON pr.id = pi.prescription_id
            GROUP BY pr.patient_id
        ) prescriptions ON p.id = prescriptions.patient_id
    """
    
    filters = []
    params = []
    search_params = request.args
    # (The filtering logic remains the same as before)
    if search_params:
        patient_id = search_params.get('patient_id')
        mobile = search_params.get('mobile')
        if patient_id:
            filters.append("(LOWER(p.patient_code) LIKE %s OR CAST(p.id AS TEXT) LIKE %s)")
            params.extend([f"%{patient_id.lower()}%", f"%{patient_id}%"])
        if mobile:
            filters.append("p.mobile_number LIKE %s")
            params.append(f"%{mobile}%")
            
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY p.id DESC"
    
    cursor.execute(query, tuple(params))
    patients = cursor.fetchall()
    cursor.close()

    # --- CSV Generation Logic ---
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Define the new, more detailed header row
    header = [
        'Patient Code', 'Name', 'Age', 'Gender', 'Initial Diagnosis', 
        'Registration Date', 'Mobile', 'Email', 'Initial Treatment', 
        'Last Follow-up Date', 'Prescribed Medications'
    ]
    writer.writerow(header)
    
    # Write the new data for each row
    for patient in patients:
        row = [
            patient['patient_code'], 
            patient['name'], 
            patient['age'], 
            patient['gender'],
            patient['diagnosis'], 
            patient['date_of_registration'], 
            patient['mobile_number'],
            patient['email'],
            patient['initial_treatment_plan'],
            patient['last_follow_up_date'],
            patient['all_medications']
        ]
        writer.writerow(row)
    
    output.seek(0)
    
    # Create a Flask response to send the file
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=patient_detailed_export.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

# --- ADD THIS NEW FUNCTION to app.py ---



# --- ADD THIS NEW FUNCTION to app.py ---

  

@app.route('/assignment/<int:assignment_id>/discharge', methods=['GET', 'POST'])
@login_required
def discharge_patient(assignment_id):
    """
    Handles the creation of a NEW discharge summary.
    - GET: Shows the form, auto-generating a summary from daily notes.
    - POST: Saves the final summary, updates patient/bed status, and completes the discharge.
    """
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        # This block handles SAVING the new discharge summary.
        discharge_summary = request.form.get('discharge_summary', 'Patient discharged without summary.')
        try:
            cursor.execute("SELECT bed_id, patient_id FROM BedAssignment WHERE id = %s", (assignment_id,))
            assignment = cursor.fetchone()
            if assignment:
                # Update the record with the discharge date and the full summary text
                cursor.execute(
                    "UPDATE BedAssignment SET discharge_date = %s, discharge_summary = %s WHERE id = %s",
                    (datetime.now(), discharge_summary, assignment_id)
                )
                # Update related records
                cursor.execute("UPDATE Bed SET status = 'Available' WHERE id = %s", (assignment['bed_id'],))
                cursor.execute("UPDATE Patient SET is_admitted = FALSE WHERE id = %s", (assignment['patient_id'],))
                db.commit()
                flash('Patient discharged successfully.', 'success')
            else:
                flash('Assignment not found.', 'danger')
        except (Exception, psycopg2.Error) as e:
            db.rollback()
            flash(f'Error during discharge: {e}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('bed_management'))
    
    # This block handles SHOWING the form for a NEW discharge (GET request).
    cursor.execute("""
        SELECT p.id, p.name, p.patient_code, p.diagnosis, b.bed_number
        FROM BedAssignment ba 
        JOIN Patient p ON ba.patient_id = p.id
        JOIN Bed b ON ba.bed_id = b.id
        WHERE ba.id = %s
    """, (assignment_id,))
    patient_info = cursor.fetchone()

    if not patient_info:
        cursor.close()
        flash('Patient or assignment not found.', 'danger')
        return redirect(url_for('bed_management'))
        
    cursor.execute("""
        SELECT dpn.notes, dpn.note_date, u.username as doctor_name
        FROM DailyProgressNote dpn
        JOIN Users u ON dpn.doctor_id = u.id
        WHERE dpn.assignment_id = %s
        ORDER BY dpn.note_date ASC
    """, (assignment_id,))
    notes = cursor.fetchall()
    cursor.close()

    # Auto-generate the summary string
    summary_parts = []
    if patient_info['diagnosis']:
        summary_parts.append(f"Patient was admitted with a diagnosis of {patient_info['diagnosis']}.")
    
    summary_parts.append("\nCourse of treatment during hospital stay:")
    if notes:
        for note in notes:
            note_date = note['note_date'].strftime('%d-%b-%Y')
            summary_parts.append(f"- On {note_date}, Dr. {note['doctor_name']} noted: {note['notes']}")
    else:
        summary_parts.append("- No daily progress notes were recorded.")
        
    auto_summary = "\n".join(summary_parts)

    return render_template(
        'discharge_summary.html', 
        patient=patient_info, 
        assignment_id=assignment_id,
        auto_summary=auto_summary,
        is_editing=False # Flag to tell the template this is a new discharge
    )


@app.route('/assignment/<int:assignment_id>/edit_summary', methods=['GET', 'POST'])
@login_required
def edit_discharge_summary(assignment_id):
    """
    Handles EDITING an EXISTING discharge summary.
    - GET: Fetches the saved summary, parses it, and pre-fills the form.
    - POST: Saves the updated summary text to the existing record.
    """
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        # This block handles SAVING the edited summary.
        updated_summary = request.form.get('discharge_summary')
        try:
            cursor.execute("SELECT patient_id FROM BedAssignment WHERE id = %s", (assignment_id,))
            assignment = cursor.fetchone()
            
            cursor.execute("UPDATE BedAssignment SET discharge_summary = %s WHERE id = %s", (updated_summary, assignment_id))
            db.commit()
            flash('Discharge summary updated successfully.', 'success')
            
            if assignment:
                return redirect(url_for('patient_detail', patient_id=assignment['patient_id']))
        except (Exception, psycopg2.Error) as e:
            db.rollback()
            flash(f'Error updating summary: {e}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('bed_management'))

    # This block handles SHOWING the form for EDITING (GET request).
    cursor.execute("""
        SELECT ba.discharge_summary, p.id, p.name, p.patient_code, p.diagnosis, b.bed_number
        FROM BedAssignment ba 
        JOIN Patient p ON ba.patient_id = p.id
        JOIN Bed b ON ba.bed_id = b.id
        WHERE ba.id = %s
    """, (assignment_id,))
    assignment_data = cursor.fetchone()
    cursor.close()

    if not assignment_data:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('bed_management'))

    # Parse the saved summary string back into its component parts
    full_summary = assignment_data['discharge_summary'] or ''
    parts = {'diagnosis': '', 'summary': '', 'follow_up': ''}
    try:
        diag_split = full_summary.split('SUMMARY OF HOSPITAL STAY:')
        parts['diagnosis'] = diag_split[0].replace('FINAL DIAGNOSIS:', '').strip()
        
        summary_split = diag_split[1].split('FOLLOW-UP PLAN:')
        parts['summary'] = summary_split[0].strip()
        parts['follow_up'] = summary_split[1].strip()
    except IndexError:
        parts['summary'] = full_summary

    return render_template(
        'discharge_summary.html',
        patient=assignment_data,
        assignment_id=assignment_id,
        is_editing=True,  # Flag to tell the template it's in "edit mode"
        existing_diagnosis=parts['diagnosis'],
        auto_summary=parts['summary'],
        existing_follow_up=parts['follow_up']
    )
# --- ADD THIS NEW FUNCTION to app.py ---

@app.route('/patient/<int:patient_id>/edit_initial', methods=['POST'])
@login_required
def edit_initial_visit(patient_id):
    db = get_db()
    cursor = db.cursor()
    try:
        complaints = request.form.get('complaints')
        diagnosis = request.form.get('diagnosis')

        # This updates the columns on the main Patient record
        sql = """
            UPDATE Patient SET 
            complaints = %s,
            diagnosis = %s
            WHERE id = %s
        """
        cursor.execute(sql, (complaints, diagnosis, patient_id))
        db.commit()
        
        flash('Initial visit details updated successfully.', 'success')

    except Exception as e:
        db.rollback()
        logging.error(f"Error updating initial visit for patient {patient_id}: {e}")
        flash('An error occurred while updating the details.', 'danger')
    finally:
        cursor.close()
    
    # Redirect back to the patient detail page
    return redirect(url_for('patient_detail', patient_id=patient_id))

# --- ADD THIS NEW FUNCTION to app.py ---

@app.route('/mobile_upload/<int:patient_id>', methods=['GET', 'POST'])
def mobile_upload(patient_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get patient details to display on the page
    cursor.execute("SELECT patient_code, name FROM Patient WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        return "Patient not found.", 404

    if request.method == 'POST':
        if 'patient_image' not in request.files:
            flash('No file part in the request.', 'danger')
            return redirect(request.url)
        
        file = request.files['patient_image']

        if file.filename == '':
            flash('No file selected for upload.', 'warning')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
          
            cursor.execute(
                "INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes) VALUES (%s, %s, %s, %s)",
                (patient_id, filename, datetime.now().date(), 'Uploaded via mobile')
            )
            db.commit()
            flash(f'Image for {patient["name"]} uploaded successfully!', 'success')
        else:
            flash('File type not allowed.', 'danger')
        
        cursor.close()
        return redirect(url_for('mobile_upload', patient_id=patient_id))

    # For a GET request, just show the upload page
    cursor.close()
    return render_template('mobile_upload.html', patient=patient)



# --- NEW: API for Patient Search with Visit Count ---
@app.route('/api/search_existing_patients')
@login_required
def search_patients():
    """
    API endpoint that ONLY searches the local 'Patient' table
    to find existing patients that can be edited.
    """
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    sql = """
        SELECT id, patient_code, name 
        FROM Patient
        WHERE name ILIKE %s OR patient_code ILIKE %s
        ORDER BY name
        LIMIT 10;
        
    """
    search_term = f"%{query}%"
    cursor.execute(sql, (search_term, search_term))
    patients = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    
    return jsonify(patients)

# --- NEW: Route for Standalone Follow-up Visit Form ---
@app.route('/patient_visit', methods=['GET', 'POST'])
@login_required
def patient_visit():
    """
    Handles the standalone follow-up visit form.
    - GET: Displays the form with the patient search bar.
    - POST: Saves the new follow-up visit to the database.
    """
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        try:
            patient_id = request.form.get('patient_id')
            if not patient_id:
                flash('No patient selected. Please search and select a patient first.', 'danger')
                return redirect(url_for('patient_visit'))

            # Save the visit details to the database
            sql = """
                INSERT INTO FollowUpVisit (patient_id, doctor_id, visit_date, complaints, 
                                           examination_findings, diagnosis, treatment_plan) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                patient_id, session['user_id'], date.today(), 
                request.form.get('complaints'), 
                request.form.get('examination_findings'), 
                request.form.get('diagnosis'), 
                request.form.get('updated_treatment_plan')
            ))
            db.commit()
            flash('Follow-up visit recorded successfully.', 'success')
            return redirect(url_for('patient_detail', patient_id=patient_id))
        except Exception as e:
            db.rollback()
            logging.error(f"Error adding follow-up visit from patient_visit route: {e}")
            flash('An error occurred while saving the visit.', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('patient_visit'))
        
    return render_template('patient_visit.html')

# --- NEW ROUTE TO DISPLAY THE STANDALONE FORM ---
@app.route('/request_investigation_form')
@login_required
def request_investigation_form():
    """Renders the standalone investigation request page."""
    return render_template('request_lab_report.html')

from radiology_api import radiology_bp, perform_radiology_request
from lab_api import lab_bp

app.register_blueprint(radiology_bp, url_prefix='/api/radiology')
app.register_blueprint(lab_bp, url_prefix='/api/lab')

# --- Final Main execution block (ngrok removed for manual execution) ---
if __name__ == '__main__':
    port = 5001
    
    print("--- Dermatology Application Server ---")
    print(f" * Main application is running on: http://127.0.0.1:{port}")
    print("-" * 60)
    print("## ACTION REQUIRED: To Get Public API Links for Sharing ##")
    print("\nTo create a public URL for your application, please run ngrok manually.")
    print("1. Open a NEW, separate terminal window.")
    print(f"2. In the new terminal, run this command: ngrok http {port}")
    print("\n   The new terminal will display a public 'Forwarding' URL.")
    print("   Use that URL to build your shareable API links, for example:")
    print("   - For dummy data: [Your-Ngrok-URL]/api/patient/DERM001")
    print("   - For real data:  [Your-Ngrok-URL]/api/patient/DERM-00001\n")
    print("-" * 60)

    # Start the Flask server
    app.run(host='0.0.0.0', port=port, debug=True)