"""API client for the football-data.org v4 API."""

import time
import logging

import requests

from src.exceptions import APIError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class APIClient:
    """Client for fetching match data from football-data.org.

    Respects rate limiting using response headers:
    - X-RequestsAvailable: remaining requests before being blocked
    - X-RequestCounter-Reset: seconds until counter resets
    """

    def __init__(self, api_key: str, base_url: str = "https://api.football-data.org/v4"):
        """Initialize with API key for X-Auth-Token header.

        Args:
            api_key: The API key for authenticating with football-data.org.
            base_url: The base URL of the football-data.org API.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Auth-Token": api_key}
        self._requests_available: int | None = None
        self._counter_reset_at: float | None = None

    def _update_rate_limit(self, response: requests.Response):
        """Track rate limit state from response headers."""
        available = response.headers.get("X-RequestsAvailable")
        reset_secs = response.headers.get("X-RequestCounter-Reset")

        if available is not None:
            try:
                self._requests_available = int(available)
            except (ValueError, TypeError):
                pass

        if reset_secs is not None:
            try:
                self._counter_reset_at = time.time() + int(reset_secs)
            except (ValueError, TypeError):
                pass

        logger.info(
            "Rate limit: %s requests available, resets in %s sec",
            available, reset_secs
        )

    def _wait_if_needed(self):
        """Proactively wait if we're nearly out of requests."""
        if self._requests_available is not None and self._requests_available <= 2:
            if self._counter_reset_at is not None:
                wait_time = self._counter_reset_at - time.time()
                if wait_time > 0:
                    logger.warning(
                        "Only %d requests left. Waiting %.1f sec for reset...",
                        self._requests_available, wait_time
                    )
                    time.sleep(wait_time + 1)
                    self._requests_available = None
                    self._counter_reset_at = None

    def get_matches(self, competition_id: int, timeout: int = 60) -> dict:
        """Fetch all matches for a competition.

        Args:
            competition_id: The football-data.org competition ID.
            timeout: Request timeout in seconds.

        Returns:
            Raw JSON dict from /v4/competitions/{competition_id}/matches.

        Raises:
            AuthenticationError: If the API key is invalid (401/403).
            RateLimitError: If rate limit retries are exhausted (429).
            APIError: For other HTTP errors or timeout.
        """
        url = f"{self._base_url}/competitions/{competition_id}/matches"
        return self._request_with_retry(url, max_retries=3, timeout=timeout)

    def _request_with_retry(self, url: str, max_retries: int = 3, timeout: int = 60) -> dict:
        """Execute GET request with rate-limit awareness and retry logic.

        Checks X-RequestsAvailable before each request and waits if nearly
        exhausted. Uses X-RequestCounter-Reset to determine wait time.
        Raises AuthenticationError for 401/403 without retrying.
        Raises RateLimitError after max retries exhausted.
        Raises APIError for other HTTP errors.

        Args:
            url: The full URL to request.
            max_retries: Maximum number of retries on rate limit (429).
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON response as a dict.
        """
        retries = 0

        while True:
            # Proactively wait if we know we're low on requests
            self._wait_if_needed()

            try:
                logger.debug("GET %s (attempt %d)", url, retries + 1)
                response = requests.get(url, headers=self._headers, timeout=timeout)
            except requests.exceptions.Timeout:
                raise APIError(408, f"Request timed out after {timeout} seconds")
            except requests.exceptions.RequestException as e:
                raise APIError(0, f"Request failed: {str(e)}")

            # Always update rate limit tracking from response
            self._update_rate_limit(response)

            if response.status_code == 200:
                return response.json()

            # Authentication errors - no retry
            if response.status_code in (401, 403):
                message = self._extract_error_message(response)
                raise AuthenticationError(
                    response.status_code,
                    message,
                )

            # Rate limit - use X-RequestCounter-Reset for wait time
            if response.status_code == 429:
                retries += 1
                if retries >= max_retries:
                    raise RateLimitError(
                        429,
                        f"Rate limit exceeded after {max_retries} retries",
                    )
                # Use X-RequestCounter-Reset header for precise wait time
                reset_secs = response.headers.get("X-RequestCounter-Reset")
                retry_after = response.headers.get("Retry-After")
                if reset_secs:
                    wait_time = int(reset_secs) + 1
                elif retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = 2 ** retries
                logger.warning(
                    "Rate limited (429). Waiting %d seconds before retry %d/%d",
                    wait_time, retries, max_retries
                )
                time.sleep(wait_time)
                continue

            # All other HTTP errors
            message = self._extract_error_message(response)
            raise APIError(response.status_code, message)

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract error message from API response.

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
