"""Application configuration."""

import os
from datetime import datetime, timedelta

SECRET_KEY = os.environ.get("SECRET_KEY", "primescore-dev-secret")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "database": os.environ.get("DB_NAME", "primescore"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "port": os.environ.get("DB_PORT", "5432"),
}

def _default_current_season():
    """Return the most likely API-Football season key for today's date.

    API-Football represents a season by the year in which it starts.
    For example, the 2025/2026 European season is keyed as 2025.
    """

    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_API_BASE = "https://v3.football.api-sports.io"
FOOTBALL_API_TIMEOUT = 10
CURRENT_SEASON = int(os.environ.get("CURRENT_SEASON", str(_default_current_season())))
