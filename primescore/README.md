# PrimeScore

PrimeScore is a Flask + PostgreSQL football statistics app that uses API-Football for live matches, standings, fixtures, results, search, favourites, profile data, and team comparison.

## Tech stack
- Python
- Flask
- PostgreSQL
- HTML, CSS, JavaScript
- API-Football (`https://v3.football.api-sports.io`)

## Project structure
```text
primescore/
|-- app.py
|-- config.py
|-- requirements.txt
|-- db/
|   |-- schema.sql
|-- routes/
|-- services/
|-- static/
|   |-- js/
|   |-- style.css
|-- templates/
|-- README.md
```

## Requirements
- Python 3.10 or newer
- PostgreSQL running locally
- An API-Football API key

## Environment variables
The app reads configuration from environment variables.

Required:
- `FOOTBALL_API_KEY`

Usually needed:
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_PORT`

Optional:
- `SECRET_KEY`
- `CURRENT_SEASON`

Default database values in `config.py` are:
- host: `localhost`
- database: `primescore`
- user: `postgres`
- port: `5432`

## First-time setup on Windows PowerShell

### 1) Open the project folder
```powershell
cd C:\path\to\primescore
```

### 2) Create a virtual environment
```powershell
py -m venv .venv
```

### 3) Activate the virtual environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 4) Install Python packages
```powershell
pip install -r requirements.txt
```

### 5) Create the PostgreSQL database
```powershell
psql -U postgres -c "CREATE DATABASE primescore;"
```

If the database already exists, PostgreSQL will tell you. That is fine.

### 6) Load the schema
```powershell
psql -U postgres -d primescore -f db\schema.sql
```

### 7) Set the environment variables for the current PowerShell window
```powershell
$env:FOOTBALL_API_KEY="YOUR_API_FOOTBALL_KEY"
$env:DB_HOST="localhost"
$env:DB_NAME="primescore"
$env:DB_USER="postgres"
$env:DB_PASSWORD="YOUR_POSTGRES_PASSWORD"
$env:DB_PORT="5432"
```

### 8) Run the app
```powershell
python app.py
```

### 9) Open the app in the browser
```text
http://localhost:5000
```

## Quick start for another developer
If another developer clones the repository, they should do this:

```powershell
git clone <your-repo-url>
cd primescore
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
psql -U postgres -c "CREATE DATABASE primescore;"
psql -U postgres -d primescore -f db\schema.sql
$env:FOOTBALL_API_KEY="YOUR_API_FOOTBALL_KEY"
$env:DB_HOST="localhost"
$env:DB_NAME="primescore"
$env:DB_USER="postgres"
$env:DB_PASSWORD="YOUR_POSTGRES_PASSWORD"
$env:DB_PORT="5432"
python app.py
```

Then they open:
- `http://localhost:5000`

## How to upload this project to GitHub

### 1) Make sure these are included
Upload the source files and folders:
- `app.py`
- `config.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `db/`
- `routes/`
- `services/`
- `static/`
- `templates/`

### 2) Make sure these are not uploaded
These are local-only files and should stay out of Git:
- `.venv/`
- `__pycache__/`
- local logs
- local editor folders such as `.vscode/`

### 3) Git commands
```powershell
git init
git add .
git commit -m "Initial PrimeScore upload"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Quick smoke tests
After the app starts, check:

1. The home page opens.
2. Register works.
3. Login works.
4. Home standings load.
5. Profile page opens.
6. Username and email can be updated from the profile page.
7. Team search works.
8. Team comparison works.

## Automated tests

A starter `pytest` suite is included in:
- `tests/`

The current tests focus on:
- core backend logic
- safe route validation
- authenticated route protection
- statistics formatting and calculation
- authentication flows with fake database responses
- favourites save/load flows with mocked resolution
- profile and notification routes with recorded SQL behaviour

Main test files:
- `tests/conftest.py`
- `tests/helpers.py`
- `tests/test_core_logic.py`
- `tests/test_public_routes.py`
- `tests/test_authenticated_routes.py`
- `tests/test_statistics_routes.py`
- `tests/test_authentication_routes.py`
- `tests/test_favourites_routes.py`
- `tests/test_profile_notification_routes.py`

These starter tests mostly use mocked API responses, so they do not need a live API-Football key to run.

### Install test dependencies

If your virtual environment is already active:

```powershell
pip install -r requirements.txt -r requirements-dev.txt
```

Or install the test dependency separately:

```powershell
pip install -r requirements-dev.txt
```

### Run all tests

From the project root:

```powershell
cd C:\path\to\primescore
python -m pytest -v
```

### Run a single test file

```powershell
python -m pytest tests\test_statistics_routes.py -v
```

### Run a single test function

```powershell
python -m pytest tests\test_core_logic.py -k compute_team_stats -v
```

### Notes about the current test suite

- The current starter tests are designed to run even if PostgreSQL is not available.
- They also avoid hitting the real football API in the tested paths by using mocks.
- Database-heavy route tests use the documented fake helpers in `tests/helpers.py` so you can still verify route logic, SQL intent, and session behaviour without standing up a dedicated test database first.
- If you expand the suite later to cover full database writes or full login/register persistence, you should run those tests against a dedicated test database.

## Common problems

### `export` does not work in PowerShell
Use this instead:
```powershell
$env:FOOTBALL_API_KEY="YOUR_KEY"
```

### `psql` is not recognized
This means PostgreSQL command-line tools are not in your PATH.

You can either:
- add PostgreSQL `bin` to PATH
- use pgAdmin
- run `psql.exe` with its full path

### PostgreSQL password authentication failed
Your PostgreSQL username or password is wrong for that machine.

Check:
- `DB_USER`
- `DB_PASSWORD`
- the PostgreSQL server is running

### The app opens but football data is missing
Check:
- `FOOTBALL_API_KEY` is set
- the key is valid
- you are not hitting the API free-plan rate limit

### The app starts but the page is blank or broken
Hard refresh the browser:
```text
Ctrl + F5
```

## Notes
- The app serves both frontend and backend from Flask.
- There is no separate frontend dev server.
- The free API-Football plan is rate-limited, so repeated refreshes can temporarily return `429`.
