"""Minimal API-Football client used by the current PrimeScore app."""

import logging

import requests

from config import FOOTBALL_API_BASE, FOOTBALL_API_KEY, FOOTBALL_API_TIMEOUT

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "fixtures": "fixtures",
    "matches": "fixtures",
    "teams": "teams",
    "players": "players",
    "standings": "standings",
    "leagues": "leagues",
}


def _headers():
    if "api-sports.io" in FOOTBALL_API_BASE:
        return {
            "x-apisports-key": FOOTBALL_API_KEY,
            "Accept": "application/json",
        }

    host = FOOTBALL_API_BASE.replace("https://", "").split("/")[0]
    return {
        "x-rapidapi-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": host,
        "Accept": "application/json",
    }


def call_football_api(endpoint, params=None):
    api_path = ENDPOINTS.get(endpoint)
    if not api_path:
        logger.error("Unsupported endpoint: %s", endpoint)
        return None

    try:
        response = requests.get(
            f"{FOOTBALL_API_BASE}/{api_path}",
            headers=_headers(),
            params=params or {},
            timeout=FOOTBALL_API_TIMEOUT,
        )
        logger.info("API Request %s params=%s -> %s", f"{FOOTBALL_API_BASE}/{api_path}", params or {}, response.status_code)
    except Exception as error:
        logger.error("API request failed: %s - %s", type(error).__name__, error)
        return None

    if response.status_code != 200:
        logger.error("API request failed with status %s", response.status_code)
        return None

    data = response.json()
    if data.get("errors"):
        logger.error("API-Football errors: %s", data["errors"])
        if "rateLimit" in data["errors"]:
            return {"_error": "rate_limit", "errors": data["errors"]}
        return None

    return data


def format_standings(data):
    if not data or not data.get("response"):
        return {"competition": "Unknown", "season": "", "standings": []}

    league = data["response"][0].get("league", {})
    standings_groups = league.get("standings", [])
    standings = standings_groups[0] if standings_groups else []

    return {
        "competition": league.get("name", "Unknown"),
        "season": str(league.get("season", "")),
        "standings": [
            {
                "position": team.get("rank"),
                "team": (team.get("team") or {}).get("name", "Unknown"),
                "team_crest": (team.get("team") or {}).get("logo"),
                "played": (team.get("all") or {}).get("played", 0),
                "won": (team.get("all") or {}).get("win", 0),
                "drawn": (team.get("all") or {}).get("draw", 0),
                "lost": (team.get("all") or {}).get("lose", 0),
                "goals_for": ((team.get("all") or {}).get("goals") or {}).get("for", 0),
                "goals_against": ((team.get("all") or {}).get("goals") or {}).get("against", 0),
                "goal_difference": team.get("goalsDiff", 0),
                "points": team.get("points", 0),
            }
            for team in standings
        ],
    }


def compute_team_stats(team_id, team, matches_data):
    stats = {
        "team_id": team_id,
        "team_name": team.get("name", "Unknown"),
        "team_crest": team.get("logo"),
        "matches_played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_scored": 0,
        "goals_conceded": 0,
        "clean_sheets": 0,
    }

    for match in (matches_data or {}).get("response", [])[:10]:
        fixture = match.get("fixture", {})
        status = (fixture.get("status") or {}).get("short")
        if status not in ("FT", "AET", "PEN"):
            continue

        teams = match.get("teams", {})
        goals = match.get("goals", {})
        is_home = ((teams.get("home") or {}).get("id")) == team_id
        goals_for = goals.get("home", 0) if is_home else goals.get("away", 0)
        goals_against = goals.get("away", 0) if is_home else goals.get("home", 0)

        stats["matches_played"] += 1
        stats["goals_scored"] += goals_for or 0
        stats["goals_conceded"] += goals_against or 0

        if goals_against == 0:
            stats["clean_sheets"] += 1
        if goals_for > goals_against:
            stats["wins"] += 1
        elif goals_for < goals_against:
            stats["losses"] += 1
        else:
            stats["draws"] += 1

    return stats
