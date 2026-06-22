"""Predictor orchestrator for the World Cup prediction pipeline."""

import logging

import pandas as pd

from src.api_client import APIClient
from src.data_pipeline import DataPipeline
from src.exceptions import NoTrainingDataError
from src.feature_engine import FeatureEngine
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

    def run(self, competition_id: int, training_competition_ids: list[int] | None = None) -> pd.DataFrame:
        """
        Execute full prediction pipeline.

        Args:
            competition_id: The competition to predict matches for.
            training_competition_ids: Optional additional competition IDs to fetch
                historical match data from for training. Useful when the target
                competition has few finished matches (e.g., early in a tournament).

        Returns DataFrame with columns:
            - home_team_id: int
            - away_team_id: int
            - home_win_prob: float
            - home_loss_prob: float
            - match_date: datetime

        Sorted by match_date ascending.
        Returns empty DataFrame if no scheduled matches.
        Raises NoTrainingDataError if no finished matches across all competitions.
        Propagates errors from any pipeline step.
        """
        # Step 1: Fetch matches via API_Client
        raw_response = self._api_client.get_matches(competition_id)

        # Step 2: Parse finished matches via Data_Pipeline
        finished_matches = self._data_pipeline.parse_matches(raw_response)

        # Fetch supplementary training data from additional competitions
        if training_competition_ids:
            for extra_id in training_competition_ids:
                if extra_id == competition_id:
                    continue
                try:
                    extra_response = self._api_client.get_matches(extra_id)
                    extra_finished = self._data_pipeline.parse_matches(extra_response)
                    if not extra_finished.empty:
                        finished_matches = pd.concat(
                            [finished_matches, extra_finished], ignore_index=True
                        )
                        logger.info(
                            "Added %d matches from competition %d for training.",
                            len(extra_finished), extra_id,
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch supplementary data from competition %d: %s",
                        extra_id, e,
                    )

        if finished_matches.empty:
            raise NoTrainingDataError(
                "No finished matches available for training."
            )

        # Step 3: Extract scheduled matches via Data_Pipeline
        scheduled_matches = self._data_pipeline.get_scheduled_matches(raw_response)

        if not scheduled_matches:
            logger.info("No scheduled matches found for prediction.")
            return pd.DataFrame(columns=PREDICTION_COLUMNS)

        # Step 4: Compute features via Feature_Engine
        features_df = self._feature_engine.compute_features(finished_matches)

        # Step 5: Build training feature matrix and binary labels
        training_features = []
        labels = []

        for _, match in finished_matches.iterrows():
            match_features = self._feature_engine.get_match_features(
                int(match["home_team_id"]),
                int(match["away_team_id"]),
                features_df,
            )
            training_features.append(match_features)
            # 3-class label: 2 = home win, 1 = draw, 0 = away win
            if match["home_score"] > match["away_score"]:
                label = 2  # home win
            elif match["home_score"] == match["away_score"]:
                label = 1  # draw
            else:
                label = 0  # away win
            labels.append(label)

        training_matrix = pd.concat(training_features, ignore_index=True)
        labels_series = pd.Series(labels, dtype=int)

        # Step 6: Scale training features via Scaler
        scaled_training = self._scaler.fit_transform(training_matrix)

        # Step 7: Train model
        self._model.train(scaled_training, labels_series)

        # Step 8: For each scheduled match: build feature vector, scale, predict
        predictions = []

        for scheduled in scheduled_matches:
            match_features = self._feature_engine.get_match_features(
                int(scheduled["home_team_id"]),
                int(scheduled["away_team_id"]),
                features_df,
            )
            scaled_features = self._scaler.transform(match_features)
            prediction = self._model.predict(scaled_features)

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
                }
            )

        # Step 9: Return sorted DataFrame of predictions
        result_df = pd.DataFrame(predictions, columns=PREDICTION_COLUMNS)
        result_df = result_df.sort_values("match_date", ascending=True).reset_index(
            drop=True
        )

        return result_df
