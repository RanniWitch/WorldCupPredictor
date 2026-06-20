"""Custom Hypothesis strategies for World Cup Predictor property-based tests."""

from hypothesis import strategies as st
import pandas as pd
import numpy as np


# --- Match Record Strategy ---
# Generates a valid match dict with team IDs, scores, and dates.
match_record = st.fixed_dictionaries({
    "home_team_id": st.integers(min_value=1, max_value=10000),
    "away_team_id": st.integers(min_value=1, max_value=10000),
    "home_score": st.integers(min_value=0, max_value=15),
    "away_score": st.integers(min_value=0, max_value=15),
    "match_date": st.datetimes(),
})


# --- Match List Strategy ---
# Generates a list of match records (1-50 records).
match_list = st.lists(match_record, min_size=1, max_size=50)


# --- Training Data Strategy ---
# Generates >=10 records with both classes present (home win and not home win).
training_data = st.lists(match_record, min_size=10, max_size=100).filter(
    lambda matches: len(set(
        1 if m["home_score"] > m["away_score"] else 0 for m in matches
    )) > 1
)


# --- API Response Strategy ---
# Generates a full API response JSON matching football-data.org structure
# with mixed FINISHED and SCHEDULED statuses.

_finished_match = st.fixed_dictionaries({
    "id": st.integers(min_value=1, max_value=999999),
    "utcDate": st.datetimes().map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
    "status": st.just("FINISHED"),
    "homeTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "awayTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "score": st.fixed_dictionaries({
        "fullTime": st.fixed_dictionaries({
            "home": st.integers(min_value=0, max_value=15),
            "away": st.integers(min_value=0, max_value=15),
        }),
    }),
})

_scheduled_match = st.fixed_dictionaries({
    "id": st.integers(min_value=1, max_value=999999),
    "utcDate": st.datetimes().map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
    "status": st.just("SCHEDULED"),
    "homeTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "awayTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "score": st.fixed_dictionaries({
        "fullTime": st.fixed_dictionaries({
            "home": st.none(),
            "away": st.none(),
        }),
    }),
})

api_response = st.fixed_dictionaries({
    "matches": st.tuples(
        st.lists(_finished_match, min_size=1, max_size=25),
        st.lists(_scheduled_match, min_size=0, max_size=25),
    ).map(lambda t: t[0] + t[1]),
})

# FINISHED match with null scores (should be excluded by parser)
_finished_match_null_score = st.fixed_dictionaries({
    "id": st.integers(min_value=1, max_value=999999),
    "utcDate": st.datetimes().map(lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
    "status": st.just("FINISHED"),
    "homeTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "awayTeam": st.fixed_dictionaries({
        "id": st.integers(min_value=1, max_value=10000),
        "name": st.text(min_size=1, max_size=20),
    }),
    "score": st.fixed_dictionaries({
        "fullTime": st.fixed_dictionaries({
            "home": st.none(),
            "away": st.none(),
        }),
    }),
})

# API response with mixed statuses INCLUDING finished matches with null scores
api_response_mixed = st.fixed_dictionaries({
    "matches": st.tuples(
        st.lists(_finished_match, min_size=0, max_size=15),
        st.lists(_finished_match_null_score, min_size=0, max_size=10),
        st.lists(_scheduled_match, min_size=0, max_size=15),
    ).map(lambda t: t[0] + t[1] + t[2]),
})


# --- Feature DataFrame Strategy ---
# Generates numeric DataFrames with bounded float values suitable for scaler tests.

@st.composite
def feature_dataframe(draw, min_rows=2, max_rows=50, min_cols=1, max_cols=10):
    """Generate a pandas DataFrame with numeric columns and bounded float values.

    Parameters
    ----------
    min_rows : int
        Minimum number of rows (default 2).
    max_rows : int
        Maximum number of rows (default 50).
    min_cols : int
        Minimum number of columns (default 1).
    max_cols : int
        Maximum number of columns (default 10).

    Returns
    -------
    pd.DataFrame
        A DataFrame with float values in [-1000, 1000].
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    n_cols = draw(st.integers(min_value=min_cols, max_value=max_cols))

    col_names = [f"feature_{i}" for i in range(n_cols)]

    data = {}
    for col in col_names:
        values = draw(
            st.lists(
                st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                min_size=n_rows,
                max_size=n_rows,
            )
        )
        data[col] = values

    return pd.DataFrame(data, columns=col_names)
