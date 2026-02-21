"""
Model selector: reranks active models by rolling 30-day Brier score.
Models with Brier > MODEL_KILL_BRIER are removed from rotation (weight → 0).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from bot.config import MODELS, MODEL_KILL_BRIER
from bot.db import store as db

log = logging.getLogger(__name__)

ROLLING_WINDOW_DAYS = 30


async def run_model_selection() -> dict[str, float]:
    """
    Compute rolling Brier per model over the last 30 days,
    normalise to weights summing to 1.0, apply kill switch,
    and persist to DB.

    Returns new weight dict.
    """
    since = datetime.now(timezone.utc) - timedelta(days=ROLLING_WINDOW_DAYS)
    outcomes = await db.get_outcomes_since(since)

    # Group by model
    model_briers: dict[str, list[float]] = defaultdict(list)
    for o in outcomes:
        if o.get("brier") is not None and o.get("model"):
            model_briers[o["model"]].append(o["brier"])

    active_models = {cfg["id"] for cfg in MODELS}
    weights: dict[str, float] = {}

    for model_id in active_models:
        briers = model_briers.get(model_id, [])
        if not briers:
            # No data yet — keep default weight
            existing = await db.get_model_weights()
            weights[model_id] = existing.get(model_id, 1.0)
            await db.upsert_model_weight(model_id, weights[model_id], None, 0)
            continue

        mean_brier = sum(briers) / len(briers)
        n = len(briers)

        if mean_brier > MODEL_KILL_BRIER:
            log.warning(
                "KILL SWITCH: model %s Brier=%.3f > %.2f — removing from rotation",
                model_id, mean_brier, MODEL_KILL_BRIER
            )
            weights[model_id] = 0.0
        else:
            # Convert Brier → skill score (lower Brier = higher skill)
            # skill = 1 - (brier / 0.25)   [0.25 = random baseline]
            skill = max(0.01, 1.0 - (mean_brier / 0.25))
            weights[model_id] = skill

        await db.upsert_model_weight(model_id, weights[model_id], mean_brier, n)
        log.info("Model %s: Brier=%.3f n=%d → weight=%.3f", model_id, mean_brier, n, weights[model_id])

    # Normalise so active weights sum to 1.0
    total = sum(w for w in weights.values() if w > 0)
    if total > 0:
        weights = {m: w / total for m, w in weights.items()}
        # Re-persist normalised weights
        for model_id, w in weights.items():
            briers_list = model_briers.get(model_id, [])
            mean_b = sum(briers_list) / len(briers_list) if briers_list else None
            await db.upsert_model_weight(model_id, w, mean_b, len(briers_list))

    log.info("Model weights updated: %s", {m: f"{w:.3f}" for m, w in weights.items()})
    return weights


async def get_current_weights() -> dict[str, float]:
    """
    Load current model weights from DB, falling back to config defaults.
    """
    db_weights = await db.get_model_weights()
    result = {}
    for cfg in MODELS:
        mid = cfg["id"]
        result[mid] = db_weights.get(mid, cfg.get("weight", 1.0))
    return result
