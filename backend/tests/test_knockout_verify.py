"""Quick verification test for knockout service and route."""

from unittest.mock import patch

from src.exceptions import AuthenticationError, RateLimitError
from backend.services import get_knockout_data
from backend.error_handling import handle_api_error


def test_knockout_data_filters_and_organizes_matches():
    """Test that get_knockout_data properly filters knockout matches."""
    mock_data = {
        "matches": [
            {
                "id": 1,
                "stage": "ROUND_OF_16",
                "homeTeam": {"id": 100, "name": "Brazil", "crest": "https://brazil.svg"},
                "awayTeam": {"id": 200, "name": "Germany", "crest": "https://germany.svg"},
                "status": "FINISHED",
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
            {
                "id": 2,
                "stage": "QUARTER_FINALS",
                "homeTeam": {"id": None, "name": None, "crest": None},
                "awayTeam": {"id": 300, "name": "France", "crest": "https://france.svg"},
                "status": "SCHEDULED",
                "score": {"fullTime": {"home": None, "away": None}},
            },
            {
                "id": 3,
                "stage": "GROUP_A",
                "homeTeam": {"id": 400, "name": "Spain", "crest": "https://spain.svg"},
                "awayTeam": {"id": 500, "name": "Italy", "crest": "https://italy.svg"},
                "status": "FINISHED",
                "score": {"fullTime": {"home": 1, "away": 0}},
            },
        ]
    }

    with patch("backend.services.APIClient") as MockClient:
        MockClient.return_value.get_matches.return_value = mock_data

        result = get_knockout_data()

    # Should have 5 rounds in order
    assert len(result.rounds) == 5
    round_names = [r.round_name for r in result.rounds]
    assert round_names == [
        "Round_of_32",
        "Round_of_16",
        "Quarter_Finals",
        "Semi_Finals",
        "Final",
    ]

    # Round_of_16 has the Brazil vs Germany match
    r16 = result.rounds[1]
    assert len(r16.matches) == 1
    assert r16.matches[0].home_team.team_name == "Brazil"
    assert r16.matches[0].home_team.crest == "https://brazil.svg"
    assert r16.matches[0].away_team.team_name == "Germany"
    assert r16.matches[0].away_team.crest == "https://germany.svg"
    assert r16.matches[0].status == "FINISHED"
    assert r16.matches[0].home_score == 2
    assert r16.matches[0].away_score == 1

    # Quarter_Finals has TBD home team
    qf = result.rounds[2]
    assert len(qf.matches) == 1
    assert qf.matches[0].home_team.team_name == "TBD"
    assert qf.matches[0].home_team.crest == ""
    assert qf.matches[0].away_team.team_name == "France"
    assert qf.matches[0].status == "SCHEDULED"
    assert qf.matches[0].home_score is None
    assert qf.matches[0].away_score is None

    # GROUP_A match is filtered out
    assert result.rounds[0].matches == []  # Round_of_32 empty
    assert result.rounds[3].matches == []  # Semi_Finals empty
    assert result.rounds[4].matches == []  # Final empty


def test_knockout_data_tbd_for_null_teams():
    """Test that null team IDs produce TBD placeholders."""
    mock_data = {
        "matches": [
            {
                "id": 10,
                "stage": "FINAL",
                "homeTeam": {"id": None, "name": None, "crest": None},
                "awayTeam": {"id": None, "name": None, "crest": None},
                "status": "TIMED",
                "score": {"fullTime": {"home": None, "away": None}},
            }
        ]
    }

    with patch("backend.services.APIClient") as MockClient:
        MockClient.return_value.get_matches.return_value = mock_data

        result = get_knockout_data()

    final = result.rounds[4]
    assert len(final.matches) == 1
    assert final.matches[0].home_team.team_name == "TBD"
    assert final.matches[0].home_team.crest == ""
    assert final.matches[0].away_team.team_name == "TBD"
    assert final.matches[0].away_team.crest == ""
    assert final.matches[0].status == "TIMED"
    assert final.matches[0].home_score is None
    assert final.matches[0].away_score is None


def test_knockout_data_scores_only_for_finished():
    """Test that scores are only included for FINISHED matches."""
    mock_data = {
        "matches": [
            {
                "id": 20,
                "stage": "ROUND_OF_32",
                "homeTeam": {"id": 1, "name": "TeamA", "crest": "a.svg"},
                "awayTeam": {"id": 2, "name": "TeamB", "crest": "b.svg"},
                "status": "IN_PLAY",
                "score": {"fullTime": {"home": 1, "away": 0}},
            },
            {
                "id": 21,
                "stage": "ROUND_OF_32",
                "homeTeam": {"id": 3, "name": "TeamC", "crest": "c.svg"},
                "awayTeam": {"id": 4, "name": "TeamD", "crest": "d.svg"},
                "status": "FINISHED",
                "score": {"fullTime": {"home": 3, "away": 2}},
            },
        ]
    }

    with patch("backend.services.APIClient") as MockClient:
        MockClient.return_value.get_matches.return_value = mock_data

        result = get_knockout_data()

    r32 = result.rounds[0]
    assert len(r32.matches) == 2

    # IN_PLAY match: no scores
    in_play = r32.matches[0]
    assert in_play.status == "IN_PLAY"
    assert in_play.home_score is None
    assert in_play.away_score is None

    # FINISHED match: has scores
    finished = r32.matches[1]
    assert finished.status == "FINISHED"
    assert finished.home_score == 3
    assert finished.away_score == 2


def test_knockout_error_propagation():
    """Test that API errors propagate for the route handler to catch."""
    with patch("backend.services.APIClient") as MockClient:
        MockClient.return_value.get_matches.side_effect = AuthenticationError(
            401, "Invalid key"
        )

        try:
            get_knockout_data()
            assert False, "Should have raised AuthenticationError"
        except AuthenticationError as e:
            assert e.status_code == 401
            http_exc = handle_api_error(e)
            assert http_exc.status_code == 502
            assert http_exc.detail == "Upstream authentication failed"

    with patch("backend.services.APIClient") as MockClient:
        MockClient.return_value.get_matches.side_effect = RateLimitError(
            429, "Too many"
        )

        try:
            get_knockout_data()
            assert False, "Should have raised RateLimitError"
        except RateLimitError as e:
            assert e.status_code == 429
            http_exc = handle_api_error(e)
            assert http_exc.status_code == 503
