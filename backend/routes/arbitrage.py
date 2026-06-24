"""Arbitrage scanner route for detecting betting opportunities across bookmakers."""

import logging

from fastapi import APIRouter

from backend.error_handling import handle_api_error
from backend.services_arbitrage import scan_arbitrage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/arbitrage")
async def arbitrage(sport: str = "soccer_fifa_world_cup", markets: str = "h2h"):
    """Scan for arbitrage opportunities across bookmakers.

    Args:
        sport: The Odds API sport key to scan. Defaults to FIFA World Cup.
        markets: Comma-separated market keys (h2h, spreads, totals).

    Returns:
        List of events with arbitrage analysis including best odds per outcome,
        combined implied probability, and potential profit percentage.
    """
    try:
        return scan_arbitrage(sport, markets)
    except Exception as e:
        logger.exception("Error scanning arbitrage: %s", e)
        raise handle_api_error(e)


@router.get("/api/sports")
async def sports():
    """Get all available sports from The Odds API, grouped by active/inactive."""
    try:
        from backend.services_arbitrage import get_available_sports
        return get_available_sports()
    except Exception as e:
        logger.exception("Error fetching sports: %s", e)
        raise handle_api_error(e)


@router.get("/api/arbitrage/quick-scan")
async def quick_scan(markets: str = "h2h"):
    """Scan popular sports for arbitrage opportunities in one call."""
    try:
        from backend.services_arbitrage import scan_popular_sports
        return scan_popular_sports(markets)
    except Exception as e:
        logger.exception("Error in quick scan: %s", e)
        raise handle_api_error(e)
