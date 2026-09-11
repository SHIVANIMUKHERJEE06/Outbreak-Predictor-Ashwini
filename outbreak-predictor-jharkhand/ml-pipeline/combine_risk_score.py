"""
combine_risk_score.py

Merges the DBSCAN clustering results and the Prophet forecasting
results into ONE risk score per district. This is the piece that
turns two separate models into a single coherent system.

How the score works (0-100):
  - +50 points if DBSCAN flagged the district as an anomalous cluster
  - up to +50 points based on how far actual cases are running above
    the forecasted trend (capped, so one runaway number can't break it)

Risk levels:
  - 70-100 : High
  - 30-69  : Medium
  - 0-29   : Low

Run this AFTER detect_clusters.py and forecast_outbreak.py, since it
reads cluster_results.csv and forecast_results.csv.
"""

import pandas as pd

FORECAST_POINTS_DIVISOR = 2  # controls how quickly forecast overshoot maxes out the 50 points
FORECAST_POINTS_CAP = 50


def compute_risk_score(row):
    cluster_points = 50 if row["is_anomaly_cluster"] else 0

    forecast_points = max(0, row["percent_above_forecast"]) / FORECAST_POINTS_DIVISOR
    forecast_points = min(forecast_points, FORECAST_POINTS_CAP)

    return round(cluster_points + forecast_points, 1)


def risk_level_from_score(score):
    if score >= 70:
        return "High"
    elif score >= 30:
        return "Medium"
    else:
        return "Low"


def build_explanation(row):
    parts = []
    if row["is_anomaly_cluster"]:
        parts.append("flagged as a spatial case cluster outlier")
    else:
        parts.append("within normal range for spatial clustering")

    if row["percent_above_forecast"] > 20:
        parts.append(f"running {row['percent_above_forecast']:.0f}% above its forecasted trend")
    elif row["percent_above_forecast"] > 0:
        parts.append("tracking slightly above its forecasted trend")
    else:
        parts.append("tracking at or below its forecasted trend")

    return " and ".join(parts).capitalize() + "."


def run():
    clusters = pd.read_csv("cluster_results.csv")
    forecasts = pd.read_csv("forecast_results.csv")

    merged = clusters.merge(
        forecasts[["pincode", "avg_actual_recent", "avg_forecast_upper_bound",
                    "percent_above_forecast", "is_trending_anomaly"]],
        on="pincode", how="left"
    )

    merged["risk_score"] = merged.apply(compute_risk_score, axis=1)
    merged["risk_level"] = merged["risk_score"].apply(risk_level_from_score)
    merged["explanation"] = merged.apply(build_explanation, axis=1)

    return merged


if __name__ == "__main__":
    import os
    missing = [f for f in ("cluster_results.csv", "forecast_results.csv") if not os.path.exists(f)]
    if missing:
        print(f"ERROR: missing required file(s): {', '.join(missing)}")
        print("Run detect_clusters.py and forecast_outbreak.py first, then run this script again.")
        raise SystemExit(1)

    result = run()
    output_path = "risk_scores.csv"
    result.to_csv(output_path, index=False)

    print("Combined risk scores:\n")
    display_cols = ["district", "disease_type", "risk_score", "risk_level", "explanation"]
    print(result[display_cols].sort_values("risk_score", ascending=False).to_string(index=False))

    print(f"\nSaved to {output_path}")
