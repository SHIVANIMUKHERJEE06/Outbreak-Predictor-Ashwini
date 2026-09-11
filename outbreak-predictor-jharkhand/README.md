# Smart Health Surveillance & Outbreak Predictor (Jharkhand)

An early-warning system that flags a localized disease outbreak 10-14
days before it peaks, using spatial clustering (DBSCAN) and time-series
forecasting (Prophet) on ASHA-worker-style field logs, combined with
real weather data.

This is a **hackathon demo built on synthetic data**. It is not
connected to any real health surveillance system - see "What's real
vs. simulated" below for an honest breakdown.

## Project structure

```
outbreak-predictor-jharkhand/
├── ml-pipeline/        # Python: data, ML models, risk scoring, dashboard
├── field-app/          # Offline-capable PWA for field data logging
└── backend/            # OPTIONAL backup: live API server (see backend/README.md)
```

## Quick start - ML pipeline (the main demo)

Requires Python 3.10+.

```bash
cd ml-pipeline
pip install -r requirements.txt
python run_pipeline.py        # runs the full pipeline, one command
streamlit run dashboard.py    # opens the dashboard in your browser
```

`run_pipeline.py` runs, in order: synthetic data generation → DBSCAN
clustering → Prophet forecasting → combined risk scoring. Each step
also runs standalone if you want to inspect it individually (see
"Running steps individually" below).

To pull real live weather data (optional, not required for the
dashboard to work):
```bash
python fetch_weather.py
```

## Quick start - field-logging app (offline PWA)

Requires Node.js 18+.

```bash
cd field-app
npm install
npm run build
npm run preview
```
Open the printed URL. To verify true offline behavior: load the page
once while online, then disconnect your network and refresh - the app
should still load and let you save entries.

## Running pipeline steps individually

If you'd rather run each stage yourself instead of `run_pipeline.py`:

```bash
cd ml-pipeline
python generate_case_data.py     # creates case_data.csv
python detect_clusters.py        # creates cluster_results.csv
python forecast_outbreak.py      # creates forecast_results.csv
python combine_risk_score.py     # creates risk_scores.csv
streamlit run dashboard.py
```
Each script checks for its required input file(s) and prints a clear
message telling you which earlier step to run if something's missing.

## What's real vs. simulated

| Component | Status |
|---|---|
| District locations, coordinates | Real (8 Jharkhand districts) |
| Disease-district mapping (e.g. Malaria in West Singhbhum) | Real, based on IDSP/NVBDCP documented vulnerability data |
| Daily case counts | **Synthetic** - generated with one seeded outbreak (West Singhbhum, Malaria) |
| Weather data (`fetch_weather.py`) | **Real** - live pull from the free Open-Meteo API |
| DBSCAN clustering, Prophet forecasting, risk scoring | Real, working ML models running on the synthetic case data |
| Field-logging PWA | Real, working offline-capable app; not yet wired to a live backend |
| IHIP export (in the dashboard) | **Mock** - structured to match the real IDSP S/P/L report format, populated with our synthetic data. Not connected to the real IHIP system, which has no public API. |

## Tech stack

- **ML pipeline:** Python, pandas, scikit-learn (DBSCAN), Prophet, Streamlit
- **Field app:** Vite, vanilla JS, `vite-plugin-pwa` (service worker + offline caching)
- **Weather data:** Open-Meteo (free, no API key required)

## Optional backup: live backend

The `backend/` folder is a small FastAPI server that lets the field
app sync directly over the network instead of the CSV-export workflow
above. It's entirely optional and doesn't affect the rest of the
project - see `backend/README.md` for setup and usage.

## Known limitations

- Case data is synthetic; only the outbreak *pattern* (real disease,
  real district, real season) is grounded in real epidemiological data.
- The field app's "sync" is a CSV export/download in this demo, not a
  live connection to the ML pipeline or any backend server.
- Prophet's first run compiles a small model backend and can take
  10-30 seconds longer than subsequent runs - this is normal.
