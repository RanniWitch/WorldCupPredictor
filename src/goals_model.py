"""Poisson-based goals prediction model for expected goals, over/under, and scorelines.

Uses team-level attack/defense strength parameters derived from historical
match data to model goal-scoring as independent Poisson processes.

Key concepts:
- Attack strength: How much better/worse a team scores relative to average.
- Defense strength: How much more/fewer goals a team concedes relative to average.
- λ (lambda): Expected goals for a team in a given match.

Regularization is applied to prevent overfitting for teams with few matches,
pulling estimates toward league averages (shrinkage/Bayesian prior approach).
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import poisson

from src.exceptions import InsufficientDataError, NotFittedError

logger = logging.getLogger(__name__)

# Maximum goals to consider in the probability matrix (0 through MAX_GOALS inclusive)
MAX_GOALS = 7

# Minimum matches a team must have to use their raw stats (otherwise shrink to average)
MIN_MATCHES_FOR_FULL_WEIGHT = 10

# Shrinkage strength — higher = more pull toward average for low-sample teams
SHRINKAGE_FACTOR = 5


@dataclass
class GoalsPrediction:
    """Container for a single match's goals prediction output."""

    expected_home_goals: float
    expected_away_goals: float
    expected_total_goals: float

    # Over/under probabilities for common lines
    over_1_5_prob: float
    over_2_5_prob: float
    over_3_5_prob: float
    over_4_5_prob: float

    # Most likely scorelines: list of (home_goals, away_goals, probability)
    top_scorelines: list[tuple[int, int, float]]

    # Most likely exact scoreline
    predicted_home_goals: int
    predicted_away_goals: int
    predicted_score_prob: float


class GoalsModel:
    """Poisson model for predicting match goals and scorelines.

    Fits team-level attack and defense strength parameters from historical
    matches, then uses them to generate expected goals (lambda) for each
    team in a new fixture. Applies regularization (shrinkage toward league
    averages) to prevent overfitting for teams with limited data.
    """

    def __init__(self):
        self._is_fitted: bool = False
        self._team_attack: dict[int, float] = {}
        self._team_defense: dict[int, float] = {}
        self._home_advantage: float = 1.0
        self._league_avg_home_goals: float = 1.5
        self._league_avg_away_goals: float = 1.2
        self._team_matches_count: dict[int, int] = {}

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(self, matches_df: pd.DataFrame, sample_weights: np.ndarray | None = None) -> None:
        """Fit attack/defense parameters from historical match data.

        Uses weighted averages with optional sample weights (e.g., recency)
        and applies shrinkage regularization for teams with few matches.

        Args:
            matches_df: DataFrame with columns [home_team_id, away_team_id,
                        home_score, away_score].
            sample_weights: Optional per-match weights. If None, uniform weights used.

        Raises:
            InsufficientDataError: If fewer than 20 matches provided.
        """
        if len(matches_df) < 20:
            raise InsufficientDataError(
                f"Goals model requires at least 20 matches, got {len(matches_df)}."
            )

        if sample_weights is None:
            sample_weights = np.ones(len(matches_df))

        # Normalize weights to sum to len(matches_df) for interpretable counts
        sample_weights = sample_weights * len(matches_df) / sample_weights.sum()

        # Compute weighted league averages
        total_weight = sample_weights.sum()
        self._league_avg_home_goals = (
            (matches_df["home_score"].values * sample_weights).sum() / total_weight
        )
        self._league_avg_away_goals = (
            (matches_df["away_score"].values * sample_weights).sum() / total_weight
        )

        # Home advantage ratio
        if self._league_avg_away_goals > 0:
            self._home_advantage = self._league_avg_home_goals / self._league_avg_away_goals
        else:
            self._home_advantage = 1.3  # Sensible default

        logger.info(
            "League averages: home=%.3f, away=%.3f, home_advantage=%.3f",
            self._league_avg_home_goals, self._league_avg_away_goals, self._home_advantage,
        )

        # Compute per-team attack and defense strengths
        all_team_ids = set(matches_df["home_team_id"].unique()) | set(
            matches_df["away_team_id"].unique()
        )

        for team_id in all_team_ids:
            # Find matches where this team played
            home_mask = matches_df["home_team_id"] == team_id
            away_mask = matches_df["away_team_id"] == team_id

            home_indices = matches_df.index[home_mask]
            away_indices = matches_df.index[away_mask]

            # Weighted goals scored
            home_goals_scored = (
                matches_df.loc[home_indices, "home_score"].values
                * sample_weights[home_mask.values]
            ).sum()
            away_goals_scored = (
                matches_df.loc[away_indices, "away_score"].values
                * sample_weights[away_mask.values]
            ).sum()

            # Weighted goals conceded
            home_goals_conceded = (
                matches_df.loc[home_indices, "away_score"].values
                * sample_weights[home_mask.values]
            ).sum()
            away_goals_conceded = (
                matches_df.loc[away_indices, "home_score"].values
                * sample_weights[away_mask.values]
            ).sum()

            # Effective match count (sum of weights for this team)
            home_weight_sum = sample_weights[home_mask.values].sum()
            away_weight_sum = sample_weights[away_mask.values].sum()
            effective_matches = home_weight_sum + away_weight_sum

            self._team_matches_count[team_id] = int(home_mask.sum() + away_mask.sum())

            if effective_matches < 0.5:
                # No meaningful data — use league average
                self._team_attack[team_id] = 1.0
                self._team_defense[team_id] = 1.0
                continue

            # Raw attack strength: goals scored relative to what average team would score
            # in same positions (home/away)
            expected_scored = (
                home_weight_sum * self._league_avg_home_goals
                + away_weight_sum * self._league_avg_away_goals
            )
            raw_attack = (home_goals_scored + away_goals_scored) / expected_scored if expected_scored > 0 else 1.0

            # Raw defense strength: goals conceded relative to what average team would concede
            expected_conceded = (
                home_weight_sum * self._league_avg_away_goals
                + away_weight_sum * self._league_avg_home_goals
            )
            raw_defense = (home_goals_conceded + away_goals_conceded) / expected_conceded if expected_conceded > 0 else 1.0

            # Apply shrinkage regularization:
            # Teams with few matches get pulled toward 1.0 (league average)
            # Formula: shrunk = (n * raw + k * prior) / (n + k)
            # where k = SHRINKAGE_FACTOR, prior = 1.0
            n = effective_matches
            k = SHRINKAGE_FACTOR
            shrunk_attack = (n * raw_attack + k * 1.0) / (n + k)
            shrunk_defense = (n * raw_defense + k * 1.0) / (n + k)

            # Clamp to reasonable range to prevent extreme predictions
            self._team_attack[team_id] = np.clip(shrunk_attack, 0.3, 2.5)
            self._team_defense[team_id] = np.clip(shrunk_defense, 0.3, 2.5)

        self._is_fitted = True

        logger.info(
            "Goals model fitted: %d teams, avg attack=%.3f, avg defense=%.3f",
            len(all_team_ids),
            np.mean(list(self._team_attack.values())),
            np.mean(list(self._team_defense.values())),
        )

    def predict(self, home_team_id: int, away_team_id: int) -> GoalsPrediction:
        """Predict goals for a match using the Poisson model.

        Args:
            home_team_id: ID of the home team.
            away_team_id: ID of the away team.

        Returns:
            GoalsPrediction with expected goals, over/under probs, and scorelines.

        Raises:
            NotFittedError: If the model hasn't been fitted yet.
        """
        if not self._is_fitted:
            raise NotFittedError("Goals model has not been fitted. Call fit() first.")

        # Get team parameters (default to 1.0 for unknown teams)
        home_attack = self._team_attack.get(home_team_id, 1.0)
        home_defense = self._team_defense.get(home_team_id, 1.0)
        away_attack = self._team_attack.get(away_team_id, 1.0)
        away_defense = self._team_defense.get(away_team_id, 1.0)

        # Calculate expected goals (lambda) for each team
        # Home lambda = home_attack * away_defense * league_avg_home_goals
        # (strong attack + weak opponent defense = more goals)
        lambda_home = home_attack * away_defense * self._league_avg_home_goals
        lambda_away = away_attack * home_defense * self._league_avg_away_goals

        # Clamp lambdas to prevent unrealistic extremes
        lambda_home = np.clip(lambda_home, 0.2, 5.0)
        lambda_away = np.clip(lambda_away, 0.2, 5.0)

        # Build the scoreline probability matrix
        score_matrix = self._build_score_matrix(lambda_home, lambda_away)

        # Calculate over/under probabilities
        total_goals_probs = self._compute_total_goals_probs(score_matrix)

        over_1_5 = 1.0 - sum(total_goals_probs.get(g, 0) for g in range(2))
        over_2_5 = 1.0 - sum(total_goals_probs.get(g, 0) for g in range(3))
        over_3_5 = 1.0 - sum(total_goals_probs.get(g, 0) for g in range(4))
        over_4_5 = 1.0 - sum(total_goals_probs.get(g, 0) for g in range(5))

        # Get top scorelines
        top_scorelines = self._get_top_scorelines(score_matrix, n=5)

        # Most likely scoreline
        best_home, best_away, best_prob = top_scorelines[0]

        return GoalsPrediction(
            expected_home_goals=round(lambda_home, 2),
            expected_away_goals=round(lambda_away, 2),
            expected_total_goals=round(lambda_home + lambda_away, 2),
            over_1_5_prob=round(over_1_5, 4),
            over_2_5_prob=round(over_2_5, 4),
            over_3_5_prob=round(over_3_5, 4),
            over_4_5_prob=round(over_4_5, 4),
            top_scorelines=top_scorelines,
            predicted_home_goals=best_home,
            predicted_away_goals=best_away,
            predicted_score_prob=round(best_prob, 4),
        )

    def _build_score_matrix(self, lambda_home: float, lambda_away: float) -> np.ndarray:
        """Build the joint probability matrix for all scoreline combinations.

        Assumes independence between home and away goals (standard Poisson model).
        Returns (MAX_GOALS+1) x (MAX_GOALS+1) matrix where [i][j] = P(home=i, away=j).
        """
        home_probs = poisson.pmf(np.arange(MAX_GOALS + 1), lambda_home)
        away_probs = poisson.pmf(np.arange(MAX_GOALS + 1), lambda_away)

        # Outer product gives joint probability matrix (independence assumption)
        matrix = np.outer(home_probs, away_probs)

        # Normalize to account for truncation at MAX_GOALS
        matrix = matrix / matrix.sum()

        return matrix

    def _compute_total_goals_probs(self, score_matrix: np.ndarray) -> dict[int, float]:
        """Compute probability distribution for total goals in the match."""
        max_total = 2 * MAX_GOALS
        total_probs = {}

        for total in range(max_total + 1):
            prob = 0.0
            for home_goals in range(min(total, MAX_GOALS) + 1):
                away_goals = total - home_goals
                if 0 <= away_goals <= MAX_GOALS:
                    prob += score_matrix[home_goals][away_goals]
            total_probs[total] = prob

        return total_probs

    def _get_top_scorelines(
        self, score_matrix: np.ndarray, n: int = 5
    ) -> list[tuple[int, int, float]]:
        """Get the n most probable scorelines from the matrix."""
        scorelines = []

        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                scorelines.append((i, j, float(score_matrix[i][j])))

        # Sort by probability descending
        scorelines.sort(key=lambda x: x[2], reverse=True)

        return scorelines[:n]

    def get_team_strengths(self, team_id: int) -> dict[str, float]:
        """Get a team's fitted attack and defense parameters (for diagnostics)."""
        if not self._is_fitted:
            raise NotFittedError("Goals model has not been fitted.")

        return {
            "attack": self._team_attack.get(team_id, 1.0),
            "defense": self._team_defense.get(team_id, 1.0),
            "matches": self._team_matches_count.get(team_id, 0),
        }
