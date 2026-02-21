"""
Shannon entropy computation from LLM token log-probabilities.

Used as a confidence signal: low entropy → model is certain → higher confidence tier.
Implements the entropy filter from the "Think Just Enough" research signal.
"""
from __future__ import annotations

import math
from typing import Optional

from bot.config import (
    ENTROPY_THRESHOLD_DEFAULT,
    ENTROPY_HIGH_TIER,
    ENTROPY_MEDIUM_TIER,
)


def compute_sequence_entropy(logprobs: list[float]) -> float:
    """
    Compute mean per-token Shannon entropy from a sequence of log-probabilities.

    The entropy of a single token is:
        H = -sum_i p_i * log2(p_i)

    When we only have the top-1 log-probability (logprob of the chosen token),
    we can't compute full entropy. We use a conservative estimate:
        H_token ≈ -logprob / ln(2)     [i.e. -log2(p_chosen)]

    This is the *minimum* entropy (if p_chosen = 1, H=0; if p_chosen → 0, H → ∞).
    For tokens where top-logprobs are available, use full distribution.

    Returns:
        Mean entropy in bits across the sequence.
    """
    if not logprobs:
        return ENTROPY_THRESHOLD_DEFAULT  # default to uncertain if no logprobs

    entropies = []
    for lp in logprobs:
        # Clamp to avoid log(0)
        lp = min(lp, -1e-9)
        # Convert to per-token entropy approximation
        h = -lp / math.log(2)
        entropies.append(h)

    return sum(entropies) / len(entropies)


def compute_distribution_entropy(top_logprobs: list[list[tuple[str, float]]]) -> float:
    """
    Compute true Shannon entropy from top-k logprob distributions.

    top_logprobs: list of per-token top-k distributions.
    Each element is a list of (token, logprob) pairs.

    Returns:
        Mean entropy in bits across the sequence.
    """
    if not top_logprobs:
        return ENTROPY_THRESHOLD_DEFAULT

    entropies = []
    for token_dist in top_logprobs:
        if not token_dist:
            continue
        # Renormalise the distribution (top-k may not sum to 1)
        probs = [math.exp(lp) for _, lp in token_dist]
        total = sum(probs)
        if total <= 0:
            continue
        probs = [p / total for p in probs]
        h = -sum(p * math.log2(p) for p in probs if p > 0)
        entropies.append(h)

    if not entropies:
        return ENTROPY_THRESHOLD_DEFAULT
    return sum(entropies) / len(entropies)


def confidence_tier(entropy: float, domain: str | None = None, domain_threshold: float | None = None) -> str:
    """
    Map entropy value to confidence tier: "high" | "medium" | "low".

    Uses per-domain thresholds if available, else global defaults.
    """
    threshold = domain_threshold if domain_threshold is not None else ENTROPY_HIGH_TIER
    medium_threshold = threshold * 1.5

    if entropy <= threshold:
        return "high"
    elif entropy <= medium_threshold:
        return "medium"
    else:
        return "low"


def probability_from_logprobs(
    yes_logprob: float,
    no_logprob: float | None = None,
) -> float:
    """
    Convert YES token log-probability to a calibrated probability.

    If both YES and no_logprob are available, use softmax over the two.
    Otherwise use sigmoid of yes_logprob (monotone rescaling).
    """
    p_yes = math.exp(yes_logprob)
    if no_logprob is not None:
        p_no = math.exp(no_logprob)
        total = p_yes + p_no
        if total > 0:
            return p_yes / total
    # Fallback: clamp raw probability
    return max(0.01, min(0.99, p_yes))


def extract_number_logprobs(
    logprobs_content: list[dict],
) -> tuple[float, Optional[list[float]]]:
    """
    From OpenAI / Anthropic logprobs payload, extract:
    - The log-probability of the numeric tokens (for probability calibration)
    - A flat list of per-token logprobs for entropy computation

    Returns (mean_logprob_of_digits, flat_logprobs_list).
    """
    flat: list[float] = []
    digit_logprobs: list[float] = []

    for item in logprobs_content:
        lp = item.get("logprob", 0.0)
        token = item.get("token", "")
        flat.append(lp)
        if token.strip().lstrip("-").isdigit():
            digit_logprobs.append(lp)

    mean_digit_lp = sum(digit_logprobs) / len(digit_logprobs) if digit_logprobs else -2.0
    return mean_digit_lp, flat
