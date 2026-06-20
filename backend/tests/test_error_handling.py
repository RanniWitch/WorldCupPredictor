"""Unit tests for backend error handling utility."""

import pytest
from fastapi import HTTPException

from backend.error_handling import handle_api_error
from src.exceptions import (
    APIError,
    AuthenticationError,
    NoTrainingDataError,
    RateLimitError,
)


class TestHandleApiError:
    """Tests for handle_api_error mapping function."""

    def test_authentication_error_returns_502(self):
        error = AuthenticationError(401, "Unauthorized")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 502
        assert result.detail == "Upstream authentication failed"

    def test_rate_limit_error_returns_503(self):
        error = RateLimitError(429, "Too Many Requests")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 503
        assert result.detail == "Rate limit exceeded, try again later"

    def test_api_error_408_returns_504(self):
        error = APIError(408, "Request Timeout")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 504
        assert result.detail == "Upstream service timeout"

    def test_generic_api_error_returns_502_with_original_message(self):
        error = APIError(500, "Internal Server Error")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 502
        assert "500" in result.detail
        assert "Internal Server Error" in result.detail

    def test_no_training_data_error_returns_503(self):
        error = NoTrainingDataError("No finished matches")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 503
        assert result.detail == "Insufficient data for predictions"

    def test_key_error_returns_502(self):
        error = KeyError("missing_field")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 502
        assert result.detail == "Invalid upstream response"

    def test_value_error_returns_502(self):
        error = ValueError("invalid value")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 502
        assert result.detail == "Invalid upstream response"

    def test_unexpected_exception_returns_502(self):
        error = RuntimeError("unexpected")
        result = handle_api_error(error)
        assert isinstance(result, HTTPException)
        assert result.status_code == 502
        assert result.detail == "Invalid upstream response"
