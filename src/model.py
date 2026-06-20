"""Prediction model module using Logistic Regression."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.exceptions import InsufficientDataError, NotFittedError, SingleClassError


class PredictionModel:
    """Wraps scikit-learn's LogisticRegression with validation and probability output."""

    MIN_TRAINING_SAMPLES = 10

    def __init__(self):
        self._model: LogisticRegression | None = None
        self._is_fitted: bool = False

    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """
        Train Logistic Regression on scaled features and binary labels.

        Labels: 1 = home win, 0 = home loss or draw.
        Raises InsufficientDataError if len(features) < 10.
        Raises SingleClassError if labels contain only one unique value.
        Raises ValueError if features contain NaN or infinite values.
        """
        self._validate_training_data(features, labels)

        self._model = LogisticRegression(max_iter=1000, solver="lbfgs")
        self._model.fit(features, labels)
        self._is_fitted = True

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict probabilities for given feature vectors.

        Returns DataFrame with columns: home_win_prob, home_loss_prob
        Probabilities sum to 1.0 per row.
        Raises NotFittedError if model has not been trained.
        """
        if not self._is_fitted:
            raise NotFittedError("Model has not been trained. Call train first.")

        probabilities = self._model.predict_proba(features)

        # LogisticRegression.classes_ is sorted, so index 0 = class 0 (loss/draw),
        # index 1 = class 1 (win)
        return pd.DataFrame(
            {
                "home_win_prob": probabilities[:, 1],
                "home_loss_prob": probabilities[:, 0],
            },
            index=features.index,
        )

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
                "Training labels must contain both classes (0 and 1), "
                f"but only found {labels.unique().tolist()}."
            )

        if features.isnull().any().any() or np.isinf(features.values).any():
            raise ValueError(
                "Training features contain NaN or infinite values."
            )
