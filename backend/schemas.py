"""Pydantic response models for the World Cup Predictor API."""

from pydantic import BaseModel


class Team(BaseModel):
    """A team in the group stage standings."""

    team_id: int
    team_name: str
    crest: str  # SVG URL or empty string


class Group(BaseModel):
    """A World Cup group containing teams."""

    group_name: str  # "A" through "L"
    teams: list[Team]


class GroupsResponse(BaseModel):
    """Response model for the /api/groups endpoint."""

    groups: list[Group]


class MatchPrediction(BaseModel):
    """A single match prediction with win/draw/loss probabilities."""

    home_team_name: str
    away_team_name: str
    home_win_prob: float  # Probability of home team winning, bounded [0.0, 1.0]
    draw_prob: float  # Probability of a draw, bounded [0.0, 1.0]
    away_win_prob: float  # Probability of away team winning, bounded [0.0, 1.0]
    home_loss_prob: float  # away_win_prob + draw_prob (backward compat)
    home_team_crest: str
    away_team_crest: str
    match_date: str  # ISO 8601 format


class PredictionsResponse(BaseModel):
    """Response model for the /api/predictions endpoint."""

    predictions: list[MatchPrediction]


class KnockoutTeam(BaseModel):
    """A team in the knockout bracket. Uses 'TBD' for undetermined teams."""

    team_name: str  # "TBD" for undetermined
    crest: str  # empty string for undetermined


class KnockoutMatch(BaseModel):
    """A single knockout stage match."""

    home_team: KnockoutTeam
    away_team: KnockoutTeam
    status: str  # SCHEDULED | TIMED | IN_PLAY | FINISHED
    home_score: int | None = None
    away_score: int | None = None


class KnockoutRound(BaseModel):
    """A round in the knockout stage containing multiple matches."""

    round_name: str  # Round_of_32, Round_of_16, Quarter_Finals, Semi_Finals, Final
    matches: list[KnockoutMatch]


class KnockoutResponse(BaseModel):
    """Response model for the /api/knockout endpoint."""

    rounds: list[KnockoutRound]
