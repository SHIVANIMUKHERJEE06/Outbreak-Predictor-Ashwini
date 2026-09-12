"""
dashboard.py

The visual front-end for the project. Run this with:
    streamlit run dashboard.py

It shows:
  - A colored table of all districts ranked by risk score
  - A bar chart comparing risk scores
  - A dropdown to pick a district and see its case trend over time
  - The plain-language explanation for why that district got its score
  - A button to generate a mock IHIP-format export for the selected district
"""

from datetime import datetime
import json
from pathlib import Path
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="Outbreak Early Warning - Jharkhand", layout="wide")

st.title("Smart Health Surveillance & Outbreak Predictor")
st.caption("Early warning system for localized disease outbreaks in Jharkhand - demo data")


def load_data():
  # Resolve path relative to dashboard.py location
  risk_path = BASE_DIR / "risk_scores.csv"
  case_path = BASE_DIR / "case_data.csv"

  risk_scores = pd.read_csv(risk_path)
  case_data = pd.read_csv(case_path)
  case_data["date"] = pd.to_datetime(case_data["date"])
  return risk_scores, case_data

try:
    risk_scores, case_data = load_data()
except FileNotFoundError as e:
    st.error(
        "Couldn't find the data files. Make sure you've run, in order: "
        "generate_case_data.py, detect_clusters.py, forecast_outbreak.py, "
        "combine_risk_score.py - all in this same folder as dashboard.py."
    )
    st.stop()


def risk_color(level):
    return {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(level, "⚪")


# ---- Top-level risk table ----
st.subheader("District Risk Overview")

display_df = risk_scores.sort_values("risk_score", ascending=False).copy()
display_df["Risk"] = display_df["risk_level"].apply(lambda lvl: f"{risk_color(lvl)} {lvl}")

st.dataframe(
    display_df[["district", "disease_type", "risk_score", "Risk", "explanation"]]
    .rename(columns={
        "district": "District", "disease_type": "Disease",
        "risk_score": "Risk Score", "explanation": "Why flagged",
    }),
    use_container_width=True,
    hide_index=True,
)

# ---- Bar chart ----
st.subheader("Risk Score Comparison")
chart_data = risk_scores.set_index("district")["risk_score"]
st.bar_chart(chart_data)

# ---- District drill-down ----
st.subheader("District Trend Explorer")
selected_district = st.selectbox("Select a district to inspect", risk_scores["district"].tolist())

district_row = risk_scores[risk_scores["district"] == selected_district].iloc[0]
district_cases = case_data[case_data["district"] == selected_district].sort_values("date")

col1, col2 = st.columns([2, 1])

with col1:
    st.line_chart(district_cases.set_index("date")["reported_cases"])

with col2:
    st.metric("Risk Score", f"{district_row['risk_score']:.0f} / 100")
    st.metric("Risk Level", f"{risk_color(district_row['risk_level'])} {district_row['risk_level']}")
    st.write(f"**Disease:** {district_row['disease_type']}")
    st.write(f"**Why:** {district_row['explanation']}")

# ---- Mock IHIP export ----
st.subheader("IHIP-Format Export (Mock)")
st.caption(
    "This does NOT connect to the real IHIP system - it's a demo export "
    "structured to match IDSP's real S/P/L (Suspected/Presumptive/Lab-confirmed) "
    "reporting format, using our own synthetic data."
)

if st.button(f"Generate IHIP-format export for {selected_district}"):
    recent = district_cases.tail(7)
    mock_export = {
        "report_type": "IDSP_WEEKLY_SPL_MOCK",
        "district": selected_district,
        "disease_under_surveillance": district_row["disease_type"],
        "reporting_period_end": recent["date"].max().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "S_suspected_cases": int(recent["reported_cases"].sum()),
        "P_presumptive_cases": int(recent["reported_cases"].sum() * 0.4),
        "L_lab_confirmed_cases": int(recent["reported_cases"].sum() * 0.15),
        "system_risk_score": float(district_row["risk_score"]),
        "system_risk_level": district_row["risk_level"],
        "note": "DEMO DATA - not connected to real IHIP/IDSP systems",
    }
    st.json(mock_export)

st.divider()
st.caption("Demo data only. Not connected to any real health surveillance system.")
