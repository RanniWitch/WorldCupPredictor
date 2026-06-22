"""Prediction model module using XGBoost."""

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.exceptions import InsufficientDataError, NotFittedError, SingleClassError


class PredictionModel:
    """Wraps XGBoost classifier with 3-class probability output.

    Uses gradient-boosted decision trees to capture non-linear patterns
    and feature interactions that logistic regression cannot model.

    Classes:
        0 = away win
        1 = draw
        2 = home win
    """

    MIN_TRAINING_SAMPLES = 10

    def __init__(self):
        self._model: XGBClassifier | None = None
        self._is_fitted: bool = False

    def train(self, features: pd.DataFrame, labels: pd.Series, sample_weights: np.ndarray | None = None) -> None:
        """
        Train XGBoost on scaled features and 3-class labels.

        Labels: 2 = home win, 1 = draw, 0 = away win.
        sample_weights: Optional per-sample weights for recency bias.
        Raises InsufficientDataError if len(features) < 10.
        Raises SingleClassError if labels contain fewer than 2 unique values.
        Raises ValueError if features contain NaN or infinite values.
        """
        self._validate_training_data(features, labels)

        self._model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            use_label_encoder=False,
            verbosity=0,
            random_state=42,
        )
        self._model.fit(features, labels, sample_weight=sample_weights)
        self._is_fitted = True

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict probabilities for given feature vectors.

        Returns DataFrame with columns: home_win_prob, draw_prob, away_win_prob, home_loss_prob
        Probabilities sum to 1.0 per row.
        Raises NotFittedError if model has not been trained.
        """
        if not self._is_fitted:
            raise NotFittedError("Model has not been trained. Call train first.")

        probabilities = self._model.predict_proba(features)

        # XGBoost with num_class=3 outputs probabilities in class order [0, 1, 2]
        # Class 0 = away win, Class 1 = draw, Class 2 = home win
        result = pd.DataFrame(
            {
                "away_win_prob": probabilities[:, 0],
                "draw_prob": probabilities[:, 1],
                "home_win_prob": probabilities[:, 2],
            },
            index=features.index,
        )

        # Backward compatibility
        result["home_loss_prob"] = result["away_win_prob"] + result["draw_prob"]

        return result

    def _validate_training_data(
        self, features: pd.DataFrame, labels: pd.Series
    ) -> None:
        """Validate training data meets all requirements."""
        if len(features) < self.MIN_TRAINING_SAMPLES:
            raise InsufficientDataError(
                f"Training requires at least {self.MIN_TRAINING_SAMPLES} samples, "
                f"got {len(features)}."
            )

        unique_classes = labels.nunique()
        if unique_classes < 2:
            raise SingleClassError(
                "Training labels must contain at least 2 classes, "
                f"but only found {labels.unique().tolist()}."
            )

        if features.isnull().any().any() or np.isinf(features.values).any():
            raise ValueError(
                "Training features contain NaN or infinite values."
            )
