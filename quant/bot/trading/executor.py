"""
Order executor.
paper_mode=True → write to DB only.
paper_mode=False → submit to exchange via exchange client.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from bot.config import PAPER_MODE, MAX_OPEN_POSITIONS, MIN_EDGE
from bot.db import store as db
from bot.exchanges.base import Market
from bot.trading import edge as edge_module
from bot.trading import kelly as kelly_module
from bot.trading import portfolio

log = logging.getLogger(__name__)


@dataclass
class TradeIntent:
    market: Market
    forecast_id: int
    ensemble_prob: float
    confidence_tier: str
    domain_weight: float


async def maybe_trade(
    intent: TradeIntent,
    paper_mode: bool = PAPER_MODE,
) -> Optional[int]:
    """
    Evaluate whether to trade, compute size, and execute or paper-log.

    Returns trade DB id if placed, else None.
    """
    market = intent.market

    # ---- Pre-trade filters ----
    open_count = await db.count_open_positions()
    side, edge_val = edge_module.best_side_and_edge(intent.ensemble_prob, market.market_price)
    tradeable, reason = edge_module.is_tradeable(
        ensemble_prob=intent.ensemble_prob,
        market_price=market.market_price,
        confidence_tier=intent.confidence_tier,
        domain_weight=intent.domain_weight,
        min_edge=MIN_EDGE,
        max_open_positions=MAX_OPEN_POSITIONS,
        current_open=open_count,
    )

    if not tradeable:
        log.debug("No trade for %s: %s", market.id, reason)
        return None

    # Check no existing position
    if await db.has_position(market.id):
        log.debug("Already have position in %s", market.id)
        return None

    # ---- Sizing ----
    cash = await portfolio.get_cash()
    fill_price = market.market_price if side == "YES" else (1.0 - market.market_price)
    frac = kelly_module.kelly_fraction(edge_val, market.market_price, side)
    size = kelly_module.size_from_fraction(frac, cash, fill_price)
    cost = size * fill_price

    if cost > cash:
        log.warning("Insufficient cash: need %.2f have %.2f", cost, cash)
        return None

    if paper_mode:
        # ---- Paper execution ----
        trade_row = {
            "market_id": market.id,
            "forecast_id": intent.forecast_id,
            "exchange": market.exchange,
            "side": side,
            "size_units": size,
            "price": fill_price,
            "kelly_fraction": frac,
            "edge": edge_val,
            "is_paper": 1,
        }
        trade_id = await db.insert_trade(trade_row)
        await portfolio.deduct_cash(cost)
        log.info(
            "PAPER TRADE: %s %s %s @ %.3f | edge=%.3f size=%.1f cost=%.2f",
            market.exchange, side, market.question[:50], fill_price, edge_val, size, cost,
        )
        return trade_id

    else:
        # ---- Live execution ----
        from bot.exchanges.polymarket import PolymarketClient
        from bot.exchanges.kalshi import KalshiClient

        if market.exchange == "polymarket":
            client = PolymarketClient()
        else:
            client = KalshiClient()

        try:
            order = await client.place_order(market.id, side, size, fill_price)
        except Exception as exc:
            log.error("Live order failed for %s: %s", market.id, exc)
            return None
        finally:
            await client.close()

        trade_row = {
            "market_id": market.id,
            "forecast_id": intent.forecast_id,
            "exchange": market.exchange,
            "side": side,
            "size_units": size,
            "price": fill_price,
            "kelly_fraction": frac,
            "edge": edge_val,
            "is_paper": 0,
        }
        trade_id = await db.insert_trade(trade_row)
        await portfolio.deduct_cash(cost)
        log.info(
            "LIVE TRADE: %s %s %s @ %.3f | order=%s",
            market.exchange, side, market.question[:50], fill_price, order.order_id,
        )
        return trade_id
