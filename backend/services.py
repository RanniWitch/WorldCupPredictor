"""Service layer for the World Cup Predictor backend.

Provides business logic functions that fetch data from football-data.org
and transform it into structured response models.
"""

import os
import time
import threading
import logging

import requests

from src.api_client import APIClient
from src.exceptions import APIError, AuthenticationError, RateLimitError
from src.predictor import Predictor
from backend.schemas import (
    KnockoutMatch,
    KnockoutResponse,
    KnockoutRound,
    KnockoutTeam,
    MatchPrediction,
    PredictionsResponse,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"

# Simple in-memory cache to avoid hammering the rate-limited API
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str):
    """Return cached value if still valid, else None."""
    if key in _cache:
        ts, value = _cache[key]
        if time.time() - ts < CACHE_TTL:
            logger.debug("Cache hit for %s", key)
            return value
        del _cache[key]
    return None


def _set_cached(key: str, value: object):
    """Store a value in cache with current timestamp."""
    _cache[key] = (time.time(), value)


# --- Rate limit tracking using football-data.org response headers ---
# X-RequestsAvailable: remaining requests before being blocked
# X-RequestCounter-Reset: seconds left until the counter resets

_rate_limit_lock = threading.Lock()
_requests_available: int | None = None
_counter_reset_at: float | None = None  # time.time() when counter resets

# Minimum available requests before we proactively wait
_MIN_REQUESTS_BEFORE_WAIT = 2


def _update_rate_limit_from_headers(headers: dict):
    """Update rate limit state from football-data.org response headers."""
    global _requests_available, _counter_reset_at

    available = headers.get("X-RequestsAvailable") or headers.get("x-requestsavailable")
    reset_secs = headers.get("X-RequestCounter-Reset") or headers.get("x-requestcounter-reset")

    with _rate_limit_lock:
        if available is not None:
            try:
                _requests_available = int(available)
            except (ValueError, TypeError):
                pass

        if reset_secs is not None:
            try:
                _counter_reset_at = time.time() + int(reset_secs)
            except (ValueError, TypeError):
                pass

    logger.info(
        "Rate limit status: %s requests available, counter resets in %s seconds",
        available, reset_secs
    )


def _wait_if_rate_limited():
    """Block if we're about to hit the rate limit, waiting for the counter to reset."""
    global _requests_available, _counter_reset_at

    with _rate_limit_lock:
        if _requests_available is not None and _requests_available <= _MIN_REQUESTS_BEFORE_WAIT:
            if _counter_reset_at is not None:
                wait_time = _counter_reset_at - time.time()
                if wait_time > 0:
                    logger.warning(
                        "Rate limit nearly exhausted (%d remaining). "
                        "Waiting %.1f seconds for counter reset...",
                        _requests_available, wait_time
                    )
                    # Release lock while sleeping
                    _rate_limit_lock.release()
                    try:
                        time.sleep(wait_time + 1)  # +1 second buffer
                    finally:
                        _rate_limit_lock.acquire()
                    # Reset tracking after waiting
                    _requests_available = None
                    _counter_reset_at = None


def _rate_limited_get(url: str, headers: dict, timeout: int = 60) -> requests.Response:
    """Make a GET request with rate limit awareness.

    Checks if we're near the rate limit and waits if necessary.
    Updates rate limit tracking from response headers.

    Args:
        url: The URL to request.
        headers: Request headers (must include X-Auth-Token).
        timeout: Request timeout in seconds.

    Returns:
        The HTTP response object.

    Raises:
        APIError: On timeout or request failure.
    """
    _wait_if_rate_limited()

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        raise APIError(408, f"Request timed out after {timeout} seconds")
    except requests.exceptions.RequestException as e:
        raise APIError(0, f"Request failed: {str(e)}")

    # Update rate limit tracking from response headers
    _update_rate_limit_from_headers(dict(response.headers))

    return response


def _get_api_key() -> str:
    """Retrieve the football-data.org API key from environment.

    Returns:
        The API key string.

    Raises:
        ValueError: If FOOTBALL_DATA_API_KEY is not set.
    """
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("FOOTBALL_DATA_API_KEY environment variable is not set")
    return api_key


def _fetch_standings(competition_id: int) -> dict:
    """Fetch standings data from football-data.org.

    Args:
        competition_id: The competition ID (2000 for World Cup).

    Returns:
        Raw JSON response dict from the standings endpoint.

    Raises:
        AuthenticationError: If the API key is invalid (401/403).
        RateLimitError: If rate limit is exceeded (429).
        APIError: For other HTTP errors or timeouts.
    """
    api_key = _get_api_key()
    url = f"{BASE_URL}/competitions/{competition_id}/standings"
    headers = {"X-Auth-Token": api_key}

    response = _rate_limited_get(url, headers, timeout=60)

    if response.status_code == 200:
        return response.json()

    if response.status_code in (401, 403):
        message = _extract_error_message(response)
        raise AuthenticationError(response.status_code, message)

    if response.status_code == 429:
        # If we get 429 despite our checks, wait and retry once
        reset_secs = response.headers.get("X-RequestCounter-Reset", "60")
        try:
            wait = int(reset_secs) + 1
        except ValueError:
            wait = 60
        logger.warning("Got 429 on standings. Waiting %d seconds and retrying...", wait)
        time.sleep(wait)
        response = _rate_limited_get(url, headers, timeout=60)
        if response.status_code == 200:
            return response.json()
        raise RateLimitError(429, "Rate limit exceeded after retry")

    message = _extract_error_message(response)
    raise APIError(response.status_code, message)


def _extract_error_message(response: requests.Response) -> str:
    """Extract error message from an API response.

    Args:
        response: The HTTP response object.

    Returns:
        Error message string.
    """
    try:
        data = response.json()
        return data.get("message", data.get("error", response.text))
    except (ValueError, KeyError):
        return response.text or f"HTTP {response.status_code}"


def get_group_data() -> dict:
    """Fetch and parse World Cup 2026 group stage standings.

    Calls the football-data.org standings API for competition 2000,
    parses the response into groups A-L each with up to 4 teams.

    Returns:
        A dict matching GroupsResponse schema:
        {"groups": [{"group_name": "A", "teams": [...]}, ...]}

    Raises:
        AuthenticationError: If the API key is invalid.
        RateLimitError: If rate limit is exceeded.
        APIError: For other HTTP/API errors.
        KeyError/ValueError: If response structure is unexpected.
    """
    cached = _get_cached("groups")
    if cached is not None:
        return cached

    standings_data = _fetch_standings(2000)

    standings = standings_data.get("standings", [])

    groups = []
    for standing in standings:
        # Process standings entries — WC 2026 uses stage="ALL" and type="TOTAL"
        # with group names like "Group A" instead of "GROUP_A"
        if standing.get("type") != "TOTAL":
            continue

        stage = standing.get("stage", "")
        # Accept both "GROUP_STAGE" (historical) and "ALL" (WC 2026 format)
        if stage not in ("GROUP_STAGE", "ALL"):
            continue

        # Extract group letter: handles both "GROUP_A" and "Group A" formats
        group_raw = standing.get("group", "")
        if group_raw.startswith("GROUP_"):
            group_name = group_raw.replace("GROUP_", "")
        elif group_raw.startswith("Group "):
            group_name = group_raw.replace("Group ", "")
        else:
            group_name = group_raw

        table = standing.get("table", [])
        teams = []
        for entry in table:
            team_data = entry.get("team", {})
            teams.append({
                "team_id": team_data.get("id", 0),
                "team_name": team_data.get("name", "Unknown"),
                "crest": team_data.get("crest", ""),
            })

        groups.append({
            "group_name": group_name,
            "teams": teams,
        })

    # Sort groups alphabetically by group_name
    groups.sort(key=lambda g: g["group_name"])

    result = {"groups": groups}
    _set_cached("groups", result)
    return result


def get_predictions() -> PredictionsResponse:
    """Run prediction engine and return match predictions.

    Instantiates the Predictor with competition ID 2000,
    runs the prediction pipeline, and transforms the result DataFrame
    into a list of MatchPrediction objects sorted by match_date ascending.

    Returns:
        PredictionsResponse with predictions sorted by match_date.
        Returns empty predictions list if no scheduled matches exist.

    Raises:
        AuthenticationError: If the API key is invalid.
        RateLimitError: If rate limit is exceeded.
        APIError: For other upstream errors.
        NoTrainingDataError: If insufficient data exists for predictions.
    """
    api_key = _get_api_key()

    cached = _get_cached("predictions")
    if cached is not None:
        return cached

    predictor = Predictor(api_key=api_key)
    # Use supplementary international competition data for training when
    # the World Cup 2026 has insufficient finished matches.
    # 2018 = European Championship, 2152 = Copa America
    df = predictor.run(2000, training_competition_ids=[2018, 2152])

    if df.empty:
        return PredictionsResponse(predictions=[])

    predictions = [
        MatchPrediction(
            home_team_name=row["home_team_name"],
            away_team_name=row["away_team_name"],
            home_win_prob=float(row["home_win_prob"]),
            draw_prob=float(row["draw_prob"]),
            away_win_prob=float(row["away_win_prob"]),
            home_loss_prob=float(row["home_loss_prob"]),
            home_team_crest=row["home_team_crest"],
            away_team_crest=row["away_team_crest"],
            match_date=row["match_date"].isoformat(),
        )
        for _, row in df.iterrows()
    ]

    response = PredictionsResponse(predictions=predictions)
    _set_cached("predictions", response)
    return response


# Mapping from football-data.org stage names to our round names
KNOCKOUT_STAGE_MAP = {
    "ROUND_OF_32": "Round_of_32",
    "ROUND_OF_16": "Round_of_16",
    "QUARTER_FINALS": "Quarter_Finals",
    "SEMI_FINALS": "Semi_Finals",
    "FINAL": "Final",
}

# Ordered list of rounds for consistent output
KNOCKOUT_ROUND_ORDER = [
    "Round_of_32",
    "Round_of_16",
    "Quarter_Finals",
    "Semi_Finals",
    "Final",
]


def get_knockout_data() -> KnockoutResponse:
    """Fetch knockout stage matches and organize into rounds.

    Calls the football-data.org API to get all matches for competition 2000,
    filters for knockout stage matches, and organizes them into rounds.

    Uses "TBD" for undetermined team names and "" for undetermined crests.
    Scores are included only when match status is FINISHED.

    Returns:
        KnockoutResponse with rounds organized from Round_of_32 through Final.

    Raises:
        AuthenticationError: If the API key is invalid.
        RateLimitError: If rate limit is exceeded.
        APIError: For other upstream errors.
    """
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    cached = _get_cached("knockout")
    if cached is not None:
        return cached

    client = APIClient(api_key)
    data = client.get_matches(2000)

    matches = data.get("matches", [])

    # Group matches by round
    rounds_dict: dict[str, list[KnockoutMatch]] = {
        round_name: [] for round_name in KNOCKOUT_ROUND_ORDER
    }

    for match in matches:
        stage = match.get("stage", "")
        if stage not in KNOCKOUT_STAGE_MAP:
            continue

        round_name = KNOCKOUT_STAGE_MAP[stage]

        # Resolve home team
        home_team_data = match.get("homeTeam", {})
        if home_team_data.get("id") is not None:
            home_team = KnockoutTeam(
                team_name=home_team_data["name"],
                crest=home_team_data.get("crest", ""),
            )
        else:
            home_team = KnockoutTeam(team_name="TBD", crest="")

        # Resolve away team
        away_team_data = match.get("awayTeam", {})
        if away_team_data.get("id") is not None:
            away_team = KnockoutTeam(
                team_name=away_team_data["name"],
                crest=away_team_data.get("crest", ""),
            )
        else:
            away_team = KnockoutTeam(team_name="TBD", crest="")

        # Resolve scores
        status = match.get("status", "SCHEDULED")
        home_score = None
        away_score = None
        if status == "FINISHED":
            score = match.get("score", {})
            full_time = score.get("fullTime", {})
            home_score = full_time.get("home")
            away_score = full_time.get("away")

        knockout_match = KnockoutMatch(
            home_team=home_team,
            away_team=away_team,
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

        rounds_dict[round_name].append(knockout_match)

    # Build response with rounds in order
    rounds = [
        KnockoutRound(round_name=round_name, matches=rounds_dict[round_name])
        for round_name in KNOCKOUT_ROUND_ORDER
    ]

    response = KnockoutResponse(rounds=rounds)
    _set_cached("knockout", response)
    return response
