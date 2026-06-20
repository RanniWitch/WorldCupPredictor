"""Data pipeline for parsing raw API responses into structured DataFrames."""

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Schema columns for the finished matches DataFrame
MATCH_COLUMNS = ["home_team_id", "away_team_id", "home_score", "away_score", "match_date"]


class DataPipeline:
    """Transforms raw football-data.org API responses into structured DataFrames."""

    def parse_matches(self, raw_response: dict) -> pd.DataFrame:
        """
        Parse raw API response into a DataFrame of finished matches.

        Returns DataFrame with columns:
            - home_team_id: int
            - away_team_id: int
            - home_score: int
            - away_score: int
            - match_date: datetime

        Excludes matches with status != "FINISHED".
        Excludes matches with null/missing scores (logs warning).
        Returns empty DataFrame with correct schema if no finished matches.
        """
        matches = raw_response.get("matches", [])
        parsed_records = []

        for match in matches:
            status = match.get("status")
            if status != "FINISHED":
                continue

            # Extract score fields
            score = match.get("score", {})
            full_time = score.get("fullTime", {}) if score else {}
            home_score = full_time.get("home") if full_time else None
            away_score = full_time.get("away") if full_time else None

            # Exclude matches with null/missing scores
            if home_score is None or away_score is None:
                match_id = match.get("id", "unknown")
                logger.warning(
                    "Excluding match %s: missing or null score fields", match_id
                )
                continue

            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})

            home_team_id = home_team.get("id")
            away_team_id = away_team.get("id")

            # Exclude matches with missing team IDs
            if home_team_id is None or away_team_id is None:
                match_id = match.get("id", "unknown")
                logger.warning(
                    "Excluding match %s: missing team ID", match_id
                )
                continue

            parsed_records.append(
                {
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "match_date": datetime.fromisoformat(
                        match["utcDate"].replace("Z", "+00:00")
                    ),
                }
            )

        if not parsed_records:
            return pd.DataFrame(columns=MATCH_COLUMNS)

        df = pd.DataFrame(parsed_records, columns=MATCH_COLUMNS)
        df["home_team_id"] = df["home_team_id"].astype(int)
        df["away_team_id"] = df["away_team_id"].astype(int)
        df["home_score"] = df["home_score"].astype(int)
        df["away_score"] = df["away_score"].astype(int)
        return df

    def get_scheduled_matches(self, raw_response: dict) -> list[dict]:
        """
        Extract scheduled matches for prediction.

        Returns list of dicts with keys:
            - home_team_id: int
            - away_team_id: int
            - home_team_name: str
            - away_team_name: str
            - home_team_crest: str (URL to flag/crest SVG)
            - away_team_crest: str (URL to flag/crest SVG)
            - match_date: datetime

        Includes matches with status SCHEDULED or TIMED (confirmed kickoff time).
        """
        matches = raw_response.get("matches", [])
        scheduled = []

        for match in matches:
            status = match.get("status")
            if status not in ("SCHEDULED", "TIMED"):
                continue

            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})

            home_team_id = home_team.get("id")
            away_team_id = away_team.get("id")

            # Skip matches with missing team IDs (e.g., TBD placeholders)
            if home_team_id is None or away_team_id is None:
                continue

            scheduled.append(
                {
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "home_team_name": home_team.get("name", "Unknown"),
                    "away_team_name": away_team.get("name", "Unknown"),
                    "home_team_crest": home_team.get("crest", ""),
                    "away_team_crest": away_team.get("crest", ""),
                    "match_date": datetime.fromisoformat(
                        match["utcDate"].replace("Z", "+00:00")
                    ),
                }
            )

        return scheduled
