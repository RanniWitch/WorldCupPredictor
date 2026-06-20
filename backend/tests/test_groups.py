"""Unit tests for the groups service and route."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.services import get_group_data


# Sample standings API response
MOCK_STANDINGS = {
    "standings": [
        {
            "stage": "GROUP_STAGE",
            "type": "TOTAL",
            "group": "GROUP_A",
            "table": [
                {"position": 1, "team": {"id": 1, "name": "Brazil", "crest": "https://crest1.svg"}},
                {"position": 2, "team": {"id": 2, "name": "Germany", "crest": "https://crest2.svg"}},
                {"position": 3, "team": {"id": 3, "name": "France", "crest": "https://crest3.svg"}},
                {"position": 4, "team": {"id": 4, "name": "Italy", "crest": "https://crest4.svg"}},
            ],
        },
        {
            "stage": "GROUP_STAGE",
            "type": "TOTAL",
            "group": "GROUP_B",
            "table": [
                {"position": 1, "team": {"id": 5, "name": "Spain", "crest": "https://crest5.svg"}},
                {"position": 2, "team": {"id": 6, "name": "England", "crest": "https://crest6.svg"}},
                {"position": 3, "team": {"id": 7, "name": "Argentina", "crest": "https://crest7.svg"}},
                {"position": 4, "team": {"id": 8, "name": "Portugal", "crest": "https://crest8.svg"}},
            ],
        },
        # Non-TOTAL type should be skipped
        {
            "stage": "GROUP_STAGE",
            "type": "HOME",
            "group": "GROUP_A",
            "table": [],
        },
        # Non-GROUP_STAGE should be skipped
        {
            "stage": "KNOCKOUT",
            "type": "TOTAL",
            "group": "GROUP_C",
            "table": [],
        },
    ],
}


class TestGetGroupData:
    """Tests for the get_group_data service function."""

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_returns_correct_groups(self, mock_fetch):
        """Groups are parsed correctly from standings response."""
        result = get_group_data()
        groups = result["groups"]
        assert len(groups) == 2
        assert groups[0]["group_name"] == "A"
        assert groups[1]["group_name"] == "B"

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_teams_have_required_fields(self, mock_fetch):
        """Each team has team_id, team_name, and crest."""
        result = get_group_data()
        for group in result["groups"]:
            for team in group["teams"]:
                assert "team_id" in team
                assert "team_name" in team
                assert "crest" in team

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_groups_sorted_alphabetically(self, mock_fetch):
        """Groups are returned sorted by group_name."""
        result = get_group_data()
        group_names = [g["group_name"] for g in result["groups"]]
        assert group_names == sorted(group_names)

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_skips_non_total_type(self, mock_fetch):
        """Standings with type != TOTAL are excluded."""
        result = get_group_data()
        # Only 2 groups should be returned (HOME type is skipped)
        assert len(result["groups"]) == 2

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_skips_non_group_stage(self, mock_fetch):
        """Standings with stage != GROUP_STAGE are excluded."""
        result = get_group_data()
        # KNOCKOUT stage entry should be skipped
        group_names = [g["group_name"] for g in result["groups"]]
        assert "C" not in group_names

    @patch("backend.services._fetch_standings", return_value={"standings": []})
    def test_empty_standings_returns_empty_groups(self, mock_fetch):
        """Empty standings returns empty groups list."""
        result = get_group_data()
        assert result == {"groups": []}

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_team_data_values(self, mock_fetch):
        """Team fields contain correct values from the API response."""
        result = get_group_data()
        first_team = result["groups"][0]["teams"][0]
        assert first_team["team_id"] == 1
        assert first_team["team_name"] == "Brazil"
        assert first_team["crest"] == "https://crest1.svg"


class TestGroupsRoute:
    """Tests for the GET /api/groups route."""

    @patch("backend.services._fetch_standings", return_value=MOCK_STANDINGS)
    def test_get_groups_success(self, mock_fetch):
        """GET /api/groups returns 200 with valid groups data."""
        from backend.main import app
        from backend.routes.groups import router

        # Ensure router is included
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/api/groups")
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert len(data["groups"]) == 2
        assert data["groups"][0]["group_name"] == "A"

    @patch("backend.services._fetch_standings", side_effect=Exception("Network error"))
    def test_get_groups_error(self, mock_fetch):
        """GET /api/groups returns error on upstream failure."""
        from backend.main import app
        from backend.routes.groups import router

        app.include_router(router)
        client = TestClient(app)

        response = client.get("/api/groups")
        assert response.status_code >= 400
