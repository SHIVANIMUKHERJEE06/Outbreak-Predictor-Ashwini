"""
main.py - Backend server (OPTIONAL / BACKUP)

A small FastAPI server that lets the field-logging app send entries
directly over the network instead of exporting a CSV by hand. This is
an ADDITIVE alternative to the CSV-export workflow in ml-pipeline/
merge_synced_entries.py - that workflow still works exactly as before
and is untouched by this file.

Endpoints:
    GET  /api/health         - basic status check
    POST /api/entries        - add one field-log entry (fast, no recompute)
    POST /api/recompute      - re-run clustering + forecasting + risk scoring
    GET  /api/risk-scores    - current risk scores as JSON
    GET  /api/case-data      - current case data as JSON (for debugging)

Run with:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ml-pipeline/ is a sibling folder to backend/, both inside the main repo folder
PIPELINE_DIR = Path(__file__).resolve().parent.parent / "ml-pipeline"
CASE_DATA_PATH = PIPELINE_DIR / "case_data.csv"
RISK_SCORES_PATH = PIPELINE_DIR / "risk_scores.csv"

app = FastAPI(title="Outbreak Predictor Backend (optional/backup)")

# Allows the field-app (running on a different port) to call this API
# from the browser. Wide open ("*") is fine for a local hackathon demo;
# would be tightened for a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Same mappings used in ml-pipeline/merge_synced_entries.py - kept in
# sync manually since these are two separate small projects.
DISTRICT_INFO = {
    "814112": {"name": "Deoghar", "lat": 24.4823, "lon": 86.6961},
    "834001": {"name": "Ranchi", "lat": 23.3441, "lon": 85.3096},
    "826001": {"name": "Dhanbad", "lat": 23.7957, "lon": 86.4304},
    "827001": {"name": "Bokaro", "lat": 23.6693, "lon": 86.1511},
    "831001": {"name": "Jamshedpur", "lat": 22.8046, "lon": 86.2029},
    "833201": {"name": "West Singhbhum", "lat": 22.5497, "lon": 85.7985},
    "816109": {"name": "Sahibganj", "lat": 25.2494, "lon": 87.6420},
    "822101": {"name": "Palamu", "lat": 24.0469, "lon": 84.0699},
}

DISEASE_LABELS = {
    "Malaria": "Malaria (P. falciparum)",
    "Dengue": "Dengue",
    "Kala-azar": "Kala-azar (Visceral Leishmaniasis)",
    "ADD/Cholera": "Acute Diarrheal Disease / Cholera",
    "Typhoid": "Typhoid",
    "Other": "Unspecified / Other",
}


class FieldEntry(BaseModel):
    district_code: str
    disease: str
    case_count: int
    notes: str = ""
    timestamp: str | None = None  # ISO string; defaults to "now" if not given


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "case_data_exists": CASE_DATA_PATH.exists(),
        "risk_scores_exists": RISK_SCORES_PATH.exists(),
    }


@app.post("/api/entries")
def add_entry(entry: FieldEntry):
    district_code = entry.district_code.zfill(6)
    info = DISTRICT_INFO.get(district_code)
    if info is None:
        raise HTTPException(status_code=400, detail=f"Unknown district_code '{district_code}'")

    if not CASE_DATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="case_data.csv not found. Run generate_case_data.py in ml-pipeline/ first.",
        )

    timestamp = entry.timestamp or datetime.now().isoformat()
    date_str = pd.to_datetime(timestamp).strftime("%Y-%m-%d")

    new_row = {
        "date": date_str,
        "pincode": district_code,
        "district": info["name"],
        "latitude": info["lat"],
        "longitude": info["lon"],
        "disease_type": DISEASE_LABELS.get(entry.disease, entry.disease),
        "symptoms": entry.notes,
        "reported_cases": entry.case_count,
    }

    df = pd.read_csv(CASE_DATA_PATH)
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CASE_DATA_PATH, index=False)

    return {"status": "saved", "entry": new_row}


@app.post("/api/recompute")
def recompute():
    """Re-runs detect_clusters.py, forecast_outbreak.py, combine_risk_score.py."""
    steps = ["detect_clusters.py", "forecast_outbreak.py", "combine_risk_score.py"]

    for step in steps:
        try:
            result = subprocess.run(
                [sys.executable, step],
                cwd=str(PIPELINE_DIR),
                capture_output=True,
                text=True,
                timeout=240,  # Prophet's first-ever run can take a while to compile
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=504,
                detail=(
                    f"{step} took longer than 240 seconds and was stopped. "
                    "If this is the first time forecast_outbreak.py has run, Prophet may "
                    "still be compiling its model backend - try again, it should be much "
                    "faster the second time."
                ),
            )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"{step} failed:\n{result.stdout[-1500:]}\n{result.stderr[-1500:]}",
            )

    if not RISK_SCORES_PATH.exists():
        raise HTTPException(status_code=500, detail="Recompute finished but risk_scores.csv was not created.")

    risk_df = pd.read_csv(RISK_SCORES_PATH)
    return {"status": "recomputed", "risk_scores": risk_df.to_dict(orient="records")}


@app.get("/api/risk-scores")
def get_risk_scores():
    if not RISK_SCORES_PATH.exists():
        raise HTTPException(status_code=404, detail="risk_scores.csv not found. Call /api/recompute first.")
    df = pd.read_csv(RISK_SCORES_PATH)
    return df.to_dict(orient="records")


@app.get("/api/case-data")
def get_case_data():
    if not CASE_DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="case_data.csv not found.")
    df = pd.read_csv(CASE_DATA_PATH)
    return df.to_dict(orient="records")
