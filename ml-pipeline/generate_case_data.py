"""
generate_case_data.py  (v2 - district & disease-specific)

Generates a fake ASHA-worker-style field log across 8 REAL Jharkhand
districts, each mapped to the disease it's actually documented to be
vulnerable to (per IDSP/NVBDCP seasonal + district vulnerability data),
with realistic symptom sets and season-aware baseline case rates.

Only Deoghar is seeded with a rising OUTBREAK (Kala-azar), matching its
real post-monsoon endemic pattern. Every other district stays at a
realistic seasonal baseline - including one (Palamu) that is
deliberately OFF-SEASON right now, so the demo can show the model
correctly staying quiet where it should.

Run this file directly to create case_data.csv in this folder.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ---- Settings you can tweak ----
NUM_DAYS = 60
OUTBREAK_PINCODE = "833201"  # West Singhbhum - Malaria outbreak
OUTBREAK_START_DAY = 46      # outbreak starts 14 days before the end

# Real Jharkhand districts, mapped to the disease each is documented to
# be vulnerable to, based on IDSP / NVBDCP seasonal district data.
# baseline_cases and in_season reflect whether that disease's real
# peak season is active right now (Sep = post-monsoon).
PINCODES = {
    "814112": {
        "name": "Deoghar", "lat": 24.4823, "lon": 86.6961,
        "disease": "Kala-azar (Visceral Leishmaniasis)",
        "symptoms": "prolonged fever, weight loss, spleen enlargement, anemia",
        "baseline_cases": 3, "in_season": True,
    },
    "834001": {
        "name": "Ranchi", "lat": 23.3441, "lon": 85.3096,
        "disease": "Dengue",
        "symptoms": "high fever, severe headache, joint pain, skin rash",
        "baseline_cases": 4, "in_season": True,
    },
    "826001": {
        "name": "Dhanbad", "lat": 23.7957, "lon": 86.4304,
        "disease": "Dengue",
        "symptoms": "high fever, severe headache, joint pain, skin rash",
        "baseline_cases": 4, "in_season": True,
    },
    "827001": {
        "name": "Bokaro", "lat": 23.6693, "lon": 86.1511,
        "disease": "Dengue",
        "symptoms": "high fever, severe headache, joint pain, skin rash",
        "baseline_cases": 3, "in_season": True,
    },
    "831001": {
        "name": "Jamshedpur", "lat": 22.8046, "lon": 86.2029,
        "disease": "Dengue",
        "symptoms": "high fever, severe headache, joint pain, skin rash",
        "baseline_cases": 4, "in_season": True,
    },
    "833201": {
        "name": "West Singhbhum", "lat": 22.5497, "lon": 85.7985,
        "disease": "Malaria (P. falciparum)",
        "symptoms": "cyclical fever with chills, sweating, headache, nausea",
        "baseline_cases": 4, "in_season": True,
    },
    "816109": {
        "name": "Sahibganj", "lat": 25.2494, "lon": 87.6420,
        "disease": "Acute Diarrheal Disease / Cholera",
        "symptoms": "watery diarrhea, vomiting, dehydration, abdominal cramps",
        "baseline_cases": 3, "in_season": True,
    },
    "822101": {
        "name": "Palamu", "lat": 24.0469, "lon": 84.0699,
        "disease": "Typhoid",
        "symptoms": "sustained fever, weakness, abdominal pain, loss of appetite",
        "baseline_cases": 1, "in_season": False,  # real peak season is Mar-Jun, not now
    },
}


def generate_case_data():
    rng = np.random.default_rng(seed=42)  # fixed seed = reproducible demo data
    start_date = datetime.today() - timedelta(days=NUM_DAYS)

    rows = []
    for day_num in range(NUM_DAYS):
        current_date = start_date + timedelta(days=day_num)

        for pincode, info in PINCODES.items():
            baseline = info["baseline_cases"]

            # Normal random daily fluctuation around the baseline
            case_count = rng.poisson(lam=baseline)

            # If this is the outbreak pincode and we've hit the outbreak
            # window, add a growing extra number of cases each day
            if pincode == OUTBREAK_PINCODE and day_num >= OUTBREAK_START_DAY:
                days_into_outbreak = day_num - OUTBREAK_START_DAY
                extra_cases = int(2 + days_into_outbreak * 1.6)
                case_count += rng.poisson(lam=extra_cases)

            rows.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "pincode": pincode,
                "district": info["name"],
                "latitude": info["lat"],
                "longitude": info["lon"],
                "disease_type": info["disease"],
                "symptoms": info["symptoms"],
                "reported_cases": case_count,
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_case_data()
    output_path = "case_data.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {len(df)} rows across {df['pincode'].nunique()} districts\n")

    print("Districts and their disease profile:")
    profile = df[["district", "disease_type"]].drop_duplicates()
    print(profile.to_string(index=False))

    print(f"\nSaved to {output_path}")
    outbreak_name = PINCODES[OUTBREAK_PINCODE]["name"]
    outbreak_disease = PINCODES[OUTBREAK_PINCODE]["disease"]
    print(f"\nPreview of the outbreak district's ({outbreak_name}) last 10 days:")
    outbreak_rows = df[df["pincode"] == OUTBREAK_PINCODE].tail(10)
    print(outbreak_rows[["date", "disease_type", "reported_cases"]].to_string(index=False))
