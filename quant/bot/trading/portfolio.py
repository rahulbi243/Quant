"""
Virtual portfolio / bankroll tracker.
Tracks paper cash and open positions; computes total mark-to-market value.
"""
from __future__ import annotations

import logging
from datetime import datetime

from bot.db import store as db

log = logging.getLogger(__name__)


async def get_cash() -> float:
    p = await db.get_portfolio()
    return p["cash"]


async def get_total_value() -> float:
    p = await db.get_portfolio()
    return p["total_value"]


async def deduct_cash(amount: float) -> float:
    """
    Deduct amount from cash (when placing a paper trade).
    Returns new cash balance.
    """
    p = await db.get_portfolio()
    new_cash = max(0.0, p["cash"] - amount)
    await db.update_portfolio(new_cash, p["total_value"])
    log.debug("Portfolio: deducted %.2f → cash=%.2f", amount, new_cash)
    return new_cash


async def add_cash(amount: float) -> float:
    """Add cash (when a trade resolves in our favour)."""
    p = await db.get_portfolio()
    new_cash = p["cash"] + amount
    await db.update_portfolio(new_cash, p["total_value"])
    return new_cash


async def recompute_total_value() -> float:
    """
    Recompute total portfolio value:
    cash + mark-to-market of open positions.

    For simplicity, open position value = size * current_market_price.
    """
    p = await db.get_portfolio()
    cash = p["cash"]

    # Get all open trades and current market prices
    active = await db.get_active_markets()
    price_map = {m["id"]: m.get("market_price", 0.5) for m in active}

    # Sum open position value
    open_value = 0.0
    async with db.get_db() as conn:
        cur = await conn.execute(
            """
            SELECT t.market_id, t.side, t.size_units, t.price AS fill_price
            FROM trades t
            JOIN markets m ON t.market_id = m.id
            WHERE m.resolved = 0 AND t.is_paper = 1
            """
        )
        rows = await cur.fetchall()

    for row in rows:
        mkt_price = price_map.get(row["market_id"], row["fill_price"])
        if row["side"] == "YES":
            position_value = row["size_units"] * mkt_price
        else:
            position_value = row["size_units"] * (1.0 - mkt_price)
        open_value += position_value

    total = cash + open_value
    await db.update_portfolio(cash, total)
    log.info("Portfolio: cash=%.2f open=%.2f total=%.2f", cash, open_value, total)
    return total


async def print_summary() -> None:
    p = await db.get_portfolio()
    open_count = await db.count_open_positions()
    spend = await db.get_total_llm_spend()
    log.info(
        "=== Portfolio ===\n"
        "  Cash:          $%.2f\n"
        "  Total Value:   $%.2f\n"
        "  Open Positions: %d\n"
        "  LLM Spend:     $%.4f",
        p["cash"], p["total_value"], open_count, spend
    )
