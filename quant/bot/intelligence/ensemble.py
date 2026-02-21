"""
Weighted ensemble combination of multi-model forecasts.
Weight = model_weight × domain_weight for (model, domain) pair.
"""
from __future__ import annotations

import logging
from typing import Optional

from bot.config import MODELS
from bot.intelligence.forecaster import Forecast
from bot.intelligence.entropy import confidence_tier

log = logging.getLogger(__name__)


def combine(
    forecasts: list[Forecast],
    model_weights: dict[str, float],
    calibration: dict[tuple[str, str], float],   # {(domain, model): domain_weight}
    domain: str,
    domain_threshold: float | None = None,
) -> tuple[float, float, str]:
    """
    Combine per-model forecasts into a single ensemble probability.

    Args:
        forecasts:     Per-model Forecast objects
        model_weights: Global model weights from model_selector
        calibration:   (domain, model) → domain_weight from domain_calibrator
        domain:        Market domain for calibration lookup
        domain_threshold: Per-domain entropy threshold for confidence tier

    Returns:
        (ensemble_probability, ensemble_entropy, confidence_tier)
    """
    if not forecasts:
        return 0.5, 6.0, "low"

    weighted_sum = 0.0
    weight_total = 0.0
    entropy_sum = 0.0

    for f in forecasts:
        mw = model_weights.get(f.model, 1.0)
        dw = calibration.get((domain, f.model), 1.0)
        w = mw * dw

        # Zero-weight models are already filtered, but double-check
        if w <= 0:
            continue

        weighted_sum += f.raw_probability * w
        entropy_sum += f.entropy * w
        weight_total += w

    if weight_total <= 0:
        # Fallback: simple average
        probs = [f.raw_probability for f in forecasts]
        return sum(probs) / len(probs), 5.0, "low"

    ensemble_prob = weighted_sum / weight_total
    ensemble_entropy = entropy_sum / weight_total

    tier = confidence_tier(ensemble_entropy, domain, domain_threshold)

    log.debug(
        "Ensemble: %d models → prob=%.3f entropy=%.2f tier=%s",
        len(forecasts), ensemble_prob, ensemble_entropy, tier
    )
    return ensemble_prob, ensemble_entropy, tier


def build_calibration_lookup(calibration_rows: list[dict]) -> dict[tuple[str, str], float]:
    """Convert DB calibration_state rows to lookup dict."""
    return {
        (row["domain"], row["model"]): row.get("domain_weight", 1.0)
        for row in calibration_rows
    }


def build_domain_thresholds(calibration_rows: list[dict]) -> dict[str, float]:
    """Extract per-domain entropy thresholds (averaged across models)."""
    from bot.config import ENTROPY_THRESHOLD_DEFAULT
    domain_thresholds: dict[str, list[float]] = {}
    for row in calibration_rows:
        t = row.get("entropy_threshold")
        if t is not None:
            domain_thresholds.setdefault(row["domain"], []).append(float(t))
    return {
        domain: sum(vals) / len(vals)
        for domain, vals in domain_thresholds.items()
        if vals
    }
