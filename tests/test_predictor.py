"""Property-based tests for the Predictor orchestrator."""
# Feature: world-cup-predictor, Property 9: Prediction output has correct shape

from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.predictor import Predictor


# --- Strategy: generate a valid API response with >=10 finished matches
# (ensuring both classes in labels) and 1-10 scheduled matches with varying dates ---

def _make_finished_match(match_id, home_id, away_id, home_score, away_score, utc_date_str):
    """Helper to create a finished match dict in football-data.org format."""
    return {
        "id": match_id,
        "utcDate": utc_date_str,
        "status": "FINISHED",
        "homeTeam": {"id": home_id, "name": f"Team {home_id}"},
        "awayTeam": {"id": away_id, "name": f"Team {away_id}"},
        "score": {"fullTime": {"home": home_score, "away": away_score}},
    }


def _make_scheduled_match(match_id, home_id, away_id, utc_date_str):
    """Helper to create a scheduled match dict in football-data.org format."""
    return {
        "id": match_id,
        "utcDate": utc_date_str,
        "status": "SCHEDULED",
        "homeTeam": {"id": home_id, "name": f"Team {home_id}"},
        "awayTeam": {"id": away_id, "name": f"Team {away_id}"},
        "score": {"fullTime": {"home": None, "away": None}},
    }


# Fixed set of finished matches ensuring >=10 records with both classes present
_FIXED_FINISHED_MATCHES = [
    _make_finished_match(1, 100, 200, 3, 1, "2022-11-20T16:00:00Z"),  # home win
    _make_finished_match(2, 300, 400, 0, 2, "2022-11-21T13:00:00Z"),  # home loss
    _make_finished_match(3, 100, 300, 2, 0, "2022-11-22T16:00:00Z"),  # home win
    _make_finished_match(4, 200, 400, 1, 1, "2022-11-23T13:00:00Z"),  # draw (0)
    _make_finished_match(5, 400, 100, 0, 3, "2022-11-24T16:00:00Z"),  # home loss
    _make_finished_match(6, 300, 200, 2, 1, "2022-11-25T13:00:00Z"),  # home win
    _make_finished_match(7, 200, 100, 1, 0, "2022-11-26T16:00:00Z"),  # home win
    _make_finished_match(8, 400, 300, 3, 2, "2022-11-27T13:00:00Z"),  # home win
    _make_finished_match(9, 100, 400, 2, 1, "2022-11-28T16:00:00Z"),  # home win
    _make_finished_match(10, 200, 300, 0, 1, "2022-11-29T13:00:00Z"),  # home loss
]


@st.composite
def scheduled_matches_strategy(draw):
    """Generate 1-10 scheduled matches with varying dates for property testing."""
    n_matches = draw(st.integers(min_value=1, max_value=10))
    team_ids = [100, 200, 300, 400]

    scheduled = []
    for i in range(n_matches):
        home_id = draw(st.sampled_from(team_ids))
        away_id = draw(st.sampled_from([t for t in team_ids if t != home_id]))
        # Generate dates across a range to ensure varying ordering
        match_date = draw(
            st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            )
        )
        utc_date_str = match_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        scheduled.append(
            _make_scheduled_match(1000 + i, home_id, away_id, utc_date_str)
        )

    return scheduled


# Feature: world-cup-predictor, Property 10: Predictions are sorted by match date
class TestPredictionSorting:
    """Property tests for prediction result sorting."""

    @given(scheduled=scheduled_matches_strategy())
    @settings(max_examples=100)
    def test_predictions_sorted_by_match_date(self, scheduled):
        """
        Property 10: Predictions are sorted by match date.

        For any set of prediction results with varying match dates,
        the output DataFrame SHALL be sorted by match_date in ascending order.

        Validates: Requirements 6.4
        """
        # Build a full API response with fixed finished matches + generated scheduled
        api_response = {"matches": _FIXED_FINISHED_MATCHES + scheduled}

        predictor = Predictor(api_key="test-key")

        # Mock the API client to return our generated response
        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        # Assert output is not empty (we have scheduled matches)
        assert len(result) == len(scheduled)

        # Assert output DataFrame is sorted by match_date ascending
        match_dates = result["match_date"].tolist()
        assert match_dates == sorted(match_dates), (
            f"Predictions not sorted by match_date ascending. "
            f"Got dates: {match_dates}"
        )


# Feature: world-cup-predictor, Property 9: Prediction output has correct shape
class TestPredictionOutputShape:
    """Property tests for prediction output shape."""

    @given(scheduled=scheduled_matches_strategy())
    @settings(max_examples=100)
    def test_prediction_output_has_correct_shape(self, scheduled):
        """
        Property 9: Prediction output has correct shape.

        For any list of N upcoming matches provided for prediction, the Predictor SHALL
        produce a DataFrame with exactly N rows, each containing home_team_id,
        away_team_id, home_win_prob, and home_loss_prob columns.

        Validates: Requirements 6.2, 6.3
        """
        # Build a full API response with fixed finished matches + generated scheduled
        api_response = {"matches": _FIXED_FINISHED_MATCHES + scheduled}

        predictor = Predictor(api_key="test-key")

        # Mock the API client to return our generated response
        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        # Assert: result is a DataFrame
        assert isinstance(result, pd.DataFrame)

        # Assert: output DataFrame has exactly N rows for N scheduled matches
        assert len(result) == len(scheduled), (
            f"Expected {len(scheduled)} rows, got {len(result)}"
        )

        # Assert: columns include home_team_id, away_team_id, home_win_prob, home_loss_prob
        required_columns = {"home_team_id", "away_team_id", "home_win_prob", "home_loss_prob"}
        assert required_columns.issubset(set(result.columns)), (
            f"Missing columns: {required_columns - set(result.columns)}"
        )


# =============================================================================
# Integration Tests for Full Pipeline
# =============================================================================

import pytest
from unittest.mock import patch, MagicMock

from src.exceptions import (
    APIError,
    AuthenticationError,
    NoTrainingDataError,
    RateLimitError,
    InsufficientDataError,
)
from src.predictor import PREDICTION_COLUMNS


class TestPredictorIntegrationFullPipeline:
    """Integration tests for the complete prediction pipeline."""

    def _build_api_response(self, finished_matches, scheduled_matches=None):
        """Helper to build a full API response dict."""
        matches = list(finished_matches)
        if scheduled_matches:
            matches.extend(scheduled_matches)
        return {"matches": matches}

    def test_complete_pipeline_produces_valid_predictions(self):
        """
        Test complete pipeline with a mix of finished + scheduled matches
        produces a valid prediction output DataFrame.

        Validates: Requirements 7.1, 7.2
        """
        scheduled = [
            _make_scheduled_match(101, 100, 300, "2023-01-15T18:00:00Z"),
            _make_scheduled_match(102, 200, 400, "2023-01-16T20:00:00Z"),
            _make_scheduled_match(103, 300, 200, "2023-01-14T15:00:00Z"),
        ]
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES, scheduled)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        # Should return a DataFrame with 3 rows (one per scheduled match)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_output_dataframe_has_correct_columns(self):
        """
        Test output DataFrame has correct columns:
        home_team_id, away_team_id, home_win_prob, home_loss_prob, match_date.

        Validates: Requirements 6.2, 6.3
        """
        scheduled = [
            _make_scheduled_match(101, 100, 300, "2023-02-10T18:00:00Z"),
        ]
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES, scheduled)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        expected_columns = set(PREDICTION_COLUMNS)
        assert set(result.columns) == expected_columns, (
            f"Expected columns {expected_columns}, got {set(result.columns)}"
        )

    def test_output_sorted_by_match_date_ascending(self):
        """
        Test output is sorted by match_date ascending.

        Validates: Requirements 6.4
        """
        # Schedule matches in intentionally non-sorted order
        scheduled = [
            _make_scheduled_match(101, 100, 300, "2023-03-20T18:00:00Z"),
            _make_scheduled_match(102, 200, 400, "2023-03-10T15:00:00Z"),
            _make_scheduled_match(103, 300, 200, "2023-03-25T20:00:00Z"),
            _make_scheduled_match(104, 400, 100, "2023-03-05T12:00:00Z"),
        ]
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES, scheduled)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        match_dates = result["match_date"].tolist()
        assert match_dates == sorted(match_dates), (
            "Output DataFrame is not sorted by match_date ascending."
        )

    def test_no_scheduled_matches_returns_empty_dataframe(self):
        """
        Test that when no scheduled matches exist, an empty DataFrame is returned.

        Validates: Requirements 7.3
        """
        # Only finished matches, no scheduled ones
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert set(result.columns) == set(PREDICTION_COLUMNS)

    def test_no_finished_matches_raises_no_training_data_error(self):
        """
        Test that when no finished matches exist, NoTrainingDataError is raised.

        Validates: Requirements 7.4
        """
        # Only scheduled matches, no finished ones
        scheduled = [
            _make_scheduled_match(101, 100, 300, "2023-01-15T18:00:00Z"),
            _make_scheduled_match(102, 200, 400, "2023-01-16T20:00:00Z"),
        ]
        api_response = {"matches": scheduled}

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            with pytest.raises(NoTrainingDataError):
                predictor.run(competition_id=2000)

    def test_api_error_propagates(self):
        """
        Test error propagation: APIError from the API client propagates to caller.

        Validates: Requirements 7.5
        """
        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client,
            "get_matches",
            side_effect=APIError(500, "Internal Server Error"),
        ):
            with pytest.raises(APIError) as exc_info:
                predictor.run(competition_id=2000)
            assert exc_info.value.status_code == 500

    def test_authentication_error_propagates(self):
        """
        Test error propagation: AuthenticationError propagates to caller.

        Validates: Requirements 7.5
        """
        predictor = Predictor(api_key="invalid-key")

        with patch.object(
            predictor._api_client,
            "get_matches",
            side_effect=AuthenticationError(401, "Invalid API key"),
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                predictor.run(competition_id=2000)
            assert exc_info.value.status_code == 401

    def test_rate_limit_error_propagates(self):
        """
        Test error propagation: RateLimitError propagates to caller.

        Validates: Requirements 7.5
        """
        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client,
            "get_matches",
            side_effect=RateLimitError(429, "Rate limit exceeded after 3 retries"),
        ):
            with pytest.raises(RateLimitError) as exc_info:
                predictor.run(competition_id=2000)
            assert exc_info.value.status_code == 429

    def test_prediction_probabilities_are_valid(self):
        """
        Test that predicted probabilities are in [0, 1] and sum to 1.0.

        Validates: Requirements 6.1
        """
        scheduled = [
            _make_scheduled_match(101, 100, 200, "2023-04-01T18:00:00Z"),
            _make_scheduled_match(102, 300, 400, "2023-04-02T20:00:00Z"),
        ]
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES, scheduled)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        for _, row in result.iterrows():
            assert 0.0 <= row["home_win_prob"] <= 1.0
            assert 0.0 <= row["home_loss_prob"] <= 1.0
            assert abs(row["home_win_prob"] + row["home_loss_prob"] - 1.0) < 1e-7

    def test_output_contains_correct_team_ids(self):
        """
        Test that prediction output contains the correct team IDs from scheduled matches.

        Validates: Requirements 6.2
        """
        scheduled = [
            _make_scheduled_match(101, 100, 300, "2023-05-01T18:00:00Z"),
            _make_scheduled_match(102, 200, 400, "2023-05-02T20:00:00Z"),
        ]
        api_response = self._build_api_response(_FIXED_FINISHED_MATCHES, scheduled)

        predictor = Predictor(api_key="test-key")

        with patch.object(
            predictor._api_client, "get_matches", return_value=api_response
        ):
            result = predictor.run(competition_id=2000)

        # Sorted by date, so first row should be 100 vs 300
        assert result.iloc[0]["home_team_id"] == 100
        assert result.iloc[0]["away_team_id"] == 300
        assert result.iloc[1]["home_team_id"] == 200
        assert result.iloc[1]["away_team_id"] == 400
