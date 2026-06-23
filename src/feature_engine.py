"""Feature engineering for team performance statistics.

Computes features including:
- Win rate and goal statistics (overall)
- Recent form (last 5 matches)
- Head-to-head history
- FIFA ranking and ranking gap
- Neutral venue flag
"""

from pathlib import Path

import pandas as pd

# Path to FIFA rankings data
RANKINGS_PATH = Path(__file__).parent.parent / "data" / "fifa_rankings.csv"


def _load_fifa_rankings() -> dict[str, tuple[int, float]]:
    """Load FIFA rankings into a dict of team_name -> (rank, points)."""
    if not RANKINGS_PATH.exists():
        return {}
    df = pd.read_csv(RANKINGS_PATH)
    return {
        row["team"]: (int(row["rank"]), float(row["points"]))
        for _, row in df.iterrows()
    }


# Load rankings once at module level
_FIFA_RANKINGS = _load_fifa_rankings()

# Default ranking for unranked teams (assume bottom of table)
DEFAULT_RANK = 100
DEFAULT_POINTS = 1400.0


class FeatureEngine:
    """Computes team performance statistics from historical match data."""

    DEFAULT_WIN_RATE = 0.33
    DEFAULT_AVG_GOALS_SCORED = 1.0
    DEFAULT_AVG_GOALS_CONCEDED = 1.0
    FORM_WINDOW = 5  # Number of recent matches for form calculation

    def compute_features(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-team features from historical match data.

        Returns DataFrame indexed by team_id with columns:
            - win_rate: float (wins / total_matches)
            - draw_rate: float (draws / total_matches)
            - avg_goals_scored: float
            - avg_goals_conceded: float
            - recent_win_rate: float (last 5 matches)
            - recent_goals_scored: float (avg last 5)

        Teams are counted for both home and away appearances.
        """
        if matches_df.empty:
            return pd.DataFrame(
                columns=[
                    "win_rate", "draw_rate", "avg_goals_scored",
                    "avg_goals_conceded", "recent_win_rate", "recent_goals_scored",
                ],
                index=pd.Index([], name="team_id"),
            )

        # Sort by match date for form calculations
        if "match_date" in matches_df.columns:
            matches_df = matches_df.sort_values("match_date").reset_index(drop=True)

        # Collect all unique team IDs
        all_team_ids = set(matches_df["home_team_id"].unique()) | set(
            matches_df["away_team_id"].unique()
        )

        records = []

        for team_id in all_team_ids:
            # Home appearances
            home_matches = matches_df[matches_df["home_team_id"] == team_id]
            # Away appearances
            away_matches = matches_df[matches_df["away_team_id"] == team_id]

            total_matches = len(home_matches) + len(away_matches)

            if total_matches == 0:
                records.append(self._default_record(team_id))
                continue

            # Wins
            home_wins = (home_matches["home_score"] > home_matches["away_score"]).sum()
            away_wins = (away_matches["away_score"] > away_matches["home_score"]).sum()
            total_wins = home_wins + away_wins

            # Draws
            home_draws = (home_matches["home_score"] == home_matches["away_score"]).sum()
            away_draws = (away_matches["away_score"] == away_matches["home_score"]).sum()
            total_draws = home_draws + away_draws

            # Goals
            goals_scored = home_matches["home_score"].sum() + away_matches["away_score"].sum()
            goals_conceded = home_matches["away_score"].sum() + away_matches["home_score"].sum()

            # Recent form (last N matches by date)
            recent_win_rate, recent_goals = self._compute_recent_form(
                team_id, matches_df
            )

            records.append({
                "team_id": team_id,
                "win_rate": total_wins / total_matches,
                "draw_rate": total_draws / total_matches,
                "avg_goals_scored": goals_scored / total_matches,
                "avg_goals_conceded": goals_conceded / total_matches,
                "recent_win_rate": recent_win_rate,
                "recent_goals_scored": recent_goals,
            })

        features_df = pd.DataFrame(records)
        features_df = features_df.set_index("team_id")
        return features_df

    def _compute_recent_form(self, team_id: int, matches_df: pd.DataFrame) -> tuple[float, float]:
        """Compute recent form stats from last N matches."""
        # Get all matches for this team, sorted by date
        home = matches_df[matches_df["home_team_id"] == team_id].copy()
        away = matches_df[matches_df["away_team_id"] == team_id].copy()

        # Build a unified recent matches list
        home_records = []
        for _, m in home.iterrows():
            home_records.append({
                "date": m.get("match_date", 0),
                "goals_scored": m["home_score"],
                "goals_conceded": m["away_score"],
                "won": m["home_score"] > m["away_score"],
            })

        away_records = []
        for _, m in away.iterrows():
            away_records.append({
                "date": m.get("match_date", 0),
                "goals_scored": m["away_score"],
                "goals_conceded": m["home_score"],
                "won": m["away_score"] > m["home_score"],
            })

        all_records = home_records + away_records
        # Sort by date descending, take last N
        all_records.sort(key=lambda x: str(x["date"]), reverse=True)
        recent = all_records[:self.FORM_WINDOW]

        if not recent:
            return self.DEFAULT_WIN_RATE, self.DEFAULT_AVG_GOALS_SCORED

        wins = sum(1 for r in recent if r["won"])
        goals = sum(r["goals_scored"] for r in recent)

        return wins / len(recent), goals / len(recent)

    def _default_record(self, team_id: int) -> dict:
        return {
            "team_id": team_id,
            "win_rate": self.DEFAULT_WIN_RATE,
            "draw_rate": 0.33,
            "avg_goals_scored": self.DEFAULT_AVG_GOALS_SCORED,
            "avg_goals_conceded": self.DEFAULT_AVG_GOALS_CONCEDED,
            "recent_win_rate": self.DEFAULT_WIN_RATE,
            "recent_goals_scored": self.DEFAULT_AVG_GOALS_SCORED,
        }

    def get_match_features(
        self, home_team_id: int, away_team_id: int, features_df: pd.DataFrame,
        home_team_name: str = "", away_team_name: str = "",
        is_neutral: bool = True, matches_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """
        Build a single-row feature vector for a match.

        Returns DataFrame with columns:
            - home_win_rate, home_draw_rate, home_avg_goals_scored, home_avg_goals_conceded
            - home_recent_win_rate, home_recent_goals_scored
            - away_win_rate, away_draw_rate, away_avg_goals_scored, away_avg_goals_conceded
            - away_recent_win_rate, away_recent_goals_scored
            - home_fifa_rank, away_fifa_rank, rank_gap
            - home_fifa_points, away_fifa_points, points_gap
            - h2h_home_win_rate, h2h_draws
            - is_neutral

        Uses default values for teams not found.
        """
        # Base team features
        home_f = self._get_team_features(home_team_id, features_df)
        away_f = self._get_team_features(away_team_id, features_df)

        # FIFA rankings
        home_rank, home_points = self._get_ranking(home_team_name)
        away_rank, away_points = self._get_ranking(away_team_name)

        # Head-to-head
        h2h_home_wr, h2h_draws = self._get_h2h(
            home_team_id, away_team_id, matches_df
        )

        return pd.DataFrame([{
            "home_win_rate": home_f["win_rate"],
            "home_draw_rate": home_f["draw_rate"],
            "home_avg_goals_scored": home_f["avg_goals_scored"],
            "home_avg_goals_conceded": home_f["avg_goals_conceded"],
            "home_recent_win_rate": home_f["recent_win_rate"],
            "home_recent_goals_scored": home_f["recent_goals_scored"],
            "away_win_rate": away_f["win_rate"],
            "away_draw_rate": away_f["draw_rate"],
            "away_avg_goals_scored": away_f["avg_goals_scored"],
            "away_avg_goals_conceded": away_f["avg_goals_conceded"],
            "away_recent_win_rate": away_f["recent_win_rate"],
            "away_recent_goals_scored": away_f["recent_goals_scored"],
            "home_fifa_rank": home_rank,
            "away_fifa_rank": away_rank,
            "rank_gap": away_rank - home_rank,  # positive = home team ranked higher
            "home_fifa_points": home_points,
            "away_fifa_points": away_points,
            "points_gap": home_points - away_points,
            "h2h_home_win_rate": h2h_home_wr,
            "h2h_draw_rate": h2h_draws,
            "is_neutral": 1.0 if is_neutral else 0.0,
        }])

    def _get_team_features(self, team_id: int, features_df: pd.DataFrame) -> dict:
        """Get features for a team, with defaults for unknown teams."""
        if team_id in features_df.index:
            row = features_df.loc[team_id]
            return {
                "win_rate": row["win_rate"],
                "draw_rate": row["draw_rate"],
                "avg_goals_scored": row["avg_goals_scored"],
                "avg_goals_conceded": row["avg_goals_conceded"],
                "recent_win_rate": row["recent_win_rate"],
                "recent_goals_scored": row["recent_goals_scored"],
            }
        return {
            "win_rate": self.DEFAULT_WIN_RATE,
            "draw_rate": 0.33,
            "avg_goals_scored": self.DEFAULT_AVG_GOALS_SCORED,
            "avg_goals_conceded": self.DEFAULT_AVG_GOALS_CONCEDED,
            "recent_win_rate": self.DEFAULT_WIN_RATE,
            "recent_goals_scored": self.DEFAULT_AVG_GOALS_SCORED,
        }

    def _get_ranking(self, team_name: str) -> tuple[int, float]:
        """Look up FIFA ranking for a team by name."""
        if team_name and team_name in _FIFA_RANKINGS:
            return _FIFA_RANKINGS[team_name]
        return DEFAULT_RANK, DEFAULT_POINTS

    def _get_h2h(
        self, home_id: int, away_id: int, matches_df: pd.DataFrame | None
    ) -> tuple[float, float]:
        """Compute head-to-head record between two teams.

        Returns (home_win_rate, draw_rate) from their historical encounters.
        """
        if matches_df is None or matches_df.empty:
            return 0.5, 0.25  # neutral default

        # Find matches between these two teams (in either direction)
        h2h = matches_df[
            ((matches_df["home_team_id"] == home_id) & (matches_df["away_team_id"] == away_id)) |
            ((matches_df["home_team_id"] == away_id) & (matches_df["away_team_id"] == home_id))
        ]

        if len(h2h) == 0:
            return 0.5, 0.25

        home_wins = 0
        draws = 0
        total = len(h2h)

        for _, match in h2h.iterrows():
            if match["home_score"] == match["away_score"]:
                draws += 1
            elif match["home_team_id"] == home_id and match["home_score"] > match["away_score"]:
                home_wins += 1
            elif match["away_team_id"] == home_id and match["away_score"] > match["home_score"]:
                home_wins += 1

        return home_wins / total, draws / total
