"""
Edge calculation: ensemble probability minus market price.
Positive edge = we think YES is underpriced.
Negative edge = we think NO is underpriced (trade the other side).
"""
from __future__ import annotations


def compute_edge(ensemble_prob: float, market_price: float) -> float:
    """
    Edge for YES position.

    Returns:
        Positive → buy YES (underpriced)
        Negative → buy NO (YES overpriced)
    """
    return ensemble_prob - market_price


def best_side_and_edge(ensemble_prob: float, market_price: float) -> tuple[str, float]:
    """
    Return the best tradeable side and the magnitude of the edge.

    For YES: edge = ensemble - price
    For NO:  edge = (1 - ensemble) - (1 - price) = price - ensemble

    Both edges have the same magnitude; we just pick the positive direction.
    """
    yes_edge = compute_edge(ensemble_prob, market_price)
    if yes_edge >= 0:
        return "YES", yes_edge
    else:
        return "NO", -yes_edge  # trade NO, which has positive edge = -yes_edge


def is_tradeable(
    ensemble_prob: float,
    market_price: float,
    confidence_tier: str,
    domain_weight: float,
    min_edge: float,
    max_open_positions: int,
    current_open: int,
) -> tuple[bool, str]:
    """
    Decision filter: should we trade this market?

    Returns (tradeable, reason_if_not).
    """
    _, edge = best_side_and_edge(ensemble_prob, market_price)

    if current_open >= max_open_positions:
        return False, f"max open positions ({max_open_positions}) reached"
    if edge < min_edge:
        return False, f"edge {edge:.3f} < min {min_edge}"
    if confidence_tier != "high":
        return False, f"confidence tier is '{confidence_tier}' (need 'high')"
    if domain_weight < 0.5:
        return False, f"domain weight {domain_weight:.2f} < 0.5"

    return True, ""
