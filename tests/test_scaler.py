"""Property-based tests for the FeatureScaler class."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, note, settings, assume
from hypothesis import strategies as st

from src.scaler import FeatureScaler
from tests.strategies import feature_dataframe


# Feature: world-cup-predictor, Property 5: Scaler rejects column count mismatch
# Validates: Requirements 4.4


@st.composite
def train_and_mismatched_predict_data(draw):
    """Generate training DataFrame and a prediction DataFrame with a different column count.

    Returns a tuple of (train_df, predict_df) where predict_df has M columns
    and train_df has N columns, with M != N.
    """
    # Generate training data with N columns
    train_df = draw(feature_dataframe(min_rows=2, max_rows=20, min_cols=1, max_cols=10))
    n_cols = train_df.shape[1]

    # Generate prediction data with M columns where M != N
    # Pick a column count that differs from training
    m_cols = draw(
        st.integers(min_value=1, max_value=10).filter(lambda m: m != n_cols)
    )
    n_pred_rows = draw(st.integers(min_value=1, max_value=10))

    pred_col_names = [f"pred_feature_{i}" for i in range(m_cols)]
    pred_data = {}
    for col in pred_col_names:
        values = draw(
            st.lists(
                st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                min_size=n_pred_rows,
                max_size=n_pred_rows,
            )
        )
        pred_data[col] = values

    predict_df = pd.DataFrame(pred_data, columns=pred_col_names)

    return train_df, predict_df


@settings(max_examples=100)
@given(data=train_and_mismatched_predict_data())
def test_scaler_rejects_column_count_mismatch(data):
    """
    Property 5: Scaler rejects column count mismatch.

    For any fitted Scaler trained on N columns, attempting to transform a
    DataFrame with M columns (where M != N) SHALL raise a ValueError
    indicating feature shape mismatch.

    **Validates: Requirements 4.4**
    """
    train_df, predict_df = data

    scaler = FeatureScaler()
    scaler.fit_transform(train_df)

    # The column counts must differ (guaranteed by strategy)
    assert train_df.shape[1] != predict_df.shape[1]

    with pytest.raises(ValueError):
        scaler.transform(predict_df)


# Feature: world-cup-predictor, Property 7: Scaler rejects NaN values
class TestScalerRejectsNaN:
    """Property 7: Scaler raises ValueError when input contains NaN values."""

    # **Validates: Requirements 4.6**

    @given(df=feature_dataframe(min_rows=2, max_rows=50, min_cols=1, max_cols=10))
    @settings(max_examples=100)
    def test_fit_transform_raises_on_nan(self, df: pd.DataFrame):
        """For any DataFrame with at least one NaN injected, fit_transform raises ValueError."""
        # Inject at least one NaN into a random cell
        nan_row = np.random.randint(0, len(df))
        nan_col = np.random.randint(0, len(df.columns))
        df.iloc[nan_row, nan_col] = np.nan

        note(f"Injected NaN at row={nan_row}, col={nan_col}")

        scaler = FeatureScaler()
        with pytest.raises(ValueError, match="[Mm]issing|NaN"):
            scaler.fit_transform(df)

    @given(
        train_df=feature_dataframe(min_rows=2, max_rows=50, min_cols=1, max_cols=10),
        pred_df=feature_dataframe(min_rows=2, max_rows=50, min_cols=1, max_cols=10),
    )
    @settings(max_examples=100)
    def test_transform_raises_on_nan(self, train_df: pd.DataFrame, pred_df: pd.DataFrame):
        """For any fitted scaler, transform raises ValueError when input contains NaN."""
        # Ensure pred_df has same number of columns as train_df
        assume(len(pred_df.columns) == len(train_df.columns))

        # Rename pred_df columns to match train_df so column count check passes
        pred_df.columns = train_df.columns

        # Fit scaler on clean training data
        scaler = FeatureScaler()
        scaler.fit_transform(train_df)

        # Inject at least one NaN into prediction data
        nan_row = np.random.randint(0, len(pred_df))
        nan_col = np.random.randint(0, len(pred_df.columns))
        pred_df.iloc[nan_row, nan_col] = np.nan

        note(f"Injected NaN at row={nan_row}, col={nan_col}")

        with pytest.raises(ValueError, match="[Mm]issing|NaN"):
            scaler.transform(pred_df)


# Feature: world-cup-predictor, Property 6: Scaler handles zero-variance columns


@st.composite
def feature_dataframe_with_constant_column(draw, min_rows=2, max_rows=50, min_cols=2, max_cols=10):
    """Generate a DataFrame where at least one column is constant (zero variance).

    Ensures the scaler zero-variance handling path is exercised.
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    n_cols = draw(st.integers(min_value=min_cols, max_value=max_cols))

    col_names = [f"feature_{i}" for i in range(n_cols)]

    # Pick at least one column index to be constant
    constant_col_indices = draw(
        st.lists(
            st.integers(min_value=0, max_value=n_cols - 1),
            min_size=1,
            max_size=max(1, n_cols // 2),
            unique=True,
        )
    )

    data = {}
    for i, col in enumerate(col_names):
        if i in constant_col_indices:
            # Constant column: all values are the same
            constant_value = draw(
                st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
            )
            data[col] = [constant_value] * n_rows
        else:
            # Normal varying column
            values = draw(
                st.lists(
                    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                    min_size=n_rows,
                    max_size=n_rows,
                )
            )
            data[col] = values

    return pd.DataFrame(data, columns=col_names)


class TestScalerZeroVarianceHandling:
    """Property 6: Scaler handles zero-variance columns."""

    # **Validates: Requirements 4.5**

    @given(df=feature_dataframe_with_constant_column(min_rows=2, max_rows=50, min_cols=2, max_cols=10))
    @settings(max_examples=100)
    def test_fit_transform_scales_constant_columns_to_zeros(self, df: pd.DataFrame):
        """For any numeric DataFrame with at least one constant column,
        fit_transform scales that column to all zeros without raising an error.

        **Validates: Requirements 4.5**
        """
        import numpy as np

        scaler = FeatureScaler()

        # Should not raise any error
        result = scaler.fit_transform(df)

        # Identify constant (zero-variance) columns
        for col in df.columns:
            if df[col].nunique() == 1:
                # Constant column should be scaled to all zeros
                # Use np.isclose to handle floating-point residuals from StandardScaler
                assert np.allclose(result[col].values, 0.0, atol=1e-10), (
                    f"Constant column '{col}' should be all zeros after fit_transform, "
                    f"got values: {result[col].tolist()}"
                )
