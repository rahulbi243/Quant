"""
Bayesian adaptation of per-domain entropy thresholds.

Compares P(correct | entropy < τ) vs P(correct | entropy > τ).
If strong separation: tighten τ.
If no separation: widen τ (entropy not useful for this domain).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from bot.config import (
    ENTROPY_THRESHOLD_DEFAULT,
    DOMAIN_PRIORITY,
    MODELS,
)
from bot.db import store as db

log = logging.getLogger(__name__)

# "Correct" = Brier score below this cutoff
CORRECT_BRIER_CUTOFF = 0.20

# Min outcomes required before adapting threshold
MIN_OUTCOMES_FOR_ADAPTATION = 20

# How much to shift threshold per update
THRESHOLD_STEP = 0.25  # bits
MIN_THRESHOLD = 1.0
MAX_THRESHOLD = 8.0

# Lookback window
LOOKBACK_DAYS = 60


async def run_threshold_adaptation() -> dict[str, float]:
    """
    Adapt entropy thresholds per domain.
    Returns {domain: new_threshold}.
    """
    since = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    outcomes = await db.get_outcomes_since(since)
    calibration = await db.get_all_calibration()

    # Get current thresholds per domain (average across models)
    domain_thresholds: dict[str, float] = {}
    for c in calibration:
        t = c.get("entropy_threshold")
        if t:
            domain = c["domain"]
            if domain not in domain_thresholds:
                domain_thresholds[domain] = []  # type: ignore[assignment]
            domain_thresholds[domain].append(float(t))  # type: ignore[arg-type]

    current_thresholds = {
        d: sum(ts) / len(ts)  # type: ignore[arg-type]
        for d, ts in domain_thresholds.items()  # type: ignore[attr-defined]
        if ts
    }

    # Need to join with forecasts to get entropy values
    # outcomes table has forecast_id; load associated entropy from forecasts
    forecast_entropy: dict[int, float] = {}
    async with db.get_db() as conn:
        cur = await conn.execute("SELECT id, entropy FROM forecasts WHERE entropy IS NOT NULL")
        rows = await cur.fetchall()
        for r in rows:
            forecast_entropy[r["id"]] = r["entropy"]

    # Group outcomes by domain with entropy attached
    domain_data: dict[str, list[tuple[float, bool]]] = defaultdict(list)  # domain → [(entropy, correct)]
    for o in outcomes:
        fid = o.get("forecast_id")
        if fid is None:
            continue
        entropy = forecast_entropy.get(fid)
        if entropy is None:
            continue
        correct = (o.get("brier", 1.0) or 1.0) < CORRECT_BRIER_CUTOFF
        domain_data[o["domain"]].append((entropy, correct))

    new_thresholds: dict[str, float] = {}

    for domain, points in domain_data.items():
        if len(points) < MIN_OUTCOMES_FOR_ADAPTATION:
            log.debug("Threshold adapt: %s has %d points (need %d)", domain, len(points), MIN_OUTCOMES_FOR_ADAPTATION)
            continue

        tau = current_thresholds.get(domain, ENTROPY_THRESHOLD_DEFAULT)
        new_tau = _adapt_threshold(points, tau)
        new_thresholds[domain] = new_tau

        # Persist per-domain threshold (update all models for this domain)
        for model_cfg in MODELS:
            state = await db.get_calibration_state(domain, model_cfg["id"])
            if state:
                await db.upsert_calibration(
                    domain=domain,
                    model=model_cfg["id"],
                    brier=state["brier_score"],
                    n=state["n_resolved"],
                    weight=state["domain_weight"],
                    entropy_threshold=new_tau,
                )

        log.info("Threshold adapt: %s τ %.2f → %.2f", domain, tau, new_tau)

    return new_thresholds


def _adapt_threshold(points: list[tuple[float, bool]], current_tau: float) -> float:
    """
    Given (entropy, correct) pairs and current threshold τ,
    evaluate whether tightening or loosening improves separation.

    Separation metric:
        sep = P(correct | entropy < τ) - P(correct | entropy > τ)

    If sep is strong (> 0.1): entropy is useful → try tightening.
    If sep is weak (< 0.05): entropy doesn't help → widen.
    """
    below = [correct for ent, correct in points if ent < current_tau]
    above = [correct for ent, correct in points if ent >= current_tau]

    if not below or not above:
        return current_tau

    p_below = sum(below) / len(below)
    p_above = sum(above) / len(above)
    separation = p_below - p_above

    log.debug(
        "Threshold eval τ=%.2f: P(correct|below)=%.2f P(correct|above)=%.2f sep=%.2f",
        current_tau, p_below, p_above, separation
    )

    if separation > 0.10:
        # Entropy is a useful predictor — try tightening (stricter high-confidence gate)
        new_tau = max(MIN_THRESHOLD, current_tau - THRESHOLD_STEP)
    elif separation < 0.05:
        # No separation — entropy not useful — widen (be more permissive)
        new_tau = min(MAX_THRESHOLD, current_tau + THRESHOLD_STEP)
    else:
        # Moderate separation — keep current
        new_tau = current_tau

    return new_tau
