"""Feature engineering for team performance statistics."""

import pandas as pd


class FeatureEngine:
    """Computes team performance statistics from historical match data."""

    DEFAULT_WIN_RATE = 0.5
    DEFAULT_AVG_GOALS_SCORED = 0.0
    DEFAULT_AVG_GOALS_CONCEDED = 0.0

    def compute_features(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-team features from historical match data.

        Returns DataFrame indexed by team_id with columns:
            - win_rate: float (wins / total_matches)
            - avg_goals_scored: float (total_goals_scored / total_matches)
            - avg_goals_conceded: float (total_goals_conceded / total_matches)

        Teams are counted for both home and away appearances.
        """
        if matches_df.empty:
            return pd.DataFrame(
                columns=["win_rate", "avg_goals_scored", "avg_goals_conceded"],
                index=pd.Index([], name="team_id"),
            )

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
                records.append(
                    {
                        "team_id": team_id,
                        "win_rate": self.DEFAULT_WIN_RATE,
                        "avg_goals_scored": self.DEFAULT_AVG_GOALS_SCORED,
                        "avg_goals_conceded": self.DEFAULT_AVG_GOALS_CONCEDED,
                    }
                )
                continue

            # Count wins: home wins (home_score > away_score) + away wins (away_score > home_score)
            home_wins = (
                (home_matches["home_score"] > home_matches["away_score"]).sum()
            )
            away_wins = (
                (away_matches["away_score"] > away_matches["home_score"]).sum()
            )
            total_wins = home_wins + away_wins

            # Goals scored: as home team it's home_score, as away team it's away_score
            goals_scored_home = home_matches["home_score"].sum()
            goals_scored_away = away_matches["away_score"].sum()
            total_goals_scored = goals_scored_home + goals_scored_away

            # Goals conceded: as home team it's away_score, as away team it's home_score
            goals_conceded_home = home_matches["away_score"].sum()
            goals_conceded_away = away_matches["home_score"].sum()
            total_goals_conceded = goals_conceded_home + goals_conceded_away

            records.append(
                {
                    "team_id": team_id,
                    "win_rate": total_wins / total_matches,
                    "avg_goals_scored": total_goals_scored / total_matches,
                    "avg_goals_conceded": total_goals_conceded / total_matches,
                }
            )

        features_df = pd.DataFrame(records)
        features_df = features_df.set_index("team_id")
        return features_df

    def get_match_features(
        self, home_team_id: int, away_team_id: int, features_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Build a single-row feature vector for a match.

        Returns DataFrame with columns:
            - home_win_rate, home_avg_goals_scored, home_avg_goals_conceded
            - away_win_rate, away_avg_goals_scored, away_avg_goals_conceded

        Uses default values for teams not found in features_df.
        """
        # Get home team features
        if home_team_id in features_df.index:
            home_features = features_df.loc[home_team_id]
            home_win_rate = home_features["win_rate"]
            home_avg_goals_scored = home_features["avg_goals_scored"]
            home_avg_goals_conceded = home_features["avg_goals_conceded"]
        else:
            home_win_rate = self.DEFAULT_WIN_RATE
            home_avg_goals_scored = self.DEFAULT_AVG_GOALS_SCORED
            home_avg_goals_conceded = self.DEFAULT_AVG_GOALS_CONCEDED

        # Get away team features
        if away_team_id in features_df.index:
            away_features = features_df.loc[away_team_id]
            away_win_rate = away_features["win_rate"]
            away_avg_goals_scored = away_features["avg_goals_scored"]
            away_avg_goals_conceded = away_features["avg_goals_conceded"]
        else:
            away_win_rate = self.DEFAULT_WIN_RATE
            away_avg_goals_scored = self.DEFAULT_AVG_GOALS_SCORED
            away_avg_goals_conceded = self.DEFAULT_AVG_GOALS_CONCEDED

        return pd.DataFrame(
            [
                {
                    "home_win_rate": home_win_rate,
                    "home_avg_goals_scored": home_avg_goals_scored,
                    "home_avg_goals_conceded": home_avg_goals_conceded,
                    "away_win_rate": away_win_rate,
                    "away_avg_goals_scored": away_avg_goals_scored,
                    "away_avg_goals_conceded": away_avg_goals_conceded,
                }
            ]
        )
