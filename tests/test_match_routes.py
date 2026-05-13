import routes.match_routes as match_routes


def test_fixtures_route_requires_login(client):
    response = client.get("/api/fixtures?league_id=PL")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Not authenticated"


def test_results_route_requires_login(client):
    response = client.get("/api/results?league_id=PL")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Not authenticated"


def test_live_matches_route_maps_scores_and_minutes(authenticated_client, monkeypatch):
    def fake_call(endpoint, params=None):
        assert endpoint == "fixtures"
        assert params == {"live": "all"}
        return {
            "response": [
                {
                    "fixture": {
                        "id": 1,
                        "date": "2026-04-29T19:00:00+00:00",
                        "status": {"long": "First Half", "elapsed": 34},
                    },
                    "teams": {
                        "home": {"name": "Arsenal"},
                        "away": {"name": "Chelsea"},
                    },
                    "league": {"name": "Premier League"},
                    "goals": {"home": 2, "away": 1},
                }
            ]
        }

    monkeypatch.setattr(match_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/matches/live")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["matches"] == [
        {
            "match_id": 1,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "competition": "Premier League",
            "date": "2026-04-29T19:00:00+00:00",
            "match_date": "2026-04-29T19:00:00+00:00",
            "status": "First Half",
            "home_score": 2,
            "away_score": 1,
            "minute": 34,
        }
    ]


def test_fixtures_route_uses_date_window_for_league_queries(authenticated_client, monkeypatch):
    recorded_calls = []

    def fake_call(endpoint, params=None):
        recorded_calls.append((endpoint, params))
        return {
            "response": [
                {
                    "fixture": {"id": 1, "date": "2026-05-01T19:00:00+00:00", "status": {"long": "Not Started"}},
                    "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": None, "away": None},
                }
            ]
        }

    monkeypatch.setattr(match_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/fixtures?league_id=PL")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["fixtures"][0]["home_team"] == "Arsenal"
    assert recorded_calls == [
        (
            "fixtures",
            {
                "date": match_routes._date_offset_string(1),
            },
        )
    ]

def test_results_route_uses_date_window_for_league_queries(authenticated_client, monkeypatch):
    recorded_calls = []

    def fake_call(endpoint, params=None):
        recorded_calls.append((endpoint, params))
        return {
            "response": [
                {
                    "fixture": {"id": 2, "date": "2026-04-20T19:00:00+00:00", "status": {"long": "Match Finished"}},
                    "teams": {"home": {"name": "Liverpool"}, "away": {"name": "Everton"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": 2, "away": 1},
                }
            ]
        }

    monkeypatch.setattr(match_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/results?league_id=PL")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["results"][0]["home_score"] == 2
    assert recorded_calls == [
        (
            "fixtures",
            {
                "league": 39,
                "season": match_routes.CURRENT_SEASON,
                "status": "FT-AET-PEN",
            },
        )
    ]

def test_fixtures_route_supports_team_filter(authenticated_client, monkeypatch):
    recorded_calls = []

    def fake_call(endpoint, params=None):
        recorded_calls.append((endpoint, params))
        return {
            "response": [
                {
                    "fixture": {"id": 3, "date": "2026-05-03T19:00:00+00:00", "status": {"long": "Not Started"}},
                    "teams": {"home": {"name": "Liverpool"}, "away": {"name": "Spurs"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": None, "away": None},
                }
            ]
        }

    monkeypatch.setattr(match_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/fixtures?team_id=40")

    assert response.status_code == 200
    assert recorded_calls == [
        (
            "fixtures",
            {
                "date": match_routes._date_offset_string(1),
            },
        )
    ]

def test_results_route_supports_team_filter_and_descending_order(authenticated_client, monkeypatch):
    def fake_call(endpoint, params=None):
        assert endpoint == "fixtures"
        assert params == {
            "team": "40",
            "season": match_routes.CURRENT_SEASON,
            "status": "FT-AET-PEN",
        }
        return {
            "response": [
                {
                    "fixture": {"id": 4, "date": "2026-04-15T19:00:00+00:00", "status": {"long": "Match Finished"}},
                    "teams": {"home": {"name": "Liverpool"}, "away": {"name": "Villa"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": 1, "away": 0},
                },
                {
                    "fixture": {"id": 5, "date": "2026-04-22T19:00:00+00:00", "status": {"long": "Match Finished"}},
                    "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Liverpool"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": 0, "away": 2},
                },
            ]
        }

    monkeypatch.setattr(match_routes, "call_football_api", fake_call)

    response = authenticated_client.get("/api/results?team_id=40")
    payload = response.get_json()

    assert response.status_code == 200
    assert [result["match_id"] for result in payload["results"]] == [5, 4]

