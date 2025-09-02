#!/usr/bin/env python3
"""
test.py - Web UI with in-browser DICOM viewer
"""

import os
import requests
import time
from datetime import datetime
from flask import Flask, request, render_template_string, send_from_directory

DEFAULT_HOST = "http://127.0.0.1:5000"

app = Flask(__name__)
# Create a 'downloads' directory to store the DICOM files
os.makedirs("downloads", exist_ok=True)

# --- Helpers ---

def save_stream_to_file(resp, out_path, chunk_size=8192):
    """Saves a streaming response content to a file."""
    with open(out_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size):
            if chunk:
                f.write(chunk)

def download_scan(host, scan_id, out_dir, uhid=None):
    """Downloads a scan by its ID and saves it."""
    url = f"{host.rstrip('/')}/api/scans/download/{scan_id}"
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            if r.ok:
                disp = r.headers.get('Content-Disposition', '')
                if 'filename=' in disp:
                    fname = disp.split('filename=')[-1].strip(' "')
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{uhid or 'scan'}_{scan_id}_{ts}.dcm"
                
                out_path = os.path.join(out_dir, fname)
                save_stream_to_file(r, out_path)
                return fname
            else:
                return None
    except Exception:
        return None

def poll_request_status(host, request_id, timeout_s, poll_interval_s, out_dir, uhid):
    """Polls the status of a request until it's attended or times out."""
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
                    return download_scan(host, scan_id, out_dir, uhid)
        except requests.RequestException:
            # Ignore connection errors and continue polling
            pass
        time.sleep(poll_interval_s)
    return None

def perform_request(host, department, uhid, scan_type, body_part, poll_interval_s=3.0, timeout_s=300.0):
    """Performs the API request to get or request a scan."""
    url = f"{host.rstrip('/')}/api/v1/get_or_request_scan"
    payload = {
        "department_name": department,
        "uhid": uhid,
        "type_of_scan": scan_type,
        "body_part": body_part
    }
    headers = {'Accept': 'application/json, application/dicom, */*'}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30, stream=True)
    except requests.RequestException as e:
        return None, f"Request error: {e}"

    if resp.status_code == 200:
        if 'application/json' in resp.headers.get('Content-Type', '').lower():
            return None, f"Received unexpected JSON: {resp.json()}"
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{uhid or 'scan'}_{ts}.dcm"
            out_path = os.path.join("downloads", fname)
            save_stream_to_file(resp, out_path)
            return fname, None

    if resp.status_code == 202:
        j = resp.json()
        request_id = j.get('request_id') or j.get('id')
        if not request_id:
            return None, f"Server returned 202 but no request_id was found: {j}"
        
        fname = poll_request_status(host, request_id, timeout_s, poll_interval_s, "downloads", uhid)
        if fname:
            return fname, None
        else:
            return None, "Polling timed out or the final download failed."

    return None, f"Server returned error {resp.status_code}: {resp.text[:400]}"

# --- Flask UI ---

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>DICOM Viewer</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen">
    <div class="bg-white shadow-lg rounded-xl p-8 max-w-lg w-full">
        <h1 class="text-xl font-bold mb-4 text-center">Scan Request Tester</h1>
<form method="POST" class="space-y-4">
    <!-- Department (readonly, but converted to uppercase anyway) -->
    <input type="text" name="department" value="SURGERY" 
           class="w-full border p-2 rounded bg-gray-100 text-gray-500" readonly
           oninput="this.value = this.value.toUpperCase()">

    <!-- UHID -->
    <input type="text" name="uhid" class="w-full border p-2 rounded" placeholder="UHID" required>

    <!-- Dropdown for scan type -->
    <select name="scan_type" class="w-full border p-2 rounded" required>
        <option value="" disabled selected>Select Scan Type</option>
        <option value="CT">CT</option>
        <option value="MR">MR</option>
        <option value="XRAY">XRAY</option>
        <option value="US">ULTRASOUND</option>
        <option value="PET">PET</option>
        <!-- Add more types as needed -->
    </select>

    <!-- Body part input -->
    <input type="text" name="body_part" id="body_part" 
           class="w-full border p-2 rounded" placeholder="Body part (e.g., BRAIN, CHEST)" required
           oninput="this.value = this.value.toUpperCase()">

    <!-- Warning for correct spelling -->
    <p class="text-sm text-red-500">⚠ Please enter the body part spelling correctly (e.g., BRAIN, CHEST)</p>

    <!-- Submit button -->
    <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Submit</button>
</form>


        {% if error %}
        <div class="mt-6 p-4 bg-red-100 border rounded text-red-700">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}

        {% if dicom_file %}
        <div class="mt-6">
            <h2 class="font-semibold mb-2">Viewer:</h2>
            <div id="dicomImage" class="border w-full h-96 bg-black"></div>
        </div>

        <!-- Using specific, compatible versions of the libraries -->
        <script src="https://unpkg.com/cornerstone-core@2.3.0/dist/cornerstone.js"></script>
        <script src="https://unpkg.com/dicom-parser@1.8.7/dist/dicomParser.js"></script>
        <script src="https://unpkg.com/cornerstone-wado-image-loader@3.1.2/dist/cornerstoneWADOImageLoader.js"></script>
        
        <script>
            // **FIX 1: Initialize the WADO Image Loader Web Worker**
            // This is a required step to configure the library to parse DICOM files.
            try {
                cornerstoneWADOImageLoader.webWorkerManager.initialize({
                    maxWebWorkers: navigator.hardwareConcurrency || 1,
                    startWebWorkersOnDemand: true,
                    taskConfiguration: {
                        'decodeTask': {
                            initializeCodecsOnStartup: false,
                            usePDFJS: false,
                            strict: false,
                        }
                    }
                });
            } catch (error) {
                console.error("Web Worker initialization failed. This may happen if the page is reloaded.", error);
            }

            const element = document.getElementById('dicomImage');
            cornerstone.enable(element);

            // Link cornerstone with the WADO loader
            cornerstoneWADOImageLoader.external.cornerstone = cornerstone;

            // **FIX 2: Construct the image URL dynamically**
            // This is more robust than a hardcoded URL.
            const dicomFileName = "{{ dicom_file }}";
            const imageId = `wadouri:${window.location.origin}/dicom/${dicomFileName}`;

            console.log("Attempting to load DICOM image:", imageId);

            // Load and display the image
            cornerstone.loadAndCacheImage(imageId).then(function(image) {
                console.log('Image loaded successfully:', image);
                cornerstone.displayImage(element, image);
            }).catch(function(err) {
                console.error("Error loading DICOM image:", err);
                element.innerHTML = `<div class="p-4 text-red-300">Failed to load DICOM image. Check browser console for details.</div>`;
            });

        </script>
        {% endif %}
    </div>
</body>
</html>
"""
@app.route("/hello", methods=["GET", "POST"])
def index():
    """Handles the form submission and renders the page."""
    dicom_file, error = None, None
    if request.method == "POST":
        host = DEFAULT_HOST
        department = request.form.get("department", "Cardiology")
        uhid = request.form.get("uhid")
        scan_type = request.form.get("scan_type")
        body_part = request.form.get("body_part")

        if not all([uhid, scan_type, body_part]):
            error = "UHID, Scan Type, and Body Part are required fields."
        else:
            dicom_file, error = perform_request(host, department, uhid, scan_type, body_part)

    return render_template_string(HTML_FORM, dicom_file=dicom_file, error=error)

@app.route("/dicom/<path:filename>")
def serve_dicom(filename):
    """Serves the downloaded DICOM file from the 'downloads' directory."""
    # Serve as a raw binary stream so the WADO loader can parse it
    return send_from_directory("downloads", filename, mimetype="application/octet-stream")

if __name__ == "__main__":
    # Runs the Flask app on port 8000
    app.run(port=8000, debug=True)
