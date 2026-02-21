"""
News retrieval with the three failure-mode guards from the Lossfunk paper:
  1. Recency bias guard
  2. Rumor anchoring guard
  3. Definition drift guard

Domain rule (from paper):
  - Finance, Sports, Politics, Geopolitics: use news
  - Entertainment, Technology: news HURTS accuracy — inject noise warning
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from bot.config import (
    TAVILY_API_KEY, BRAVE_API_KEY, NEWS_SEARCH_PROVIDER,
    MAX_NEWS_ARTICLES, NEWS_NOISE_DOMAINS,
)

log = logging.getLogger(__name__)

# Speculative language patterns (Rumor anchoring guard)
_SPECULATIVE_PATTERNS = re.compile(
    r"\b(could|may|might|reportedly|sources say|allegedly|rumored|"
    r"anonymous source|unconfirmed|expected to|likely to|possible that|"
    r"potentially|it appears|seems to)\b",
    re.IGNORECASE,
)


@dataclass
class Article:
    title: str
    url: str
    content: str
    published_date: str = ""
    is_speculative: bool = False

    def to_context_str(self) -> str:
        tag = "[SPECULATIVE] " if self.is_speculative else ""
        date_str = f" ({self.published_date})" if self.published_date else ""
        return f"{tag}{self.title}{date_str}\n{self.content[:500]}"


@dataclass
class NewsContext:
    articles: list[Article]
    domain: str
    question: str
    use_news: bool                    # False for entertainment/technology
    system_prefix: str = ""          # injected at top of forecast prompt
    body: str = ""                   # formatted article block for prompt

    def is_empty(self) -> bool:
        return not self.articles or not self.use_news


async def get_news_context(question: str, domain: str) -> NewsContext:
    """
    Retrieve news, apply all three guards, and return a NewsContext.
    If domain is in NEWS_NOISE_DOMAINS, use_news=False and inject noise warning.
    """
    use_news = domain not in NEWS_NOISE_DOMAINS

    if not use_news:
        return NewsContext(
            articles=[],
            domain=domain,
            question=question,
            use_news=False,
            system_prefix=(
                f"[DOMAIN NOTE: {domain} domain — news context is omitted because "
                "empirical research shows it degrades forecast accuracy for this domain. "
                "Rely on base rates and structural reasoning only.]"
            ),
            body="",
        )

    articles = await _fetch_articles(question)
    if not articles:
        return NewsContext(
            articles=[],
            domain=domain,
            question=question,
            use_news=True,
            system_prefix="[No recent news found — rely on base rates.]",
            body="",
        )

    # --- Guard 2: Mark speculative articles ---
    for art in articles:
        speculative_hits = _SPECULATIVE_PATTERNS.findall(art.title + " " + art.content)
        if len(speculative_hits) >= 2:
            art.is_speculative = True

    # --- Guard 3: Definition drift — extract key terms from question ---
    key_terms = _extract_key_terms(question)

    # --- Guard 1: Recency bias prefix ---
    system_prefix = (
        "[FORECASTING GUIDELINES]\n"
        "• Weight base rates equally with recent news. Recent ≠ correct.\n"
        "• Speculative articles are tagged [SPECULATIVE] — treat as weak signal only.\n"
        f"• Domain: {domain}. Key resolution terms: {', '.join(key_terms)}.\n"
        "• Distinguish confirmed facts from speculation before updating your probability."
    )

    body_parts = [art.to_context_str() for art in articles[:MAX_NEWS_ARTICLES]]
    body = "\n\n---\n\n".join(body_parts)

    return NewsContext(
        articles=articles,
        domain=domain,
        question=question,
        use_news=True,
        system_prefix=system_prefix,
        body=body,
    )


async def _fetch_articles(query: str) -> list[Article]:
    """Fetch news articles from the configured search provider."""
    if NEWS_SEARCH_PROVIDER == "tavily" and TAVILY_API_KEY:
        return await _tavily_search(query)
    elif NEWS_SEARCH_PROVIDER == "brave" and BRAVE_API_KEY:
        return await _brave_search(query)
    else:
        log.warning("No news API key configured — returning empty news context")
        return []


async def _tavily_search(query: str) -> list[Article]:
    try:
        from tavily import AsyncTavilyClient  # type: ignore
        client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
        result = await client.search(
            query=query,
            max_results=MAX_NEWS_ARTICLES,
            search_depth="basic",
        )
        articles = []
        for r in result.get("results", []):
            articles.append(Article(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                published_date=r.get("published_date", ""),
            ))
        return articles
    except Exception as exc:
        log.error("Tavily search error: %s", exc)
        return []


async def _brave_search(query: str) -> list[Article]:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.search.brave.com/res/v1/news/search",
                params={"q": query, "count": MAX_NEWS_ARTICLES},
                headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        articles = []
        for r in data.get("results", []):
            articles.append(Article(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("description", ""),
                published_date=r.get("age", ""),
            ))
        return articles
    except Exception as exc:
        log.error("Brave search error: %s", exc)
        return []


def _extract_key_terms(question: str) -> list[str]:
    """Extract important noun-phrases / named entities for definition drift guard."""
    # Simple heuristic: capitalised multi-word tokens + quoted phrases
    terms = []
    # Quoted terms
    terms.extend(re.findall(r'"([^"]+)"', question))
    # Capitalised phrases (2+ consecutive Title Case words)
    terms.extend(re.findall(r'(?:[A-Z][a-z]+\s){1,3}[A-Z][a-z]+', question))
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = []
    for t in terms:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:5]  # cap at 5 terms
