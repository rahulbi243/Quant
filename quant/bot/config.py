"""
Global configuration for the prediction market trading bot.
All tuneable parameters live here; override via environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BOT_DIR = Path(__file__).parent
DB_PATH = BOT_DIR / "bot.db"
SCHEMA_PATH = BOT_DIR / "db" / "schema.sql"

# ---------------------------------------------------------------------------
# Paper trading
# ---------------------------------------------------------------------------
PAPER_MODE: bool = os.getenv("PAPER_MODE", "true").lower() != "false"
VIRTUAL_BANKROLL: float = float(os.getenv("VIRTUAL_BANKROLL", "10000.0"))

# ---------------------------------------------------------------------------
# Exchange credentials (loaded from env)
# ---------------------------------------------------------------------------
# Polymarket
POLY_PRIVATE_KEY: str = os.getenv("POLY_PRIVATE_KEY", "")
POLY_API_KEY: str = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET: str = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE: str = os.getenv("POLY_API_PASSPHRASE", "")
POLY_HOST: str = os.getenv("POLY_HOST", "https://clob.polymarket.com")
POLY_CHAIN_ID: int = int(os.getenv("POLY_CHAIN_ID", "137"))  # Polygon mainnet

# Kalshi
KALSHI_API_KEY: str = os.getenv("KALSHI_API_KEY", "")
KALSHI_PRIVATE_KEY_PATH: str = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
KALSHI_HOST: str = os.getenv("KALSHI_HOST", "https://trading-api.kalshi.com/trade-api/v2")

# ---------------------------------------------------------------------------
# LLM Models (active roster — updated by model_selector)
# ---------------------------------------------------------------------------
MODELS: list[dict] = [
    {
        "id": "claude-sonnet-4-6",
        "provider": "anthropic",
        "has_logprobs": True,
        "weight": 1.0,
    },
    {
        "id": "gpt-4.1",
        "provider": "openai",
        "has_logprobs": True,
        "weight": 1.0,
    },
    {
        "id": "deepseek-chat",
        "provider": "deepseek",
        "has_logprobs": True,
        "weight": 0.8,
    },
]

CLASSIFIER_MODEL: str = os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")
PROMPT_EVOLVER_MODEL: str = os.getenv("PROMPT_EVOLVER_MODEL", "gpt-4.1")

# LLM API keys
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

# ---------------------------------------------------------------------------
# Domain configuration (descending LLM accuracy from the Lossfunk paper)
# ---------------------------------------------------------------------------
DOMAIN_PRIORITY: list[str] = [
    "geopolitics",
    "politics",
    "technology",
    "entertainment",
    "finance",
    "sports",
]

# Domains where news context HURTS accuracy (paper finding)
NEWS_NOISE_DOMAINS: set[str] = {"entertainment", "technology"}

# ---------------------------------------------------------------------------
# Trading parameters
# ---------------------------------------------------------------------------
MIN_EDGE: float = float(os.getenv("MIN_EDGE", "0.05"))          # 5%
KELLY_FRACTION: float = float(os.getenv("KELLY_FRACTION", "0.25"))  # 25% fractional
MAX_POSITION_PCT: float = float(os.getenv("MAX_POSITION_PCT", "0.05"))  # 5% of bankroll
MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "20"))

# ---------------------------------------------------------------------------
# Market filters
# ---------------------------------------------------------------------------
MIN_VOLUME_USD: float = float(os.getenv("MIN_VOLUME_USD", "10000.0"))
MIN_HOURS_TO_CLOSE: int = int(os.getenv("MIN_HOURS_TO_CLOSE", "48"))

# ---------------------------------------------------------------------------
# News / search
# ---------------------------------------------------------------------------
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
NEWS_SEARCH_PROVIDER: str = os.getenv("NEWS_SEARCH_PROVIDER", "tavily")  # or "brave"
MAX_NEWS_ARTICLES: int = 5

# ---------------------------------------------------------------------------
# Self-improvement
# ---------------------------------------------------------------------------
LEARNING_BATCH_SIZE: int = int(os.getenv("LEARNING_BATCH_SIZE", "10"))
ENTROPY_THRESHOLD_DEFAULT: float = float(os.getenv("ENTROPY_THRESHOLD_DEFAULT", "4.0"))  # bits
PROMPT_TOURNAMENT_MIN_TRIALS: int = int(os.getenv("PROMPT_TOURNAMENT_MIN_TRIALS", "20"))
MODEL_KILL_BRIER: float = float(os.getenv("MODEL_KILL_BRIER", "0.28"))
DOMAIN_WEIGHT_GOOD_BRIER: float = 0.15   # below → weight 1.5
DOMAIN_WEIGHT_BAD_BRIER: float = 0.25    # above → weight 0.3

# ---------------------------------------------------------------------------
# Scheduler intervals
# ---------------------------------------------------------------------------
SCAN_INTERVAL_HOURS: int = 4
PRICE_UPDATE_INTERVAL_MINUTES: int = 30
RESOLUTION_CHECK_INTERVAL_HOURS: int = 1
FORECAST_INTERVAL_HOURS: int = 4
SELF_IMPROVEMENT_HOUR: int = 6   # 6 AM daily

# ---------------------------------------------------------------------------
# Confidence tiers (entropy thresholds)
# ---------------------------------------------------------------------------
ENTROPY_HIGH_TIER: float = ENTROPY_THRESHOLD_DEFAULT
ENTROPY_MEDIUM_TIER: float = ENTROPY_THRESHOLD_DEFAULT * 1.5

# ---------------------------------------------------------------------------
# Retry / rate limiting
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3
RETRY_WAIT_SECONDS: float = 2.0
POLY_RATE_LIMIT_RPS: float = 5.0
KALSHI_RATE_LIMIT_RPS: float = 10.0
LLM_CONCURRENCY: int = 3  # max parallel LLM calls
