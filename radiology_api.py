import os
import time
import requests
import logging
from datetime import datetime
from flask import Blueprint, request, session, flash, redirect, url_for
import psycopg2
import psycopg2.extras
from werkzeug.utils import secure_filename

# --- Blueprint Setup for Radiology ---
radiology_bp = Blueprint('radiology_api', __name__)

# --- Configuration (assumed to be available from the main app) ---
RADIOLOGY_API_HOST = "http://127.0.0.1:5000" # Target Radiology Server
UPLOAD_FOLDER = 'uploads' # Main app's upload folder

DB_CONFIG = {
    'dbname': 'dermatology_db', 'user': 'postgres', 'password': 'Noor@818',
    'host': 'localhost', 'port': '5432', 'sslmode': 'disable'
}

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes a new database connection."""
    return psycopg2.connect(**DB_CONFIG)

# --- Radiology API Helper Functions ---
def save_stream_to_file(resp, out_path, chunk_size=8192):
    """Saves a streaming response content to a file."""
    with open(out_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size):
            if chunk:
                f.write(chunk)

def download_scan(db_conn, host, scan_id, patient_id, scan_type, body_part):
    """Downloads the scan and, crucially, creates a PatientImage record."""
    url = f"{host.rstrip('/')}/api/scans/download/{scan_id}"
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            if not r.ok:
                return None
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_fname = f"scan_{patient_id}_{scan_type}_{body_part}_{ts}.dcm"
            filename = secure_filename(base_fname)
            out_path = os.path.join(UPLOAD_FOLDER, filename)
            save_stream_to_file(r, out_path)

            # *** KEY CHANGE: Create a PatientImage record, not a LabReport ***
            # This makes the scan appear in the image galleries.
            notes = f"{scan_type.upper()} of {body_part.upper()}"
            with db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes)
                    VALUES (%s, %s, %s, %s)
                """, (patient_id, filename, datetime.now(), notes))
                db_conn.commit()
            return filename
    except Exception as e:
        logging.error(f"Error in download_scan: {e}")
        return None

def poll_request_status(db_conn, host, request_id, patient_id, scan_type, body_part, timeout_s=300.0, poll_interval_s=3.0):
    """Polls the status of a request until it's completed or times out."""
    status_url = f"{host.rstrip('/')}/api/request_status/{request_id}"
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            r = requests.get(status_url, timeout=15)
            if r.ok:
                j = r.json()
                status = j.get('status')
                scan_id = j.get('scan_id')
                if status and status.lower() in ('attended', 'completed') and scan_id:
                    return download_scan(db_conn, host, scan_id, patient_id, scan_type, body_part)
        except requests.RequestException:
            pass # Ignore connection errors and continue polling
        time.sleep(poll_interval_s)
    return None

def perform_radiology_request(db_conn, patient_id, uhid, scan_type, body_part):
    """Performs the full API request cycle for a radiology scan."""
    url = f"{RADIOLOGY_API_HOST.rstrip('/')}/api/v1/get_or_request_scan"
    payload = {
        "department_name": "Dermatology",
        "uhid": uhid,
        "type_of_scan": scan_type,
        "body_part": body_part
    }
    headers = {'Accept': 'application/json, application/dicom, */*'}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30, stream=True)
    except requests.RequestException as e:
        return None, f"Request error: {e}"

    # Case 1: Immediate DICOM file download
    if resp.status_code == 200 and 'application/dicom' in resp.headers.get('Content-Type', ''):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_fname = f"scan_{patient_id}_{scan_type}_{body_part}_{ts}.dcm"
        filename = secure_filename(base_fname)
        out_path = os.path.join(UPLOAD_FOLDER, filename)
        save_stream_to_file(resp, out_path)
        
        notes = f"{scan_type.upper()} of {body_part.upper()}"
        with db_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, filename, datetime.now(), notes))
            db_conn.commit()
        return filename, None

    # Case 2: Request was accepted, start polling
    if resp.status_code == 202:
        j = resp.json()
        request_id = j.get('request_id') or j.get('id')
        if not request_id:
            return None, f"Server returned 202 but no request_id was found: {j}"
        
        filename = poll_request_status(db_conn, RADIOLOGY_API_HOST, request_id, patient_id, scan_type, body_part)
        if filename:
            return filename, None
        else:
            return None, "Polling timed out or the final download failed."

    # Case 3: An error occurred
    return None, f"Server returned error {resp.status_code}: {resp.text[:400]}"
