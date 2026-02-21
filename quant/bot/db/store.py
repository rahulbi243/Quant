"""
Async SQLite access layer using aiosqlite.
All DB interaction goes through this module.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from bot.config import DB_PATH, SCHEMA_PATH, VIRTUAL_BANKROLL

log = logging.getLogger(__name__)

_db_path: Path = DB_PATH
_init_lock = asyncio.Lock()
_initialized = False


async def init_db(db_path: Path | None = None) -> None:
    """Create tables and seed initial state on first run."""
    global _db_path, _initialized
    async with _init_lock:
        if _initialized:
            return
        if db_path:
            _db_path = db_path
        schema = SCHEMA_PATH.read_text()
        async with aiosqlite.connect(_db_path) as db:
            await db.executescript(schema)
            # Seed virtual bankroll singleton if not present
            await db.execute(
                """
                INSERT OR IGNORE INTO portfolio_state (id, cash, total_value)
                VALUES (1, ?, ?)
                """,
                (VIRTUAL_BANKROLL, VIRTUAL_BANKROLL),
            )
            await db.commit()
        _initialized = True
        log.info("DB initialized at %s", _db_path)


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

async def upsert_market(market: dict[str, Any]) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO markets
                (id, exchange, question, domain, url, market_price, volume_usd,
                 close_time, resolved, outcome, dedup_group, updated_at)
            VALUES
                (:id, :exchange, :question, :domain, :url, :market_price, :volume_usd,
                 :close_time, :resolved, :outcome, :dedup_group, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                market_price = excluded.market_price,
                volume_usd   = excluded.volume_usd,
                resolved     = excluded.resolved,
                outcome      = excluded.outcome,
                domain       = COALESCE(excluded.domain, domain),
                dedup_group  = COALESCE(excluded.dedup_group, dedup_group),
                updated_at   = CURRENT_TIMESTAMP
            """,
            {
                "id": market["id"],
                "exchange": market["exchange"],
                "question": market["question"],
                "domain": market.get("domain"),
                "url": market.get("url"),
                "market_price": market.get("market_price"),
                "volume_usd": market.get("volume_usd", 0),
                "close_time": market.get("close_time"),
                "resolved": market.get("resolved", 0),
                "outcome": market.get("outcome"),
                "dedup_group": market.get("dedup_group"),
            },
        )
        await db.commit()


async def get_active_markets(exchange: str | None = None) -> list[dict]:
    async with get_db() as db:
        if exchange:
            cur = await db.execute(
                "SELECT * FROM markets WHERE resolved=0 AND exchange=?", (exchange,)
            )
        else:
            cur = await db.execute("SELECT * FROM markets WHERE resolved=0")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_market(market_id: str) -> dict | None:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM markets WHERE id=?", (market_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_unforecasted_markets(max_age_hours: int = 8) -> list[dict]:
    """Markets that have no forecast in the last max_age_hours."""
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT m.* FROM markets m
            WHERE m.resolved = 0
              AND NOT EXISTS (
                SELECT 1 FROM forecasts f
                WHERE f.market_id = m.id
                  AND f.created_at > datetime('now', ? || ' hours')
              )
            """,
            (f"-{max_age_hours}",),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def mark_market_resolved(market_id: str, outcome: int) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE markets SET resolved=1, outcome=? WHERE id=?",
            (outcome, market_id),
        )
        await db.commit()


async def update_market_price(market_id: str, price: float) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE markets SET market_price=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (price, market_id),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------

async def insert_forecast(f: dict[str, Any]) -> int:
    async with get_db() as db:
        cur = await db.execute(
            """
            INSERT INTO forecasts
                (market_id, model, prompt_version, raw_probability, entropy,
                 ensemble_probability, confidence_tier, reasoning_excerpt, news_used)
            VALUES
                (:market_id, :model, :prompt_version, :raw_probability, :entropy,
                 :ensemble_probability, :confidence_tier, :reasoning_excerpt, :news_used)
            """,
            f,
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def get_latest_forecast(market_id: str) -> dict | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM forecasts WHERE market_id=? ORDER BY created_at DESC LIMIT 1",
            (market_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_forecasts_for_market(market_id: str) -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM forecasts WHERE market_id=? ORDER BY created_at",
            (market_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

async def insert_trade(t: dict[str, Any]) -> int:
    async with get_db() as db:
        cur = await db.execute(
            """
            INSERT INTO trades
                (market_id, forecast_id, exchange, side, size_units, price,
                 kelly_fraction, edge, is_paper)
            VALUES
                (:market_id, :forecast_id, :exchange, :side, :size_units, :price,
                 :kelly_fraction, :edge, :is_paper)
            """,
            t,
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def count_open_positions() -> int:
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT COUNT(DISTINCT t.market_id) FROM trades t
            JOIN markets m ON t.market_id = m.id
            WHERE m.resolved = 0
            """,
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def has_position(market_id: str) -> bool:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT 1 FROM trades WHERE market_id=? LIMIT 1", (market_id,)
        )
        return await cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

async def insert_outcome(o: dict[str, Any]) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO outcomes
                (market_id, forecast_id, domain, model, prompt_version,
                 predicted_prob, actual_outcome, brier, resolved_at)
            VALUES
                (:market_id, :forecast_id, :domain, :model, :prompt_version,
                 :predicted_prob, :actual_outcome, :brier, :resolved_at)
            """,
            o,
        )
        await db.commit()


async def get_outcomes_since(since: datetime) -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM outcomes WHERE resolved_at > ?", (since.isoformat(),)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def count_new_outcomes(since: datetime) -> int:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM outcomes WHERE resolved_at > ?", (since.isoformat(),)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


# ---------------------------------------------------------------------------
# Calibration state
# ---------------------------------------------------------------------------

async def get_calibration_state(domain: str, model: str) -> dict | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM calibration_state WHERE domain=? AND model=?",
            (domain, model),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def upsert_calibration(domain: str, model: str, brier: float, n: int, weight: float, entropy_threshold: float | None = None) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO calibration_state
                (domain, model, brier_score, n_resolved, domain_weight, entropy_threshold, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain, model) DO UPDATE SET
                brier_score       = excluded.brier_score,
                n_resolved        = excluded.n_resolved,
                domain_weight     = excluded.domain_weight,
                entropy_threshold = COALESCE(excluded.entropy_threshold, entropy_threshold),
                updated_at        = CURRENT_TIMESTAMP
            """,
            (domain, model, brier, n, weight, entropy_threshold),
        )
        await db.commit()


async def get_all_calibration() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM calibration_state")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Model weights
# ---------------------------------------------------------------------------

async def get_model_weights() -> dict[str, float]:
    async with get_db() as db:
        cur = await db.execute("SELECT model, weight FROM model_weights")
        rows = await cur.fetchall()
        return {r["model"]: r["weight"] for r in rows}


async def upsert_model_weight(model: str, weight: float, rolling_brier: float | None, n_resolved: int) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO model_weights (model, weight, rolling_brier, n_resolved, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(model) DO UPDATE SET
                weight        = excluded.weight,
                rolling_brier = excluded.rolling_brier,
                n_resolved    = excluded.n_resolved,
                updated_at    = CURRENT_TIMESTAMP
            """,
            (model, weight, rolling_brier, n_resolved),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Prompt experiments
# ---------------------------------------------------------------------------

async def get_active_prompts(domain: str | None = None) -> list[dict]:
    async with get_db() as db:
        if domain:
            cur = await db.execute(
                "SELECT * FROM prompt_experiments WHERE active=1 AND (domain=? OR domain IS NULL)",
                (domain,),
            )
        else:
            cur = await db.execute("SELECT * FROM prompt_experiments WHERE active=1")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def upsert_prompt_experiment(p: dict[str, Any]) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO prompt_experiments
                (prompt_version, domain, prompt_template, n_trials, n_wins, mean_brier, active)
            VALUES
                (:prompt_version, :domain, :prompt_template, :n_trials, :n_wins, :mean_brier, :active)
            ON CONFLICT(prompt_version) DO UPDATE SET
                n_trials       = excluded.n_trials,
                n_wins         = excluded.n_wins,
                mean_brier     = excluded.mean_brier,
                active         = excluded.active
            """,
            p,
        )
        await db.commit()


async def retire_prompt(prompt_version: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE prompt_experiments SET active=0 WHERE prompt_version=?",
            (prompt_version,),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

async def get_portfolio() -> dict:
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM portfolio_state WHERE id=1")
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {"cash": VIRTUAL_BANKROLL, "total_value": VIRTUAL_BANKROLL}


async def update_portfolio(cash: float, total_value: float) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO portfolio_state (id, cash, total_value, updated_at)
            VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                cash        = excluded.cash,
                total_value = excluded.total_value,
                updated_at  = CURRENT_TIMESTAMP
            """,
            (cash, total_value),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# LLM cost tracking
# ---------------------------------------------------------------------------

async def log_llm_cost(model: str, input_tokens: int, output_tokens: int, cost_usd: float, call_type: str) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO llm_costs (model, input_tokens, output_tokens, cost_usd, call_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (model, input_tokens, output_tokens, cost_usd, call_type),
        )
        await db.commit()


async def get_total_llm_spend() -> float:
    async with get_db() as db:
        cur = await db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_costs")
        row = await cur.fetchone()
        return row[0] if row else 0.0
