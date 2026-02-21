"""
Fractional Kelly criterion for position sizing.

Full Kelly for a binary bet on YES:
    f* = (p * o - q) / o
  where:
    p = probability of YES (our estimate)
    q = 1 - p
    o = odds = (1 - price) / price   [net odds on YES]

Equivalently for a prediction market:
    f* = (p - price) / (1 - price)    [for YES bets]

We apply KELLY_FRACTION * f* (25% fractional Kelly) and cap at MAX_POSITION_PCT.
"""
from __future__ import annotations

from bot.config import KELLY_FRACTION, MAX_POSITION_PCT


def kelly_fraction(
    edge: float,
    market_price: float,
    side: str = "YES",
    fractional: float = KELLY_FRACTION,
    max_pct: float = MAX_POSITION_PCT,
) -> float:
    """
    Compute the fraction of bankroll to bet.

    Args:
        edge:         |ensemble_prob - market_price|
        market_price: Market's YES price (0-1)
        side:         "YES" or "NO"
        fractional:   Kelly multiplier (default 0.25)
        max_pct:      Cap on fraction of bankroll (default 0.05)

    Returns:
        Fraction of bankroll to allocate (0-1).
    """
    if side == "YES":
        price = market_price
    else:
        # For NO bet, the effective price is (1 - market_price)
        price = 1.0 - market_price

    # Avoid division by zero / degenerate markets
    if price <= 0 or price >= 1:
        return 0.0

    # Full Kelly fraction for this side
    full_kelly = edge / (1.0 - price)

    # Apply fractional Kelly
    fk = full_kelly * fractional

    # Apply position cap
    fk = min(fk, max_pct)

    # Never bet negative (shouldn't happen with positive edge, but safeguard)
    return max(0.0, fk)


def size_from_fraction(
    fraction: float,
    bankroll: float,
    price: float,
) -> float:
    """
    Convert fraction of bankroll to number of units/contracts.

    Args:
        fraction:  Kelly fraction (0-1)
        bankroll:  Available bankroll in USD
        price:     Fill price per contract (0-1)

    Returns:
        Number of units (floor for prediction markets; contracts are integer lots)
    """
    if price <= 0:
        return 0.0
    usd_to_spend = bankroll * fraction
    contracts = usd_to_spend / price
    return max(1.0, round(contracts, 2))
