"""Match routes used by the current PrimeScore interface."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session

from config import CURRENT_SEASON
from services.football_api_client import call_football_api, is_rate_limited_response

matches_bp = Blueprint("matches", __name__)

LEAGUE_MAP = {
    "PL": 39,
    "CL": 2,
    "BL1": 78,
    "SA": 135,
    "PD": 140,
    "FL1": 61,
}


def _require_login():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None


def _map_match(match, include_scores=False):
    fixture = match.get("fixture", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})
    league = match.get("league", {})
    status = fixture.get("status", {})

    payload = {
        "match_id": fixture.get("id"),
        "home_team": (teams.get("home") or {}).get("name", "Unknown"),
        "away_team": (teams.get("away") or {}).get("name", "Unknown"),
        "competition": league.get("name", "Unknown"),
        "date": fixture.get("date"),
        "match_date": fixture.get("date"),
        "status": status.get("long", "Unknown"),
    }

    if include_scores:
        payload.update({
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
        })
    return payload


def _resolve_league_id(raw_league_id):
    if not raw_league_id:
        return 39
    return LEAGUE_MAP.get(raw_league_id, raw_league_id)


def _today_string():
    return datetime.now(timezone.utc).date().isoformat()


def _date_offset_string(days):
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _format_match_event(event):
    """Shape a single fixtures/events entry into a UI-friendly dict.

    The API returns events of type "Goal", "Card", "subst", "Var". We surface
    the three the spec requires (cards, subs) plus goals for completeness so
    the timeline reads naturally.
    """
    time = event.get("time") or {}
    team = event.get("team") or {}
    player = event.get("player") or {}
    assist = event.get("assist") or {}

    event_type = (event.get("type") or "").lower()  # "goal", "card", "subst", "var"
    detail = event.get("detail") or ""

    # Normalise a friendly subtype: "yellow_card", "red_card", "substitution",
    # "goal", "own_goal", "penalty_goal" — the frontend uses this to pick an icon.
    if event_type == "card":
        subtype = "red_card" if "red" in detail.lower() else "yellow_card"
    elif event_type == "subst":
        subtype = "substitution"
    elif event_type == "goal":
        d = detail.lower()
        if "own" in d:
            subtype = "own_goal"
        elif "penalty" in d:
            subtype = "penalty_goal"
        else:
            subtype = "goal"
    else:
        subtype = event_type or "event"

    return {
        "minute": time.get("elapsed"),
        "extra_minute": time.get("extra"),
        "team": team.get("name"),
        "team_id": team.get("id"),
        "player": player.get("name"),
        "assist": assist.get("name"),
        "type": event_type,
        "subtype": subtype,
        "detail": detail,
    }


@matches_bp.route("/matches/<int:match_id>/events", methods=["GET"])
def get_match_events(match_id):
    """Return goals, cards, and substitutions for a single fixture.

    Used by the home-page live match cards (and the live-matches page) to
    satisfy FR3: live match details must include yellow/red cards and
    substitutions. Lazy-loaded — only called when the user opens a card.
    """
    auth_error = _require_login()
    if auth_error:
        return auth_error

    data = call_football_api("fixture_events", {"fixture": match_id})
    if is_rate_limited_response(data):
        return jsonify({"error": "Rate limited by API-Football. Please retry shortly."}), 429
    if not data or not data.get("response"):
        return jsonify({"match_id": match_id, "events": []}), 200

    events = [_format_match_event(event) for event in data["response"]]
    # API returns roughly chronological; ensure stable ordering by minute then extra
    events.sort(key=lambda e: ((e.get("minute") or 0), (e.get("extra_minute") or 0)))

    return jsonify({"match_id": match_id, "events": events}), 200


@matches_bp.route("/matches/live", methods=["GET"])
def get_live_matches():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    data = call_football_api("fixtures", {"live": "all"})
    if not data or not data.get("response"):
        return jsonify({"matches": []}), 200

    matches = []
    for match in data["response"]:
        mapped_match = _map_match(match, include_scores=True)
        mapped_match["minute"] = ((match.get("fixture") or {}).get("status") or {}).get("elapsed")
        matches.append(mapped_match)

    return jsonify({"matches": matches}), 200


@matches_bp.route("/fixtures", methods=["GET"])
def get_fixtures():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    # Free plan only supports date-only queries within ~2 days of today.
    # team/league + date requires season; future seasons are plan-restricted.
    data = call_football_api("fixtures", {"date": _date_offset_string(1)})
    matches = [_map_match(m) for m in (data or {}).get("response", [])]
    matches.sort(key=lambda match: match.get("date") or "")
    return jsonify({"fixtures": matches[:10]}), 200


@matches_bp.route("/results", methods=["GET"])
def get_results():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    league_id = _resolve_league_id(request.args.get("league_id"))
    team_id = request.args.get("team_id")

    if team_id:
        params = {"team": team_id, "season": CURRENT_SEASON, "status": "FT-AET-PEN"}
    else:
        params = {
            "league": league_id,
            "season": CURRENT_SEASON,
            "status": "FT-AET-PEN",
        }

    data = call_football_api("fixtures", params)
    matches = [_map_match(match, include_scores=True) for match in (data or {}).get("response", [])]
    matches.sort(key=lambda match: match.get("date") or "", reverse=True)

    return jsonify({"results": matches[:5]}), 200
