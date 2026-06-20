"""Knockout bracket route handler."""

from fastapi import APIRouter

from backend.error_handling import handle_api_error
from backend.schemas import KnockoutResponse
from backend.services import get_knockout_data

router = APIRouter()


@router.get("/api/knockout", response_model=KnockoutResponse)
async def get_knockout() -> KnockoutResponse:
    """Fetch and return the knockout bracket structure.

    Returns knockout stage matches organized by round, from Round_of_32
    through to the Final. Undetermined teams are shown as "TBD".
    Scores are included only for FINISHED matches.
    """
    try:
        return get_knockout_data()
    except Exception as e:
        raise handle_api_error(e)
