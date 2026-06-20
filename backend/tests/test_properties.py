"""Property-based tests for the World Cup Predictor backend.

Uses Hypothesis to verify universal correctness properties of the service layer.
"""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# --- Strategies ---

# Group letters for World Cup 2026 (12 groups)
GROUP_LETTERS = list("ABCDEFGHIJKL")


@st.composite
def standings_team_strategy(draw):
    """Generate a single team entry in a standings table."""
    team_id = draw(st.integers(min_value=1, max_value=99999))
    team_name = draw(st.text(
        min_size=1, max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N", "Z"))
    ))
    crest = draw(st.one_of(
        st.just(""),
        st.text(
            min_size=1, max_size=100,
            alphabet=st.characters(whitelist_categories=("L", "N"))
        ).map(lambda s: f"https://crests.football-data.org/{s}.svg"),
    ))
    return {"id": team_id, "name": team_name, "crest": crest}


@st.composite
def standings_api_response_strategy(draw):
    """Generate a valid standings API response with 12 groups, each with 4 teams.

    Produces the structure expected from football-data.org standings endpoint.
    """
    standings = []
    for letter in GROUP_LETTERS:
        teams = [draw(standings_team_strategy()) for _ in range(4)]
        table = [
            {"position": pos + 1, "team": team}
            for pos, team in enumerate(teams)
        ]
        standings.append({
            "stage": "GROUP_STAGE",
            "type": "TOTAL",
            "group": f"GROUP_{letter}",
            "table": table,
        })
    return {"standings": standings}


# --- Strategies for Knockout Tests ---

KNOCKOUT_STAGES = ["ROUND_OF_32", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
MATCH_STATUSES = ["SCHEDULED", "TIMED", "IN_PLAY", "FINISHED"]


@st.composite
def knockout_team_strategy(draw):
    """Generate a knockout team that is either determined (has id/name/crest) or undetermined (all None)."""
    is_determined = draw(st.booleans())
    if is_determined:
        team_id = draw(st.integers(min_value=1, max_value=99999))
        team_name = draw(
            st.text(
                min_size=1,
                max_size=30,
                alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
            ).filter(lambda s: s.strip())
        )
        crest = draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("L", "N")),
            ).map(lambda s: f"https://crests.football-data.org/{s}.svg")
        )
        return {"id": team_id, "name": team_name, "crest": crest}
    else:
        return {"id": None, "name": None, "crest": None}


@st.composite
def knockout_match_strategy(draw):
    """Generate a single knockout match with random stage, teams, status, and score."""
    stage = draw(st.sampled_from(KNOCKOUT_STAGES))
    home_team = draw(knockout_team_strategy())
    away_team = draw(knockout_team_strategy())
    status = draw(st.sampled_from(MATCH_STATUSES))

    if status == "FINISHED":
        home_score = draw(st.integers(min_value=0, max_value=10))
        away_score = draw(st.integers(min_value=0, max_value=10))
    else:
        home_score = None
        away_score = None

    return {
        "stage": stage,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "status": status,
        "score": {"fullTime": {"home": home_score, "away": away_score}},
    }


@st.composite
def knockout_api_response_strategy(draw):
    """Generate a knockout matches API response with 1-20 random matches."""
    num_matches = draw(st.integers(min_value=1, max_value=20))
    matches = [draw(knockout_match_strategy()) for _ in range(num_matches)]
    return {"matches": matches}


class TestProperty4KnockoutTeamResolution:
    """Property 4: Knockout match team resolution.

    For any knockout match in the API response, if both home and away team IDs
    are present, the output SHALL include actual team_name and crest values;
    if either team ID is null or missing, the output SHALL use "TBD" for
    team_name and "" for crest. Every match object SHALL include a status field.

    **Validates: Requirements 4.3, 4.4, 4.5**
    """

    @given(api_response=knockout_api_response_strategy())
    @settings(max_examples=100, deadline=None)
    def test_knockout_team_resolution(self, api_response):
        """Assert determined teams have actual names/crests, undetermined teams get TBD/"", and status is always present.

        **Validates: Requirements 4.3, 4.4, 4.5**
        """
        from backend.services import get_knockout_data

        with patch("backend.services.os.getenv", return_value="fake-api-key"):
            with patch("backend.services.APIClient") as MockAPIClient:
                mock_instance = MagicMock()
                mock_instance.get_matches.return_value = api_response
                MockAPIClient.return_value = mock_instance

                result = get_knockout_data()

        # Build a lookup of input matches by their original data for validation
        input_matches = api_response["matches"]

        # Collect all output matches across all rounds
        output_matches = []
        for round_obj in result.rounds:
            output_matches.extend(round_obj.matches)

        # The number of output matches should equal the number of knockout-stage input matches
        knockout_input_matches = [
            m for m in input_matches if m["stage"] in KNOCKOUT_STAGES
        ]
        assert len(output_matches) == len(knockout_input_matches), (
            f"Expected {len(knockout_input_matches)} output matches, got {len(output_matches)}"
        )

        # The service groups matches by round in a fixed order, so we must
        # reorder input matches to match the output ordering.
        from backend.services import KNOCKOUT_STAGE_MAP, KNOCKOUT_ROUND_ORDER

        round_order_index = {name: i for i, name in enumerate(KNOCKOUT_ROUND_ORDER)}

        # Group input matches by round, preserving insertion order within each round
        ordered_input_matches = sorted(
            knockout_input_matches,
            key=lambda m: round_order_index.get(KNOCKOUT_STAGE_MAP.get(m["stage"], ""), 99),
        )

        # Validate each output match against its corresponding input
        for input_match, output_match in zip(ordered_input_matches, output_matches):

            # Check home team resolution
            home_input = input_match["homeTeam"]
            if home_input.get("id") is not None:
                # Determined team: should have actual name and crest
                assert output_match.home_team.team_name != "TBD", (
                    f"Determined home team should not be TBD, input: {home_input}"
                )
                assert output_match.home_team.crest != "", (
                    f"Determined home team should not have empty crest, input: {home_input}"
                )
            else:
                # Undetermined team: should be TBD with empty crest
                assert output_match.home_team.team_name == "TBD", (
                    f"Undetermined home team should be TBD, got: {output_match.home_team.team_name}"
                )
                assert output_match.home_team.crest == "", (
                    f"Undetermined home team should have empty crest, got: {output_match.home_team.crest}"
                )

            # Check away team resolution
            away_input = input_match["awayTeam"]
            if away_input.get("id") is not None:
                # Determined team: should have actual name and crest
                assert output_match.away_team.team_name != "TBD", (
                    f"Determined away team should not be TBD, input: {away_input}"
                )
                assert output_match.away_team.crest != "", (
                    f"Determined away team should not have empty crest, input: {away_input}"
                )
            else:
                # Undetermined team: should be TBD with empty crest
                assert output_match.away_team.team_name == "TBD", (
                    f"Undetermined away team should be TBD, got: {output_match.away_team.team_name}"
                )
                assert output_match.away_team.crest == "", (
                    f"Undetermined away team should have empty crest, got: {output_match.away_team.crest}"
                )

            # Every match must have a non-empty status field
            assert output_match.status, (
                f"Match status should be non-empty, got: '{output_match.status}'"
            )
            assert len(output_match.status) > 0, (
                f"Match status should be non-empty string"
            )


# --- Property Tests ---


@pytest.mark.property
class TestGroupsTransformationProperty:
    """Property 1: Groups transformation produces complete team data.

    For any valid standings API response containing groups with teams,
    the get_group_data() service function SHALL return groups labeled A through L,
    each containing exactly 4 teams, where every team object includes a non-null
    team_id, team_name, and crest field.

    **Validates: Requirements 1.2, 2.2, 2.3**
    """

    @given(standings_response=standings_api_response_strategy())
    @settings(max_examples=100, deadline=None)
    def test_groups_transformation_produces_complete_team_data(self, standings_response):
        """Property 1: Groups transformation produces complete team data.

        **Validates: Requirements 1.2, 2.2, 2.3**
        """
        from backend.services import get_group_data

        with patch("backend.services._fetch_standings", return_value=standings_response):
            result = get_group_data()

        groups = result["groups"]

        # Must have exactly 12 groups (A through L)
        assert len(groups) == 12, f"Expected 12 groups, got {len(groups)}"

        # Groups must be labeled A through L
        group_names = [g["group_name"] for g in groups]
        assert group_names == sorted(GROUP_LETTERS), (
            f"Expected groups A-L, got {group_names}"
        )

        for group in groups:
            # Each group must have exactly 4 teams
            assert len(group["teams"]) == 4, (
                f"Group {group['group_name']} has {len(group['teams'])} teams, expected 4"
            )

            for team in group["teams"]:
                # Every team must have non-null team_id
                assert team["team_id"] is not None, (
                    f"team_id is None in group {group['group_name']}"
                )
                assert isinstance(team["team_id"], int), (
                    f"team_id is not int: {type(team['team_id'])}"
                )

                # Every team must have non-null team_name
                assert team["team_name"] is not None, (
                    f"team_name is None in group {group['group_name']}"
                )
                assert isinstance(team["team_name"], str), (
                    f"team_name is not str: {type(team['team_name'])}"
                )
                assert len(team["team_name"]) > 0, (
                    f"team_name is empty in group {group['group_name']}"
                )

                # Every team must have non-null crest (can be empty string)
                assert team["crest"] is not None, (
                    f"crest is None in group {group['group_name']}"
                )
                assert isinstance(team["crest"], str), (
                    f"crest is not str: {type(team['crest'])}"
                )


# --- Knockout Match Strategies (for Property 5) ---

# Non-FINISHED statuses
NON_FINISHED_STATUSES = ["SCHEDULED", "TIMED", "IN_PLAY"]


@st.composite
def knockout_match_with_scores_strategy(draw):
    """Generate a single knockout match with appropriate scores based on status.

    FINISHED matches get valid integer scores.
    Non-FINISHED matches have no scores.
    """
    stage = draw(st.sampled_from(KNOCKOUT_STAGES))
    is_finished = draw(st.booleans())

    # Build team data - always provide valid teams so they get processed
    home_team = {
        "id": draw(st.integers(min_value=1, max_value=99999)),
        "name": draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",)))),
        "crest": f"https://crests.football-data.org/{draw(st.integers(min_value=1, max_value=9999))}.svg",
    }
    away_team = {
        "id": draw(st.integers(min_value=1, max_value=99999)),
        "name": draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",)))),
        "crest": f"https://crests.football-data.org/{draw(st.integers(min_value=1, max_value=9999))}.svg",
    }

    if is_finished:
        status = "FINISHED"
        home_score = draw(st.integers(min_value=0, max_value=15))
        away_score = draw(st.integers(min_value=0, max_value=15))
        score = {"fullTime": {"home": home_score, "away": away_score}}
    else:
        status = draw(st.sampled_from(NON_FINISHED_STATUSES))
        score = {"fullTime": {"home": None, "away": None}}

    return {
        "stage": stage,
        "status": status,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "score": score,
    }


@st.composite
def knockout_matches_api_response_strategy(draw):
    """Generate a valid matches API response with knockout matches."""
    matches = draw(st.lists(knockout_match_with_scores_strategy(), min_size=1, max_size=20))
    return {"matches": matches}


# --- Property 5 Test ---


@pytest.mark.property
class TestFinishedKnockoutMatchScoresProperty:
    """Property 5: Finished knockout matches include scores.

    For any knockout match with status == "FINISHED", the output SHALL include
    non-null home_score and away_score integer values. For any match with status
    other than "FINISHED", home_score and away_score SHALL be null.

    **Validates: Requirements 4.6**
    """

    @given(matches_response=knockout_matches_api_response_strategy())
    @settings(max_examples=100)
    def test_finished_matches_have_scores_non_finished_have_null(self, matches_response):
        """Property 5: Finished knockout matches include scores.

        **Validates: Requirements 4.6**
        """
        from backend.services import get_knockout_data

        mock_client = MagicMock()
        mock_client.get_matches.return_value = matches_response

        with patch("backend.services.os.getenv", return_value="fake-api-key"), \
             patch("backend.services.APIClient", return_value=mock_client):
            result = get_knockout_data()

        # Collect all matches from all rounds
        all_matches = []
        for round_obj in result.rounds:
            all_matches.extend(round_obj.matches)

        # We should have at least one match processed (our strategy generates >= 1)
        assert len(all_matches) > 0, "Expected at least one knockout match"

        for match in all_matches:
            if match.status == "FINISHED":
                # FINISHED matches must have non-null integer scores
                assert match.home_score is not None, (
                    f"FINISHED match has null home_score"
                )
                assert match.away_score is not None, (
                    f"FINISHED match has null away_score"
                )
                assert isinstance(match.home_score, int), (
                    f"home_score is not int: {type(match.home_score)}"
                )
                assert isinstance(match.away_score, int), (
                    f"away_score is not int: {type(match.away_score)}"
                )
            else:
                # Non-FINISHED matches must have null scores
                assert match.home_score is None, (
                    f"Non-FINISHED match (status={match.status}) has non-null home_score: {match.home_score}"
                )
                assert match.away_score is None, (
                    f"Non-FINISHED match (status={match.status}) has non-null away_score: {match.away_score}"
                )


# --- Strategies for Predictions (Property 2) ---

REQUIRED_PREDICTION_FIELDS = [
    "home_team_name",
    "away_team_name",
    "home_win_prob",
    "home_loss_prob",
    "home_team_crest",
    "away_team_crest",
    "match_date",
]


@st.composite
def prediction_dataframe_strategy(draw):
    """Generate random DataFrames matching PREDICTION_COLUMNS schema.

    The DataFrame is sorted by match_date ascending to match the Predictor's
    documented contract (Predictor.run() returns sorted data).
    """
    n_rows = draw(st.integers(min_value=0, max_value=20))

    if n_rows == 0:
        return pd.DataFrame(columns=[
            "home_team_name", "away_team_name", "home_win_prob",
            "home_loss_prob", "match_date", "home_team_id",
            "away_team_id", "home_team_crest", "away_team_crest",
        ])

    home_team_names = draw(st.lists(
        st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N", "Z"))),
        min_size=n_rows, max_size=n_rows,
    ))
    away_team_names = draw(st.lists(
        st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N", "Z"))),
        min_size=n_rows, max_size=n_rows,
    ))
    home_win_probs = draw(st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_rows, max_size=n_rows,
    ))
    home_loss_probs = draw(st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=n_rows, max_size=n_rows,
    ))
    match_dates = draw(st.lists(
        st.datetimes(
            min_value=datetime(2025, 1, 1),
            max_value=datetime(2026, 12, 31),
        ),
        min_size=n_rows, max_size=n_rows,
    ))
    home_team_ids = draw(st.lists(
        st.integers(min_value=1, max_value=10000),
        min_size=n_rows, max_size=n_rows,
    ))
    away_team_ids = draw(st.lists(
        st.integers(min_value=1, max_value=10000),
        min_size=n_rows, max_size=n_rows,
    ))
    home_team_crests = draw(st.lists(
        st.text(min_size=0, max_size=50, alphabet=st.characters(categories=("L", "N", "P"))),
        min_size=n_rows, max_size=n_rows,
    ))
    away_team_crests = draw(st.lists(
        st.text(min_size=0, max_size=50, alphabet=st.characters(categories=("L", "N", "P"))),
        min_size=n_rows, max_size=n_rows,
    ))

    df = pd.DataFrame({
        "home_team_name": home_team_names,
        "away_team_name": away_team_names,
        "home_win_prob": home_win_probs,
        "home_loss_prob": home_loss_probs,
        "match_date": match_dates,
        "home_team_id": home_team_ids,
        "away_team_id": away_team_ids,
        "home_team_crest": home_team_crests,
        "away_team_crest": away_team_crests,
    })

    # Sort by match_date ascending to match the Predictor's contract
    df = df.sort_values("match_date", ascending=True).reset_index(drop=True)

    return df


# --- Property 2 Test ---


@pytest.mark.property
class TestPredictionsFieldCompletenessAndSortOrder:
    """Property 2: Predictions response preserves field completeness and sort order.

    For any non-empty DataFrame returned by Predictor.run(), the predictions
    transformation SHALL produce a list of prediction objects each containing
    home_team_name, away_team_name, home_win_prob, home_loss_prob,
    home_team_crest, away_team_crest, and match_date, and the list SHALL be
    sorted by match_date in ascending order.

    **Validates: Requirements 1.3, 3.2, 3.3**
    """

    @given(df=prediction_dataframe_strategy())
    @settings(max_examples=100, deadline=None)
    def test_predictions_field_completeness_and_sort_order(self, df: pd.DataFrame):
        """Property 2: Predictions response preserves field completeness and sort order.

        **Validates: Requirements 1.3, 3.2, 3.3**
        """
        from backend.services import get_predictions

        with patch("backend.services._get_api_key", return_value="fake-api-key"), \
             patch("src.predictor.Predictor.run", return_value=df):
            response = get_predictions()

        predictions = response.predictions

        if df.empty:
            # Edge case: empty DataFrame should return empty predictions list
            assert predictions == []
            return

        # All predictions must have all required fields
        for pred in predictions:
            pred_dict = pred.model_dump()
            for field in REQUIRED_PREDICTION_FIELDS:
                assert field in pred_dict, f"Missing field: {field}"
                assert pred_dict[field] is not None, f"Field {field} is None"

        # Predictions must be sorted by match_date ascending
        if len(predictions) > 1:
            dates = [pred.match_date for pred in predictions]
            for i in range(len(dates) - 1):
                assert dates[i] <= dates[i + 1], (
                    f"Predictions not sorted by match_date: {dates[i]} > {dates[i + 1]}"
                )


# --- Strategies for API Error Mapping (Property 6) ---


@st.composite
def api_exception_strategy(draw):
    """Generate random API exception instances for error mapping testing.

    Produces instances of AuthenticationError, RateLimitError, APIError,
    NoTrainingDataError, KeyError, and ValueError with random parameters.
    """
    from src.exceptions import APIError, AuthenticationError, NoTrainingDataError, RateLimitError

    message = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))))

    exception_type = draw(st.sampled_from([
        "AuthenticationError",
        "RateLimitError",
        "APIError",
        "NoTrainingDataError",
        "KeyError",
        "ValueError",
    ]))

    if exception_type == "AuthenticationError":
        status_code = draw(st.sampled_from([401, 403]))
        return AuthenticationError(status_code, message)
    elif exception_type == "RateLimitError":
        status_code = 429
        return RateLimitError(status_code, message)
    elif exception_type == "APIError":
        status_code = draw(st.integers(min_value=400, max_value=599))
        return APIError(status_code, message)
    elif exception_type == "NoTrainingDataError":
        return NoTrainingDataError(message)
    elif exception_type == "KeyError":
        key = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))))
        return KeyError(key)
    elif exception_type == "ValueError":
        return ValueError(message)


# --- Property 6 Test ---


@pytest.mark.property
class TestAPIErrorMappingProperty:
    """Property 6: API error mapping.

    For any error raised by the APIClient (including AuthenticationError,
    RateLimitError, and generic APIError), the Backend SHALL return an HTTP
    error response with a status code >= 400 and a JSON body containing a
    descriptive detail message.

    **Validates: Requirements 1.6**
    """

    @given(exception=api_exception_strategy())
    @settings(max_examples=100)
    def test_api_error_mapping_produces_http_error(self, exception):
        """Property 6: All API exceptions map to HTTP errors with status >= 400 and a detail message.

        **Validates: Requirements 1.6**
        """
        from fastapi import HTTPException

        from backend.error_handling import handle_api_error

        result = handle_api_error(exception)

        # Result must be an HTTPException
        assert isinstance(result, HTTPException), (
            f"Expected HTTPException, got {type(result)} for {type(exception).__name__}"
        )

        # Status code must be >= 400 (client or server error)
        assert result.status_code >= 400, (
            f"Expected status >= 400, got {result.status_code} for {type(exception).__name__}"
        )

        # Detail must be a non-empty string
        assert isinstance(result.detail, str), (
            f"Expected detail to be a string, got {type(result.detail)} for {type(exception).__name__}"
        )
        assert len(result.detail) > 0, (
            f"Expected non-empty detail message for {type(exception).__name__}"
        )
