"""
Entry point for the prediction market trading bot.

Usage:
    python run.py                 # Start full scheduler loop
    python run.py --dry-run       # Connect to both exchanges, print 5 sample markets
    python run.py --paper         # Run full pipeline on 1 market, print forecast + edge
    python run.py --once          # Run all jobs once then exit
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # type: ignore

load_dotenv(Path(__file__).parent / ".env")


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "aiosqlite", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def dry_run() -> None:
    """Connect to both exchanges, print 5 sample markets."""
    from bot.db import store as db
    await db.init_db()

    from bot.exchanges.polymarket import PolymarketClient
    from bot.exchanges.kalshi import KalshiClient
    import asyncio

    poly = PolymarketClient()
    kalshi = KalshiClient()

    poly_markets, kalshi_markets = await asyncio.gather(
        poly.get_markets(), kalshi.get_markets(), return_exceptions=True
    )
    await asyncio.gather(poly.close(), kalshi.close(), return_exceptions=True)

    print("\n=== Polymarket (first 5) ===")
    if isinstance(poly_markets, Exception):
        print(f"  ERROR: {poly_markets}")
    else:
        for m in poly_markets[:5]:  # type: ignore[index]
            print(f"  [{m.market_price:.1%}] {m.question[:80]}")

    print("\n=== Kalshi (first 5) ===")
    if isinstance(kalshi_markets, Exception):
        print(f"  ERROR: {kalshi_markets}")
    else:
        for m in kalshi_markets[:5]:  # type: ignore[index]
            print(f"  [{m.market_price:.1%}] {m.question[:80]}")


async def paper_run() -> None:
    """Run full pipeline on 1 market, print forecast + edge."""
    from bot.db import store as db
    await db.init_db()

    from bot.exchanges.scanner import scan_all_markets
    markets = await scan_all_markets()

    if not markets:
        print("No markets found. Check API credentials in .env")
        return

    market = markets[0]
    print(f"\n=== Processing market ===")
    print(f"  Exchange: {market.exchange}")
    print(f"  Question: {market.question}")
    print(f"  Market price: {market.market_price:.1%}")
    print(f"  Domain: {market.domain}")

    from bot.agent import _process_market
    await _process_market(market.to_dict())

    # Show results
    forecast = await db.get_latest_forecast(market.id)
    if forecast:
        print(f"\n=== Forecast ===")
        print(f"  Model:       {forecast['model']}")
        print(f"  Probability: {forecast['ensemble_probability']:.1%}")
        print(f"  Confidence:  {forecast['confidence_tier']}")
        print(f"  Entropy:     {forecast['entropy']:.2f} bits")
        edge_val = (forecast["ensemble_probability"] or 0.5) - market.market_price
        print(f"  Edge:        {edge_val:+.1%}")
        print(f"  Reasoning:   {forecast['reasoning_excerpt'][:200]}")

    from bot.trading.portfolio import print_summary
    await print_summary()


async def once_run() -> None:
    """Run all jobs once in sequence."""
    from bot.db import store as db
    await db.init_db()
    from bot.agent import load_state, scan_markets, update_prices, check_resolutions, run_forecasts

    await load_state()
    await scan_markets()
    await update_prices()
    await check_resolutions()
    await run_forecasts()


async def main_loop() -> None:
    """Start the full APScheduler loop."""
    from bot.db import store as db
    await db.init_db()

    from bot.agent import create_scheduler, load_state
    await load_state()

    scheduler = create_scheduler()
    scheduler.start()

    # Fire scan + forecast immediately on start
    from bot.agent import scan_markets, run_forecasts
    await scan_markets()
    await run_forecasts()

    logging.getLogger(__name__).info("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.getLogger(__name__).info("Scheduler stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prediction market trading bot")
    parser.add_argument("--dry-run", action="store_true", help="Connect and print sample markets")
    parser.add_argument("--paper", action="store_true", help="Run pipeline on 1 market")
    parser.add_argument("--once", action="store_true", help="Run all jobs once then exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    _configure_logging(args.verbose)

    if args.dry_run:
        asyncio.run(dry_run())
    elif args.paper:
        asyncio.run(paper_run())
    elif args.once:
        asyncio.run(once_run())
    else:
        asyncio.run(main_loop())
