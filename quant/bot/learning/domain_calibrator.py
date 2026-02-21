"""
Per-domain calibration.
After a batch of new outcomes, updates domain_weight in calibration_state.
Alerts when a domain is performing worse than random baseline.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bot.config import (
    DOMAIN_PRIORITY,
    MODELS,
    DOMAIN_WEIGHT_GOOD_BRIER,
    DOMAIN_WEIGHT_BAD_BRIER,
    LEARNING_BATCH_SIZE,
)
from bot.db import store as db

log = logging.getLogger(__name__)

# Brier score of random forecasting (p=0.5 always): (0.5 - outcome)^2 = 0.25
RANDOM_BASELINE_BRIER = 0.25


async def run_calibration() -> None:
    """
    Compute rolling Brier per (domain, model) from recent outcomes and
    update domain weights accordingly.
    """
    # Get all outcomes from the last 90 days
    since = datetime.now(timezone.utc) - timedelta(days=90)
    outcomes = await db.get_outcomes_since(since)

    if len(outcomes) < LEARNING_BATCH_SIZE:
        log.info("Domain calibrator: only %d outcomes, skipping (need %d)",
                 len(outcomes), LEARNING_BATCH_SIZE)
        return

    # Group by (domain, model)
    from collections import defaultdict
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for o in outcomes:
        if o.get("brier") is not None:
            groups[(o["domain"], o["model"])].append(o["brier"])

    for (domain, model), briers in groups.items():
        if len(briers) < 3:  # too few samples for reliable estimate
            continue
        mean_brier = sum(briers) / len(briers)
        n = len(briers)

        # Compute domain weight
        weight = _brier_to_weight(mean_brier)

        await db.upsert_calibration(domain, model, mean_brier, n, weight)

        if mean_brier > RANDOM_BASELINE_BRIER:
            log.warning(
                "ALERT: %s/%s Brier=%.3f worse than random (%.2f) — weight set to %.1f",
                domain, model, mean_brier, RANDOM_BASELINE_BRIER, weight
            )
        else:
            log.info(
                "Calibration: %s/%s Brier=%.3f n=%d → weight=%.2f",
                domain, model, mean_brier, n, weight
            )


def _brier_to_weight(brier: float) -> float:
    """Map Brier score to domain weight multiplier."""
    if brier < DOMAIN_WEIGHT_GOOD_BRIER:    # < 0.15 → excellent
        return 1.5
    elif brier < 0.20:                       # 0.15-0.20 → good
        return 1.2
    elif brier < RANDOM_BASELINE_BRIER:      # 0.20-0.25 → mediocre but above random
        return 1.0
    elif brier < DOMAIN_WEIGHT_BAD_BRIER:    # 0.25-0.28 → near random
        return 0.7
    else:                                     # > 0.28 → worse than random
        return 0.3


async def get_domain_weight(domain: str, model: str) -> float:
    """
    Get the current domain weight for (domain, model).
    Defaults to 1.0 if no calibration data.
    """
    state = await db.get_calibration_state(domain, model)
    return state["domain_weight"] if state else 1.0


async def get_best_domain_weight(domain: str, model_weights: dict[str, float]) -> float:
    """
    Get the average domain weight across models for a given domain,
    weighted by model weight. Used for domain-level filtering.
    """
    all_cal = await db.get_all_calibration()
    domain_cal = [c for c in all_cal if c["domain"] == domain]
    if not domain_cal:
        return 1.0

    total_weight = 0.0
    weighted_sum = 0.0
    for c in domain_cal:
        mw = model_weights.get(c["model"], 1.0)
        dw = c.get("domain_weight", 1.0)
        weighted_sum += mw * dw
        total_weight += mw

    return weighted_sum / total_weight if total_weight > 0 else 1.0
