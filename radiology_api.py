import os
import time
import requests
import logging
from datetime import datetime
from flask import Blueprint, request, session, flash, redirect, url_for
from werkzeug.utils import secure_filename

from app import get_db  # ⬅ MAIN DB CONNECTION

radiology_bp = Blueprint('radiology_api', __name__)
UPLOAD_FOLDER = 'uploads'
RADIOLOGY_API_HOST = "http://127.0.0.1:5000"

def save_stream_to_file(resp, out_path):
    with open(out_path, 'wb') as f:
        for chunk in resp.iter_content(8192):
            if chunk:
                f.write(chunk)

def download_scan(db_conn, host, scan_id, patient_id, scan_type, body_part):
    url = f"{host.rstrip('/')}/api/scans/download/{scan_id}"
    try:
        with requests.get(url, stream=True) as r:
            if not r.ok:
                return None

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = secure_filename(f"scan_{patient_id}_{scan_type}_{body_part}_{ts}.dcm")
            out_path = os.path.join(UPLOAD_FOLDER, filename)
            save_stream_to_file(r, out_path)

            notes = f"{scan_type.upper()} of {body_part.upper()}"
            with db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO PatientImage (patient_id, image_filename, upload_date, notes)
                    VALUES (%s, %s, %s, %s)
                """, (patient_id, filename, datetime.now(), notes))
                db_conn.commit()
            return filename
    except Exception as e:
        logging.error(f"Radiology Download Error: {e}")
        return None
