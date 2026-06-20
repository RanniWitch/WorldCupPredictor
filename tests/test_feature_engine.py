"""Unit tests for the FeatureEngine class."""

import pandas as pd
import pytest

from src.feature_engine import FeatureEngine


@pytest.fixture
def engine():
    """Return a FeatureEngine instance."""
    return FeatureEngine()


@pytest.fixture
def simple_matches_df():
    """Return a simple DataFrame with known outcomes for manual verification."""
    return pd.DataFrame(
        {
            "home_team_id": [1, 2, 1],
            "away_team_id": [2, 1, 3],
            "home_score": [3, 1, 0],
            "away_score": [1, 2, 0],
            "match_date": pd.to_datetime(
                ["2022-11-20", "2022-11-21", "2022-11-22"]
            ),
        }
    )


class TestComputeFeatures:
    """Tests for FeatureEngine.compute_features."""

    def test_returns_dataframe_indexed_by_team_id(self, engine, simple_matches_df):
        result = engine.compute_features(simple_matches_df)
        assert result.index.name == "team_id"
        assert set(result.columns) == {
            "win_rate",
            "avg_goals_scored",
            "avg_goals_conceded",
        }

    def test_counts_both_home_and_away_appearances(self, engine, simple_matches_df):
        result = engine.compute_features(simple_matches_df)
        # Team 1: home in match 1 (3-1 win), away in match 2 (2-1 win), home in match 3 (0-0 draw)
        # Total matches for team 1: 3
        assert 1 in result.index
        # Team 2: away in match 1, home in match 2 -> 2 matches
        assert 2 in result.index
        # Team 3: away in match 3 -> 1 match
        assert 3 in result.index

    def test_win_rate_computation(self, engine, simple_matches_df):
        result = engine.compute_features(simple_matches_df)
        # Team 1: 3 matches, wins = match1 (home 3>1) + match2 (away 2>1) = 2 wins
        # win_rate = 2/3
        assert result.loc[1, "win_rate"] == pytest.approx(2 / 3)
        # Team 2: 2 matches, wins = 0 (lost match1 as away, lost match2 as home 1<2)
        assert result.loc[2, "win_rate"] == pytest.approx(0.0)
        # Team 3: 1 match, draw (0-0) -> 0 wins
        assert result.loc[3, "win_rate"] == pytest.approx(0.0)

    def test_avg_goals_scored(self, engine, simple_matches_df):
        result = engine.compute_features(simple_matches_df)
        # Team 1: scored 3 (home m1) + 2 (away m2) + 0 (home m3) = 5, avg = 5/3
        assert result.loc[1, "avg_goals_scored"] == pytest.approx(5 / 3)
        # Team 2: scored 1 (away m1) + 1 (home m2) = 2, avg = 2/2 = 1.0
        assert result.loc[2, "avg_goals_scored"] == pytest.approx(1.0)
        # Team 3: scored 0 (away m3), avg = 0/1 = 0.0
        assert result.loc[3, "avg_goals_scored"] == pytest.approx(0.0)

    def test_avg_goals_conceded(self, engine, simple_matches_df):
        result = engine.compute_features(simple_matches_df)
        # Team 1: conceded 1 (home m1, away_score) + 1 (away m2, home_score) + 0 (home m3, away_score) = 2, avg = 2/3
        assert result.loc[1, "avg_goals_conceded"] == pytest.approx(2 / 3)
        # Team 2: conceded 3 (away m1, home_score) + 2 (home m2, away_score) = 5, avg = 5/2 = 2.5
        assert result.loc[2, "avg_goals_conceded"] == pytest.approx(2.5)
        # Team 3: conceded 0 (away m3, home_score=0), avg = 0/1 = 0.0
        assert result.loc[3, "avg_goals_conceded"] == pytest.approx(0.0)

    def test_empty_dataframe_returns_empty_features(self, engine, empty_matches_df):
        result = engine.compute_features(empty_matches_df)
        assert result.empty
        assert result.index.name == "team_id"
        assert set(result.columns) == {
            "win_rate",
            "avg_goals_scored",
            "avg_goals_conceded",
        }

    def test_all_draws(self, engine):
        matches = pd.DataFrame(
            {
                "home_team_id": [1, 2],
                "away_team_id": [2, 1],
                "home_score": [1, 1],
                "away_score": [1, 1],
                "match_date": pd.to_datetime(["2022-01-01", "2022-01-02"]),
            }
        )
        result = engine.compute_features(matches)
        assert result.loc[1, "win_rate"] == pytest.approx(0.0)
        assert result.loc[2, "win_rate"] == pytest.approx(0.0)


class TestGetMatchFeatures:
    """Tests for FeatureEngine.get_match_features."""

    def test_returns_correct_columns(self, engine, simple_matches_df):
        features_df = engine.compute_features(simple_matches_df)
        result = engine.get_match_features(1, 2, features_df)
        expected_cols = {
            "home_win_rate",
            "home_avg_goals_scored",
            "home_avg_goals_conceded",
            "away_win_rate",
            "away_avg_goals_scored",
            "away_avg_goals_conceded",
        }
        assert set(result.columns) == expected_cols

    def test_returns_single_row(self, engine, simple_matches_df):
        features_df = engine.compute_features(simple_matches_df)
        result = engine.get_match_features(1, 2, features_df)
        assert len(result) == 1

    def test_known_teams_use_computed_features(self, engine, simple_matches_df):
        features_df = engine.compute_features(simple_matches_df)
        result = engine.get_match_features(1, 2, features_df)
        # Team 1 as home: win_rate=2/3, avg_goals_scored=5/3, avg_goals_conceded=2/3
        assert result.iloc[0]["home_win_rate"] == pytest.approx(2 / 3)
        assert result.iloc[0]["home_avg_goals_scored"] == pytest.approx(5 / 3)
        assert result.iloc[0]["home_avg_goals_conceded"] == pytest.approx(2 / 3)
        # Team 2 as away: win_rate=0, avg_goals_scored=1.0, avg_goals_conceded=2.5
        assert result.iloc[0]["away_win_rate"] == pytest.approx(0.0)
        assert result.iloc[0]["away_avg_goals_scored"] == pytest.approx(1.0)
        assert result.iloc[0]["away_avg_goals_conceded"] == pytest.approx(2.5)

    def test_unknown_home_team_uses_defaults(self, engine, simple_matches_df):
        features_df = engine.compute_features(simple_matches_df)
        result = engine.get_match_features(999, 1, features_df)
        assert result.iloc[0]["home_win_rate"] == 0.5
        assert result.iloc[0]["home_avg_goals_scored"] == 0.0
        assert result.iloc[0]["home_avg_goals_conceded"] == 0.0

    def test_unknown_away_team_uses_defaults(self, engine, simple_matches_df):
        features_df = engine.compute_features(simple_matches_df)
        result = engine.get_match_features(1, 999, features_df)
        assert result.iloc[0]["away_win_rate"] == 0.5
        assert result.iloc[0]["away_avg_goals_scored"] == 0.0
        assert result.iloc[0]["away_avg_goals_conceded"] == 0.0

    def test_both_teams_unknown_uses_defaults(self, engine):
        features_df = pd.DataFrame(
            columns=["win_rate", "avg_goals_scored", "avg_goals_conceded"],
            index=pd.Index([], name="team_id"),
        )
        result = engine.get_match_features(999, 888, features_df)
        assert result.iloc[0]["home_win_rate"] == 0.5
        assert result.iloc[0]["home_avg_goals_scored"] == 0.0
        assert result.iloc[0]["home_avg_goals_conceded"] == 0.0
        assert result.iloc[0]["away_win_rate"] == 0.5
        assert result.iloc[0]["away_avg_goals_scored"] == 0.0
        assert result.iloc[0]["away_avg_goals_conceded"] == 0.0


# Feature: world-cup-predictor, Property 2: Feature computation correctness
# Validates: Requirements 3.1, 3.2, 3.3, 3.5

from hypothesis import given, settings
from tests.strategies import match_list
from src.feature_engine import FeatureEngine as FeatureEngineForProperty


@settings(max_examples=100)
@given(matches=match_list)
def test_feature_computation_correctness(matches):
    """
    Property 2: Feature computation correctness.

    For any DataFrame of match records, the Feature_Engine produces a features
    DataFrame where for each team:
    - win_rate = wins / total_matches
    - avg_goals_scored = total_goals_scored / total_matches
    - avg_goals_conceded = total_goals_conceded / total_matches
    counting both home and away appearances.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
    """
    import pandas as pd

    # Convert match list to DataFrame
    df = pd.DataFrame(matches)

    engine = FeatureEngineForProperty()
    result = engine.compute_features(df)

    # Collect all team IDs appearing in the matches
    all_team_ids = set(df["home_team_id"].unique()) | set(df["away_team_id"].unique())

    # Every team that appears in the data should be in the result
    for team_id in all_team_ids:
        assert team_id in result.index, f"Team {team_id} missing from features"

    # Verify correctness for each team
    for team_id in all_team_ids:
        # Home appearances
        home_matches = df[df["home_team_id"] == team_id]
        # Away appearances
        away_matches = df[df["away_team_id"] == team_id]

        total_matches = len(home_matches) + len(away_matches)
        assert total_matches > 0, f"Team {team_id} should have at least one match"

        # Count wins: home win when home_score > away_score, away win when away_score > home_score
        home_wins = int((home_matches["home_score"] > home_matches["away_score"]).sum())
        away_wins = int((away_matches["away_score"] > away_matches["home_score"]).sum())
        expected_win_rate = (home_wins + away_wins) / total_matches

        # Goals scored: home_score when playing at home, away_score when playing away
        goals_scored_home = int(home_matches["home_score"].sum())
        goals_scored_away = int(away_matches["away_score"].sum())
        expected_avg_goals_scored = (goals_scored_home + goals_scored_away) / total_matches

        # Goals conceded: away_score when playing at home, home_score when playing away
        goals_conceded_home = int(home_matches["away_score"].sum())
        goals_conceded_away = int(away_matches["home_score"].sum())
        expected_avg_goals_conceded = (goals_conceded_home + goals_conceded_away) / total_matches

        # Assert feature correctness
        actual_win_rate = result.loc[team_id, "win_rate"]
        actual_avg_goals_scored = result.loc[team_id, "avg_goals_scored"]
        actual_avg_goals_conceded = result.loc[team_id, "avg_goals_conceded"]

        assert abs(actual_win_rate - expected_win_rate) < 1e-9, (
            f"Team {team_id}: win_rate {actual_win_rate} != expected {expected_win_rate}"
        )
        assert abs(actual_avg_goals_scored - expected_avg_goals_scored) < 1e-9, (
            f"Team {team_id}: avg_goals_scored {actual_avg_goals_scored} != expected {expected_avg_goals_scored}"
        )
        assert abs(actual_avg_goals_conceded - expected_avg_goals_conceded) < 1e-9, (
            f"Team {team_id}: avg_goals_conceded {actual_avg_goals_conceded} != expected {expected_avg_goals_conceded}"
        )


# Feature: world-cup-predictor, Property 11: Unknown teams receive default features
from hypothesis import given, settings, assume
from hypothesis import strategies as st


@st.composite
def unknown_teams_and_features_df(draw):
    """Generate a features DataFrame and two team IDs NOT present in it.

    Returns a tuple of (home_team_id, away_team_id, features_df) where
    both team IDs are guaranteed not to be in the features DataFrame index.
    """
    # Generate known team IDs for the features DataFrame (1-5000 range)
    n_known_teams = draw(st.integers(min_value=0, max_value=20))
    known_team_ids = draw(
        st.lists(
            st.integers(min_value=1, max_value=5000),
            min_size=n_known_teams,
            max_size=n_known_teams,
            unique=True,
        )
    )

    # Generate unknown team IDs in a non-overlapping range (10001-20000)
    home_team_id = draw(st.integers(min_value=10001, max_value=20000))
    away_team_id = draw(st.integers(min_value=10001, max_value=20000))

    # Build a features DataFrame with the known teams
    if known_team_ids:
        records = []
        for team_id in known_team_ids:
            records.append(
                {
                    "team_id": team_id,
                    "win_rate": draw(
                        st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
                    ),
                    "avg_goals_scored": draw(
                        st.floats(min_value=0.0, max_value=10.0, allow_nan=False)
                    ),
                    "avg_goals_conceded": draw(
                        st.floats(min_value=0.0, max_value=10.0, allow_nan=False)
                    ),
                }
            )
        features_df = pd.DataFrame(records).set_index("team_id")
    else:
        features_df = pd.DataFrame(
            columns=["win_rate", "avg_goals_scored", "avg_goals_conceded"],
            index=pd.Index([], name="team_id"),
        )

    return home_team_id, away_team_id, features_df


class TestUnknownTeamDefaultsProperty:
    """Property 11: Unknown teams receive default features."""

    @given(data=unknown_teams_and_features_df())
    @settings(max_examples=100)
    def test_unknown_teams_receive_default_features(self, data):
        """
        For any upcoming match referencing team IDs not present in the computed
        features DataFrame, get_match_features SHALL use default values
        (win_rate=0.5, avg_goals_scored=0.0, avg_goals_conceded=0.0) and still
        produce a valid output with all 6 columns.

        **Validates: Requirements 6.6**
        """
        home_team_id, away_team_id, features_df = data
        engine = FeatureEngine()

        result = engine.get_match_features(home_team_id, away_team_id, features_df)

        # Assert valid output structure with all 6 columns
        expected_columns = {
            "home_win_rate",
            "home_avg_goals_scored",
            "home_avg_goals_conceded",
            "away_win_rate",
            "away_avg_goals_scored",
            "away_avg_goals_conceded",
        }
        assert set(result.columns) == expected_columns
        assert len(result) == 1

        # Assert default values for unknown home team
        assert result.iloc[0]["home_win_rate"] == 0.5
        assert result.iloc[0]["home_avg_goals_scored"] == 0.0
        assert result.iloc[0]["home_avg_goals_conceded"] == 0.0

        # Assert default values for unknown away team
        assert result.iloc[0]["away_win_rate"] == 0.5
        assert result.iloc[0]["away_avg_goals_scored"] == 0.0
        assert result.iloc[0]["away_avg_goals_conceded"] == 0.0
