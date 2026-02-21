"""
A/B prompt experiment manager.
Maintains 2-3 prompt variants per domain, retires underperformers,
and uses an LLM to generate improved replacements.
"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from bot.config import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY,
    PROMPT_EVOLVER_MODEL, PROMPT_TOURNAMENT_MIN_TRIALS,
    DOMAIN_PRIORITY,
)
from bot.db import store as db

log = logging.getLogger(__name__)

# Brier gap that triggers retirement of a variant
RETIRE_BRIER_GAP = 0.05

# Max active variants per domain
MAX_VARIANTS_PER_DOMAIN = 3

# ──────────────────────────────────────────────────────────────────────────────
# Initial prompt templates (seeded on first run)
# ──────────────────────────────────────────────────────────────────────────────

PROMPT_V1 = """\
You are a calibrated forecaster. Given this prediction market question:
"{question}"
[Domain: {domain}]
{news_context}
Guidelines:
- Weight base rates equally with recent news
- Distinguish confirmed facts from speculation
- Consider the specific resolution criteria carefully
- Current market price: {market_price}

Provide:
1. Probability (0-100%) that this resolves YES
2. Your reasoning (2-3 sentences)

JSON only: {{"probability": <0-100>, "reasoning": "..."}}"""

PROMPT_V2 = """\
[Forecasting task]
Question: "{question}"
Domain: {domain}
Current market price: {market_price}
{news_context}
Step 1: What is the base rate for this type of event?
Step 2: What does recent evidence add? (flag if speculative)
Step 3: What is the specific resolution criteria?
Step 4: What is your calibrated probability?

JSON: {{"probability": <0-100>, "reasoning": "..."}}"""

INITIAL_PROMPTS = [
    {"prompt_version": "v1-baseline", "prompt_template": PROMPT_V1, "domain": None},
    {"prompt_version": "v2-cot", "prompt_template": PROMPT_V2, "domain": None},
]


async def seed_initial_prompts() -> None:
    """Insert initial prompt variants if DB is empty."""
    existing = await db.get_active_prompts()
    if existing:
        return

    for p in INITIAL_PROMPTS:
        await db.upsert_prompt_experiment({
            "prompt_version": p["prompt_version"],
            "domain": p.get("domain"),
            "prompt_template": p["prompt_template"],
            "n_trials": 0,
            "n_wins": 0,
            "mean_brier": None,
            "active": 1,
        })
    log.info("Prompt evolver: seeded %d initial variants", len(INITIAL_PROMPTS))


async def get_active_prompt(domain: str | None = None) -> tuple[str, str]:
    """
    Select the active prompt template for a given domain (random among active).
    Returns (prompt_version, template).
    """
    prompts = await db.get_active_prompts(domain)
    if not prompts:
        # Fallback to global prompts
        prompts = await db.get_active_prompts(None)
    if not prompts:
        return "v1-baseline", PROMPT_V1

    chosen = random.choice(prompts)
    return chosen["prompt_version"], chosen["prompt_template"] or PROMPT_V1


async def run_prompt_tournament(domain: str | None = None) -> None:
    """
    Evaluate all active prompt variants. Retire underperformers.
    If a slot opens up, generate a new experimental variant via LLM.
    """
    from bot.db import store as db
    from datetime import datetime, timezone, timedelta

    # Get outcomes from last 60 days
    since = datetime.now(timezone.utc) - timedelta(days=60)
    outcomes = await db.get_outcomes_since(since)

    # Group by prompt_version
    from collections import defaultdict
    pv_briers: dict[str, list[float]] = defaultdict(list)
    for o in outcomes:
        pv = o.get("prompt_version")
        if pv and o.get("brier") is not None:
            if domain is None or o.get("domain") == domain:
                pv_briers[pv].append(o["brier"])

    # Update prompt_experiments table
    active = await db.get_active_prompts(domain)
    best_brier: Optional[float] = None
    best_version: Optional[str] = None

    for p in active:
        pv = p["prompt_version"]
        briers = pv_briers.get(pv, [])
        if len(briers) < PROMPT_TOURNAMENT_MIN_TRIALS:
            continue
        mean_b = sum(briers) / len(briers)
        await db.upsert_prompt_experiment({
            **p,
            "n_trials": len(briers),
            "mean_brier": mean_b,
        })
        if best_brier is None or mean_b < best_brier:
            best_brier = mean_b
            best_version = pv
            log.info("Prompt tournament: best so far %s Brier=%.3f", pv, mean_b)

    if best_brier is None:
        log.info("Prompt tournament: insufficient data for any variant")
        return

    # Retire losers
    for p in active:
        pv = p["prompt_version"]
        briers = pv_briers.get(pv, [])
        if len(briers) < PROMPT_TOURNAMENT_MIN_TRIALS:
            continue
        mean_b = sum(briers) / len(briers)
        if mean_b - best_brier > RETIRE_BRIER_GAP:
            await db.retire_prompt(pv)
            log.info("Prompt tournament: retiring %s (Brier=%.3f, best=%.3f)", pv, mean_b, best_brier)

    # Check if we need a new variant
    remaining = await db.get_active_prompts(domain)
    if len(remaining) < MAX_VARIANTS_PER_DOMAIN:
        worst_prompt = _get_worst_prompt(active, pv_briers)
        if worst_prompt:
            await _generate_new_variant(worst_prompt, domain)


def _get_worst_prompt(
    active: list[dict],
    pv_briers: dict[str, list[float]],
) -> Optional[dict]:
    """Return the active prompt with the highest (worst) mean Brier."""
    worst = None
    worst_brier = -1.0
    for p in active:
        briers = pv_briers.get(p["prompt_version"], [])
        if not briers:
            continue
        mean_b = sum(briers) / len(briers)
        if mean_b > worst_brier:
            worst_brier = mean_b
            worst = p
    return worst


async def _generate_new_variant(worst: dict, domain: str | None) -> None:
    """Ask the evolver LLM to improve the worst-performing prompt."""
    system = (
        "You are an expert at writing calibrated forecasting prompts for prediction markets. "
        "Your goal is to improve a prompt that has been performing poorly (high Brier score)."
    )
    user = f"""
The following prediction market forecasting prompt has been underperforming:

---
{worst.get('prompt_template', PROMPT_V1)}
---

Mean Brier score: {worst.get('mean_brier', 'unknown')}
Domain: {domain or 'all'}

Please write an improved version that:
1. Reduces overconfidence / underconfidence
2. Better guides the forecaster to consider base rates
3. Explicitly guards against recency bias and rumor anchoring
4. Keeps the JSON output format: {{"probability": <0-100>, "reasoning": "..."}}

Output ONLY the new prompt template (no explanation). Use {{question}}, {{domain}}, {{news_context}}, {{market_price}} as placeholders.
"""

    new_template = None
    try:
        if OPENAI_API_KEY and "gpt" in PROMPT_EVOLVER_MODEL:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            resp = await client.chat.completions.create(
                model=PROMPT_EVOLVER_MODEL,
                max_tokens=800,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
            )
            new_template = resp.choices[0].message.content
        elif ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=PROMPT_EVOLVER_MODEL if "claude" in PROMPT_EVOLVER_MODEL else "claude-sonnet-4-6",
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            new_template = msg.content[0].text
    except Exception as exc:
        log.error("Prompt evolution LLM call failed: %s", exc)
        return

    if not new_template:
        return

    import hashlib
    version_hash = hashlib.md5(new_template.encode()).hexdigest()[:8]
    new_version = f"v-evolved-{version_hash}"

    await db.upsert_prompt_experiment({
        "prompt_version": new_version,
        "domain": domain,
        "prompt_template": new_template,
        "n_trials": 0,
        "n_wins": 0,
        "mean_brier": None,
        "active": 1,
    })
    log.info("Prompt evolver: created new variant %s for domain=%s", new_version, domain)
