"""
fetch_weather.py

Pulls REAL daily weather data (rainfall, humidity) from Open-Meteo,
a free public weather API that needs no signup or API key.

Docs: https://open-meteo.com/en/docs/historical-weather-api

Run this file directly to create weather_data.csv in this folder.

NOTE: this needs real internet access, so run it on your own laptop,
not inside a restricted sandbox.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta

# Same real Jharkhand pincodes as generate_case_data.py, so the two
# datasets can be joined on pincode + date later.
PINCODES = {
    "834001": {"lat": 23.3441, "lon": 85.3096},  # Ranchi
    "831001": {"lat": 22.8046, "lon": 86.2029},  # Jamshedpur
    "826001": {"lat": 23.7957, "lon": 86.4304},  # Dhanbad
    "827001": {"lat": 23.6693, "lon": 86.1511},  # Bokaro
    "814112": {"lat": 24.4823, "lon": 86.6961},  # Deoghar
}

NUM_DAYS = 60
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather_for_pincode(pincode, lat, lon, start_date, end_date):
    """Calls Open-Meteo's historical weather API for one location."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": "precipitation_sum,relative_humidity_2m_mean",
        "timezone": "auto",
    }

    response = requests.get(BASE_URL, params=params, timeout=15)
    response.raise_for_status()  # will raise an error if the call failed
    data = response.json()

    daily = data["daily"]
    rows = []
    for i, date_str in enumerate(daily["time"]):
        rows.append({
            "date": date_str,
            "pincode": pincode,
            "rainfall_mm": daily["precipitation_sum"][i],
            "humidity_percent": daily["relative_humidity_2m_mean"][i],
        })
    return rows


def fetch_all_weather():
    end_date = datetime.today() - timedelta(days=2)  # archive API has ~2 day delay
    start_date = end_date - timedelta(days=NUM_DAYS - 1)

    all_rows = []
    for pincode, info in PINCODES.items():
        print(f"Fetching weather for pincode {pincode} ...")
        rows = fetch_weather_for_pincode(pincode, info["lat"], info["lon"], start_date, end_date)
        all_rows.extend(rows)

    return pd.DataFrame(all_rows)


if __name__ == "__main__":
    df = fetch_all_weather()
    output_path = "weather_data.csv"
    df.to_csv(output_path, index=False)

    print(f"\nSaved {len(df)} rows to {output_path}")
    print("\nPreview:")
    print(df.head(10).to_string(index=False))
