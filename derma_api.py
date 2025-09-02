#!/usr/bin/env python3
"""
derma_api.py - A simple, standalone API server for easy browser access.
NO API KEY IS REQUIRED.
"""
from flask import Flask, jsonify

# --- Configuration ---
app = Flask(__name__)

# --- Sample Dermatology Patient Database ---
DERMATOLOGY_RECORDS = {
    "DERM001": {
        "department": "Dermatology Department",
        "medical_records": {
            "diagnosis": "Chronic Plaque Psoriasis",
            "record_date": "2025-08-29",
            "record_id": "REC-73451",
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
                    "name": "Clobetasol Propionate Cream",
                    "dosage": "0.05%",
                    "frequency": "Twice daily",
                    "duration": "4 weeks"
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
            "test_results": {
                "bsa": 1.60,
                "affected_bsa_percent": 4.0,
                "skin_examination": "Multiple inflammatory nodules and cysts on the face, neck, and upper back. Significant scarring present."
            },
            "lab_reports": [
                {
                    "report_name": "Hormone Panel",
                    "result": "Within normal limits."
                }
            ],
            "prescription": [
                {
                    "name": "Isotretinoin",
                    "dosage": "40mg",
                    "frequency": "Once daily with food",
                    "duration": "6 months"
                }
            ],
            "treatment_summary": "Systemic therapy with oral isotretinoin initiated due to severity and scarring. Patient counseled on side effects."
        }
    }
}

# --- API Route ---

@app.route("/api/patient/<string:uhid>", methods=["GET"])
def get_patient_details(uhid):
    """
    Retrieves a single patient's dermatology record.
    NO API KEY IS NEEDED.
    """
    patient_data = DERMATOLOGY_RECORDS.get(uhid)
    if patient_data:
        return jsonify(patient_data)
    else:
        return jsonify({"error": f"Patient with UHID '{uhid}' not found."}), 404

# --- Main execution block ---
if __name__ == "__main__":
    base_url = "http://127.0.0.1:5000"
    example_uhid = "DERM001"
    
    print("--- Simple Dermatology API Server ---")
    print(f"Starting server on {base_url}")
    print("-" * 40)
    print(f"Example link for your own browser: {base_url}/api/patient/{example_uhid}")
    print("-" * 40)
    print("Use Ctrl+C to stop the server.")
    
    app.run(host="127.0.0.1", port=5000, debug=True)