"""
Multi-model LLM forecaster.
Runs all active models in parallel and returns per-model probability + entropy.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from bot.config import (
    MODELS, ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY,
    LLM_CONCURRENCY,
)
from bot.exchanges.base import Market
from bot.intelligence.entropy import (
    compute_sequence_entropy,
    compute_distribution_entropy,
    confidence_tier,
    extract_number_logprobs,
)
from bot.intelligence.news import NewsContext
from bot.db import store as db

log = logging.getLogger(__name__)

_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
    return _semaphore


@dataclass
class Forecast:
    model: str
    prompt_version: str
    raw_probability: float           # 0-1
    entropy: float                   # bits
    confidence: str                  # "high" | "medium" | "low"
    reasoning: str
    news_used: bool
    input_tokens: int = 0
    output_tokens: int = 0


async def forecast(
    market: Market,
    news: NewsContext | None,
    prompt_template: str,
    prompt_version: str,
    model_configs: list[dict] | None = None,
    domain_thresholds: dict[str, float] | None = None,
) -> list[Forecast]:
    """
    Run all active models in parallel against the market question.

    Returns a list of Forecast objects (one per model that succeeds).
    """
    configs = model_configs or MODELS
    thresholds = domain_thresholds or {}
    domain_threshold = thresholds.get(market.domain or "politics")

    tasks = [
        _forecast_one(
            model_cfg=cfg,
            market=market,
            news=news,
            prompt_template=prompt_template,
            prompt_version=prompt_version,
            domain_threshold=domain_threshold,
        )
        for cfg in configs
        if cfg.get("weight", 0) > 0
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    forecasts = []
    for r in results:
        if isinstance(r, Exception):
            log.error("Forecast task failed: %s", r)
        elif r is not None:
            forecasts.append(r)

    return forecasts


async def _forecast_one(
    model_cfg: dict,
    market: Market,
    news: NewsContext | None,
    prompt_template: str,
    prompt_version: str,
    domain_threshold: float | None,
) -> Optional[Forecast]:
    model_id = model_cfg["id"]
    provider = model_cfg.get("provider", "openai")
    has_logprobs = model_cfg.get("has_logprobs", False)

    news_context = ""
    news_used = False
    if news and news.use_news and not news.is_empty():
        news_context = f"\n\nRecent news:\n{news.body}\n"
        news_used = True

    prompt = prompt_template.format(
        question=market.question,
        domain=market.domain or "unknown",
        news_context=news_context,
        market_price=f"{market.market_price:.1%}",
    )
    system = news.system_prefix if news else ""

    async with _get_semaphore():
        if provider == "anthropic":
            result = await _call_anthropic(model_id, system, prompt, has_logprobs)
        elif provider == "openai":
            result = await _call_openai(model_id, system, prompt, has_logprobs)
        elif provider == "deepseek":
            result = await _call_deepseek(model_id, system, prompt, has_logprobs)
        else:
            log.warning("Unknown provider: %s", provider)
            return None

    if result is None:
        return None

    raw_prob, entropy_val, reasoning, in_tok, out_tok = result

    tier = confidence_tier(entropy_val, market.domain, domain_threshold)

    # Log LLM cost
    cost = _estimate_cost(model_id, provider, in_tok, out_tok)
    await db.log_llm_cost(model_id, in_tok, out_tok, cost, "forecast")

    return Forecast(
        model=model_id,
        prompt_version=prompt_version,
        raw_probability=raw_prob,
        entropy=entropy_val,
        confidence=tier,
        reasoning=reasoning[:500],
        news_used=news_used,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )


async def _call_anthropic(
    model: str, system: str, prompt: str, has_logprobs: bool
) -> Optional[tuple[float, float, str, int, int]]:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        msg = await client.messages.create(
            model=model,
            max_tokens=300,
            system=system or "You are a calibrated forecaster.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
        prob = _extract_probability(text)
        # Anthropic doesn't return logprobs in standard API; use max entropy sentinel
        entropy = 3.5 if prob is not None else 6.0
        reasoning = _extract_reasoning(text)
        return (
            prob or 0.5,
            entropy,
            reasoning,
            msg.usage.input_tokens,
            msg.usage.output_tokens,
        )
    except Exception as exc:
        log.error("Anthropic forecast error (%s): %s", model, exc)
        return None


async def _call_openai(
    model: str, system: str, prompt: str, has_logprobs: bool
) -> Optional[tuple[float, float, str, int, int]]:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        kwargs: dict = dict(
            model=model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system or "You are a calibrated forecaster."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        if has_logprobs:
            kwargs["logprobs"] = True
            kwargs["top_logprobs"] = 5

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        text = choice.message.content or ""
        prob = _extract_probability(text)

        entropy_val = 3.5
        if has_logprobs and choice.logprobs and choice.logprobs.content:
            lp_data = [
                {"token": t.token, "logprob": t.logprob}
                for t in choice.logprobs.content
            ]
            _, flat = extract_number_logprobs(lp_data)
            if flat:
                entropy_val = compute_sequence_entropy(flat)

        reasoning = _extract_reasoning(text)
        usage = resp.usage
        return (
            prob or 0.5,
            entropy_val,
            reasoning,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )
    except Exception as exc:
        log.error("OpenAI forecast error (%s): %s", model, exc)
        return None


async def _call_deepseek(
    model: str, system: str, prompt: str, has_logprobs: bool
) -> Optional[tuple[float, float, str, int, int]]:
    if not DEEPSEEK_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
        resp = await client.chat.completions.create(
            model=model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system or "You are a calibrated forecaster."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            logprobs=has_logprobs,
        )
        choice = resp.choices[0]
        text = choice.message.content or ""
        prob = _extract_probability(text)

        entropy_val = 3.5
        if has_logprobs and choice.logprobs and choice.logprobs.content:
            lp_data = [
                {"token": t.token, "logprob": t.logprob}
                for t in choice.logprobs.content
            ]
            _, flat = extract_number_logprobs(lp_data)
            if flat:
                entropy_val = compute_sequence_entropy(flat)

        usage = resp.usage
        return (
            prob or 0.5,
            entropy_val,
            _extract_reasoning(text),
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )
    except Exception as exc:
        log.error("DeepSeek forecast error (%s): %s", model, exc)
        return None


def _extract_probability(text: str) -> Optional[float]:
    """Parse probability from LLM response. Handles JSON and plain text."""
    # Try JSON first
    try:
        match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            for key in ("probability", "prob", "p"):
                if key in data:
                    val = float(data[key])
                    # Normalise: if >1 assume percentage
                    return val / 100.0 if val > 1 else val
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Plain number extraction: "Probability: 65%", "65", "0.65"
    patterns = [
        r'probability[:\s]+(\d+(?:\.\d+)?)%',
        r'(\d+(?:\.\d+)?)\s*%',
        r'0\.(\d+)',
        r'"probability"\s*:\s*(\d+(?:\.\d+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if "%" in m.group(0) or val > 1:
                    val /= 100.0
                return max(0.01, min(0.99, val))
            except ValueError:
                pass
    return None


def _extract_reasoning(text: str) -> str:
    """Extract the reasoning portion from LLM response."""
    # Try JSON "reasoning" field
    try:
        match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            for key in ("reasoning", "explanation", "rationale"):
                if key in data:
                    return str(data[key])[:500]
    except Exception:
        pass
    # Fallback: strip JSON, return remaining text
    text = re.sub(r'\{[^}]+\}', '', text).strip()
    return text[:500] if text else "No reasoning provided"


def _estimate_cost(model: str, provider: str, in_tok: int, out_tok: int) -> float:
    """Rough cost estimate in USD based on known pricing."""
    rates = {
        # (input_per_1M, output_per_1M) in USD
        "claude-sonnet-4-6": (3.0, 15.0),
        "claude-haiku-4-5-20251001": (0.25, 1.25),
        "gpt-4.1": (2.0, 8.0),
        "gpt-4o-mini": (0.15, 0.60),
        "deepseek-chat": (0.14, 0.28),
    }
    r = rates.get(model, (1.0, 3.0))
    return (in_tok / 1_000_000) * r[0] + (out_tok / 1_000_000) * r[1]
