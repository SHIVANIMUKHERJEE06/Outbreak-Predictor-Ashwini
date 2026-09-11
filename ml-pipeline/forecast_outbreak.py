"""
forecast_outbreak.py

Uses Prophet (a forecasting library made by Meta) to learn each
district's normal case trend, then checks whether RECENT actual case
counts are significantly higher than what the trend predicted. This is
what gives us the "10-14 days before it peaks" claim: an outbreak
shows up here as actual cases pulling away from the forecast line,
often before it would look dramatic on a simple day-to-day chart.

Run this AFTER generate_case_data.py, since it reads case_data.csv.
Run this file directly to print forecast results and save
forecast_results.csv.
"""

import pandas as pd
from prophet import Prophet
import logging

# Prophet is chatty by default - this quiets its internal logging so
# your terminal output stays readable.
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

TRAIN_DAYS = 45     # how many early days to TRAIN the model on
CHECK_DAYS = 7       # how many of the most recent days to check against the forecast
ANOMALY_MULTIPLIER = 1.6  # actual cases must exceed the forecast's upper bound by this much to count as an anomaly


def forecast_one_district(district_df):
    """
    Trains Prophet on the EARLY part of a district's data, forecasts
    forward, then compares that forecast to what ACTUALLY happened in
    the most recent days. Training only on early data (not the whole
    history) is what lets us catch a trend forming, instead of Prophet
    just learning the outbreak after it already happened.
    """
    district_df = district_df.sort_values("date")

    train_df = district_df.iloc[:TRAIN_DAYS][["date", "reported_cases"]]
    train_df = train_df.rename(columns={"date": "ds", "reported_cases": "y"})

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.90,  # gives us an upper/lower confidence bound
    )
    model.fit(train_df)

    # Forecast forward far enough to cover the remaining actual days
    periods_needed = len(district_df) - TRAIN_DAYS
    future = model.make_future_dataframe(periods=periods_needed)
    forecast = model.predict(future)

    # Line up the forecast with what actually happened
    merged = district_df[["date", "reported_cases"]].merge(
        forecast[["ds", "yhat", "yhat_upper"]],
        left_on="date", right_on="ds", how="left"
    )

    return merged


def check_recent_anomaly(merged_df):
    """
    Looks at the last CHECK_DAYS days and flags a district as trending
    toward an outbreak if actual cases meaningfully exceed the
    forecast's upper confidence bound.
    """
    recent = merged_df.tail(CHECK_DAYS)
    avg_actual = recent["reported_cases"].mean()
    avg_forecast_upper = recent["yhat_upper"].mean()

    is_trending_anomaly = avg_actual > (avg_forecast_upper * ANOMALY_MULTIPLIER)
    percent_above_forecast = ((avg_actual / avg_forecast_upper) - 1) * 100 if avg_forecast_upper > 0 else 0

    return {
        "avg_actual_recent": round(avg_actual, 1),
        "avg_forecast_upper_bound": round(avg_forecast_upper, 1),
        "percent_above_forecast": round(percent_above_forecast, 1),
        "is_trending_anomaly": is_trending_anomaly,
    }


def run_forecast_pipeline(case_data_path="case_data.csv"):
    df = pd.read_csv(case_data_path)
    df["date"] = pd.to_datetime(df["date"])

    results = []
    for pincode, district_df in df.groupby("pincode"):
        district_name = district_df["district"].iloc[0]
        disease = district_df["disease_type"].iloc[0]

        print(f"Forecasting {district_name} ({disease}) ...")
        merged = forecast_one_district(district_df)
        anomaly_check = check_recent_anomaly(merged)

        results.append({
            "pincode": pincode,
            "district": district_name,
            "disease_type": disease,
            **anomaly_check,
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    import os
    if not os.path.exists("case_data.csv"):
        print("ERROR: case_data.csv not found in this folder.")
        print("Run generate_case_data.py first, then run this script again.")
        raise SystemExit(1)

    results = run_forecast_pipeline()
    output_path = "forecast_results.csv"
    results.to_csv(output_path, index=False)

    print("\nForecast vs actual, last 7 days per district:\n")
    print(results[["district", "disease_type", "avg_actual_recent", "avg_forecast_upper_bound",
                    "percent_above_forecast", "is_trending_anomaly"]]
          .sort_values("percent_above_forecast", ascending=False)
          .to_string(index=False))

    flagged = results[results["is_trending_anomaly"]]
    print(f"\nSaved to {output_path}")
    if len(flagged) > 0:
        print(f"\nTRENDING TOWARD OUTBREAK: {', '.join(flagged['district'].tolist())}")
    else:
        print("\nNo district trending above forecast.")
