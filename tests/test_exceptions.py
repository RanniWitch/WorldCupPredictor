"""Unit tests for the custom exception hierarchy."""

import pytest

from src.exceptions import (
    APIError,
    AuthenticationError,
    InsufficientDataError,
    NoTrainingDataError,
    NotFittedError,
    RateLimitError,
    SingleClassError,
    WorldCupPredictorError,
)


class TestExceptionHierarchy:
    """Test that exceptions follow the correct inheritance hierarchy."""

    def test_base_exception_is_exception(self):
        assert issubclass(WorldCupPredictorError, Exception)

    def test_api_error_inherits_from_base(self):
        assert issubclass(APIError, WorldCupPredictorError)

    def test_authentication_error_inherits_from_api_error(self):
        assert issubclass(AuthenticationError, APIError)

    def test_rate_limit_error_inherits_from_api_error(self):
        assert issubclass(RateLimitError, APIError)

    def test_insufficient_data_error_inherits_from_base(self):
        assert issubclass(InsufficientDataError, WorldCupPredictorError)

    def test_single_class_error_inherits_from_insufficient_data(self):
        assert issubclass(SingleClassError, InsufficientDataError)

    def test_not_fitted_error_inherits_from_base(self):
        assert issubclass(NotFittedError, WorldCupPredictorError)

    def test_no_training_data_error_inherits_from_base(self):
        assert issubclass(NoTrainingDataError, WorldCupPredictorError)


class TestAPIError:
    """Test APIError attributes and message formatting."""

    def test_status_code_attribute(self):
        err = APIError(404, "Not found")
        assert err.status_code == 404

    def test_message_format(self):
        err = APIError(500, "Internal server error")
        assert str(err) == "API error 500: Internal server error"

    def test_catchable_as_base_error(self):
        with pytest.raises(WorldCupPredictorError):
            raise APIError(400, "Bad request")


class TestAuthenticationError:
    """Test AuthenticationError inherits APIError behavior."""

    def test_status_code_attribute(self):
        err = AuthenticationError(401, "Unauthorized")
        assert err.status_code == 401

    def test_message_format(self):
        err = AuthenticationError(403, "Forbidden")
        assert str(err) == "API error 403: Forbidden"

    def test_catchable_as_api_error(self):
        with pytest.raises(APIError):
            raise AuthenticationError(401, "Unauthorized")


class TestRateLimitError:
    """Test RateLimitError inherits APIError behavior."""

    def test_status_code_attribute(self):
        err = RateLimitError(429, "Too many requests")
        assert err.status_code == 429

    def test_catchable_as_api_error(self):
        with pytest.raises(APIError):
            raise RateLimitError(429, "Too many requests")


class TestInsufficientDataError:
    """Test InsufficientDataError."""

    def test_message(self):
        err = InsufficientDataError("Need at least 10 records")
        assert "10 records" in str(err)

    def test_catchable_as_base_error(self):
        with pytest.raises(WorldCupPredictorError):
            raise InsufficientDataError("Not enough data")


class TestSingleClassError:
    """Test SingleClassError inherits from InsufficientDataError."""

    def test_message(self):
        err = SingleClassError("Only one class in labels")
        assert "one class" in str(err)

    def test_catchable_as_insufficient_data(self):
        with pytest.raises(InsufficientDataError):
            raise SingleClassError("Only one class")

    def test_catchable_as_base_error(self):
        with pytest.raises(WorldCupPredictorError):
            raise SingleClassError("Only one class")


class TestNotFittedError:
    """Test NotFittedError."""

    def test_message(self):
        err = NotFittedError("Scaler not fitted")
        assert "not fitted" in str(err)

    def test_catchable_as_base_error(self):
        with pytest.raises(WorldCupPredictorError):
            raise NotFittedError("Model not trained")


class TestNoTrainingDataError:
    """Test NoTrainingDataError."""

    def test_message(self):
        err = NoTrainingDataError("No finished matches available")
        assert "finished matches" in str(err)

    def test_catchable_as_base_error(self):
        with pytest.raises(WorldCupPredictorError):
            raise NoTrainingDataError("No data")
