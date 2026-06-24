"""Arbitrage scanning service using The Odds API.

Pulls live odds from multiple bookmakers, finds the best price for each
outcome across all books, and calculates whether a guaranteed profit
(arbitrage) exists.
"""

import logging
import os
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Cache to avoid burning API quota on repeated requests
_arb_cache: dict[str, tuple[float, object]] = {}
ARB_CACHE_TTL = 120  # 2 minutes (odds change fast)

# Sports cache — refreshed less often since sports don't change frequently
_sports_cache: dict[str, tuple[float, object]] = {}
SPORTS_CACHE_TTL = 3600  # 1 hour


def _get_odds_api_key() -> str:
    """Get The Odds API key from environment."""
    key = os.getenv("THE_ODDS_API_KEY")
    if not key:
        raise ValueError("THE_ODDS_API_KEY environment variable is not set")
    return key


def get_available_sports() -> dict:
    """Fetch all sports from The Odds API, grouped by active/inactive.

    The /sports endpoint is free (doesn't count against quota).
    Results are cached for 1 hour.

    Returns:
        Dict with keys:
        - active: list of active sport objects
        - inactive: list of inactive sport objects
    """
    cache_key = "all_sports"
    if cache_key in _sports_cache:
        ts, cached = _sports_cache[cache_key]
        if time.time() - ts < SPORTS_CACHE_TTL:
            return cached

    api_key = _get_odds_api_key()
    resp = requests.get(
        f"{ODDS_API_BASE}/sports/",
        params={"apiKey": api_key, "all": "true"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Odds API error {resp.status_code}: {resp.text}")

    sports = resp.json()

    active = []
    inactive = []

    for sport in sports:
        item = {
            "key": sport["key"],
            "title": sport["title"],
            "group": sport["group"],
            "description": sport.get("description", ""),
            "has_outrights": sport.get("has_outrights", False),
        }
        if sport.get("active", False):
            active.append(item)
        else:
            inactive.append(item)

    # Sort each list by group then title
    active.sort(key=lambda s: (s["group"], s["title"]))
    inactive.sort(key=lambda s: (s["group"], s["title"]))

    result = {"active": active, "inactive": inactive}
    _sports_cache[cache_key] = (time.time(), result)
    return result


def scan_arbitrage(sport: str = "soccer_fifa_world_cup", markets: str = "h2h") -> dict:
    """Scan a sport for arbitrage opportunities across bookmakers.

    Fetches odds from US bookmakers for the specified markets, finds the best
    price for each outcome, and identifies arbitrage opportunities.

    Args:
        sport: The Odds API sport key.
        markets: Comma-separated market keys (h2h, spreads, totals).

    Returns:
        Dict with keys:
        - events: list of event analyses
        - arbitrage_found: number of arb opportunities
        - total_events: total events scanned
        - quota_remaining: API requests remaining
    """
    cache_key = f"arb_{sport}_{markets}"
    if cache_key in _arb_cache:
        ts, cached = _arb_cache[cache_key]
        if time.time() - ts < ARB_CACHE_TTL:
            return cached

    api_key = _get_odds_api_key()

    resp = requests.get(
        f"{ODDS_API_BASE}/sports/{sport}/odds",
        params={
            "apiKey": api_key,
            "regions": "us,us2",
            "markets": markets,
            "oddsFormat": "decimal",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Odds API error {resp.status_code}: {resp.text}")

    quota_remaining = resp.headers.get("x-requests-remaining", "unknown")
    events_data = resp.json()

    results = []
    arb_count = 0

    market_list = [m.strip() for m in markets.split(",")]

    for event in events_data:
        for market_key in market_list:
            analysis = _analyze_event(event, market_key)
            if analysis:
                results.append(analysis)
                if analysis["is_arbitrage"]:
                    arb_count += 1

    # Sort: arbitrage opportunities first, then by profit margin descending
    results.sort(key=lambda x: (-x["is_arbitrage"], -x["profit_pct"]))

    response = {
        "events": results,
        "arbitrage_found": arb_count,
        "total_events": len(events_data),
        "quota_remaining": quota_remaining,
        "sport": sport,
        "markets": markets,
    }

    _arb_cache[cache_key] = (time.time(), response)
    return response


def _analyze_event(event: dict, market_key: str = "h2h") -> dict | None:
    """Analyze a single event for arbitrage across its bookmakers.

    For h2h (three-way): find best odds for home, draw, away.
    For spreads: find best odds for each side of the spread.
    For totals: find best odds for over/under.

    Returns dict with analysis or None if insufficient data.
    """
    bookmakers = event.get("bookmakers", [])
    if not bookmakers:
        return None

    home_team = event.get("home_team", "Unknown")
    away_team = event.get("away_team", "Unknown")
    commence_time = event.get("commence_time", "")

    if market_key == "h2h":
        return _analyze_h2h(event, bookmakers, home_team, away_team, commence_time)
    elif market_key == "spreads":
        return _analyze_spreads(event, bookmakers, home_team, away_team, commence_time)
    elif market_key == "totals":
        return _analyze_totals(event, bookmakers, home_team, away_team, commence_time)
    return None


def _analyze_h2h(event: dict, bookmakers: list, home_team: str, away_team: str, commence_time: str) -> dict | None:
    """Analyze head-to-head (moneyline) market."""
    best_home = {"price": 0.0, "bookmaker": ""}
    best_away = {"price": 0.0, "bookmaker": ""}
    best_draw = {"price": 0.0, "bookmaker": ""}
    all_odds: list[dict] = []

    for bookmaker in bookmakers:
        bk_name = bookmaker.get("title", bookmaker.get("key", "Unknown"))
        markets = bookmaker.get("markets", [])

        for market in markets:
            if market.get("key") != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            bk_odds = {"bookmaker": bk_name}

            for outcome in outcomes:
                name = outcome.get("name", "")
                price = outcome.get("price", 0)

                if name == home_team:
                    bk_odds["home"] = price
                    if price > best_home["price"]:
                        best_home = {"price": price, "bookmaker": bk_name}
                elif name == away_team:
                    bk_odds["away"] = price
                    if price > best_away["price"]:
                        best_away = {"price": price, "bookmaker": bk_name}
                elif name == "Draw":
                    bk_odds["draw"] = price
                    if price > best_draw["price"]:
                        best_draw = {"price": price, "bookmaker": bk_name}

            if "home" in bk_odds:
                all_odds.append(bk_odds)

    if best_home["price"] <= 1 or best_away["price"] <= 1:
        return None

    is_three_way = best_draw["price"] > 1
    if is_three_way:
        implied_prob = 1 / best_home["price"] + 1 / best_draw["price"] + 1 / best_away["price"]
    else:
        implied_prob = 1 / best_home["price"] + 1 / best_away["price"]

    is_arb = implied_prob < 1.0
    profit_pct = ((1 / implied_prob) - 1) * 100 if implied_prob > 0 else 0

    stakes = None
    if is_arb:
        budget = 100
        if is_three_way:
            stakes = {
                "budget": budget,
                "home": round(budget * (1 / best_home["price"]) / implied_prob, 2),
                "draw": round(budget * (1 / best_draw["price"]) / implied_prob, 2),
                "away": round(budget * (1 / best_away["price"]) / implied_prob, 2),
                "guaranteed_profit": round(budget * profit_pct / 100, 2),
            }
        else:
            stakes = {
                "budget": budget,
                "home": round(budget * (1 / best_home["price"]) / implied_prob, 2),
                "away": round(budget * (1 / best_away["price"]) / implied_prob, 2),
                "guaranteed_profit": round(budget * profit_pct / 100, 2),
            }

    return {
        "event_id": event.get("id", ""),
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "market": "h2h",
        "market_label": "Moneyline",
        "is_arbitrage": is_arb,
        "implied_probability": round(implied_prob * 100, 2),
        "profit_pct": round(profit_pct, 2),
        "best_odds": {
            "home": {"price": best_home["price"], "bookmaker": best_home["bookmaker"]},
            "away": {"price": best_away["price"], "bookmaker": best_away["bookmaker"]},
            "draw": {"price": best_draw["price"], "bookmaker": best_draw["bookmaker"]} if is_three_way else None,
        },
        "stakes": stakes,
        "bookmaker_count": len(all_odds),
        "all_bookmaker_odds": all_odds,
    }


def _analyze_spreads(event: dict, bookmakers: list, home_team: str, away_team: str, commence_time: str) -> dict | None:
    """Analyze point spread market for arbitrage."""
    # Group by spread point value, find best odds for each side
    spread_groups: dict[float, dict] = {}

    for bookmaker in bookmakers:
        bk_name = bookmaker.get("title", bookmaker.get("key", "Unknown"))
        markets = bookmaker.get("markets", [])

        for market in markets:
            if market.get("key") != "spreads":
                continue
            outcomes = market.get("outcomes", [])

            for outcome in outcomes:
                point = outcome.get("point", 0)
                price = outcome.get("price", 0)
                name = outcome.get("name", "")

                if point not in spread_groups:
                    spread_groups[point] = {
                        "best_price": 0, "best_book": "",
                        "opposite_best_price": 0, "opposite_best_book": "",
                        "team": name, "point": point,
                        "all_odds": [],
                    }

                # The opposite spread is -point for the other team
                neg_point = -point
                if neg_point not in spread_groups:
                    spread_groups[neg_point] = {
                        "best_price": 0, "best_book": "",
                        "opposite_best_price": 0, "opposite_best_book": "",
                        "team": "", "point": neg_point,
                        "all_odds": [],
                    }

                if price > spread_groups[point]["best_price"]:
                    spread_groups[point]["best_price"] = price
                    spread_groups[point]["best_book"] = bk_name
                    spread_groups[point]["team"] = name

                # This is also the opposite side for -point
                if price > spread_groups[neg_point]["opposite_best_price"]:
                    spread_groups[neg_point]["opposite_best_price"] = price
                    spread_groups[neg_point]["opposite_best_book"] = bk_name

    # Find best arb across all spread lines
    best_arb = None
    best_profit = -999

    for point, data in spread_groups.items():
        neg_point = -point
        if neg_point not in spread_groups:
            continue

        side_a_price = data["best_price"]
        side_b_price = spread_groups[neg_point]["best_price"]

        if side_a_price <= 1 or side_b_price <= 1:
            continue

        # Skip if both best odds are from the same bookmaker (likely data artifact)
        if data["best_book"] == spread_groups[neg_point]["best_book"]:
            continue

        implied = 1 / side_a_price + 1 / side_b_price
        profit = ((1 / implied) - 1) * 100 if implied > 0 else -100

        if profit > best_profit:
            best_profit = profit
            best_arb = {
                "point": point,
                "side_a_price": side_a_price,
                "side_a_book": data["best_book"],
                "side_a_team": data["team"],
                "side_b_price": side_b_price,
                "side_b_book": spread_groups[neg_point]["best_book"],
                "side_b_team": spread_groups[neg_point]["team"],
                "implied": implied,
                "profit_pct": profit,
            }

    if not best_arb:
        return None

    is_arb = best_arb["implied"] < 1.0
    stakes = None
    if is_arb:
        budget = 100
        implied = best_arb["implied"]
        stakes = {
            "budget": budget,
            "home": round(budget * (1 / best_arb["side_a_price"]) / implied, 2),
            "away": round(budget * (1 / best_arb["side_b_price"]) / implied, 2),
            "guaranteed_profit": round(budget * best_arb["profit_pct"] / 100, 2),
        }

    return {
        "event_id": event.get("id", "") + "_spreads",
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "market": "spreads",
        "market_label": f"Spread ({best_arb['side_a_team']} {best_arb['point']:+.1f})",
        "is_arbitrage": is_arb,
        "implied_probability": round(best_arb["implied"] * 100, 2),
        "profit_pct": round(best_arb["profit_pct"], 2),
        "best_odds": {
            "home": {"price": best_arb["side_a_price"], "bookmaker": best_arb["side_a_book"]},
            "away": {"price": best_arb["side_b_price"], "bookmaker": best_arb["side_b_book"]},
            "draw": None,
        },
        "stakes": stakes,
        "bookmaker_count": len(bookmakers),
        "all_bookmaker_odds": [],
    }


def _analyze_totals(event: dict, bookmakers: list, home_team: str, away_team: str, commence_time: str) -> dict | None:
    """Analyze over/under (totals) market for arbitrage."""
    # Group by total point value
    totals_groups: dict[float, dict] = {}

    for bookmaker in bookmakers:
        bk_name = bookmaker.get("title", bookmaker.get("key", "Unknown"))
        markets = bookmaker.get("markets", [])

        for market in markets:
            if market.get("key") != "totals":
                continue
            outcomes = market.get("outcomes", [])

            for outcome in outcomes:
                point = outcome.get("point", 0)
                price = outcome.get("price", 0)
                name = outcome.get("name", "")  # "Over" or "Under"

                if point not in totals_groups:
                    totals_groups[point] = {
                        "best_over": 0, "best_over_book": "",
                        "best_under": 0, "best_under_book": "",
                        "point": point,
                    }

                if name == "Over" and price > totals_groups[point]["best_over"]:
                    totals_groups[point]["best_over"] = price
                    totals_groups[point]["best_over_book"] = bk_name
                elif name == "Under" and price > totals_groups[point]["best_under"]:
                    totals_groups[point]["best_under"] = price
                    totals_groups[point]["best_under_book"] = bk_name

    # Find best arb across all total lines
    best_arb = None
    best_profit = -999

    for point, data in totals_groups.items():
        over_price = data["best_over"]
        under_price = data["best_under"]

        if over_price <= 1 or under_price <= 1:
            continue

        # Skip if both best odds are from the same bookmaker (likely data artifact)
        if data["best_over_book"] == data["best_under_book"]:
            continue

        implied = 1 / over_price + 1 / under_price
        profit = ((1 / implied) - 1) * 100 if implied > 0 else -100

        if profit > best_profit:
            best_profit = profit
            best_arb = {
                "point": point,
                "over_price": over_price,
                "over_book": data["best_over_book"],
                "under_price": under_price,
                "under_book": data["best_under_book"],
                "implied": implied,
                "profit_pct": profit,
            }

    if not best_arb:
        return None

    is_arb = best_arb["implied"] < 1.0
    stakes = None
    if is_arb:
        budget = 100
        implied = best_arb["implied"]
        stakes = {
            "budget": budget,
            "home": round(budget * (1 / best_arb["over_price"]) / implied, 2),
            "away": round(budget * (1 / best_arb["under_price"]) / implied, 2),
            "guaranteed_profit": round(budget * best_arb["profit_pct"] / 100, 2),
        }

    return {
        "event_id": event.get("id", "") + "_totals",
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "market": "totals",
        "market_label": f"Total Goals O/U {best_arb['point']}",
        "is_arbitrage": is_arb,
        "implied_probability": round(best_arb["implied"] * 100, 2),
        "profit_pct": round(best_arb["profit_pct"], 2),
        "best_odds": {
            "home": {"price": best_arb["over_price"], "bookmaker": best_arb["over_book"]},
            "away": {"price": best_arb["under_price"], "bookmaker": best_arb["under_book"]},
            "draw": None,
        },
        "stakes": stakes,
        "bookmaker_count": len(bookmakers),
        "all_bookmaker_odds": [],
    }


# Popular sports for quick scan — high liquidity, many bookmakers, best arb potential
POPULAR_SPORTS = [
    "soccer_fifa_world_cup",
    "soccer_epl",
    "soccer_italy_serie_a",
    "americanfootball_nfl",
    "baseball_mlb",
    "basketball_wnba",
    "mma_mixed_martial_arts",
]


def scan_popular_sports(markets: str = "h2h") -> dict:
    """Scan multiple popular sports for arbitrage in one call.

    Only scans sports that are currently active to avoid wasting quota.
    Uses the /sports endpoint (free) to check which are active first.

    Args:
        markets: Comma-separated market keys.

    Returns:
        Combined results from all scanned sports.
    """
    # Check which popular sports are currently active (free call)
    try:
        all_sports = get_available_sports()
        active_keys = {s["key"] for s in all_sports["active"]}
    except Exception:
        # If we can't fetch sports list, try all popular ones
        active_keys = set(POPULAR_SPORTS)

    sports_to_scan = [s for s in POPULAR_SPORTS if s in active_keys]

    if not sports_to_scan:
        return {
            "events": [],
            "arbitrage_found": 0,
            "total_events": 0,
            "quota_remaining": "unknown",
            "sports_scanned": [],
        }

    all_events = []
    total_events = 0
    arb_count = 0
    quota_remaining = "unknown"

    for sport_key in sports_to_scan:
        try:
            result = scan_arbitrage(sport_key, markets)
            for event in result["events"]:
                event["sport"] = sport_key
            all_events.extend(result["events"])
            total_events += result["total_events"]
            arb_count += result["arbitrage_found"]
            quota_remaining = result["quota_remaining"]
        except Exception as e:
            logger.warning("Quick scan: failed to scan %s: %s", sport_key, e)
            continue

    # Sort: arbs first, then by profit
    all_events.sort(key=lambda x: (-x["is_arbitrage"], -x["profit_pct"]))

    return {
        "events": all_events,
        "arbitrage_found": arb_count,
        "total_events": total_events,
        "quota_remaining": quota_remaining,
        "sports_scanned": sports_to_scan,
    }
