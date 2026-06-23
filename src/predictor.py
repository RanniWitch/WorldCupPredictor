"""Predictor orchestrator for the World Cup prediction pipeline."""

import logging

import numpy as np
import pandas as pd

from src.api_client import APIClient
from src.data_pipeline import DataPipeline
from src.exceptions import NoTrainingDataError
from src.feature_engine import FeatureEngine
from src.goals_model import GoalsModel, GoalsPrediction
from src.historical_data import load_historical_matches
from src.model import PredictionModel
from src.scaler import FeatureScaler

logger = logging.getLogger(__name__)

# Output DataFrame columns
PREDICTION_COLUMNS = [
    "home_team_name",
    "away_team_name",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "home_loss_prob",
    "match_date",
    "home_team_id",
    "away_team_id",
    "home_team_crest",
    "away_team_crest",
    "expected_home_goals",
    "expected_away_goals",
    "expected_total_goals",
    "over_1_5_prob",
    "over_2_5_prob",
    "over_3_5_prob",
    "over_4_5_prob",
    "predicted_home_goals",
    "predicted_away_goals",
    "predicted_score_prob",
    "top_scorelines",
]


class Predictor:
    """Orchestrates the full prediction pipeline from data fetch to output."""

    def __init__(self, api_key: str):
        """Initialize all pipeline components.

        Args:
            api_key: The API key for authenticating with football-data.org.
        """
        self._api_client = APIClient(api_key)
        self._data_pipeline = DataPipeline()
        self._feature_engine = FeatureEngine()
        self._scaler = FeatureScaler()
        self._model = PredictionModel()
        self._goals_model = GoalsModel()

    def _load_historical_training_data(self) -> tuple[pd.DataFrame, np.ndarray]:
        """Load historical international results with recency weighting.

        Converts team names to synthetic IDs for compatibility with the
        feature engine. Returns the DataFrame in the standard match format
        and corresponding sample weights.

        Returns:
            Tuple of (matches_df, weights) where matches_df has columns
            [home_team_id, away_team_id, home_score, away_score, match_date]
            and weights is a numpy array of float sample weights.
        """
        try:
            hist_df, weights = load_historical_matches()
        except FileNotFoundError:
            logger.warning("Historical dataset not found. Skipping.")
            return pd.DataFrame(), np.array([])

        if hist_df.empty:
            return pd.DataFrame(), np.array([])

        # Build team name -> synthetic ID mapping (use large IDs to avoid
        # collision with football-data.org IDs which are typically < 100000)
        all_teams = sorted(
            set(hist_df["home_team"].unique()) | set(hist_df["away_team"].unique())
        )
        name_to_id = {name: 100000 + i for i, name in enumerate(all_teams)}

        # Convert to standard match format
        matches = pd.DataFrame({
            "home_team_id": hist_df["home_team"].map(name_to_id),
            "away_team_id": hist_df["away_team"].map(name_to_id),
            "home_score": hist_df["home_score"],
            "away_score": hist_df["away_score"],
            "match_date": hist_df["date"],
            "home_team_name": hist_df["home_team"],
            "away_team_name": hist_df["away_team"],
        })

        # Store the name mapping for later use in predictions
        self._historical_name_to_id = name_to_id
        self._historical_id_to_name = {v: k for k, v in name_to_id.items()}

        logger.info(
            "Loaded %d historical matches (%d unique teams) for training.",
            len(matches), len(all_teams),
        )

        return matches, weights

    def _get_team_id_from_name(self, team_name: str) -> int | None:
        """Look up a historical team ID by name."""
        if hasattr(self, "_historical_name_to_id"):
            return self._historical_name_to_id.get(team_name)
        return None

    def run(self, competition_id: int, training_competition_ids: list[int] | None = None) -> pd.DataFrame:
        """
        Execute full prediction pipeline.

        Combines historical dataset (recency-weighted) with live API data
        for maximum training coverage. The historical dataset provides
        thousands of recent international matches; the API provides
        current-tournament context.

        Args:
            competition_id: The competition to predict matches for.
            training_competition_ids: Optional additional competition IDs to fetch
                historical match data from for training.

        Returns DataFrame with columns defined in PREDICTION_COLUMNS.
        Sorted by match_date ascending.
        Returns empty DataFrame if no scheduled matches.
        Raises NoTrainingDataError if no finished matches across all sources.
        """
        # Step 1: Load historical dataset (bulk training data with recency weights)
        historical_matches, historical_weights = self._load_historical_training_data()

        # Step 2: Fetch live matches from API
        raw_response = self._api_client.get_matches(competition_id)
        api_finished = self._data_pipeline.parse_matches(raw_response)

        # Fetch supplementary API data
        if training_competition_ids:
            for extra_id in training_competition_ids:
                if extra_id == competition_id:
                    continue
                try:
                    extra_response = self._api_client.get_matches(extra_id)
                    extra_finished = self._data_pipeline.parse_matches(extra_response)
                    if not extra_finished.empty:
                        api_finished = pd.concat(
                            [api_finished, extra_finished], ignore_index=True
                        )
                        logger.info(
                            "Added %d matches from competition %d.",
                            len(extra_finished), extra_id,
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch competition %d: %s", extra_id, e,
                    )

        # Step 3: Combine all training data
        all_training = []
        all_weights = []

        if not historical_matches.empty:
            all_training.append(historical_matches)
            all_weights.append(historical_weights)

        if not api_finished.empty:
            all_training.append(api_finished)
            # API matches get maximum weight (most current/relevant)
            all_weights.append(np.ones(len(api_finished)) * 2.0)

        if not all_training:
            raise NoTrainingDataError(
                "No finished matches available for training from any source."
            )

        finished_matches = pd.concat(all_training, ignore_index=True)
        sample_weights = np.concatenate(all_weights)

        logger.info(
            "Total training matches: %d (historical: %d, API: %d)",
            len(finished_matches),
            len(historical_matches) if not historical_matches.empty else 0,
            len(api_finished) if not api_finished.empty else 0,
        )

        # Step 4: Extract scheduled matches for prediction
        scheduled_matches = self._data_pipeline.get_scheduled_matches(raw_response)

        if not scheduled_matches:
            logger.info("No scheduled matches found for prediction.")
            return pd.DataFrame(columns=PREDICTION_COLUMNS)

        # Step 5: Compute features from ALL training data
        # Normalize match_date to tz-naive for consistent sorting
        if "match_date" in finished_matches.columns:
            finished_matches["match_date"] = pd.to_datetime(
                finished_matches["match_date"], utc=True
            ).dt.tz_localize(None)

        features_df = self._feature_engine.compute_features(finished_matches)

        # Step 6: Build training feature matrix and 3-class labels
        training_features = []
        labels = []

        for _, match in finished_matches.iterrows():
            match_features = self._feature_engine.get_match_features(
                int(match["home_team_id"]),
                int(match["away_team_id"]),
                features_df,
                home_team_name=str(match.get("home_team_name", "")),
                away_team_name=str(match.get("away_team_name", "")),
                is_neutral=True,  # Assume neutral for historical international matches
                matches_df=finished_matches,
            )
            training_features.append(match_features)
            # 3-class label: 2 = home win, 1 = draw, 0 = away win
            if match["home_score"] > match["away_score"]:
                label = 2
            elif match["home_score"] == match["away_score"]:
                label = 1
            else:
                label = 0
            labels.append(label)

        training_matrix = pd.concat(training_features, ignore_index=True)
        labels_series = pd.Series(labels, dtype=int)

        # Step 7: Scale training features
        scaled_training = self._scaler.fit_transform(training_matrix)

        # Step 8: Train model with sample weights for recency bias
        self._model.train(scaled_training, labels_series, sample_weights=sample_weights)

        # Step 8b: Fit the Poisson goals model on the same training data
        self._goals_model.fit(finished_matches, sample_weights=sample_weights)

        # Step 9: Predict for each scheduled match
        predictions = []

        for scheduled in scheduled_matches:
            home_id = int(scheduled["home_team_id"])
            away_id = int(scheduled["away_team_id"])

            # Try to also use historical ID if team name matches
            home_name = scheduled.get("home_team_name", "")
            away_name = scheduled.get("away_team_name", "")
            hist_home_id = self._get_team_id_from_name(home_name)
            hist_away_id = self._get_team_id_from_name(away_name)

            # Use whichever ID has data in features_df (prefer API ID, fallback to historical)
            if home_id not in features_df.index and hist_home_id and hist_home_id in features_df.index:
                home_id = hist_home_id
            if away_id not in features_df.index and hist_away_id and hist_away_id in features_df.index:
                away_id = hist_away_id

            match_features = self._feature_engine.get_match_features(
                home_id, away_id, features_df,
                home_team_name=home_name,
                away_team_name=away_name,
                is_neutral=True,  # World Cup matches are on neutral ground
                matches_df=finished_matches,
            )
            scaled_features = self._scaler.transform(match_features)
            prediction = self._model.predict(scaled_features)

            # Goals prediction using the Poisson model
            goals_pred = self._goals_model.predict(home_id, away_id)

            predictions.append(
                {
                    "home_team_name": scheduled.get("home_team_name", "Unknown"),
                    "away_team_name": scheduled.get("away_team_name", "Unknown"),
                    "home_win_prob": prediction["home_win_prob"].iloc[0],
                    "draw_prob": prediction["draw_prob"].iloc[0],
                    "away_win_prob": prediction["away_win_prob"].iloc[0],
                    "home_loss_prob": prediction["home_loss_prob"].iloc[0],
                    "match_date": scheduled["match_date"],
                    "home_team_id": scheduled["home_team_id"],
                    "away_team_id": scheduled["away_team_id"],
                    "home_team_crest": scheduled.get("home_team_crest", ""),
                    "away_team_crest": scheduled.get("away_team_crest", ""),
                    "expected_home_goals": goals_pred.expected_home_goals,
                    "expected_away_goals": goals_pred.expected_away_goals,
                    "expected_total_goals": goals_pred.expected_total_goals,
                    "over_1_5_prob": goals_pred.over_1_5_prob,
                    "over_2_5_prob": goals_pred.over_2_5_prob,
                    "over_3_5_prob": goals_pred.over_3_5_prob,
                    "over_4_5_prob": goals_pred.over_4_5_prob,
                    "predicted_home_goals": goals_pred.predicted_home_goals,
                    "predicted_away_goals": goals_pred.predicted_away_goals,
                    "predicted_score_prob": goals_pred.predicted_score_prob,
                    "top_scorelines": goals_pred.top_scorelines,
                }
            )

        # Step 10: Return sorted predictions
        result_df = pd.DataFrame(predictions, columns=PREDICTION_COLUMNS)
        result_df = result_df.sort_values("match_date", ascending=True).reset_index(
            drop=True
        )

        return result_df
