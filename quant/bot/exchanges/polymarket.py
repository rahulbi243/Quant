"""
Polymarket CLOB exchange client.
Wraps py-clob-client for market discovery, price fetching, and order placement.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import (
    POLY_PRIVATE_KEY, POLY_API_KEY, POLY_API_SECRET, POLY_API_PASSPHRASE,
    POLY_HOST, POLY_CHAIN_ID, PAPER_MODE, MIN_VOLUME_USD, MIN_HOURS_TO_CLOSE,
    MAX_RETRIES,
)
from bot.exchanges.base import ExchangeClient, Market, Order, Position

log = logging.getLogger(__name__)

# Attempt import; gracefully degrade if package not installed
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
    _CLOB_AVAILABLE = True
except ImportError:
    _CLOB_AVAILABLE = False
    log.warning("py-clob-client not installed — Polymarket client disabled")


class PolymarketClient(ExchangeClient):
    """
    Polymarket CLOB API wrapper.

    In paper mode, place_order() records to DB only (no signing / submission).
    Real mode requires POLY_PRIVATE_KEY + API credentials.
    """

    def __init__(self) -> None:
        self._client: Optional[object] = None
        self._paper = PAPER_MODE

    def _get_client(self) -> "ClobClient":
        if self._client is None:
            if not _CLOB_AVAILABLE:
                raise RuntimeError("py-clob-client not installed")
            creds = ApiCreds(
                api_key=POLY_API_KEY,
                api_secret=POLY_API_SECRET,
                api_passphrase=POLY_API_PASSPHRASE,
            )
            self._client = ClobClient(
                host=POLY_HOST,
                chain_id=POLY_CHAIN_ID,
                key=POLY_PRIVATE_KEY or None,
                creds=creds,
            )
        return self._client  # type: ignore[return-value]

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def get_markets(self) -> list[Market]:
        """Return binary markets passing volume + time filters."""
        if not _CLOB_AVAILABLE or not POLY_API_KEY:
            log.info("Polymarket: returning empty market list (no credentials)")
            return []

        try:
            client = self._get_client()
            # py-clob-client is synchronous; run in executor for async compat
            import asyncio
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, lambda: client.get_markets())
        except Exception as exc:
            log.error("Polymarket get_markets failed: %s", exc)
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=MIN_HOURS_TO_CLOSE)
        markets = []
        for m in raw.get("data", []):
            try:
                close_time = _parse_dt(m.get("endDate") or m.get("end_date_iso", ""))
                if close_time and close_time < cutoff:
                    continue
                volume = float(m.get("volume", 0) or 0)
                if volume < MIN_VOLUME_USD:
                    continue
                # Only binary YES/NO markets
                tokens = m.get("tokens", [])
                if len(tokens) != 2:
                    continue
                yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
                if not yes_token:
                    continue
                price = float(yes_token.get("price", 0.5) or 0.5)
                market_id = f"polymarket:{m['condition_id']}"
                markets.append(
                    Market(
                        id=market_id,
                        exchange="polymarket",
                        question=m.get("question", ""),
                        market_price=price,
                        volume_usd=volume,
                        close_time=close_time or (now + timedelta(days=30)),
                        url=f"https://polymarket.com/event/{m.get('slug', '')}",
                    )
                )
            except Exception as exc:
                log.debug("Skipping polymarket market: %s", exc)

        log.info("Polymarket: found %d qualifying markets", len(markets))
        return markets

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def get_market_price(self, market_id: str) -> float:
        if not _CLOB_AVAILABLE or not POLY_API_KEY:
            return 0.5
        raw_id = market_id.removeprefix("polymarket:")
        try:
            import asyncio
            client = self._get_client()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: client.get_last_trade_price(token_id=raw_id)
            )
            return float(result.get("price", 0.5))
        except Exception as exc:
            log.error("Polymarket get_market_price(%s): %s", market_id, exc)
            return 0.5

    async def place_order(self, market_id: str, side: str, size: float, price: float) -> Order:
        if self._paper or PAPER_MODE:
            return Order(
                order_id=f"paper-poly-{market_id}-{side}",
                market_id=market_id,
                side=side,
                size=size,
                price=price,
                status="filled",
                is_paper=True,
                filled_at=datetime.now(timezone.utc),
            )
        # Real order placement
        if not _CLOB_AVAILABLE:
            raise RuntimeError("py-clob-client not installed")
        raw_id = market_id.removeprefix("polymarket:")
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        # Determine token_id (YES or NO)
        # For simplicity, trade YES side only; NO = 1-price inversion
        args = OrderArgs(
            price=price,
            size=size,
            side=side,
            token_id=raw_id,
        )
        result = await loop.run_in_executor(None, lambda: client.create_order(args))
        return Order(
            order_id=result.get("orderID", ""),
            market_id=market_id,
            side=side,
            size=size,
            price=price,
            status=result.get("status", "open"),
            is_paper=False,
            filled_at=datetime.now(timezone.utc),
        )

    async def get_positions(self) -> list[Position]:
        # Positions require subgraph / trading history — complex; return empty for now
        return []

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def get_resolved_markets(self, since: datetime) -> list[Market]:
        if not _CLOB_AVAILABLE or not POLY_API_KEY:
            return []
        try:
            import asyncio
            client = self._get_client()
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, lambda: client.get_markets(closed=True))
            result = []
            for m in raw.get("data", []):
                resolved_at = _parse_dt(m.get("resolutionTime") or m.get("end_date_iso", ""))
                if resolved_at and resolved_at < since:
                    continue
                tokens = m.get("tokens", [])
                outcome = None
                for t in tokens:
                    if t.get("winner"):
                        outcome = 1 if t.get("outcome", "").upper() == "YES" else 0
                        break
                result.append(
                    Market(
                        id=f"polymarket:{m['condition_id']}",
                        exchange="polymarket",
                        question=m.get("question", ""),
                        market_price=float(m.get("market_price", 0)),
                        volume_usd=float(m.get("volume", 0) or 0),
                        close_time=resolved_at or datetime.now(timezone.utc),
                        resolved=True,
                        outcome=outcome,
                    )
                )
            return result
        except Exception as exc:
            log.error("Polymarket get_resolved_markets: %s", exc)
            return []

    async def close(self) -> None:
        self._client = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        import dateutil.parser  # type: ignore
        return dateutil.parser.parse(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None
