"""Feature scaling module using StandardScaler."""

import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.exceptions import NotFittedError


class FeatureScaler:
    """Wraps scikit-learn's StandardScaler with validation and DataFrame preservation."""

    def __init__(self):
        self._scaler: StandardScaler | None = None
        self._is_fitted: bool = False
        self._n_features: int | None = None

    def fit_transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Fit scaler on training data and return transformed DataFrame.

        Preserves column names. Sets _is_fitted = True.
        Raises ValueError if features contain NaN values.
        """
        self._validate_no_nans(features)

        self._scaler = StandardScaler()
        scaled_array = self._scaler.fit_transform(features)

        self._is_fitted = True
        self._n_features = features.shape[1]

        return pd.DataFrame(scaled_array, columns=features.columns, index=features.index)

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Transform features using previously fitted parameters.

        Raises NotFittedError if not yet fitted.
        Raises ValueError if column count differs from training.
        Raises ValueError if features contain NaN values.
        """
        if not self._is_fitted:
            raise NotFittedError("Scaler has not been fitted. Call fit_transform first.")

        self._validate_no_nans(features)

        if features.shape[1] != self._n_features:
            raise ValueError(
                f"Feature shape mismatch: expected {self._n_features} columns, "
                f"got {features.shape[1]} columns."
            )

        scaled_array = self._scaler.transform(features)

        return pd.DataFrame(scaled_array, columns=features.columns, index=features.index)

    def _validate_no_nans(self, features: pd.DataFrame) -> None:
        """Raise ValueError if the DataFrame contains any NaN values."""
        if features.isnull().any().any():
            raise ValueError("Input contains missing (NaN) values.")
