"""Historical data loader for international football results.

Loads and processes the Kaggle international results dataset, applying
time-based filtering and recency weighting to ensure training data
reflects current team strength rather than decades-old rosters.
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Path to the historical dataset relative to project root
DATA_PATH = Path(__file__).parent.parent / "data" / "international_results.csv"

# Only use matches from this date onward (captures current-era rosters)
CUTOFF_DATE = "2020-01-01"

# Half-life for exponential decay weighting (in days).
# Matches from HALF_LIFE days ago get 50% weight; older matches decay further.
HALF_LIFE_DAYS = 365  # 1 year half-life


def load_historical_matches(
    cutoff_date: str = CUTOFF_DATE,
    half_life_days: int = HALF_LIFE_DAYS,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Load historical international match results with recency weights.

    Filters to matches after cutoff_date, excludes matches with missing scores
    (scheduled future matches), and computes exponential decay sample weights
    based on match date.

    Args:
        cutoff_date: ISO date string. Only matches on or after this date are used.
        half_life_days: Half-life for the exponential decay weighting.

    Returns:
        Tuple of (matches_df, weights_array):
        - matches_df: DataFrame with columns [home_team, away_team, home_score,
          away_score, date, tournament, neutral]
        - weights_array: numpy array of float weights (same length as matches_df),
          where more recent matches have higher weight.

    Raises:
        FileNotFoundError: If the dataset file doesn't exist.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical dataset not found at {DATA_PATH}. "
            "Download from: https://github.com/martj42/international_results"
        )

    df = pd.read_csv(DATA_PATH)
    logger.info("Loaded %d total historical matches from dataset.", len(df))

    # Filter by date
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= cutoff_date].copy()
    logger.info("Filtered to %d matches since %s.", len(df), cutoff_date)

    # Remove matches with missing scores (future/unplayed matches in the dataset)
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    logger.info("After removing unplayed matches: %d matches.", len(df))

    # Compute recency weights using exponential decay
    reference_date = pd.Timestamp.now()
    days_ago = (reference_date - df["date"]).dt.days.values
    decay_rate = np.log(2) / half_life_days
    weights = np.exp(-decay_rate * days_ago)

    # Normalize weights to have mean of 1 (so total effective sample size ~ n)
    weights = weights / weights.mean()

    logger.info(
        "Weight stats: min=%.3f, max=%.3f, mean=%.3f (half-life=%d days)",
        weights.min(), weights.max(), weights.mean(), half_life_days,
    )

    return df, weights


def get_team_name_mapping() -> dict[str, int]:
    """Create a consistent team name to ID mapping from the dataset.

    Returns:
        Dict mapping team name strings to integer IDs.
    """
    if not DATA_PATH.exists():
        return {}

    df = pd.read_csv(DATA_PATH, usecols=["home_team", "away_team"])
    all_teams = sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    return {name: i + 1 for i, name in enumerate(all_teams)}
