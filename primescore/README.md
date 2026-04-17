# PrimeScore (API-Football) — Setup & Quick Test

Updated: 2026-03-17

## Prerequisites
- Python 3.10+ with `pip`
- PostgreSQL running locally (defaults: "individual defaults creations")
- API-Football key (free plan OK): set `FOOTBALL_API_KEY`

## 1) Install & run
```bash
cd primescore
pip install -r requirements.txt  # if not yet installed
setx FOOTBALL_API_KEY "YOUR_KEY"   # or $env:FOOTBALL_API_KEY in PowerShell
python app.py
```
App listens on **http://localhost:5000**.

## 2) Key config (config/settings.py)
- `FOOTBALL_API_BASE = https://v3.football.api-sports.io`
- `CURRENT_SEASON = 2024` (override via env if needed)
- DB creds in `DB_CONFIG` (env vars override defaults).

## 3) What was fixed recently
- Restored `/api/resolve/*` endpoints and search so name → ID lookups work.
- Switched back to API-Football client with proper headers; API errors are now detected.
- Removed misleading fake standings; standings/fixtures fall back across seasons instead.
- Home screen now fetches live, upcoming (next 5), and recent (last 5) fixtures.
- Team stats use last fixtures only (no unsupported status+last combo).
- first_time_user logic corrected; first-time banner no longer shows for everyone.

## 4) Quick smoke tests
Run in a separate terminal:
```bash
# Standings
curl -i http://localhost:5000/api/leagues/PL/standings

# Home data
curl -i http://localhost:5000/api/home-screen

# Team stats (Arsenal = 42)
curl -i http://localhost:5000/api/teams/42/statistics
```

Open **DIAGNOSTIC.html** in your browser (double-click the file). It runs:
- API_BASE check
- Standings call
- Home-screen data counts
- Fixtures (next 5)
- Team stats for Arsenal (42)

## 5) Compare workflow (UI)
1. Open http://localhost:5000
2. In Compare → Teams, type team names (no dropdown needed) and press Enter/Compare.
3. Stats should render; if not, check `/api/teams/<id>/statistics` responses.

## 6) Notes
- Free API-Football plan: date ranges are not supported; we use `next`/`last` params instead.
- Auth is not required for standings/home/compare stats; favourites updates still need login.
- If standings are empty, verify the API key and network; the code now surfaces API errors instead of silent fallbacks.
