"""
Domain classifier: maps prediction market question text to one of the 6
domains from the Lossfunk paper (ranked by LLM accuracy, descending):
  geopolitics > politics > technology > entertainment > finance > sports
"""
from __future__ import annotations

import json
import logging
import re

from bot.config import CLASSIFIER_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY, DOMAIN_PRIORITY

log = logging.getLogger(__name__)

DOMAIN_DEFINITIONS = {
    "geopolitics": "International relations, wars, conflicts, treaties, sanctions, foreign policy",
    "politics": "Domestic elections, legislation, political figures, government policy",
    "technology": "Tech companies, products, AI/ML, software releases, startups",
    "entertainment": "Movies, TV, celebrities, sports entertainment, awards, music",
    "finance": "Stock markets, economic indicators, company earnings, crypto prices, central banks",
    "sports": "Game scores, championships, player transfers, athletic performance",
}

_SYSTEM_PROMPT = """You are a domain classifier for prediction market questions.
Classify each question into exactly one of these domains:
- geopolitics: {geopolitics}
- politics: {politics}
- technology: {technology}
- entertainment: {entertainment}
- finance: {finance}
- sports: {sports}

Respond ONLY with valid JSON: {{"domain": "<domain>", "confidence": <0.0-1.0>}}"""

_USER_PROMPT = 'Question: "{question}"\n\nClassify this question.'


async def classify(question: str) -> tuple[str, float]:
    """
    Classify a prediction market question into one of 6 domains.

    Returns:
        (domain, confidence) — domain is always one of DOMAIN_PRIORITY
    """
    prompt = _USER_PROMPT.format(question=question)
    system = _SYSTEM_PROMPT.format(**DOMAIN_DEFINITIONS)

    raw = await _call_classifier(system, prompt)
    domain, confidence = _parse_response(raw)
    log.debug("Classified '%s...' → %s (%.2f)", question[:50], domain, confidence)
    return domain, confidence


async def _call_classifier(system: str, user: str) -> str:
    """Call the cheap classifier model."""
    if ANTHROPIC_API_KEY and "claude" in CLASSIFIER_MODEL:
        return await _call_anthropic(system, user)
    elif OPENAI_API_KEY:
        return await _call_openai(system, user)
    else:
        log.warning("No API key for classifier — using keyword fallback")
        return _keyword_fallback(user)


async def _call_anthropic(system: str, user: str) -> str:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        msg = await client.messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=64,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
    except Exception as exc:
        log.error("Anthropic classifier error: %s", exc)
        return '{"domain": "politics", "confidence": 0.3}'


async def _call_openai(system: str, user: str) -> str:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=64,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        log.error("OpenAI classifier error: %s", exc)
        return '{"domain": "politics", "confidence": 0.3}'


def _parse_response(raw: str) -> tuple[str, float]:
    """Extract domain and confidence from LLM JSON response."""
    try:
        # Extract JSON from response (may have surrounding text)
        match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            domain = data.get("domain", "politics").lower()
            confidence = float(data.get("confidence", 0.5))
            if domain not in DOMAIN_PRIORITY:
                domain = _closest_domain(domain)
            return domain, max(0.0, min(1.0, confidence))
    except (json.JSONDecodeError, ValueError) as exc:
        log.debug("Classifier parse error: %s | raw=%s", exc, raw[:100])

    return "politics", 0.3


def _closest_domain(raw: str) -> str:
    """Map unexpected domain name to nearest valid domain."""
    raw = raw.lower()
    mappings = {
        "geo": "geopolitics", "international": "geopolitics", "war": "geopolitics",
        "election": "politics", "political": "politics", "government": "politics",
        "tech": "technology", "ai": "technology", "crypto": "finance",
        "econ": "finance", "economic": "finance", "market": "finance",
        "sport": "sports", "athlete": "sports", "celebrity": "entertainment",
        "movie": "entertainment", "tv": "entertainment",
    }
    for key, domain in mappings.items():
        if key in raw:
            return domain
    return "politics"


def _keyword_fallback(user: str) -> str:
    """Offline keyword-based domain guess."""
    text = user.lower()
    if any(w in text for w in ["war", "nato", "sanction", "geopolit", "treaty"]):
        return '{"domain": "geopolitics", "confidence": 0.5}'
    if any(w in text for w in ["election", "president", "congress", "senate", "vote", "poll"]):
        return '{"domain": "politics", "confidence": 0.5}'
    if any(w in text for w in ["stock", "gdp", "fed ", "inflation", "bitcoin", "earnings"]):
        return '{"domain": "finance", "confidence": 0.5}'
    if any(w in text for w in ["nfl", "nba", "mlb", "soccer", "championship", "super bowl"]):
        return '{"domain": "sports", "confidence": 0.5}'
    if any(w in text for w in ["apple", "google", "openai", "ai ", "release", "iphone"]):
        return '{"domain": "technology", "confidence": 0.5}'
    if any(w in text for w in ["oscar", "emmy", "grammy", "celebrity", "netflix", "film"]):
        return '{"domain": "entertainment", "confidence": 0.5}'
    return '{"domain": "politics", "confidence": 0.3}'
