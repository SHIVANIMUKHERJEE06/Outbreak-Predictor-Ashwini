"""
run_pipeline.py

Runs the entire ML pipeline in the correct order, in one command:
  1. generate_case_data.py   - creates the synthetic case data
  2. detect_clusters.py      - DBSCAN clustering
  3. forecast_outbreak.py    - Prophet forecasting
  4. combine_risk_score.py   - merges both into risk_scores.csv

After this finishes, run:  streamlit run dashboard.py

Usage:
  python run_pipeline.py
"""

import subprocess
import sys

STEPS = [
    ("generate_case_data.py", "Generating synthetic case data"),
    ("detect_clusters.py", "Running DBSCAN clustering"),
    ("forecast_outbreak.py", "Running Prophet forecasting"),
    ("combine_risk_score.py", "Combining into final risk scores"),
]


def main():
    print("=" * 60)
    print("Running the full outbreak-prediction pipeline")
    print("=" * 60)

    for script, description in STEPS:
        print(f"\n>>> {description} ({script}) ...\n")
        result = subprocess.run([sys.executable, script])

        if result.returncode != 0:
            print(f"\nPipeline stopped: {script} exited with an error (see above).")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Pipeline complete. risk_scores.csv is ready.")
    print("Next: run  streamlit run dashboard.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
