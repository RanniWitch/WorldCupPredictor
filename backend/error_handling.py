"""Error handling utility for mapping upstream exceptions to HTTP responses."""

from fastapi import HTTPException

from src.exceptions import APIError, AuthenticationError, NoTrainingDataError, RateLimitError


def handle_api_error(e: Exception) -> HTTPException:
    """Map upstream exceptions to appropriate HTTP error responses.

    Args:
        e: The exception raised by the upstream service or prediction engine.

    Returns:
        An HTTPException with an appropriate status code and detail message.
    """
    if isinstance(e, AuthenticationError):
        return HTTPException(status_code=502, detail="Upstream authentication failed")
    elif isinstance(e, RateLimitError):
        return HTTPException(status_code=503, detail="Rate limit exceeded, try again later")
    elif isinstance(e, APIError) and e.status_code == 408:
        return HTTPException(status_code=504, detail="Upstream service timeout")
    elif isinstance(e, APIError):
        return HTTPException(status_code=502, detail=str(e))
    elif isinstance(e, NoTrainingDataError):
        return HTTPException(status_code=503, detail="Insufficient data for predictions")
    elif isinstance(e, (KeyError, ValueError)):
        return HTTPException(status_code=502, detail="Invalid upstream response")
    else:
        return HTTPException(status_code=502, detail="Invalid upstream response")
