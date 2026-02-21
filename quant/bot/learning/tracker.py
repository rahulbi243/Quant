"""
Outcome tracker: polls exchanges for newly resolved markets and records
Brier scores in the outcomes table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from bot.exchanges.polymarket import PolymarketClient
from bot.exchanges.kalshi import KalshiClient
from bot.db import store as db

log = logging.getLogger(__name__)

# How far back to look for resolutions each run
LOOKBACK_HOURS = 26


async def check_new_outcomes() -> int:
    """
    Poll both exchanges for markets resolved in the last LOOKBACK_HOURS.
    Record outcomes + Brier scores in DB.

    Returns number of new outcomes recorded.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    poly = PolymarketClient()
    kalshi = KalshiClient()

    import asyncio
    poly_resolved, kalshi_resolved = await asyncio.gather(
        poly.get_resolved_markets(since),
        kalshi.get_resolved_markets(since),
        return_exceptions=True,
    )
    await asyncio.gather(poly.close(), kalshi.close(), return_exceptions=True)

    if isinstance(poly_resolved, Exception):
        log.error("Poly resolution check failed: %s", poly_resolved)
        poly_resolved = []
    if isinstance(kalshi_resolved, Exception):
        log.error("Kalshi resolution check failed: %s", kalshi_resolved)
        kalshi_resolved = []

    all_resolved = list(poly_resolved) + list(kalshi_resolved)  # type: ignore[operator]
    new_outcomes = 0

    for market in all_resolved:
        if market.outcome is None:
            continue

        # Update DB market record
        await db.mark_market_resolved(market.id, market.outcome)

        # Find matching forecasts
        forecasts = await db.get_forecasts_for_market(market.id)
        mkt_record = await db.get_market(market.id)
        domain = (mkt_record or {}).get("domain", "unknown")

        for f in forecasts:
            pred = f.get("raw_probability")
            if pred is None:
                continue
            brier = (pred - market.outcome) ** 2
            outcome_row = {
                "market_id": market.id,
                "forecast_id": f["id"],
                "domain": domain,
                "model": f["model"],
                "prompt_version": f["prompt_version"],
                "predicted_prob": pred,
                "actual_outcome": market.outcome,
                "brier": brier,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.insert_outcome(outcome_row)
            new_outcomes += 1

    if new_outcomes:
        log.info("Tracker: recorded %d new outcomes", new_outcomes)

    return new_outcomes
