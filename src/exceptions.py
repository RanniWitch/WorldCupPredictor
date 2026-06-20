"""Custom exception hierarchy for the World Cup Predictor."""


class WorldCupPredictorError(Exception):
    """Base exception for all predictor errors."""


class APIError(WorldCupPredictorError):
    """Raised when the football-data.org API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")


class AuthenticationError(APIError):
    """Raised when the API key is invalid or expired (401/403)."""


class RateLimitError(APIError):
    """Raised when rate limit retries are exhausted (429)."""


class InsufficientDataError(WorldCupPredictorError):
    """Raised when training data is insufficient (<10 records or single class)."""


class SingleClassError(InsufficientDataError):
    """Raised when training labels contain only one class."""


class NotFittedError(WorldCupPredictorError):
    """Raised when Scaler or Model is used before fitting/training."""


class NoTrainingDataError(WorldCupPredictorError):
    """Raised when no finished matches are available for training."""
