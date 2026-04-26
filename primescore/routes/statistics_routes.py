"""Statistics routes used by standings and compare pages."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from config import CURRENT_SEASON
from services.football_api_client import call_football_api, compute_team_stats, format_standings

stats_bp = Blueprint("stats", __name__)

LEAGUE_MAP = {
    "PL": 39,
    "CL": 2,
    "BL1": 78,
    "SA": 135,
    "PD": 140,
    "FL1": 61,
}


def _league_id(value):
    return LEAGUE_MAP.get(value, value)


def _today_string():
    return datetime.now(timezone.utc).date().isoformat()


def _date_offset_string(days):
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _safe_total(node, *path):
    current = node
    for key in path:
        if not isinstance(current, dict):
            return 0
        current = current.get(key)
    return current or 0


def _extract_league_id_from_standings(data):
    response_items = (data or {}).get("response") or []
    if not response_items:
        return None
    return (response_items[0].get("league") or {}).get("id")


def _extract_league_id_from_leagues(data):
    response_items = (data or {}).get("response") or []
    if not response_items:
        return None

    preferred_item = next(
        (
            item
            for item in response_items
            if str((item.get("league") or {}).get("type", "")).lower() == "league"
        ),
        response_items[0],
    )
    return (preferred_item.get("league") or {}).get("id")


def _resolve_team_league_id(team_id, requested_league=None):
    if requested_league:
        return _league_id(requested_league)

    standings_data = call_football_api("standings", {"team": team_id, "season": CURRENT_SEASON})
    league_id = _extract_league_id_from_standings(standings_data)
    if league_id:
        return league_id

    leagues_data = call_football_api("leagues", {"team": team_id, "season": CURRENT_SEASON})
    return _extract_league_id_from_leagues(leagues_data)


def _format_official_team_statistics(team_id, stats_data):
    response_payload = (stats_data or {}).get("response") or {}
    if not response_payload:
        return None

    team = response_payload.get("team") or {}
    fixtures = response_payload.get("fixtures") or {}
    goals = response_payload.get("goals") or {}
    clean_sheet = response_payload.get("clean_sheet") or {}

    return {
        "team_id": team.get("id", team_id),
        "team_name": team.get("name", f"Team {team_id}"),
        "team_crest": team.get("logo"),
        "matches_played": _safe_total(fixtures, "played", "total"),
        "wins": _safe_total(fixtures, "wins", "total"),
        "draws": _safe_total(fixtures, "draws", "total"),
        "losses": _safe_total(fixtures, "loses", "total"),
        "goals_scored": _safe_total(goals, "for", "total", "total"),
        "goals_conceded": _safe_total(goals, "against", "total", "total"),
        "clean_sheets": clean_sheet.get("total", 0) or 0,
    }


@stats_bp.route("/leagues/<league_id>/standings", methods=["GET"])
def get_league_standings(league_id):
    data = call_football_api("standings", {"league": _league_id(league_id), "season": CURRENT_SEASON})
    return jsonify(format_standings(data)), 200


@stats_bp.route("/standings/lookup", methods=["GET"])
def standings_lookup():
    league_id = request.args.get("league", "PL")
    data = call_football_api("standings", {"league": _league_id(league_id), "season": CURRENT_SEASON})
    formatted = format_standings(data)

    return jsonify(
        {
            "competition": formatted.get("competition", str(league_id)),
            "season": formatted.get("season", str(CURRENT_SEASON)),
            "standings": formatted.get("standings", []),
        }
    ), 200


@stats_bp.route("/teams/<int:team_id>/statistics", methods=["GET"])
def get_team_statistics(team_id):
    team_name = (request.args.get("name") or "").strip()
    requested_league = (request.args.get("league") or "").strip()

    team_data = call_football_api("teams", {"id": team_id})
    team = None
    if team_data and team_data.get("response"):
        team = team_data["response"][0].get("team", {})

    if not team and team_name:
        resolved_team = call_football_api("teams", {"search": team_name})
        if resolved_team and resolved_team.get("response"):
            team = resolved_team["response"][0].get("team", {})
            team_id = team.get("id", team_id)

    team = team or {"id": team_id, "name": team_name or f"Team {team_id}"}

    recent_match_params = {
        "team": team_id,
        "from": _date_offset_string(-365),
        "to": _today_string(),
        "status": "FT-AET-PEN",
    }
    if requested_league:
        recent_match_params["league"] = _league_id(requested_league)

    matches_data = call_football_api("matches", recent_match_params)
    recent_stats = compute_team_stats(team_id, team, matches_data)
    if recent_stats["matches_played"] > 0:
        return jsonify(recent_stats), 200

    league_id = _resolve_team_league_id(team_id, requested_league=requested_league)
    if league_id:
        official_stats = call_football_api(
            "team_statistics",
            {
                "team": team_id,
                "league": league_id,
                "season": CURRENT_SEASON,
            },
        )
        formatted_official_stats = _format_official_team_statistics(team_id, official_stats)
        if formatted_official_stats:
            return jsonify(formatted_official_stats), 200

    return jsonify(recent_stats), 200


@stats_bp.route("/players/<int:player_id>/statistics", methods=["GET"])
def get_player_statistics(player_id):
    data = call_football_api(
        "players",
        {
            "id": player_id,
            "season": CURRENT_SEASON,
        },
    )

    if not data or not data.get("response"):
        return jsonify({"error": "Player not found"}), 404

    player_data = data["response"][0]
    player = player_data.get("player", {})
    statistics = (player_data.get("statistics") or [{}])[0]

    return jsonify(
        {
            "player_id": player_id,
            "player_name": player.get("name", "Unknown"),
            "current_team": (statistics.get("team") or {}).get("name"),
            "position": (statistics.get("games") or {}).get("position"),
            "statistics": {
                "goals": (statistics.get("goals") or {}).get("total", 0) or 0,
                "assists": (statistics.get("goals") or {}).get("assists", 0) or 0,
                "appearances": (statistics.get("games") or {}).get("appearances", 0) or 0,
                "yellow_cards": (statistics.get("cards") or {}).get("yellow", 0) or 0,
                "red_cards": (statistics.get("cards") or {}).get("red", 0) or 0,
            },
        }
    ), 200
