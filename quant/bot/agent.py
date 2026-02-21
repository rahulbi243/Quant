"""
APScheduler orchestrator: wires all jobs and runs the main forecast pipeline.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore

from bot.config import (
    SCAN_INTERVAL_HOURS,
    PRICE_UPDATE_INTERVAL_MINUTES,
    RESOLUTION_CHECK_INTERVAL_HOURS,
    FORECAST_INTERVAL_HOURS,
    SELF_IMPROVEMENT_HOUR,
    PAPER_MODE,
    MIN_EDGE,
    LEARNING_BATCH_SIZE,
)
from bot.db import store as db

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Job: Scan for new markets
# ──────────────────────────────────────────────────────────────────────────────

async def scan_markets() -> None:
    """Discover new markets on both exchanges and upsert to DB."""
    log.info("Job: scan_markets started")
    try:
        from bot.exchanges.scanner import scan_all_markets
        markets = await scan_all_markets()
        log.info("Job: scan_markets found %d markets", len(markets))
    except Exception as exc:
        log.error("scan_markets failed: %s", exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Job: Refresh prices
# ──────────────────────────────────────────────────────────────────────────────

async def update_prices() -> None:
    """Refresh market_price for all active markets."""
    log.info("Job: update_prices started")
    try:
        from bot.exchanges.scanner import refresh_prices
        await refresh_prices()
    except Exception as exc:
        log.error("update_prices failed: %s", exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Job: Check resolutions
# ──────────────────────────────────────────────────────────────────────────────

_last_outcome_count = 0


async def check_resolutions() -> None:
    """Poll exchanges for resolved markets and record outcomes."""
    global _last_outcome_count
    log.info("Job: check_resolutions started")
    try:
        from bot.learning.tracker import check_new_outcomes
        new_count = await check_new_outcomes()
        _last_outcome_count += new_count
        log.info("Job: check_resolutions recorded %d new outcomes (total since start: %d)",
                 new_count, _last_outcome_count)

        # Trigger self-improvement if we've accumulated enough data
        if _last_outcome_count >= LEARNING_BATCH_SIZE:
            log.info("Batch size reached — triggering incremental calibration")
            await _run_incremental_calibration()
            _last_outcome_count = 0
    except Exception as exc:
        log.error("check_resolutions failed: %s", exc, exc_info=True)


async def _run_incremental_calibration() -> None:
    """Run calibration + threshold adaptation (lighter than full daily job)."""
    from bot.learning.domain_calibrator import run_calibration
    from bot.learning.threshold_adapter import run_threshold_adaptation
    await run_calibration()
    await run_threshold_adaptation()


# ──────────────────────────────────────────────────────────────────────────────
# Job: Run forecasts
# ──────────────────────────────────────────────────────────────────────────────

async def run_forecasts() -> None:
    """For each unforecasted market, run the full prediction pipeline."""
    log.info("Job: run_forecasts started")
    try:
        markets = await db.get_unforecasted_markets(max_age_hours=FORECAST_INTERVAL_HOURS)
        if not markets:
            log.info("run_forecasts: no unforecasted markets")
            return
        log.info("run_forecasts: processing %d markets", len(markets))
        for market_dict in markets:
            await _process_market(market_dict)
    except Exception as exc:
        log.error("run_forecasts failed: %s", exc, exc_info=True)


async def _process_market(market_dict: dict) -> None:
    """Full pipeline for a single market."""
    from bot.exchanges.base import Market
    from bot.intelligence import classifier, news as news_module, forecaster, ensemble
    from bot.learning import domain_calibrator, model_selector, prompt_evolver
    from bot.trading.executor import TradeIntent, maybe_trade

    mid = market_dict["id"]
    question = market_dict["question"]
    domain = market_dict.get("domain")

    try:
        # Step 1: Classify domain if not yet classified
        if not domain:
            domain, _ = await classifier.classify(question)
            await db.upsert_market({**market_dict, "domain": domain})
            market_dict["domain"] = domain

        # Step 2: Reconstruct Market object
        from datetime import datetime as _dt
        close_time_raw = market_dict.get("close_time")
        close_time = (
            _dt.fromisoformat(close_time_raw) if close_time_raw
            else _dt.now(timezone.utc)
        )
        if hasattr(close_time, 'tzinfo') and close_time.tzinfo is None:
            close_time = close_time.replace(tzinfo=timezone.utc)

        market = Market(
            id=mid,
            exchange=market_dict["exchange"],
            question=question,
            market_price=float(market_dict.get("market_price") or 0.5),
            volume_usd=float(market_dict.get("volume_usd") or 0),
            close_time=close_time,
            domain=domain,
        )

        # Step 3: News context (domain-aware)
        news_ctx = await news_module.get_news_context(question, domain)

        # Step 4: Get active prompt
        prompt_version, prompt_template = await prompt_evolver.get_active_prompt(domain)

        # Step 5: Load model weights + calibration
        model_weights = await model_selector.get_current_weights()
        calibration_rows = await db.get_all_calibration()
        cal_lookup = ensemble.build_calibration_lookup(calibration_rows)
        domain_thresholds = ensemble.build_domain_thresholds(calibration_rows)

        # Build model configs with current weights
        from bot.config import MODELS
        model_configs = [
            {**cfg, "weight": model_weights.get(cfg["id"], cfg.get("weight", 1.0))}
            for cfg in MODELS
        ]

        # Step 6: Run forecasts
        forecasts = await forecaster.forecast(
            market=market,
            news=news_ctx,
            prompt_template=prompt_template,
            prompt_version=prompt_version,
            model_configs=model_configs,
            domain_thresholds=domain_thresholds,
        )

        if not forecasts:
            log.warning("No forecasts produced for %s", mid)
            return

        # Step 7: Ensemble
        ens_prob, ens_entropy, confidence = ensemble.combine(
            forecasts=forecasts,
            model_weights=model_weights,
            calibration=cal_lookup,
            domain=domain,
            domain_threshold=domain_thresholds.get(domain),
        )

        # Step 8: Store per-model forecasts + ensemble result
        last_forecast_id = None
        for f in forecasts:
            fid = await db.insert_forecast({
                "market_id": mid,
                "model": f.model,
                "prompt_version": f.prompt_version,
                "raw_probability": f.raw_probability,
                "entropy": f.entropy,
                "ensemble_probability": ens_prob,
                "confidence_tier": confidence,
                "reasoning_excerpt": f.reasoning,
                "news_used": 1 if f.news_used else 0,
            })
            last_forecast_id = fid

        # Step 9: Trading decision
        domain_weight = await domain_calibrator.get_domain_weight(domain, list(model_weights.keys())[0] if model_weights else "claude-sonnet-4-6")

        intent = TradeIntent(
            market=market,
            forecast_id=last_forecast_id or 0,
            ensemble_prob=ens_prob,
            confidence_tier=confidence,
            domain_weight=domain_weight,
        )
        trade_id = await maybe_trade(intent, paper_mode=PAPER_MODE)

        log.info(
            "Pipeline done: %s | domain=%s prob=%.3f entropy=%.2f conf=%s edge=%.3f trade=%s",
            mid, domain, ens_prob, ens_entropy, confidence,
            ens_prob - market.market_price,
            trade_id if trade_id else "none",
        )

    except Exception as exc:
        log.error("Pipeline failed for %s: %s", mid, exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Job: Daily self-improvement
# ──────────────────────────────────────────────────────────────────────────────

async def self_improvement() -> None:
    """Run full self-improvement cycle: domain calibration + model selection."""
    log.info("Job: self_improvement started")
    try:
        from bot.learning.domain_calibrator import run_calibration
        from bot.learning.model_selector import run_model_selection
        from bot.learning.threshold_adapter import run_threshold_adaptation
        await run_calibration()
        await run_model_selection()
        await run_threshold_adaptation()
        log.info("Job: self_improvement complete")
    except Exception as exc:
        log.error("self_improvement failed: %s", exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Job: Weekly prompt tournament
# ──────────────────────────────────────────────────────────────────────────────

async def prompt_tournament() -> None:
    """Run prompt A/B tournament for all domains."""
    log.info("Job: prompt_tournament started")
    try:
        from bot.learning.prompt_evolver import run_prompt_tournament
        from bot.config import DOMAIN_PRIORITY
        for domain in [None] + DOMAIN_PRIORITY:
            await run_prompt_tournament(domain)
        log.info("Job: prompt_tournament complete")
    except Exception as exc:
        log.error("prompt_tournament failed: %s", exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Startup: load state
# ──────────────────────────────────────────────────────────────────────────────

async def load_state() -> None:
    """Restore model weights + thresholds from DB on startup."""
    from bot.learning.model_selector import get_current_weights
    from bot.learning.prompt_evolver import seed_initial_prompts

    weights = await get_current_weights()
    await seed_initial_prompts()
    log.info("State loaded. Model weights: %s", {m: f"{w:.3f}" for m, w in weights.items()})
    from bot.trading.portfolio import print_summary
    await print_summary()


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler setup
# ──────────────────────────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        scan_markets,
        trigger=IntervalTrigger(hours=SCAN_INTERVAL_HOURS),
        id="scan_markets",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        update_prices,
        trigger=IntervalTrigger(minutes=PRICE_UPDATE_INTERVAL_MINUTES),
        id="update_prices",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        check_resolutions,
        trigger=IntervalTrigger(hours=RESOLUTION_CHECK_INTERVAL_HOURS),
        id="check_resolutions",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        run_forecasts,
        trigger=IntervalTrigger(hours=FORECAST_INTERVAL_HOURS),
        id="run_forecasts",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        self_improvement,
        trigger=CronTrigger(hour=SELF_IMPROVEMENT_HOUR, minute=0),
        id="self_improvement",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        prompt_tournament,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="prompt_tournament",
        replace_existing=True,
        max_instances=1,
    )

    return scheduler
