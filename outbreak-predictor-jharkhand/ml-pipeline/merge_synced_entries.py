"""
merge_synced_entries.py

Takes a CSV exported by the field-logging app (the "Export & sync"
button in field-app) and merges its entries into case_data.csv, then
automatically re-runs clustering, forecasting, and risk scoring so the
dashboard reflects the new field data.

This is what turns "sync" from a five-step manual chore into ONE
command - it's still not a live server connection, but it closes the
loop end-to-end for a demo: new field entries -> updated risk scores,
with a single step in between instead of five.

Usage:
    python merge_synced_entries.py path/to/asha_field_log_sync_XXXX.csv
"""

import sys
import subprocess
import pandas as pd

# Must match the district list in generate_case_data.py and the
# field-app's main.js. If you add a district in one place, add it here too.
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


def convert_field_export(export_path):
    """Reads the field app's export CSV and reshapes it to match case_data.csv's columns."""
    field_df = pd.read_csv(export_path)

    rows = []
    for _, entry in field_df.iterrows():
        district_code = str(entry["district_code"]).zfill(6)
        info = DISTRICT_INFO.get(district_code)
        if info is None:
            print(f"WARNING: unknown district code '{district_code}' - skipping this entry.")
            continue

        rows.append({
            "date": pd.to_datetime(entry["timestamp"]).strftime("%Y-%m-%d"),
            "pincode": district_code,
            "district": info["name"],
            "latitude": info["lat"],
            "longitude": info["lon"],
            "disease_type": DISEASE_LABELS.get(entry["disease"], entry["disease"]),
            "symptoms": entry.get("notes", ""),
            "reported_cases": int(entry["case_count"]),
        })

    return pd.DataFrame(rows)


def merge_into_case_data(new_rows, case_data_path="case_data.csv"):
    existing = pd.read_csv(case_data_path)
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined.to_csv(case_data_path, index=False)
    return len(new_rows)


def rerun_downstream_pipeline():
    """Re-runs clustering, forecasting, and risk scoring on the updated data."""
    steps = ["detect_clusters.py", "forecast_outbreak.py", "combine_risk_score.py"]
    for step in steps:
        print(f"\n>>> Re-running {step} with updated data ...")
        result = subprocess.run([sys.executable, step])
        if result.returncode != 0:
            print(f"Stopped: {step} failed. Fix the error above before continuing.")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_synced_entries.py path/to/exported_file.csv")
        sys.exit(1)

    export_path = sys.argv[1]

    new_rows = convert_field_export(export_path)
    if len(new_rows) == 0:
        print("No valid entries found in the export file - nothing to merge.")
        sys.exit(1)

    count = merge_into_case_data(new_rows)
    print(f"Merged {count} new field entries into case_data.csv")

    rerun_downstream_pipeline()

    print("\nDone. Refresh your Streamlit dashboard (or re-run 'streamlit run dashboard.py')")
    print("to see the updated risk scores reflecting the new field data.")
