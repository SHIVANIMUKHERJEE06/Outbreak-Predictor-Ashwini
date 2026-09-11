"""
detect_clusters.py

Uses DBSCAN to find which Jharkhand locations have an unusually high
recent case count compared to the others. DBSCAN groups similar points
together into "clusters" - any point that doesn't fit into a dense
cluster gets labelled as an outlier (-1), which is exactly what we want
for spotting an outbreak location.

Run this AFTER generate_case_data.py, since it reads case_data.csv.
Run this file directly to print the cluster results and save
cluster_results.csv.
"""

import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

RECENT_DAYS = 7  # how many of the most recent days to judge each location on


def build_recent_summary(case_data_path="case_data.csv"):
    """
    Turns the daily case log into ONE row per pincode, summarising
    their case activity over the last RECENT_DAYS days. DBSCAN needs
    one row per "thing we're comparing" - here, that's each location.
    """
    df = pd.read_csv(case_data_path)
    df["date"] = pd.to_datetime(df["date"])

    most_recent_date = df["date"].max()
    cutoff_date = most_recent_date - pd.Timedelta(days=RECENT_DAYS - 1)
    recent = df[df["date"] >= cutoff_date]

    summary = recent.groupby(["pincode", "district", "latitude", "longitude", "disease_type"]).agg(
        avg_recent_cases=("reported_cases", "mean"),
        total_recent_cases=("reported_cases", "sum"),
    ).reset_index()

    return summary


def run_dbscan(summary):
    """
    Runs DBSCAN on the case-count summary. We scale the numbers first
    (StandardScaler) so DBSCAN judges "closeness" fairly, since raw
    case counts and coordinates are on very different number scales.
    """
    features = summary[["avg_recent_cases", "total_recent_cases"]]
    scaled_features = StandardScaler().fit_transform(features)

    # eps = how close points need to be to count as the same cluster.
    # min_samples = how many points are needed to form a cluster.
    # These values work for a small demo dataset - see the note below
    # if you want to tune them.
    model = DBSCAN(eps=1.0, min_samples=2)
    summary["cluster_label"] = model.fit_predict(scaled_features)

    # DBSCAN labels outliers as -1. We turn that into a plain flag.
    summary["is_anomaly_cluster"] = summary["cluster_label"] == -1

    return summary


if __name__ == "__main__":
    import os
    if not os.path.exists("case_data.csv"):
        print("ERROR: case_data.csv not found in this folder.")
        print("Run generate_case_data.py first, then run this script again.")
        raise SystemExit(1)

    summary = build_recent_summary()
    result = run_dbscan(summary)

    output_path = "cluster_results.csv"
    result.to_csv(output_path, index=False)

    print(f"Analysed the last {RECENT_DAYS} days of case data per location:\n")
    print(result[["district", "pincode", "disease_type", "avg_recent_cases", "total_recent_cases", "is_anomaly_cluster"]]
          .sort_values("avg_recent_cases", ascending=False)
          .to_string(index=False))

    flagged = result[result["is_anomaly_cluster"]]
    print(f"\nSaved to {output_path}")
    if len(flagged) > 0:
        print(f"\nFLAGGED as anomalous: {', '.join(flagged['district'].tolist())}")
    else:
        print("\nNo location flagged as anomalous - see the tuning note in this file if that's unexpected.")
