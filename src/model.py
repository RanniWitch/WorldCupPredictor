"""Prediction model module using Logistic Regression."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.exceptions import InsufficientDataError, NotFittedError, SingleClassError


class PredictionModel:
    """Wraps scikit-learn's LogisticRegression with 3-class probability output.

    Classes:
        0 = away win
        1 = draw
        2 = home win
    """

    MIN_TRAINING_SAMPLES = 10

    def __init__(self):
        self._model: LogisticRegression | None = None
        self._is_fitted: bool = False

    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """
        Train Logistic Regression on scaled features and 3-class labels.

        Labels: 2 = home win, 1 = draw, 0 = away win.
        Raises InsufficientDataError if len(features) < 10.
        Raises SingleClassError if labels contain fewer than 2 unique values.
        Raises ValueError if features contain NaN or infinite values.
        """
        self._validate_training_data(features, labels)

        self._model = LogisticRegression(max_iter=1000, solver="lbfgs")
        self._model.fit(features, labels)
        self._is_fitted = True

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict probabilities for given feature vectors.

        Returns DataFrame with columns: home_win_prob, draw_prob, away_win_prob
        Probabilities sum to 1.0 per row.
        Raises NotFittedError if model has not been trained.
        """
        if not self._is_fitted:
            raise NotFittedError("Model has not been trained. Call train first.")

        probabilities = self._model.predict_proba(features)

        # Map class indices to column names based on classes_ array
        classes = list(self._model.classes_)
        result = pd.DataFrame(index=features.index)

        # Assign probabilities based on which class index corresponds to which outcome
        if 0 in classes:
            result["away_win_prob"] = probabilities[:, classes.index(0)]
        else:
            result["away_win_prob"] = 0.0

        if 1 in classes:
            result["draw_prob"] = probabilities[:, classes.index(1)]
        else:
            result["draw_prob"] = 0.0

        if 2 in classes:
            result["home_win_prob"] = probabilities[:, classes.index(2)]
        else:
            result["home_win_prob"] = 0.0

        # For backward compatibility, compute home_loss_prob as away_win + draw
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
