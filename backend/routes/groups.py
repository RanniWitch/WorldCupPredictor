"""Groups route handler for the World Cup Predictor API."""

import logging

from fastapi import APIRouter

from backend.error_handling import handle_api_error
from backend.schemas import GroupsResponse
from backend.services import get_group_data

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/groups", response_model=GroupsResponse)
async def get_groups() -> GroupsResponse:
    """Fetch and return all World Cup 2026 groups.

    Returns group stage standings with teams A through L,
    each containing team_id, team_name, and crest URL.
    """
    try:
        data = get_group_data()
        return GroupsResponse(**data)
    except Exception as e:
        logger.exception("Error fetching groups: %s", e)
        raise handle_api_error(e)
