# Backend (optional / backup)

A small live-server alternative to the CSV export/merge workflow in
`ml-pipeline/`. **The CSV workflow still works exactly as before and
does not depend on this at all** - this is an additional option, not
a replacement.

## What this adds

Instead of: field app → export CSV → run `merge_synced_entries.py` by hand

You get: field app → POSTs directly to this server → one API call to recompute

## Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Leave this running in its own terminal window during your demo.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Confirms the server is up and can see the pipeline's data files |
| POST | `/api/entries` | Adds one field-log entry to `case_data.csv` (fast, no recompute) |
| POST | `/api/recompute` | Re-runs clustering + forecasting + risk scoring (takes ~5-15 seconds) |
| GET | `/api/risk-scores` | Returns the current risk scores as JSON |
| GET | `/api/case-data` | Returns all current case data as JSON (for debugging) |

Full interactive API docs (auto-generated): once running, open
`http://localhost:8000/docs` in your browser.

## Quick manual test

```bash
curl http://localhost:8000/api/health

curl -X POST http://localhost:8000/api/entries \
  -H "Content-Type: application/json" \
  -d '{"district_code": "834001", "disease": "Dengue", "case_count": 12, "notes": "test entry"}'

curl -X POST http://localhost:8000/api/recompute

curl http://localhost:8000/api/risk-scores
```

## Important notes

- This modifies `ml-pipeline/case_data.csv` directly (appends rows).
  If you want to reset back to the original demo data at any point,
  just re-run `python generate_case_data.py` in `ml-pipeline/` - it
  regenerates the file from scratch with the same fixed random seed.
- CORS is wide open (`allow_origins=["*"]`) since this is a local
  demo. Don't deploy this publicly as-is.
- `/api/recompute` retrains the Prophet forecasting model on all 8
  districts every time it's called, so it takes several seconds - this
  is expected, not a bug.
