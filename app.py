# app.py
from flask import Flask, render_template, request, redirect, url_for, g, flash, session, jsonify, send_from_directory, make_response
import psycopg2
import psycopg2.extras 
import math
from datetime import datetime
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
from collections import Counter, defaultdict
import io
import csv

# --- App Configuration & Setup ---
app = Flask(__name__)
app.secret_key = 'a-very-secure-and-random-secret-key-for-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

logging.basicConfig(level=logging.DEBUG)
DB_CONFIG = {
    'dbname': 'dermatology_db', 'user': 'postgres', 'password': 'Noor@818',
    'host': 'localhost', 'port': '5432', 'sslmode': 'disable'
}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- Database Connection ---
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db

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

# --- Main Landing & Auth Routes ---
@app.route('/')
def index():
    return render_template('landing.html')

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
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    cursor.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(id) FROM Users")
    user_count = cursor.fetchone()[0]
    
    if user_count > 0 and 'user_id' not in session: # Block public registration if users exist
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role_id = 1 # First user is always an Admin
        
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
def register_user():
    if session.get('role_id') != 1:
        flash('You do not have permission to create new users.', 'danger')
        return redirect(url_for('dashboard'))

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
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM Patient")
    stats['total_patients'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Bed WHERE status = 'Occupied'")
    stats['occupied_beds'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Bed")
    stats['total_beds'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM LabReport WHERE status = 'Pending'")
    stats['pending_reports'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM FollowUpVisit")
    stats['follow_up_visits'] = cursor.fetchone()[0]
    # Placeholder for abnormal vitals - requires business logic
    stats['abnormal_vitals'] = 0 
    cursor.execute("SELECT diagnosis FROM Patient WHERE diagnosis IS NOT NULL AND diagnosis != ''")
    diagnoses = [row['diagnosis'].strip() for row in cursor.fetchall()]
    disease_counts = Counter(diagnoses)
    cursor.execute("SELECT gender FROM Patient")
    genders = [row['gender'] for row in cursor.fetchall()]
    gender_counts = Counter(genders)
    cursor.close()
    return render_template('dashboard.html', stats=stats, disease_data=disease_counts, gender_data=gender_counts)
    
# --- NEW PATIENT REGISTRATION ROUTE ---
@app.route('/register_patient', methods=['GET', 'POST'])
@login_required
def register_patient():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        try:
            # Combine BP fields
            blood_pressure = f"{request.form['bp_sys']}/{request.form['bp_dia']}"
            
            # Calculate BMI and BSA (can also be taken directly from the auto-calculated form fields)
            height_cm = request.form.get('height', 0, type=float)
            weight_kg = request.form.get('weight', 0, type=float)
            bmi = request.form.get('bmi', 0, type=float)
            bsa = request.form.get('bsa', 0, type=float)

            # SQL to insert into Patient table
            sql_patient = """
                INSERT INTO Patient (
                    name, age, gender, mobile_number, email, date_of_registration,
                    initial_temperature, initial_blood_pressure, blood_sugar,
                    initial_height, initial_weight, initial_bmi, initial_bsa,
                    complaints, examination_findings, diagnosis, initial_treatment_plan,
                    registered_by_doctor_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """
            cursor.execute(sql_patient, (
                request.form['name'],
                request.form.get('age', type=int),
                request.form['gender'],
                request.form.get('phone_number'),
                request.form.get('email'),
                request.form['record_date'],
                request.form.get('temp', type=float),
                blood_pressure,
                request.form.get('sugar', type=int),
                height_cm,
                weight_kg,
                bmi,
                bsa,
                request.form.get('complaints'), # ADDED
                request.form.get('examination_findings'), # ADDED
                request.form.get('diagnosis'), # ADDED
                request.form.get('initial_treatment_plan'), # ADDED
                session.get('user_id')
            ))
            new_patient_id = cursor.fetchone()[0]
            
            # Generate and update patient code
            patient_code = f"DERM-{new_patient_id:05d}"
            cursor.execute("UPDATE Patient SET patient_code = %s WHERE id = %s", (patient_code, new_patient_id))

            # Handle dynamically added laboratory values
            i = 1
            while f'vital_name_{i}' in request.form:
                vital_name = request.form[f'vital_name_{i}']
                vital_value = request.form[f'vital_value_{i}']
                if vital_name and vital_value:
                    cursor.execute(
                        "INSERT INTO AdditionalVitals (patient_id, vital_name, vital_value, record_date) VALUES (%s, %s, %s, %s)",
                        (new_patient_id, vital_name, vital_value, request.form['record_date'])
                    )
                i += 1
            
            db.commit()
            flash(f'New patient {request.form["name"]} registered successfully with code {patient_code}!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.rollback()
            logging.error(f"Error registering patient: {e}")
            flash('An error occurred while registering the patient. Please check the data and try again.', 'danger')
        finally:
            cursor.close()

    return render_template('register_patient.html')


# --- Patient Routes ---
@app.route('/patients', methods=['GET'])
@login_required
def list_patients():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    query = "SELECT * FROM Patient"
    filters = []
    params = []
    if request.args:
        patient_id = request.args.get('patient_id')
        mobile = request.args.get('mobile')
        age_from = request.args.get('age_from')
        age_to = request.args.get('age_to')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if patient_id:
            filters.append("(LOWER(patient_code) LIKE %s OR CAST(id AS TEXT) LIKE %s)")
            params.extend([f"%{patient_id.lower()}%", f"%{patient_id}%"])
        if mobile:
            filters.append("mobile_number LIKE %s")
            params.append(f"%{mobile}%")
        if age_from:
            filters.append("age >= %s")
            params.append(int(age_from))
        if age_to:
            filters.append("age <= %s")
            params.append(int(age_to))
        if date_from:
            filters.append("date_of_registration >= %s")
            params.append(date_from)
        if date_to:
            filters.append("date_of_registration <= %s")
            params.append(date_to)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    patients = cursor.fetchall()
    cursor.close()
    return render_template('patients.html', patients=patients, search_params=request.args)

@app.route('/patient_visit', methods=['GET', 'POST'])
@login_required
def patient_visit():
    patient_id_from_link = request.args.get('patient_id')
    
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()
        patient_id = request.form.get('patient_id')

        # --- LOGIC FOR AN EXISTING PATIENT (FOLLOW-UP VISIT) ---
        if patient_id:
            # Step 1: Insert clinical details into FollowUpVisit and get the new visit ID
            sql_followup = """
                INSERT INTO FollowUpVisit 
                (patient_id, visit_date, updated_complaints, updated_examination, diagnosis, 
                 updated_treatment_plan, affected_bsa_percentage, doctor_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """
            cursor.execute(sql_followup, (
                patient_id, 
                datetime.now(), 
                request.form.get('complaints'), 
                request.form.get('examination_findings'),
                request.form.get('diagnosis'),
                request.form.get('updated_treatment_plan'), # Corrected column name
                request.form.get('affected_bsa_percentage', type=float),
                session.get('user_id')
            ))
            new_visit_id = cursor.fetchone()[0]

            # Step 2: Insert the vitals into the separate Vitals table, linking to the new visit
            height_cm = request.form.get('height', 0, type=float)
            weight_kg = request.form.get('weight', 0, type=float)
            bmi = round(weight_kg / ((height_cm/100)**2), 2) if height_cm > 0 and weight_kg > 0 else 0
            bsa = round(math.sqrt((height_cm * weight_kg) / 3600), 2) if height_cm > 0 and weight_kg > 0 else 0

            sql_vitals = """
                INSERT INTO Vitals
                (patient_id, visit_id, visit_date, blood_pressure, temperature, pulse_rate, 
                 weight, height, bmi, bsa, recorded_by_staff_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_vitals, (
                patient_id,
                new_visit_id,
                datetime.now(),
                request.form.get('blood_pressure'),
                request.form.get('temperature', type=float),
                request.form.get('pulse_rate', type=int),
                weight_kg,
                height_cm,
                bmi,
                bsa,
                session.get('user_id') # Assumes current user recorded vitals
            ))
            
            db.commit()
            cursor.close()
            flash('Follow-up visit and vitals recorded successfully.', 'success')
            return redirect(url_for('patient_detail', patient_id=patient_id))

        # --- LOGIC FOR A NEW PATIENT REGISTRATION ---
        else:
            # This logic remains largely the same, as it saves to the Patient table's "initial_" columns
            height_cm = request.form.get('height', 0, type=float)
            weight_kg = request.form.get('weight', 0, type=float)
            bmi = round(weight_kg / ((height_cm/100)**2), 2) if height_cm > 0 and weight_kg > 0 else 0
            bsa = round(math.sqrt((height_cm * weight_kg) / 3600), 2) if height_cm > 0 and weight_kg > 0 else 0
            
            sql_patient = """
                INSERT INTO Patient (
                    name, age, gender, mobile_number, date_of_registration, 
                    complaints, examination_findings, diagnosis, initial_treatment_plan, 
                    initial_height, initial_weight, initial_bmi, initial_bsa, 
                    initial_blood_pressure, initial_pulse_rate, initial_temperature, 
                    affected_bsa_percentage, registered_by_doctor_id, past_medical_history
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """
            cursor.execute(sql_patient, (
                request.form['name'], 
                request.form['age'], 
                request.form['gender'], 
                request.form.get('mobile_number'), 
                datetime.now(), 
                request.form.get('complaints'), 
                request.form.get('examination_findings'), 
                request.form.get('diagnosis'), 
                request.form.get('updated_treatment_plan'),
                height_cm, weight_kg, bmi, bsa,
                request.form.get('blood_pressure'),
                request.form.get('pulse_rate', type=int),
                request.form.get('temperature', type=float),
                request.form.get('affected_bsa_percentage', type=float),
                session.get('user_id'),
                request.form.get('past_medical_history') # Assuming this field is added to your form
            ))
            new_patient_id = cursor.fetchone()[0]
            patient_code = f"DERM-{new_patient_id:05d}"
            cursor.execute("UPDATE Patient SET patient_code = %s WHERE id = %s", (patient_code, new_patient_id))
            
            db.commit()
            cursor.close()
            flash(f"New patient registered with code {patient_code}", 'success')
            return redirect(url_for('patient_detail', patient_id=new_patient_id))
    
    return render_template('patient_visit.html', patient_id_from_link=patient_id_from_link)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch patient details
    cursor.execute("SELECT p.*, u.username as doctor_name FROM Patient p LEFT JOIN Users u ON p.registered_by_doctor_id = u.id WHERE p.id = %s", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('list_patients'))

    # Fetch followup visits
    cursor.execute("SELECT fv.*, u.username as doctor_name FROM FollowUpVisit fv LEFT JOIN Users u ON fv.doctor_id = u.id WHERE fv.patient_id = %s ORDER BY fv.visit_date DESC", (patient_id,))
    followup_visits = cursor.fetchall()
    
    # Fetch images
    cursor.execute("SELECT * FROM PatientImage WHERE patient_id = %s ORDER BY upload_date DESC", (patient_id,))
    images = cursor.fetchall()
    
    # Fetch lab reports
    cursor.execute("SELECT lr.*, u.username as doctor_name FROM LabReport lr LEFT JOIN Users u ON lr.requested_by_doctor_id = u.id WHERE lr.patient_id = %s ORDER BY lr.report_date DESC", (patient_id,))
    lab_reports = cursor.fetchall()
    
    # Fetch prescriptions
    cursor.execute("SELECT pr.*, u.username as doctor_name FROM Prescription pr JOIN Users u ON pr.doctor_id = u.id WHERE pr.patient_id = %s ORDER BY pr.prescription_date DESC", (patient_id,))
    prescriptions_raw = cursor.fetchall()
    prescriptions = []
    for pr in prescriptions_raw:
        prescription = dict(pr)
        cursor.execute("SELECT * FROM PrescriptionItem WHERE prescription_id = %s", (pr['id'],))
        prescription['items'] = cursor.fetchall()
        prescriptions.append(prescription)
        
    # Fetch admission and daily notes
    cursor.execute("SELECT ba.*, b.bed_number FROM BedAssignment ba JOIN Bed b ON ba.bed_id = b.id WHERE ba.patient_id = %s AND ba.discharge_date IS NULL", (patient_id,))
    admission = cursor.fetchone()
    daily_notes = []
    if admission:
        # --- ADDED THIS QUERY TO FETCH DAILY NOTES ---
        cursor.execute("""
            SELECT dn.*, u.username as doctor_name 
            FROM DailyProgressNote dn JOIN Users u ON dn.doctor_id = u.id 
            WHERE dn.assignment_id = %s ORDER BY dn.note_date DESC
        """, (admission['id'],))
        daily_notes = cursor.fetchall()
        
    cursor.close()
    
    # Pass the new 'daily_notes' list to the template
    return render_template(
        'patient_detail.html', patient=patient, followup_visits=followup_visits, 
        images=images, lab_reports=lab_reports, prescriptions=prescriptions, 
        admission=admission, daily_notes=daily_notes
    )
@app.route('/patient/<int:patient_id>/edit', methods=['POST'])
@login_required
def edit_patient(patient_id):
    name = request.form['name']
    age = request.form['age']
    gender = request.form['gender']
    mobile_number = request.form['mobile_number']
    db = get_db()
    cursor = db.cursor()
    sql = "UPDATE Patient SET name = %s, age = %s, gender = %s, mobile_number = %s WHERE id = %s"
    cursor.execute(sql, (name, age, gender, mobile_number, patient_id))
    db.commit()
    cursor.close()
    flash('Patient information updated successfully.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/patient/<int:patient_id>/edit_initial', methods=['POST'])
@login_required
def edit_initial_visit(patient_id):
    complaints = request.form['complaints']
    examination = request.form['examination_findings']
    diagnosis = request.form['diagnosis']
    db = get_db()
    cursor = db.cursor()
    sql = "UPDATE Patient SET complaints = %s, examination_findings = %s, diagnosis = %s WHERE id = %s"
    cursor.execute(sql, (complaints, examination, diagnosis, patient_id))
    db.commit()
    cursor.close()
    flash('Initial visit details updated successfully.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/visit/<int:visit_id>/edit', methods=['POST'])
@login_required
def edit_followup_visit(visit_id):
    complaints = request.form['complaints']
    examination = request.form['examination_findings']
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT patient_id FROM FollowUpVisit WHERE id = %s", (visit_id,))
    visit = cursor.fetchone()
    if not visit:
        flash('Visit not found.', 'danger')
        return redirect(url_for('dashboard'))
    sql = "UPDATE FollowUpVisit SET updated_complaints = %s, updated_examination = %s WHERE id = %s"
    cursor.execute(sql, (complaints, examination, visit_id))
    db.commit()
    cursor.close()
    flash('Follow-up visit details updated successfully.', 'success')
    return redirect(url_for('patient_detail', patient_id=visit['patient_id']))

@app.route('/visit/<int:visit_id>/delete', methods=['POST'])
@login_required
def delete_visit(visit_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT patient_id FROM FollowUpVisit WHERE id = %s", (visit_id,))
    visit = cursor.fetchone()
    if visit:
        patient_id = visit['patient_id']
        cursor.execute("DELETE FROM FollowUpVisit WHERE id = %s", (visit_id,))
        db.commit()
        flash('Follow-up visit has been deleted.', 'success')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    else:
        flash('Visit not found.', 'danger')
        return redirect(url_for('dashboard'))
    cursor.close()

# --- Image Routes ---
@app.route('/patient/<int:patient_id>/add_image', methods=['POST'])
@login_required
def add_image(patient_id):
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes) VALUES (%s, %s, %s, %s)",
                       (patient_id, filename, datetime.now(), request.form.get('notes')))
        db.commit()
        cursor.close()
        flash('Image uploaded successfully!', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_image(image_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT patient_id, image_filename FROM PatientImage WHERE id = %s", (image_id,))
    image_data = cursor.fetchone()
    if image_data:
        patient_id = image_data['patient_id']
        filename = image_data['image_filename']
        cursor.execute("DELETE FROM PatientImage WHERE id = %s", (image_id,))
        db.commit()
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('Image deleted successfully.', 'success')
        except FileNotFoundError:
            flash('Image file not found on server, but record was deleted.', 'warning')
    else:
        flash('Image record not found.', 'danger')
        return redirect(url_for('dashboard'))
    cursor.close()
    return redirect(url_for('patient_detail', patient_id=patient_id))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_mobile/<int:patient_id>', methods=['GET', 'POST'])
def mobile_upload(patient_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT name FROM Patient WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        return "Patient not found", 404
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return "Invalid file", 400
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        sql = "INSERT INTO PatientImage (patient_id, image_filename, upload_date) VALUES (%s, %s, %s)"
        cursor.execute(sql, (patient_id, filename, datetime.now()))
        db.commit()
        cursor.close()
        return "<h1>Upload Successful!</h1><p>You can now close this window.</p>"
    cursor.close()
    return render_template('mobile_upload.html', patient_name=patient['name'])

# --- Lab Report Routes ---
@app.route('/lab_reports')
@login_required
def list_lab_reports():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Corrected the query to ORDER BY lr.department
    cursor.execute("""
        SELECT lr.*, p.name as patient_name, p.patient_code, u.username as doctor_name 
        FROM LabReport lr 
        JOIN Patient p ON lr.patient_id = p.id 
        JOIN Users u ON lr.requested_by_doctor_id = u.id 
        ORDER BY lr.department, lr.report_date DESC
    """)
    reports = cursor.fetchall()
    cursor.close()

    # Group reports by department for the template
    grouped_reports = defaultdict(list)
    for report in reports:
        grouped_reports[report['department']].append(report)

    return render_template('lab_reports.html', grouped_reports=grouped_reports)

@app.route('/request_lab_report', methods=['GET', 'POST'])
@login_required
def request_lab_report():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Define the structured list of departments with groups
    departments = {
        'Diagnostic Labs': ['Biochemistry', 'Hematology', 'Pathology', 'Immunology', 'Microbiology'],
        'Imaging': ['Radiology', 'Ultrasound'],
        'Other': ['Other (Specify in Report Type)']
    }

    patient_id = request.args.get('patient_id', type=int)
    
    cursor.execute("SELECT id, patient_code, name FROM Patient ORDER BY name")
    patients = cursor.fetchall()
    if request.method == 'POST':
        department = request.form.get('department')
        cursor.execute("INSERT INTO LabReport (patient_id, report_type, department, report_date, requested_by_doctor_id) VALUES (%s, %s, %s, %s, %s)",
                       (patient_id, request.form['report_type'], department, datetime.now(), session['user_id']))
        db.commit()
        flash('Lab report requested.', 'success')
        return redirect(url_for('list_lab_reports'))
    cursor.close()
    return render_template('request_lab_report.html', patients=patients, departments=departments, selected_patient_id=patient_id)

@app.route('/upload_lab_report/<int:report_id>', methods=['POST'])
@login_required
def upload_lab_report(report_id):
    file = request.files.get('file')
    summary = request.form.get('report_summary')
    filename = None

    if file and file.filename != '' and allowed_file(file.filename):
        filename = f"report_{report_id}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    if filename or summary:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE LabReport SET file_path = %s, report_summary = %s, status = 'Completed' WHERE id = %s", 
                       (filename, summary, report_id))
        db.commit()
        cursor.close()
        flash('Lab report updated.', 'success')
    else:
        flash('No file uploaded or summary provided.', 'warning')
        
    return redirect(url_for('list_lab_reports'))

# --- Bed Management Routes ---
@app.route('/beds')
@login_required
def bed_management():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT b.id, b.bed_number, b.status, p.name as patient_name, p.patient_code, ba.id as assignment_id, ba.admission_date FROM Bed b LEFT JOIN (SELECT * FROM BedAssignment WHERE discharge_date IS NULL) ba ON b.id = ba.bed_id LEFT JOIN Patient p ON ba.patient_id = p.id ORDER BY b.bed_number")
    beds = cursor.fetchall()
    cursor.execute("SELECT id, patient_code, name FROM Patient WHERE is_admitted = FALSE ORDER BY name")
    unassigned_patients = cursor.fetchall()
    cursor.close()
    return render_template('bed_management.html', beds=beds, unassigned_patients=unassigned_patients)

@app.route('/add_bed', methods=['POST'])
@login_required
def add_bed():
    bed_prefix = request.form.get('bed_prefix')
    start_number = request.form.get('start_number')
    end_number = request.form.get('end_number')
    try:
        start = int(start_number)
        end = int(end_number)
    except (ValueError, TypeError):
        flash('Start and end numbers must be valid integers.', 'danger')
        return redirect(url_for('bed_management'))
    db = get_db()
    cursor = db.cursor()
    beds_added, beds_skipped = 0, 0
    for i in range(start, end + 1):
        bed_number = f"{bed_prefix}{i}"
        cursor.execute("SELECT id FROM Bed WHERE bed_number = %s", (bed_number,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO Bed (bed_number) VALUES (%s)", (bed_number,))
            beds_added += 1
        else:
            beds_skipped += 1
    db.commit()
    cursor.close()
    flash(f"{beds_added} beds added. {beds_skipped} skipped as they already exist.", 'success')
    return redirect(url_for('bed_management'))

@app.route('/remove_bed/<int:bed_id>', methods=['POST'])
@login_required
def remove_bed(bed_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT status FROM Bed WHERE id = %s", (bed_id,))
    bed = cursor.fetchone()
    if bed and bed[0] == 'Available':
        cursor.execute("DELETE FROM Bed WHERE id = %s", (bed_id,))
        db.commit()
        flash('Bed removed successfully.', 'success')
    else:
        flash('Cannot remove an occupied bed.', 'danger')
    cursor.close()
    return redirect(url_for('bed_management'))

@app.route('/assign_bed/<int:bed_id>', methods=['POST'])
@login_required
def assign_bed(bed_id):
    patient_id = request.form.get('patient_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO BedAssignment (patient_id, bed_id, admission_date) VALUES (%s, %s, %s)", (patient_id, bed_id, datetime.now()))
    cursor.execute("UPDATE Bed SET status = 'Occupied' WHERE id = %s", (bed_id,))
    cursor.execute("UPDATE Patient SET is_admitted = TRUE WHERE id = %s", (patient_id,))
    db.commit()
    cursor.close()
    flash('Patient assigned to bed.', 'success')
    return redirect(url_for('bed_management'))

# --- Discharge & Daily Notes Routes ---
@app.route('/discharge/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def discharge_patient(assignment_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT ba.id, ba.patient_id, p.name, p.patient_code, p.diagnosis FROM BedAssignment ba JOIN Patient p ON ba.patient_id = p.id WHERE ba.id = %s", (assignment_id,))
    assignment_details = cursor.fetchone()
    if request.method == 'POST':
        cursor.execute("INSERT INTO DischargeSummary (assignment_id, summary_date, final_diagnosis, treatment_summary, follow_up_instructions, doctor_id) VALUES (%s, %s, %s, %s, %s, %s)",
                       (assignment_id, datetime.now(), request.form['final_diagnosis'], request.form['treatment_summary'], request.form['follow_up_instructions'], session['user_id']))
        cursor.execute("UPDATE BedAssignment SET discharge_date = %s WHERE id = %s", (datetime.now(), assignment_id))
        cursor.execute("UPDATE Bed SET status = 'Available' WHERE id = (SELECT bed_id FROM BedAssignment WHERE id = %s)", (assignment_id,))
        cursor.execute("UPDATE Patient SET is_admitted = FALSE WHERE id = %s", (assignment_details['patient_id'],))
        db.commit()
        flash('Patient discharged.', 'success')
        return redirect(url_for('patient_detail', patient_id=assignment_details['patient_id']))
    cursor.close()
    return render_template('discharge_summary.html', patient=assignment_details)

@app.route('/add_daily_note/<int:assignment_id>', methods=['POST'])
@login_required
def add_daily_note(assignment_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT patient_id FROM BedAssignment WHERE id = %s", (assignment_id,))
    patient_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO DailyProgressNote (assignment_id, note_date, notes, doctor_id) VALUES (%s, %s, %s, %s)",
                   (assignment_id, datetime.now(), request.form['notes'], session['user_id']))
    db.commit()
    cursor.close()
    flash('Daily note added.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))

# --- Consultation Routes ---
@app.route('/consultations')
@login_required
def list_consultations():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT cr.*, p.name as patient_name, p.patient_code, u.username as doctor_name FROM ConsultationRequest cr JOIN Patient p ON cr.patient_id = p.id JOIN Users u ON cr.requesting_doctor_id = u.id ORDER BY cr.request_date DESC")
    requests = cursor.fetchall()
    cursor.close()
    return render_template('consultations.html', requests=requests)

@app.route('/request_consultation', methods=['GET', 'POST'])
@login_required
def request_consultation():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Define a structured list of departments for the form
    departments = {
        'Clinical': ['General Medicine', 'Cardiology', 'Neurology', 'Orthopedics'],
        'Surgical': ['General Surgery', 'Neurosurgery'],
        'Other': ['Other (Specify in Reason)']
    }
    
    cursor.execute("SELECT id, patient_code, name FROM Patient ORDER BY name")
    patients = cursor.fetchall()

    if request.method == 'POST':
        # Corrected INSERT statement using the 'department' column
        cursor.execute("""
            INSERT INTO ConsultationRequest 
            (patient_id, requesting_doctor_id, referral_department, reason_for_referral, request_date) 
            VALUES (%s, %s, %s, %s, %s)
        """, (
            request.form['patient_id'], 
            session['user_id'], 
            request.form['department'], # The form name is fine, just the SQL column name was wrong
            request.form['reason_for_referral'], 
            datetime.now()
        ))
        db.commit()
        flash('Consultation request submitted.', 'success')
        return redirect(url_for('list_consultations'))
        
    cursor.close()
    return render_template('request_consultation.html', patients=patients, departments=departments)

# --- Prescription Routes ---
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
        sql_presc = "INSERT INTO Prescription (patient_id, doctor_id, prescription_date, condition_notes) VALUES (%s, %s, %s, %s) RETURNING id"
        cursor.execute(sql_presc, (patient_id, session['user_id'], datetime.now(), condition_notes))
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

# --- API Routes ---
@app.route('/api/search_patients')
@login_required
def search_patients():
    query = request.args.get('q', '')
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT id, patient_code, name, age, gender, mobile_number, diagnosis, initial_height, initial_weight, initial_bmi, initial_bsa, treatment_course_duration, (SELECT COUNT(id) FROM FollowUpVisit WHERE patient_id = p.id) as visit_count FROM Patient p WHERE LOWER(name) LIKE %s OR LOWER(patient_code) LIKE %s OR mobile_number LIKE %s LIMIT 10",
                   (f'%{query.lower()}%', f'%{query.lower()}%', f'%{query.lower()}%'))
    patients = cursor.fetchall()
    cursor.close()
    return jsonify([dict(p) for p in patients])

# --- Data Export ---
@app.route('/export/patients.csv')
@login_required
def download_patient_data():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Reuse the same filtering logic from list_patients
    query = "SELECT patient_code, name, age, gender, mobile_number, date_of_registration, complaints, examination_findings, diagnosis, initial_treatment_plan FROM Patient"
    filters = []
    params = []
    search_args = request.args
    
    patient_id = search_args.get('patient_id')
    mobile = search_args.get('mobile')
    age_from = search_args.get('age_from')
    age_to = search_args.get('age_to')
    date_from = search_args.get('date_from')
    date_to = search_args.get('date_to')

    if patient_id:
        filters.append("(LOWER(patient_code) LIKE %s OR CAST(id AS TEXT) LIKE %s)")
        params.extend([f"%{patient_id.lower()}%", f"%{patient_id}%"])
    if mobile:
        filters.append("mobile_number LIKE %s")
        params.append(f"%{mobile}%")
    if age_from:
        filters.append("age >= %s")
        params.append(int(age_from))
    if age_to:
        filters.append("age <= %s")
        params.append(int(age_to))
    if date_from:
        filters.append("date_of_registration >= %s")
        params.append(date_from)
    if date_to:
        filters.append("date_of_registration <= %s")
        params.append(date_to)

    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    patients = cursor.fetchall()
    cursor.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Patient Code', 'Name', 'Age', 'Gender', 'Mobile', 'Registration Date', 'Complaints', 'Findings', 'Diagnosis', 'Treatment Plan'])
    
    # Write data rows
    for patient in patients:
        writer.writerow(patient)
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=patients.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

# --- NEW: Diagnostic Center Route ---
@app.route('/diagnostic_center')
@login_required
def diagnostic_center():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    search_query = request.args.get('search', '')
    
    # Query for images uploaded as part of a lab report
    diag_sql = """
        SELECT lr.report_type, lr.report_date, p.id as patient_id, p.name as patient_name, pi.image_filename
        FROM LabReport lr
        JOIN PatientImage pi ON lr.image_id = pi.id
        JOIN Patient p ON lr.patient_id = p.id
    """
    # Query for general clinical photos
    clinical_sql = """
        SELECT pi.upload_date, p.id as patient_id, p.name as patient_name, pi.image_filename
        FROM PatientImage pi
        JOIN Patient p ON pi.patient_id = p.id
        WHERE pi.image_type = 'Clinical'
    """
    params = []

    # Apply search filter if a search term is provided
    if search_query:
        search_term = f"%{search_query.lower()}%"
        diag_sql += " WHERE LOWER(p.name) LIKE %s OR LOWER(p.patient_code) LIKE %s"
        clinical_sql += " AND (LOWER(p.name) LIKE %s OR LOWER(p.patient_code) LIKE %s)"
        params.extend([search_term, search_term])

    diag_sql += " ORDER BY lr.report_date DESC"
    clinical_sql += " ORDER BY pi.upload_date DESC"

    cursor.execute(diag_sql, tuple(params))
    diagnostic_reports = cursor.fetchall()
    
    cursor.execute(clinical_sql, tuple(params))
    clinical_photos = cursor.fetchall()
    
    cursor.close()
    return render_template('diagnostic_center.html', 
                           diagnostic_reports=diagnostic_reports, 
                           clinical_photos=clinical_photos,
                           search_query=search_query)

@app.route('/follow_ups')
@login_required
def list_follow_up_visits():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # SQL query to get all follow-up visits and join with patient and doctor info
    sql = """
        SELECT 
            fv.id, 
            fv.visit_date, 
            p.patient_code, 
            p.name as patient_name,
            p.id as patient_id,
            u.username as doctor_name
        FROM 
            FollowUpVisit fv
        JOIN 
            Patient p ON fv.patient_id = p.id
        JOIN 
            Users u ON fv.doctor_id = u.id
        ORDER BY 
            fv.visit_date DESC
    """
    cursor.execute(sql)
    visits = cursor.fetchall()
    cursor.close()
    
    return render_template('follow_ups.html', visits=visits)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)