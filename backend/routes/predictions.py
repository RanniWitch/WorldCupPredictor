"""Predictions route handler for the World Cup Predictor API."""

import logging

from fastapi import APIRouter

from backend.error_handling import handle_api_error
from backend.schemas import PredictionsResponse
from backend.services import get_predictions

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/predictions", response_model=PredictionsResponse)
async def predictions() -> PredictionsResponse:
    """Run prediction engine and return match predictions.

    Returns a list of match predictions sorted by match_date ascending.
    Returns an empty predictions array with status 200 when no scheduled
    matches exist.
    """
    try:
        return get_predictions()
    except Exception as e:
        logger.exception("Error fetching predictions: %s", e)
        raise handle_api_error(e)
