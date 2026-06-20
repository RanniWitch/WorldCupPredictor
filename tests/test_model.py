"""Unit tests for the PredictionModel class."""

import numpy as np
import pandas as pd
import pytest

from src.exceptions import InsufficientDataError, NotFittedError, SingleClassError
from src.model import PredictionModel


@pytest.fixture
def model():
    """Create a fresh PredictionModel instance."""
    return PredictionModel()


@pytest.fixture
def valid_training_data():
    """Generate valid training data with >=10 samples and both classes."""
    np.random.seed(42)
    n_samples = 20
    features = pd.DataFrame(
        {
            "home_win_rate": np.random.uniform(0, 1, n_samples),
            "home_avg_goals_scored": np.random.uniform(0, 3, n_samples),
            "home_avg_goals_conceded": np.random.uniform(0, 3, n_samples),
            "away_win_rate": np.random.uniform(0, 1, n_samples),
            "away_avg_goals_scored": np.random.uniform(0, 3, n_samples),
            "away_avg_goals_conceded": np.random.uniform(0, 3, n_samples),
        }
    )
    # Ensure both classes are present
    labels = pd.Series([1, 0] * 10)
    return features, labels


class TestTrainValidation:
    """Tests for training data validation."""

    def test_insufficient_data_raises_error(self, model):
        """Raises InsufficientDataError when fewer than 10 samples provided."""
        features = pd.DataFrame({"a": [1.0] * 5, "b": [2.0] * 5})
        labels = pd.Series([0, 1, 0, 1, 0])

        with pytest.raises(InsufficientDataError):
            model.train(features, labels)

    def test_exactly_nine_samples_raises_error(self, model):
        """Raises InsufficientDataError for exactly 9 samples (boundary)."""
        features = pd.DataFrame({"a": range(9), "b": range(9)}, dtype=float)
        labels = pd.Series([0, 1, 0, 1, 0, 1, 0, 1, 0])

        with pytest.raises(InsufficientDataError):
            model.train(features, labels)

    def test_exactly_ten_samples_succeeds(self, model):
        """Ten samples with both classes should succeed."""
        features = pd.DataFrame(
            {"a": np.random.uniform(0, 1, 10), "b": np.random.uniform(0, 1, 10)}
        )
        labels = pd.Series([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])

        model.train(features, labels)
        assert model._is_fitted is True

    def test_single_class_raises_error(self, model):
        """Raises SingleClassError when labels contain only one class."""
        features = pd.DataFrame({"a": range(10), "b": range(10)}, dtype=float)
        labels = pd.Series([0] * 10)

        with pytest.raises(SingleClassError):
            model.train(features, labels)

    def test_single_class_all_ones_raises_error(self, model):
        """Raises SingleClassError when labels are all 1."""
        features = pd.DataFrame({"a": range(10), "b": range(10)}, dtype=float)
        labels = pd.Series([1] * 10)

        with pytest.raises(SingleClassError):
            model.train(features, labels)

    def test_nan_in_features_raises_error(self, model):
        """Raises ValueError when features contain NaN."""
        features = pd.DataFrame({"a": [1.0] * 10, "b": [2.0] * 10})
        features.iloc[3, 0] = np.nan
        labels = pd.Series([0, 1] * 5)

        with pytest.raises(ValueError, match="NaN or infinite"):
            model.train(features, labels)

    def test_inf_in_features_raises_error(self, model):
        """Raises ValueError when features contain infinite values."""
        features = pd.DataFrame({"a": [1.0] * 10, "b": [2.0] * 10})
        features.iloc[5, 1] = np.inf
        labels = pd.Series([0, 1] * 5)

        with pytest.raises(ValueError, match="NaN or infinite"):
            model.train(features, labels)

    def test_negative_inf_in_features_raises_error(self, model):
        """Raises ValueError when features contain negative infinity."""
        features = pd.DataFrame({"a": [1.0] * 10, "b": [2.0] * 10})
        features.iloc[0, 0] = -np.inf
        labels = pd.Series([0, 1] * 5)

        with pytest.raises(ValueError, match="NaN or infinite"):
            model.train(features, labels)


class TestPredict:
    """Tests for the predict method."""

    def test_predict_before_train_raises_error(self, model):
        """Raises NotFittedError when predict is called before train."""
        features = pd.DataFrame({"a": [1.0], "b": [2.0]})

        with pytest.raises(NotFittedError):
            model.predict(features)

    def test_predict_returns_correct_columns(self, model, valid_training_data):
        """Prediction returns DataFrame with home_win_prob and home_loss_prob columns."""
        features, labels = valid_training_data
        model.train(features, labels)

        prediction_features = features.iloc[:3]
        result = model.predict(prediction_features)

        assert "home_win_prob" in result.columns
        assert "home_loss_prob" in result.columns
        assert len(result.columns) == 2

    def test_predict_probabilities_in_valid_range(self, model, valid_training_data):
        """All probabilities are between 0.0 and 1.0."""
        features, labels = valid_training_data
        model.train(features, labels)

        result = model.predict(features)

        assert (result["home_win_prob"] >= 0.0).all()
        assert (result["home_win_prob"] <= 1.0).all()
        assert (result["home_loss_prob"] >= 0.0).all()
        assert (result["home_loss_prob"] <= 1.0).all()

    def test_predict_probabilities_sum_to_one(self, model, valid_training_data):
        """home_win_prob + home_loss_prob == 1.0 for each row."""
        features, labels = valid_training_data
        model.train(features, labels)

        result = model.predict(features)
        row_sums = result["home_win_prob"] + result["home_loss_prob"]

        np.testing.assert_allclose(row_sums, 1.0, atol=1e-10)

    def test_predict_row_count_matches_input(self, model, valid_training_data):
        """Output has same number of rows as input features."""
        features, labels = valid_training_data
        model.train(features, labels)

        subset = features.iloc[:5]
        result = model.predict(subset)

        assert len(result) == 5

    def test_predict_preserves_index(self, model, valid_training_data):
        """Output DataFrame preserves input index."""
        features, labels = valid_training_data
        model.train(features, labels)

        subset = features.iloc[3:7]
        result = model.predict(subset)

        assert list(result.index) == list(subset.index)


class TestTrainSuccessful:
    """Tests for successful training scenarios."""

    def test_train_sets_fitted_flag(self, model, valid_training_data):
        """Training sets _is_fitted to True."""
        features, labels = valid_training_data
        model.train(features, labels)
        assert model._is_fitted is True

    def test_model_initially_not_fitted(self, model):
        """Model starts in not-fitted state."""
        assert model._is_fitted is False
        assert model._model is None


# Feature: world-cup-predictor, Property 12: Training validation rejects invalid data
# Validates: Requirements 5.4, 5.5, 5.6

from hypothesis import given, settings
from hypothesis import strategies as st


@st.composite
def insufficient_training_data(draw):
    """Generate a features DataFrame with fewer than 10 records."""
    n_rows = draw(st.integers(min_value=1, max_value=9))
    n_cols = draw(st.integers(min_value=1, max_value=6))
    col_names = [f"feature_{i}" for i in range(n_cols)]
    data = {}
    for col in col_names:
        values = draw(
            st.lists(
                st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                min_size=n_rows,
                max_size=n_rows,
            )
        )
        data[col] = values
    features = pd.DataFrame(data, columns=col_names)
    # Generate labels with both classes if possible (to ensure only the sample count triggers the error)
    if n_rows >= 2:
        label_values = draw(
            st.lists(st.sampled_from([0, 1]), min_size=n_rows, max_size=n_rows).filter(
                lambda lst: len(set(lst)) > 1
            )
        )
    else:
        label_values = [draw(st.sampled_from([0, 1]))]
    labels = pd.Series(label_values)
    return features, labels


@st.composite
def single_class_training_data(draw):
    """Generate training data with >=10 records but only a single class in labels."""
    n_rows = draw(st.integers(min_value=10, max_value=50))
    n_cols = draw(st.integers(min_value=1, max_value=6))
    col_names = [f"feature_{i}" for i in range(n_cols)]
    data = {}
    for col in col_names:
        values = draw(
            st.lists(
                st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                min_size=n_rows,
                max_size=n_rows,
            )
        )
        data[col] = values
    features = pd.DataFrame(data, columns=col_names)
    # Single class: all 0 or all 1
    single_class = draw(st.sampled_from([0, 1]))
    labels = pd.Series([single_class] * n_rows)
    return features, labels


@st.composite
def nan_inf_training_data(draw):
    """Generate training data with >=10 records, both classes, but NaN or inf in features."""
    n_rows = draw(st.integers(min_value=10, max_value=50))
    n_cols = draw(st.integers(min_value=1, max_value=6))
    col_names = [f"feature_{i}" for i in range(n_cols)]
    data = {}
    for col in col_names:
        values = draw(
            st.lists(
                st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                min_size=n_rows,
                max_size=n_rows,
            )
        )
        data[col] = values
    features = pd.DataFrame(data, columns=col_names)

    # Inject NaN or inf into a random cell
    bad_value = draw(st.sampled_from([np.nan, np.inf, -np.inf]))
    row_idx = draw(st.integers(min_value=0, max_value=n_rows - 1))
    col_idx = draw(st.integers(min_value=0, max_value=n_cols - 1))
    features.iloc[row_idx, col_idx] = bad_value

    # Generate labels with both classes
    label_values = draw(
        st.lists(st.sampled_from([0, 1]), min_size=n_rows, max_size=n_rows).filter(
            lambda lst: len(set(lst)) > 1
        )
    )
    labels = pd.Series(label_values)
    return features, labels


class TestProperty12TrainingValidation:
    """Property 12: Training validation rejects invalid data."""

    @given(data=insufficient_training_data())
    @settings(max_examples=100)
    def test_insufficient_data_raises_error(self, data):
        """For any dataset with <10 records, InsufficientDataError is raised."""
        features, labels = data
        model = PredictionModel()
        with pytest.raises(InsufficientDataError):
            model.train(features, labels)

    @given(data=single_class_training_data())
    @settings(max_examples=100)
    def test_single_class_labels_raises_error(self, data):
        """For any dataset with single-class labels, SingleClassError is raised."""
        features, labels = data
        model = PredictionModel()
        with pytest.raises(SingleClassError):
            model.train(features, labels)

    @given(data=nan_inf_training_data())
    @settings(max_examples=100)
    def test_nan_inf_features_raises_error(self, data):
        """For any dataset with NaN/inf in features, ValueError is raised."""
        features, labels = data
        model = PredictionModel()
        with pytest.raises(ValueError, match="NaN or infinite"):
            model.train(features, labels)


# Feature: world-cup-predictor, Property 8: Prediction probabilities form a valid distribution

from hypothesis import given, settings
from tests.strategies import training_data
from src.feature_engine import FeatureEngine


class TestPredictionProbabilitiesProperty:
    """Property-based test: prediction probabilities form a valid distribution.

    **Validates: Requirements 5.3, 6.1**
    """

    @given(matches=training_data)
    @settings(max_examples=100)
    def test_probabilities_form_valid_distribution(self, matches):
        """For any trained model and valid feature vector, home_win_prob and
        home_loss_prob are each in [0.0, 1.0] and sum to 1.0."""
        # Build a DataFrame from generated match records
        matches_df = pd.DataFrame(matches)

        # Compute team features from the match data
        feature_engine = FeatureEngine()
        team_features = feature_engine.compute_features(matches_df)

        # Build training feature matrix and labels
        training_features = []
        labels = []
        for _, row in matches_df.iterrows():
            match_features = feature_engine.get_match_features(
                row["home_team_id"], row["away_team_id"], team_features
            )
            training_features.append(match_features)
            labels.append(1 if row["home_score"] > row["away_score"] else 0)

        X_train = pd.concat(training_features, ignore_index=True)
        y_train = pd.Series(labels)

        # Train the model
        model = PredictionModel()
        model.train(X_train, y_train)

        # Generate prediction features from the same matches (use a subset)
        prediction_features = []
        for _, row in matches_df.head(5).iterrows():
            match_features = feature_engine.get_match_features(
                row["home_team_id"], row["away_team_id"], team_features
            )
            prediction_features.append(match_features)

        X_pred = pd.concat(prediction_features, ignore_index=True)

        # Predict
        result = model.predict(X_pred)

        # Assert: home_win_prob in [0.0, 1.0]
        assert (result["home_win_prob"] >= 0.0).all(), "home_win_prob has values < 0.0"
        assert (result["home_win_prob"] <= 1.0).all(), "home_win_prob has values > 1.0"

        # Assert: home_loss_prob in [0.0, 1.0]
        assert (result["home_loss_prob"] >= 0.0).all(), "home_loss_prob has values < 0.0"
        assert (result["home_loss_prob"] <= 1.0).all(), "home_loss_prob has values > 1.0"

        # Assert: home_win_prob + home_loss_prob == 1.0 (within floating point tolerance)
        row_sums = result["home_win_prob"] + result["home_loss_prob"]
        np.testing.assert_allclose(
            row_sums, 1.0, atol=1e-10,
            err_msg="Probabilities do not sum to 1.0"
        )
