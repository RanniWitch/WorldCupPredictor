"""Shared fixtures and configuration for World Cup Predictor tests."""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def empty_matches_df():
    """Return an empty DataFrame with the correct match schema."""
    return pd.DataFrame(columns=[
        "home_team_id", "away_team_id", "home_score", "away_score", "match_date"
    ])


@pytest.fixture
def sample_api_response():
    """Return a sample API response with mixed match statuses."""
    return {
        "matches": [
            {
                "id": 1,
                "utcDate": "2022-11-20T16:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 100, "name": "Team A"},
                "awayTeam": {"id": 200, "name": "Team B"},
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
            {
                "id": 2,
                "utcDate": "2022-11-21T13:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 300, "name": "Team C"},
                "awayTeam": {"id": 400, "name": "Team D"},
                "score": {"fullTime": {"home": 0, "away": 0}},
            },
            {
                "id": 3,
                "utcDate": "2022-12-18T15:00:00Z",
                "status": "SCHEDULED",
                "homeTeam": {"id": 100, "name": "Team A"},
                "awayTeam": {"id": 300, "name": "Team C"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
        ]
    }


@pytest.fixture
def sample_matches_df():
    """Return a sample DataFrame of finished matches."""
    return pd.DataFrame({
        "home_team_id": [100, 300, 200, 400, 100, 300, 200, 400, 100, 300],
        "away_team_id": [200, 400, 300, 100, 400, 200, 100, 300, 300, 100],
        "home_score": [2, 0, 1, 3, 2, 1, 0, 2, 1, 2],
        "away_score": [1, 0, 1, 1, 0, 2, 1, 0, 0, 1],
        "match_date": pd.to_datetime([
            "2022-11-20", "2022-11-21", "2022-11-22", "2022-11-23",
            "2022-11-24", "2022-11-25", "2022-11-26", "2022-11-27",
            "2022-11-28", "2022-11-29",
        ]),
    })


@pytest.fixture
def api_response_finished_only():
    """Return an API response with only FINISHED matches (no scheduled)."""
    return {
        "matches": [
            {
                "id": 10,
                "utcDate": "2022-11-20T16:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 100, "name": "Team A"},
                "awayTeam": {"id": 200, "name": "Team B"},
                "score": {"fullTime": {"home": 3, "away": 0}},
            },
            {
                "id": 11,
                "utcDate": "2022-11-21T13:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 300, "name": "Team C"},
                "awayTeam": {"id": 400, "name": "Team D"},
                "score": {"fullTime": {"home": 1, "away": 2}},
            },
        ]
    }


@pytest.fixture
def api_response_with_null_scores():
    """Return an API response with some matches having null scores."""
    return {
        "matches": [
            {
                "id": 20,
                "utcDate": "2022-11-20T16:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 100, "name": "Team A"},
                "awayTeam": {"id": 200, "name": "Team B"},
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
            {
                "id": 21,
                "utcDate": "2022-11-21T13:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"id": 300, "name": "Team C"},
                "awayTeam": {"id": 400, "name": "Team D"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
        ]
    }


@pytest.fixture
def api_response_scheduled_only():
    """Return an API response with only SCHEDULED matches."""
    return {
        "matches": [
            {
                "id": 30,
                "utcDate": "2022-12-18T15:00:00Z",
                "status": "SCHEDULED",
                "homeTeam": {"id": 100, "name": "Team A"},
                "awayTeam": {"id": 300, "name": "Team C"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
            {
                "id": 31,
                "utcDate": "2022-12-19T15:00:00Z",
                "status": "SCHEDULED",
                "homeTeam": {"id": 200, "name": "Team B"},
                "awayTeam": {"id": 400, "name": "Team D"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
        ]
    }


@pytest.fixture
def sample_features_df():
    """Return a sample features DataFrame indexed by team_id."""
    return pd.DataFrame(
        {
            "win_rate": [0.6, 0.4, 0.5, 0.3],
            "avg_goals_scored": [1.8, 1.2, 1.5, 0.9],
            "avg_goals_conceded": [0.8, 1.0, 1.2, 1.5],
        },
        index=pd.Index([100, 200, 300, 400], name="team_id"),
    )


@pytest.fixture
def sample_feature_matrix():
    """Return a sample numeric DataFrame suitable for scaler input."""
    return pd.DataFrame({
        "home_win_rate": [0.6, 0.4, 0.5, 0.3, 0.7, 0.2, 0.8, 0.55, 0.45, 0.65],
        "home_avg_goals_scored": [1.8, 1.2, 1.5, 0.9, 2.1, 0.7, 2.3, 1.6, 1.1, 1.9],
        "home_avg_goals_conceded": [0.8, 1.0, 1.2, 1.5, 0.6, 1.8, 0.5, 0.9, 1.3, 0.7],
        "away_win_rate": [0.4, 0.6, 0.3, 0.5, 0.35, 0.55, 0.25, 0.45, 0.6, 0.4],
        "away_avg_goals_scored": [1.2, 1.8, 0.9, 1.5, 1.0, 1.7, 0.8, 1.3, 1.6, 1.1],
        "away_avg_goals_conceded": [1.0, 0.8, 1.5, 1.2, 1.1, 0.7, 1.6, 1.0, 0.9, 1.3],
    })


@pytest.fixture
def sample_training_labels():
    """Return sample binary labels for training (1=home win, 0=not home win)."""
    return pd.Series([1, 0, 0, 1, 1, 0, 1, 1, 0, 1], name="label")


@pytest.fixture
def mock_successful_api_response():
    """Return a mock response object simulating a successful API call."""
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "matches": [
                    {
                        "id": 1,
                        "utcDate": "2022-11-20T16:00:00Z",
                        "status": "FINISHED",
                        "homeTeam": {"id": 100, "name": "Team A"},
                        "awayTeam": {"id": 200, "name": "Team B"},
                        "score": {"fullTime": {"home": 2, "away": 1}},
                    },
                ]
            }
        def raise_for_status(self):
            pass
    return MockResponse()


@pytest.fixture
def sample_nan_dataframe():
    """Return a DataFrame containing NaN values for error testing."""
    return pd.DataFrame({
        "feature_0": [1.0, 2.0, np.nan, 4.0],
        "feature_1": [5.0, 6.0, 7.0, 8.0],
    })


@pytest.fixture
def sample_constant_column_df():
    """Return a DataFrame with a zero-variance (constant) column."""
    return pd.DataFrame({
        "feature_0": [3.0, 3.0, 3.0, 3.0, 3.0],
        "feature_1": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
