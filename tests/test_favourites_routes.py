"""Deeper tests for favourites and home-screen behaviour.

These tests focus on route logic that sits between user input and persistence:
- favourite resolution
- limit validation
- display-name handling
- safe home-screen behaviour
"""

import routes.favourites_routes as favourites_routes
from tests.helpers import build_dbcontext_patch


def test_get_favourites_returns_saved_display_names_for_logged_in_user(authenticated_client, monkeypatch):
    """Logged-in users should see friendly names, not just internal IDs."""

    db_patch = build_dbcontext_patch(
        fetchone_results=[
            {
                "favourite_teams": [42],
                "favourite_players": [276],
                "favourite_leagues": ["PL"],
                "favourite_team_names": ["Arsenal"],
                "favourite_player_names": ["Mohamed Salah"],
                "favourite_league_names": ["Premier League"],
            }
        ]
    )
    monkeypatch.setattr(favourites_routes, "DBContext", db_patch.factory)
    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)

    response = authenticated_client.get("/api/favourites")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["favourite_teams"] == ["Arsenal"]
    assert payload["favourite_players"] == ["Mohamed Salah"]
    assert payload["favourite_leagues"] == ["Premier League"]
    assert payload["favourite_team_ids"] == [42]
    assert payload["favourite_player_ids"] == [276]


def test_save_favourites_resolves_and_persists_names_and_ids(authenticated_client, monkeypatch):
    """Saving favourites should persist both IDs and user-facing display names."""

    db_patch = build_dbcontext_patch()
    monkeypatch.setattr(favourites_routes, "DBContext", db_patch.factory)
    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)
    monkeypatch.setattr(favourites_routes, "_get_saved_favourites_row", lambda user_id: {})
    monkeypatch.setattr(
        favourites_routes,
        "_resolve_team_entries",
        lambda references, known_id_to_name=None: {"ids": [42], "names": ["Arsenal"]},
    )
    monkeypatch.setattr(
        favourites_routes,
        "_resolve_player_entries",
        lambda references, known_id_to_name=None: {"ids": [276], "names": ["Mohamed Salah"]},
    )
    monkeypatch.setattr(
        favourites_routes,
        "_resolve_league_entries",
        lambda references, known_id_to_name=None: {"codes": ["PL"], "names": ["Premier League"]},
    )

    response = authenticated_client.post(
        "/api/favourites",
        json={
            "favourite_teams": ["Arsenal"],
            "favourite_players": ["Mohamed Salah - Liverpool"],
            "favourite_leagues": ["Premier League"],
        },
    )

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["message"] == "Saved"
    assert payload["favourite_teams"] == ["Arsenal"]
    assert payload["favourite_players"] == ["Mohamed Salah"]
    assert payload["favourite_leagues"] == ["Premier League"]
    assert db_patch.transaction_state.committed is True

    executed_query = db_patch.cursor.executed_statements[0]["query"]
    assert "INSERT INTO user_favourites" in executed_query

def test_save_favourites_returns_404_when_resolution_fails(authenticated_client, monkeypatch):
    """If a team name cannot be resolved, the route should report that clearly."""

    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)
    monkeypatch.setattr(favourites_routes, "_get_saved_favourites_row", lambda user_id: {})
    monkeypatch.setattr(
        favourites_routes,
        "_resolve_team_entries",
        lambda references, known_id_to_name=None: {"error": 'Team "Unknown FC" was not found.'},
    )

    response = authenticated_client.post(
        "/api/favourites",
        json={
            "favourite_teams": ["Unknown FC"],
            "favourite_players": [],
            "favourite_leagues": [],
        },
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == 'Team "Unknown FC" was not found.'

def test_save_favourites_returns_429_when_resolver_hits_rate_limit(authenticated_client, monkeypatch):
    """Resolver-level rate limits should be translated into a user-facing 429."""

    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)
    monkeypatch.setattr(favourites_routes, "_get_saved_favourites_row", lambda user_id: {})
    monkeypatch.setattr(
        favourites_routes,
        "_resolve_team_entries",
        lambda references, known_id_to_name=None: {"_error": "rate_limit"},
    )

    response = authenticated_client.post(
        "/api/favourites",
        json={
            "favourite_teams": ["Arsenal"],
            "favourite_players": [],
            "favourite_leagues": [],
        },
    )

    assert response.status_code == 429
    assert response.get_json()["error"] == "Rate limited by API-Football. Please retry shortly."

def test_save_favourites_rejects_more_than_ten_players(authenticated_client):
    response = authenticated_client.post(
        "/api/favourites",
        json={
            "favourite_teams": [],
            "favourite_players": [f"Player {index}" for index in range(11)],
            "favourite_leagues": [],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "You can save up to 10 favourite players."


def test_save_favourites_rejects_more_than_three_leagues(authenticated_client):
    response = authenticated_client.post(
        "/api/favourites",
        json={
            "favourite_teams": [],
            "favourite_players": [],
            "favourite_leagues": ["PL", "SA", "PD", "FL1"],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "You can save up to 3 favourite leagues."


def test_home_screen_returns_safe_empty_payload_on_rate_limit(client, monkeypatch):
    """If the very first home-screen API call hits rate limits, the route should
    still return a stable JSON structure instead of crashing.
    """

    monkeypatch.setattr(
        favourites_routes,
        "call_football_api",
        lambda endpoint, params=None: {"_error": "rate_limit", "status_code": 429},
    )

    response = client.get("/api/home-screen")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {
        "live_matches": [],
        "recent_results": [],
        "upcoming_fixtures": [],
        "league_tables": [],
        "selected_league": {
            "id": 39,
            "code": "PL",
            "name": "Premier League",
        },
        "favourite_player_stats": [],
        "favourite_team_stats": [],
        "favourite_league_stats": [],
    }

def test_home_screen_uses_generic_premier_league_feed_before_favourites_exist(client, monkeypatch):
    api_calls = []

    def fake_call(endpoint, params=None):
        api_calls.append((endpoint, params))
        if endpoint == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "name": "Premier League",
                            "season": 2024,
                            "standings": [[{"rank": 1, "team": {"name": "Arsenal", "logo": "arsenal.png"}, "all": {"played": 30, "win": 21, "draw": 5, "lose": 4, "goals": {"for": 66, "against": 26}}, "goalsDiff": 40, "points": 68}]],
                        }
                    }
                ]
            }
        if endpoint == "fixtures" and params == {"live": "all"}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"date": favourites_routes._date_offset_string(1)}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"league": 39, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {"response": []}
        raise AssertionError(f"Unexpected endpoint: {endpoint} {params}")

    monkeypatch.setattr(favourites_routes, "call_football_api", fake_call)

    response = client.get("/api/home-screen")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["selected_league"] == {"id": 39, "code": "PL", "name": "Premier League"}
    assert payload["league_tables"][0]["competition"] == "Premier League"
    assert ("standings", {"league": 39, "season": favourites_routes.CURRENT_SEASON}) in api_calls
    assert ("fixtures", {"live": "all"}) in api_calls
    assert ("fixtures", {"date": favourites_routes._date_offset_string(1)}) in api_calls
    assert (
        "fixtures",
        {"league": 39, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"},
    ) in api_calls

def test_home_screen_uses_most_recently_saved_favourite_league(authenticated_client, monkeypatch):
    """The homepage should load standings/results for the most recently saved favourite league."""

    db_patch = build_dbcontext_patch(
        fetchone_results=[
            {
                "favourite_leagues": ["PL", "FL1"],
                "favourite_league_names": ["Premier League", "Ligue 1"],
            }
        ]
    )
    monkeypatch.setattr(favourites_routes, "DBContext", db_patch.factory)
    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)

    api_calls = []

    def fake_call(endpoint, params=None):
        api_calls.append((endpoint, params))
        if endpoint == "standings":
            league_name = "Ligue 1" if params["league"] == 61 else "Premier League"
            return {
                "response": [
                    {
                        "league": {
                            "name": league_name,
                            "season": 2024,
                            "logo": "league.png",
                            "standings": [[{"rank": 1, "team": {"id": 524 if params["league"] == 61 else 42, "name": "PSG" if params["league"] == 61 else "Arsenal", "logo": "team.png"}, "all": {"played": 30, "win": 22, "draw": 5, "lose": 3, "goals": {"for": 70, "against": 25}}, "goalsDiff": 45, "points": 71}]],
                        }
                    }
                ]
            }
        if endpoint == "fixtures" and params == {"live": "all"}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"date": favourites_routes._date_offset_string(1)}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"league": 61, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {"response": []}
        raise AssertionError(f"Unexpected endpoint: {endpoint} {params}")

    monkeypatch.setattr(favourites_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/home-screen")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["selected_league"] == {"id": 61, "code": "FL1", "name": "Ligue 1"}
    assert payload["league_tables"][0]["competition"] == "Ligue 1"
    assert payload["favourite_league_stats"][0]["league_code"] == "PL"
    assert ("standings", {"league": 61, "season": favourites_routes.CURRENT_SEASON}) in api_calls
    assert ("standings", {"league": 39, "season": favourites_routes.CURRENT_SEASON}) in api_calls
    assert ("fixtures", {"live": "all"}) in api_calls
    assert ("fixtures", {"date": favourites_routes._date_offset_string(1)}) in api_calls
    assert (
        "fixtures",
        {"league": 61, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"},
    ) in api_calls

def test_home_screen_honours_explicit_league_override(client, monkeypatch):
    """The home screen should switch league when the frontend asks for a specific code."""

    api_calls = []

    def fake_call(endpoint, params=None):
        api_calls.append((endpoint, params))
        if endpoint == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "name": "Serie A",
                            "season": 2024,
                            "standings": [[{"rank": 1, "team": {"name": "Inter", "logo": "inter.png"}, "all": {"played": 30, "win": 21, "draw": 6, "lose": 3, "goals": {"for": 60, "against": 20}}, "goalsDiff": 40, "points": 69}]],
                        }
                    }
                ]
            }
        if endpoint == "fixtures" and params == {"live": "all"}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"date": favourites_routes._date_offset_string(1)}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"league": 135, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {"response": []}
        raise AssertionError(f"Unexpected endpoint: {endpoint} {params}")

    monkeypatch.setattr(favourites_routes, "call_football_api", fake_call)

    response = client.get("/api/home-screen?league=SA")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["selected_league"] == {"id": 135, "code": "SA", "name": "Serie A"}
    assert ("standings", {"league": 135, "season": favourites_routes.CURRENT_SEASON}) in api_calls
    assert ("fixtures", {"date": favourites_routes._date_offset_string(1)}) in api_calls
    assert (
        "fixtures",
        {"league": 135, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"},
    ) in api_calls

def test_home_screen_reuses_cached_payload_for_same_context(authenticated_client, monkeypatch):
    row = {
        "favourite_teams": [],
        "favourite_players": [],
        "favourite_leagues": ["PL"],
        "favourite_team_names": [],
        "favourite_player_names": [],
        "favourite_league_names": ["Premier League"],
    }
    db_patch = build_dbcontext_patch(fetchone_results=[row, row])
    monkeypatch.setattr(favourites_routes, "DBContext", db_patch.factory)
    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)

    call_counts = {"standings": 0, "fixtures": 0}

    def fake_call(endpoint, params=None):
        call_counts[endpoint] = call_counts.get(endpoint, 0) + 1
        if endpoint == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "name": "Premier League",
                            "season": 2024,
                            "logo": "league.png",
                            "standings": [[{"rank": 1, "team": {"id": 42, "name": "Arsenal", "logo": "arsenal.png"}, "all": {"played": 30, "win": 21, "draw": 5, "lose": 4, "goals": {"for": 66, "against": 26}}, "goalsDiff": 40, "points": 68}]],
                        }
                    }
                ]
            }
        if endpoint == "fixtures" and params == {"live": "all"}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"date": favourites_routes._date_offset_string(1)}:
            return {"response": []}
        if endpoint == "fixtures" and params == {"league": 39, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {"response": []}
        raise AssertionError(f"Unexpected endpoint: {endpoint} {params}")

    monkeypatch.setattr(favourites_routes, "call_football_api", fake_call)

    first_response = authenticated_client.get("/api/home-screen")
    second_response = authenticated_client.get("/api/home-screen")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.get_json() == second_response.get_json()
    assert call_counts["standings"] == 2
    assert call_counts["fixtures"] == 3

def test_home_screen_uses_favourite_teams_and_players_when_available(authenticated_client, monkeypatch):
    """In My Teams mode, the homepage should filter live/results to favourite teams and include favourite player stats."""

    db_patch = build_dbcontext_patch(
        fetchone_results=[
            {
                "favourite_teams": [42, 40],
                "favourite_players": [306],
                "favourite_leagues": ["PL"],
                "favourite_team_names": ["Arsenal", "Liverpool"],
                "favourite_player_names": ["Mohamed Salah"],
                "favourite_league_names": ["Premier League"],
            }
        ]
    )
    monkeypatch.setattr(favourites_routes, "DBContext", db_patch.factory)
    monkeypatch.setattr(favourites_routes, "_ensure_display_columns", lambda: None)

    def fake_call(endpoint, params=None):
        if endpoint == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "name": "Premier League",
                            "season": 2024,
                            "standings": [[{"rank": 1, "team": {"name": "Liverpool", "logo": "liv.png"}, "all": {"played": 30, "win": 23, "draw": 5, "lose": 2, "goals": {"for": 68, "against": 24}}, "goalsDiff": 44, "points": 74}]],
                        }
                    }
                ]
            }

        if endpoint == "fixtures" and params == {"live": "all"}:
            return {
                "response": [
                    {
                        "fixture": {"id": 1, "date": "2026-04-25T12:00:00+00:00", "status": {"long": "First Half", "elapsed": 26}},
                        "teams": {"home": {"id": 40, "name": "Liverpool"}, "away": {"id": 99, "name": "Everton"}},
                        "goals": {"home": 1, "away": 0},
                        "league": {"id": 39, "name": "Premier League"},
                    },
                    {
                        "fixture": {"id": 2, "date": "2026-04-25T13:00:00+00:00", "status": {"long": "Second Half", "elapsed": 70}},
                        "teams": {"home": {"id": 77, "name": "Chelsea"}, "away": {"id": 42, "name": "Arsenal"}},
                        "goals": {"home": 0, "away": 2},
                        "league": {"id": 39, "name": "Premier League"},
                    },
                    {
                        "fixture": {"id": 3, "date": "2026-04-25T13:30:00+00:00", "status": {"long": "First Half", "elapsed": 15}},
                        "teams": {"home": {"id": 88, "name": "Inter"}, "away": {"id": 89, "name": "Milan"}},
                        "goals": {"home": 0, "away": 0},
                        "league": {"id": 135, "name": "Serie A"},
                    },
                ]
            }

        if endpoint == "fixtures" and params == {"team": 42, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {
                "response": [
                    {
                        "fixture": {"id": 20, "date": "2026-04-20T12:00:00+00:00", "status": {"long": "Match Finished"}},
                        "teams": {"home": {"id": 42, "name": "Arsenal"}, "away": {"id": 66, "name": "Newcastle"}},
                        "goals": {"home": 2, "away": 1},
                        "league": {"id": 39, "name": "Premier League"},
                    }
                ]
            }

        if endpoint == "fixtures" and params == {"team": 40, "season": favourites_routes.CURRENT_SEASON, "status": "FT-AET-PEN"}:
            return {
                "response": [
                    {
                        "fixture": {"id": 21, "date": "2026-04-18T12:00:00+00:00", "status": {"long": "Match Finished"}},
                        "teams": {"home": {"id": 67, "name": "West Ham"}, "away": {"id": 40, "name": "Liverpool"}},
                        "goals": {"home": 1, "away": 3},
                        "league": {"id": 39, "name": "Premier League"},
                    }
                ]
            }

        if endpoint == "players" and params == {"id": 306, "season": favourites_routes.CURRENT_SEASON}:
            return {
                "response": [
                    {
                        "player": {"id": 306, "name": "Mohamed Salah", "photo": "salah.png"},
                        "statistics": [
                            {
                                "team": {"name": "Liverpool"},
                                "games": {"position": "Attacker", "appearences": 30, "minutes": 2500, "rating": "7.8"},
                                "goals": {"total": 21, "assists": 9},
                                "cards": {"yellow": 2, "red": 0},
                            }
                        ],
                    }
                ]
            }

        raise AssertionError(f"Unexpected endpoint: {endpoint} {params}")

    monkeypatch.setattr(favourites_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/home-screen?mode=my_teams")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["selected_league"] == {"id": 39, "code": "PL", "name": "Premier League"}
    assert {match["match_id"] for match in payload["live_matches"]} == {1, 2}
    assert payload["upcoming_fixtures"] == []
    assert {match["match_id"] for match in payload["recent_results"]} == {20, 21}
    assert payload["league_tables"][0]["competition"] == "Premier League"
    assert payload["favourite_player_stats"][0]["player_name"] == "Mohamed Salah"
    assert payload["favourite_player_stats"][0]["statistics"]["goals"] == 21

