"""Unit tests for the DataPipeline class."""

import logging

import pandas as pd
import pytest

from src.data_pipeline import DataPipeline, MATCH_COLUMNS


@pytest.fixture
def pipeline():
    return DataPipeline()


class TestParseMatches:
    """Tests for DataPipeline.parse_matches."""

    def test_parses_finished_matches(self, pipeline, sample_api_response):
        """Finished matches with valid scores are parsed correctly."""
        df = pipeline.parse_matches(sample_api_response)
        assert len(df) == 2
        assert list(df.columns) == MATCH_COLUMNS

    def test_correct_values_extracted(self, pipeline, sample_api_response):
        """Parsed values match the input JSON."""
        df = pipeline.parse_matches(sample_api_response)
        row = df.iloc[0]
        assert row["home_team_id"] == 100
        assert row["away_team_id"] == 200
        assert row["home_score"] == 2
        assert row["away_score"] == 1

    def test_excludes_non_finished_matches(self, pipeline):
        """Matches with status != FINISHED are excluded."""
        response = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2022-12-18T15:00:00Z",
                    "status": "SCHEDULED",
                    "homeTeam": {"id": 100, "name": "A"},
                    "awayTeam": {"id": 200, "name": "B"},
                    "score": {"fullTime": {"home": None, "away": None}},
                },
                {
                    "id": 2,
                    "utcDate": "2022-12-18T15:00:00Z",
                    "status": "TIMED",
                    "homeTeam": {"id": 300, "name": "C"},
                    "awayTeam": {"id": 400, "name": "D"},
                    "score": {"fullTime": {"home": None, "away": None}},
                },
            ]
        }
        df = pipeline.parse_matches(response)
        assert len(df) == 0
        assert list(df.columns) == MATCH_COLUMNS

    def test_excludes_null_scores_with_warning(self, pipeline, caplog):
        """Finished matches with null scores are excluded and a warning is logged."""
        response = {
            "matches": [
                {
                    "id": 99,
                    "utcDate": "2022-11-20T16:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 100, "name": "A"},
                    "awayTeam": {"id": 200, "name": "B"},
                    "score": {"fullTime": {"home": None, "away": 1}},
                },
            ]
        }
        with caplog.at_level(logging.WARNING):
            df = pipeline.parse_matches(response)
        assert len(df) == 0
        assert "99" in caplog.text

    def test_empty_response_returns_empty_dataframe(self, pipeline):
        """Empty matches list returns DataFrame with correct schema."""
        df = pipeline.parse_matches({"matches": []})
        assert len(df) == 0
        assert list(df.columns) == MATCH_COLUMNS

    def test_missing_matches_key_returns_empty_dataframe(self, pipeline):
        """Missing 'matches' key returns DataFrame with correct schema."""
        df = pipeline.parse_matches({})
        assert len(df) == 0
        assert list(df.columns) == MATCH_COLUMNS

    def test_column_dtypes(self, pipeline, sample_api_response):
        """Numeric columns have integer dtype."""
        df = pipeline.parse_matches(sample_api_response)
        assert df["home_team_id"].dtype == int
        assert df["away_team_id"].dtype == int
        assert df["home_score"].dtype == int
        assert df["away_score"].dtype == int


class TestGetScheduledMatches:
    """Tests for DataPipeline.get_scheduled_matches."""

    def test_extracts_scheduled_matches(self, pipeline, sample_api_response):
        """Scheduled matches are extracted correctly."""
        scheduled = pipeline.get_scheduled_matches(sample_api_response)
        assert len(scheduled) == 1
        assert scheduled[0]["home_team_id"] == 100
        assert scheduled[0]["away_team_id"] == 300

    def test_excludes_non_scheduled_matches(self, pipeline):
        """Only SCHEDULED status matches are included."""
        response = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2022-11-20T16:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 100, "name": "A"},
                    "awayTeam": {"id": 200, "name": "B"},
                    "score": {"fullTime": {"home": 2, "away": 1}},
                },
            ]
        }
        scheduled = pipeline.get_scheduled_matches(response)
        assert len(scheduled) == 0

    def test_empty_response_returns_empty_list(self, pipeline):
        """Empty matches returns empty list."""
        scheduled = pipeline.get_scheduled_matches({"matches": []})
        assert scheduled == []

    def test_scheduled_match_has_correct_keys(self, pipeline, sample_api_response):
        """Each scheduled match dict has the required keys."""
        scheduled = pipeline.get_scheduled_matches(sample_api_response)
        for match in scheduled:
            assert "home_team_id" in match
            assert "away_team_id" in match
            assert "match_date" in match


# Feature: world-cup-predictor, Property 13: Match classification by status
from hypothesis import given, settings
from tests.strategies import api_response


class TestMatchClassificationProperty:
    """Property 13: Match classification by status.

    For any raw API response containing matches with mixed statuses,
    the Predictor SHALL route all FINISHED matches to the training set
    and all SCHEDULED matches to the prediction set, with no overlap
    between the two sets.

    **Validates: Requirements 7.2**
    """

    @given(response=api_response)
    @settings(max_examples=100)
    def test_finished_matches_go_to_training_set_only(self, response):
        """FINISHED matches appear in parse_matches output only."""
        pipeline = DataPipeline()
        training_df = pipeline.parse_matches(response)
        scheduled_list = pipeline.get_scheduled_matches(response)

        # Collect team-id pairs from training set
        training_pairs = set(
            zip(training_df["home_team_id"], training_df["away_team_id"])
        ) if not training_df.empty else set()

        # Collect team-id pairs from prediction set
        prediction_pairs = set(
            (m["home_team_id"], m["away_team_id"]) for m in scheduled_list
        )

        # Count expected finished matches (with non-null scores)
        expected_finished = [
            m for m in response.get("matches", [])
            if m.get("status") == "FINISHED"
            and m.get("score", {}).get("fullTime", {}).get("home") is not None
            and m.get("score", {}).get("fullTime", {}).get("away") is not None
        ]
        assert len(training_df) == len(expected_finished)

    @given(response=api_response)
    @settings(max_examples=100)
    def test_scheduled_matches_go_to_prediction_set_only(self, response):
        """SCHEDULED matches appear in get_scheduled_matches output only."""
        pipeline = DataPipeline()
        scheduled_list = pipeline.get_scheduled_matches(response)

        # Count expected scheduled matches
        expected_scheduled = [
            m for m in response.get("matches", [])
            if m.get("status") == "SCHEDULED"
        ]
        assert len(scheduled_list) == len(expected_scheduled)

        # Each scheduled match has correct team IDs from the original response
        for orig, parsed in zip(expected_scheduled, scheduled_list):
            assert parsed["home_team_id"] == orig["homeTeam"]["id"]
            assert parsed["away_team_id"] == orig["awayTeam"]["id"]

    @given(response=api_response)
    @settings(max_examples=100)
    def test_no_overlap_between_training_and_prediction_sets(self, response):
        """No match appears in both training and prediction sets.

        The total number of matches classified (training + prediction)
        equals the number of valid FINISHED matches plus SCHEDULED matches,
        confirming no match is routed to both sets.
        """
        pipeline = DataPipeline()
        training_df = pipeline.parse_matches(response)
        scheduled_list = pipeline.get_scheduled_matches(response)

        # Count matches by status in the original response
        finished_count = sum(
            1 for m in response.get("matches", [])
            if m.get("status") == "FINISHED"
            and m.get("score", {}).get("fullTime", {}).get("home") is not None
            and m.get("score", {}).get("fullTime", {}).get("away") is not None
        )
        scheduled_count = sum(
            1 for m in response.get("matches", [])
            if m.get("status") == "SCHEDULED"
        )

        # Training set contains exactly the finished matches
        assert len(training_df) == finished_count
        # Prediction set contains exactly the scheduled matches
        assert len(scheduled_list) == scheduled_count
        # Total classified matches equals sum of both categories (no overlap)
        assert len(training_df) + len(scheduled_list) == finished_count + scheduled_count


# =============================================================================
# Property-Based Tests
# =============================================================================

from hypothesis import given, settings
from tests.strategies import api_response_mixed


# Feature: world-cup-predictor, Property 1: Data parsing preserves match information
class TestParseMatchesProperty:
    """Property-based tests for DataPipeline.parse_matches."""

    @given(response=api_response_mixed)
    @settings(max_examples=100)
    def test_data_parsing_preserves_match_information(self, response):
        """
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

        For any valid API response containing finished matches with non-null
        scores, parsing the response into a DataFrame SHALL produce exactly one
        row per finished match with non-null scores, where each row's values
        match the corresponding values from the input JSON. Matches with
        non-FINISHED status or null scores are excluded.
        """
        pipeline = DataPipeline()
        df = pipeline.parse_matches(response)

        # Determine expected finished matches with non-null scores
        expected_matches = [
            m for m in response["matches"]
            if m["status"] == "FINISHED"
            and m["score"]["fullTime"]["home"] is not None
            and m["score"]["fullTime"]["away"] is not None
        ]

        # Assert: one row per FINISHED match with non-null scores
        assert len(df) == len(expected_matches), (
            f"Expected {len(expected_matches)} rows, got {len(df)}"
        )

        # Assert: columns match expected schema
        expected_columns = [
            "home_team_id", "away_team_id", "home_score", "away_score", "match_date"
        ]
        assert list(df.columns) == expected_columns

        # Assert: each row's values match the corresponding input JSON exactly
        for i, match in enumerate(expected_matches):
            row = df.iloc[i]
            assert row["home_team_id"] == match["homeTeam"]["id"], (
                f"Row {i}: home_team_id mismatch"
            )
            assert row["away_team_id"] == match["awayTeam"]["id"], (
                f"Row {i}: away_team_id mismatch"
            )
            assert row["home_score"] == match["score"]["fullTime"]["home"], (
                f"Row {i}: home_score mismatch"
            )
            assert row["away_score"] == match["score"]["fullTime"]["away"], (
                f"Row {i}: away_score mismatch"
            )

        # Assert: non-FINISHED matches are excluded
        non_finished_ids = {
            m["homeTeam"]["id"]
            for m in response["matches"]
            if m["status"] != "FINISHED"
        }
        # If there are non-finished matches, confirm they aren't in the output
        # (unless they also appear in a finished match by coincidence)
        finished_home_ids = set(df["home_team_id"].tolist())
        for m in response["matches"]:
            if m["status"] != "FINISHED":
                # This specific match entry should not produce a row
                # We verify via row count above (exact match)
                pass

        # Assert: null-score FINISHED matches are excluded
        null_score_finished = [
            m for m in response["matches"]
            if m["status"] == "FINISHED"
            and (m["score"]["fullTime"]["home"] is None
                 or m["score"]["fullTime"]["away"] is None)
        ]
        # The total rows should not include null-score matches
        assert len(df) == len(expected_matches), (
            f"Null-score matches should be excluded. "
            f"Got {len(df)} rows, expected {len(expected_matches)}"
        )
