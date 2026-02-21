"""
Cross-exchange market scanner.
Discovers new markets on both exchanges, deduplicates cross-listed markets,
and persists everything to the DB.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from bot.exchanges.base import Market
from bot.exchanges.polymarket import PolymarketClient
from bot.exchanges.kalshi import KalshiClient
from bot.db import store

log = logging.getLogger(__name__)

# Fuzzy match threshold for detecting same market on both exchanges
DEDUP_THRESHOLD = 85  # thefuzz score 0-100


async def scan_all_markets() -> list[Market]:
    """
    Scan both exchanges, dedup cross-listed markets, and upsert to DB.
    Returns the combined list of unique markets.
    """
    poly = PolymarketClient()
    kalshi = KalshiClient()

    try:
        poly_markets, kalshi_markets = await asyncio.gather(
            poly.get_markets(),
            kalshi.get_markets(),
            return_exceptions=True,
        )
    finally:
        await asyncio.gather(poly.close(), kalshi.close(), return_exceptions=True)

    if isinstance(poly_markets, Exception):
        log.error("Polymarket scan failed: %s", poly_markets)
        poly_markets = []
    if isinstance(kalshi_markets, Exception):
        log.error("Kalshi scan failed: %s", kalshi_markets)
        kalshi_markets = []

    all_markets: list[Market] = poly_markets + kalshi_markets  # type: ignore[operator]
    log.info("Scanner: %d poly + %d kalshi = %d total raw markets",
             len(poly_markets), len(kalshi_markets), len(all_markets))

    # Cross-exchange deduplication
    dedup_groups = _find_dedup_groups(poly_markets, kalshi_markets)  # type: ignore[arg-type]

    # Persist to DB
    for market in all_markets:
        d = market.to_dict()
        d["dedup_group"] = dedup_groups.get(market.id)
        await store.upsert_market(d)

    log.info("Scanner: upserted %d markets to DB", len(all_markets))
    return all_markets


def _find_dedup_groups(
    poly_markets: list[Market],
    kalshi_markets: list[Market],
) -> dict[str, Optional[str]]:
    """
    Match Polymarket markets to Kalshi markets by fuzzy question similarity.
    Returns {market_id: matching_market_id_on_other_exchange | None}.
    """
    groups: dict[str, Optional[str]] = {}

    try:
        from thefuzz import fuzz  # type: ignore
    except ImportError:
        log.warning("thefuzz not installed — skipping dedup")
        return groups

    for pm in poly_markets:
        best_score = 0
        best_match: Optional[str] = None
        for km in kalshi_markets:
            score = fuzz.token_sort_ratio(
                _normalize_question(pm.question),
                _normalize_question(km.question),
            )
            if score > best_score:
                best_score = score
                best_match = km.id

        if best_score >= DEDUP_THRESHOLD and best_match:
            groups[pm.id] = best_match
            groups[best_match] = pm.id
            log.debug(
                "Dedup match (score=%d): %s ↔ %s",
                best_score,
                pm.question[:60],
                best_match,
            )

    return groups


def _normalize_question(q: str) -> str:
    """Lower-case, strip punctuation for better fuzzy matching."""
    import re
    return re.sub(r"[^\w\s]", "", q.lower()).strip()


async def refresh_prices() -> None:
    """Refresh market_price for all active markets in DB."""
    active = await store.get_active_markets()
    if not active:
        return

    poly = PolymarketClient()
    kalshi = KalshiClient()

    async def _update(market: dict) -> None:
        mid = market["id"]
        try:
            if market["exchange"] == "polymarket":
                price = await poly.get_market_price(mid)
            else:
                price = await kalshi.get_market_price(mid)
            await store.update_market_price(mid, price)
        except Exception as exc:
            log.debug("Price refresh failed for %s: %s", mid, exc)

    try:
        await asyncio.gather(*[_update(m) for m in active], return_exceptions=True)
    finally:
        await asyncio.gather(poly.close(), kalshi.close(), return_exceptions=True)

    log.info("Scanner: refreshed prices for %d markets", len(active))
