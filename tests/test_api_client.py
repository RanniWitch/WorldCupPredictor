"""Unit tests for APIClient.

Tests verify error handling, retry logic, and correct exception types
for the football-data.org API client.
"""

from unittest.mock import patch, MagicMock

import pytest
import requests

from src.api_client import APIClient
from src.exceptions import APIError, AuthenticationError, RateLimitError


@pytest.fixture
def client():
    """Return an APIClient instance with a test API key."""
    return APIClient(api_key="test-api-key-123")


class TestAPIClientSuccess:
    """Tests for successful API responses."""

    @patch("src.api_client.requests.get")
    def test_successful_response_returns_parsed_json(self, mock_get, client):
        """A 200 response should return parsed JSON dict."""
        expected_data = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2022-11-20T16:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 100, "name": "Team A"},
                    "awayTeam": {"id": 200, "name": "Team B"},
                    "score": {"fullTime": {"home": 2, "away": 1}},
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_get.return_value = mock_response

        result = client.get_matches(competition_id=2000)

        assert result == expected_data
        mock_get.assert_called_once_with(
            "https://api.football-data.org/v4/competitions/2000/matches",
            headers={"X-Auth-Token": "test-api-key-123"},
            timeout=60,
        )

    @patch("src.api_client.requests.get")
    def test_successful_response_with_custom_timeout(self, mock_get, client):
        """Custom timeout is passed to the requests call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_get.return_value = mock_response

        client.get_matches(competition_id=2001, timeout=30)

        mock_get.assert_called_once_with(
            "https://api.football-data.org/v4/competitions/2001/matches",
            headers={"X-Auth-Token": "test-api-key-123"},
            timeout=30,
        )


class TestAPIClientAuthentication:
    """Tests for authentication error handling (401/403)."""

    @patch("src.api_client.requests.get")
    def test_401_raises_authentication_error(self, mock_get, client):
        """HTTP 401 should raise AuthenticationError immediately."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)
        # Should not retry - only one call
        assert mock_get.call_count == 1

    @patch("src.api_client.requests.get")
    def test_403_raises_authentication_error(self, mock_get, client):
        """HTTP 403 should raise AuthenticationError immediately."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Access denied"}
        mock_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)
        # Should not retry - only one call
        assert mock_get.call_count == 1


class TestAPIClientRateLimit:
    """Tests for rate limit (429) retry logic."""

    @patch("src.api_client.time.sleep")
    @patch("src.api_client.requests.get")
    def test_429_retries_up_to_3_times_then_raises(self, mock_get, mock_sleep, client):
        """HTTP 429 should retry up to max_retries times then raise RateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value)
        # 1st call -> 429, retry 1, sleep -> 2nd call -> 429, retry 2, sleep -> 3rd call -> 429, retry 3 >= max, raise
        assert mock_get.call_count == 3
        # sleep called before each retry attempt
        assert mock_sleep.call_count == 2

    @patch("src.api_client.time.sleep")
    @patch("src.api_client.requests.get")
    def test_429_then_success_returns_data(self, mock_get, mock_sleep, client):
        """Rate limit followed by success should return the data."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"matches": []}

        # First call hits rate limit, second succeeds
        mock_get.side_effect = [rate_limit_response, success_response]

        result = client.get_matches(competition_id=2000)

        assert result == {"matches": []}
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("src.api_client.time.sleep")
    @patch("src.api_client.requests.get")
    def test_429_uses_retry_after_header(self, mock_get, mock_sleep, client):
        """Rate limit response with Retry-After header should use that wait time."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "5"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"matches": []}

        mock_get.side_effect = [rate_limit_response, success_response]

        client.get_matches(competition_id=2000)

        mock_sleep.assert_called_once_with(5)


class TestAPIClientHTTPErrors:
    """Tests for other HTTP errors raising APIError."""

    @patch("src.api_client.requests.get")
    def test_500_raises_api_error_with_status_code(self, mock_get, client):
        """HTTP 500 should raise APIError with status code and message."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        mock_get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @patch("src.api_client.requests.get")
    def test_404_raises_api_error(self, mock_get, client):
        """HTTP 404 should raise APIError with appropriate message."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Competition not found"}
        mock_get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            client.get_matches(competition_id=9999)

        assert exc_info.value.status_code == 404
        assert "Competition not found" in str(exc_info.value)

    @patch("src.api_client.requests.get")
    def test_502_raises_api_error(self, mock_get, client):
        """HTTP 502 should raise APIError."""
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.return_value = {"error": "Bad Gateway"}
        mock_get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 502
        assert "Bad Gateway" in str(exc_info.value)


class TestAPIClientTimeout:
    """Tests for request timeout handling."""

    @patch("src.api_client.requests.get")
    def test_timeout_raises_api_error(self, mock_get, client):
        """Request timeout should raise APIError with timeout info."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with pytest.raises(APIError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 408
        assert "timed out" in str(exc_info.value)

    @patch("src.api_client.requests.get")
    def test_connection_error_raises_api_error(self, mock_get, client):
        """Connection errors should raise APIError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(APIError) as exc_info:
            client.get_matches(competition_id=2000)

        assert exc_info.value.status_code == 0
        assert "Request failed" in str(exc_info.value)


class TestAPIClientHeaders:
    """Tests for correct request headers."""

    @patch("src.api_client.requests.get")
    def test_sends_auth_token_header(self, mock_get):
        """Requests should include X-Auth-Token header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_get.return_value = mock_response

        client = APIClient(api_key="my-secret-key")
        client.get_matches(competition_id=2000)

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"] == {"X-Auth-Token": "my-secret-key"}

    @patch("src.api_client.requests.get")
    def test_custom_base_url(self, mock_get):
        """Custom base URL should be used in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_get.return_value = mock_response

        client = APIClient(api_key="key", base_url="https://custom-api.example.com/v4")
        client.get_matches(competition_id=100)

        call_args = mock_get.call_args[0]
        assert call_args[0] == "https://custom-api.example.com/v4/competitions/100/matches"
