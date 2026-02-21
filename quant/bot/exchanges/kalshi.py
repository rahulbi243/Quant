"""
Kalshi REST API v2 exchange client.
Uses aiohttp for direct REST calls (official SDK is optional).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from base64 import b64decode
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import (
    KALSHI_API_KEY, KALSHI_PRIVATE_KEY_PATH, KALSHI_HOST,
    PAPER_MODE, MIN_VOLUME_USD, MIN_HOURS_TO_CLOSE, MAX_RETRIES,
    KALSHI_RATE_LIMIT_RPS,
)
from bot.exchanges.base import ExchangeClient, Market, Order, Position

log = logging.getLogger(__name__)

_RSA_AVAILABLE = False
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    _RSA_AVAILABLE = True
except ImportError:
    log.warning("cryptography package not installed — Kalshi RSA auth disabled")


class KalshiClient(ExchangeClient):
    """
    Kalshi REST API v2 client.

    Handles RSA-based authentication (required for live trading).
    Paper mode bypasses all real API calls.
    """

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._private_key = None
        self._last_request = 0.0
        self._min_interval = 1.0 / KALSHI_RATE_LIMIT_RPS

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=KALSHI_HOST,
                headers={"Content-Type": "application/json"},
            )
        return self._session

    def _load_private_key(self):
        if self._private_key is not None:
            return self._private_key
        if not KALSHI_PRIVATE_KEY_PATH or not _RSA_AVAILABLE:
            return None
        try:
            with open(KALSHI_PRIVATE_KEY_PATH, "rb") as f:
                self._private_key = serialization.load_pem_private_key(f.read(), password=None)
        except Exception as exc:
            log.error("Failed to load Kalshi private key: %s", exc)
            return None
        return self._private_key

    def _sign_request(self, method: str, path: str, body: str = "") -> dict:
        """Generate Kalshi RSA auth headers."""
        if not _RSA_AVAILABLE:
            return {}
        pk = self._load_private_key()
        if not pk:
            return {}
        ts = str(int(time.time() * 1000))
        msg = ts + method.upper() + path + body
        signature = pk.sign(msg.encode(), padding.PKCS1v15(), hashes.SHA256())
        import base64
        return {
            "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
        }

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request = time.monotonic()

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def _get(self, path: str, params: dict | None = None) -> dict:
        await self._rate_limit()
        session = await self._get_session()
        headers = self._sign_request("GET", path)
        async with session.get(path, params=params, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    async def _post(self, path: str, payload: dict) -> dict:
        await self._rate_limit()
        import json
        body = json.dumps(payload)
        session = await self._get_session()
        headers = self._sign_request("POST", path, body)
        async with session.post(path, data=body, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_markets(self) -> list[Market]:
        if not KALSHI_API_KEY:
            log.info("Kalshi: returning empty market list (no API key)")
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=MIN_HOURS_TO_CLOSE)
        markets = []
        cursor = None

        while True:
            params: dict = {"limit": 200, "status": "open"}
            if cursor:
                params["cursor"] = cursor
            try:
                data = await self._get("/markets", params=params)
            except Exception as exc:
                log.error("Kalshi get_markets: %s", exc)
                break

            for m in data.get("markets", []):
                try:
                    close_time = _parse_kalshi_dt(m.get("close_time", ""))
                    if close_time and close_time < cutoff:
                        continue
                    # Only binary yes/no markets
                    if m.get("market_type") not in ("binary", "yes_no", None):
                        continue
                    yes_price = float(m.get("yes_bid", m.get("yes_ask", 0.5)) or 0.5)
                    # Normalise price to (yes_bid + yes_ask) / 2 if available
                    yes_bid = m.get("yes_bid")
                    yes_ask = m.get("yes_ask")
                    if yes_bid is not None and yes_ask is not None:
                        yes_price = (float(yes_bid) + float(yes_ask)) / 2 / 100.0
                    else:
                        yes_price = float(yes_price) / 100.0 if yes_price > 1 else float(yes_price)

                    volume = float(m.get("volume", 0) or 0)
                    if volume < MIN_VOLUME_USD:
                        continue

                    ticker = m.get("ticker", "")
                    markets.append(
                        Market(
                            id=f"kalshi:{ticker}",
                            exchange="kalshi",
                            question=m.get("title", ""),
                            market_price=yes_price,
                            volume_usd=volume,
                            close_time=close_time or (now + timedelta(days=30)),
                            url=f"https://kalshi.com/markets/{ticker}",
                        )
                    )
                except Exception as exc:
                    log.debug("Skipping kalshi market: %s", exc)

            cursor = data.get("cursor")
            if not cursor:
                break

        log.info("Kalshi: found %d qualifying markets", len(markets))
        return markets

    async def get_market_price(self, market_id: str) -> float:
        ticker = market_id.removeprefix("kalshi:")
        try:
            data = await self._get(f"/markets/{ticker}")
            m = data.get("market", {})
            yes_bid = m.get("yes_bid")
            yes_ask = m.get("yes_ask")
            if yes_bid is not None and yes_ask is not None:
                return (float(yes_bid) + float(yes_ask)) / 2 / 100.0
            return float(m.get("last_price", 50)) / 100.0
        except Exception as exc:
            log.error("Kalshi get_market_price(%s): %s", market_id, exc)
            return 0.5

    async def place_order(self, market_id: str, side: str, size: float, price: float) -> Order:
        if PAPER_MODE:
            return Order(
                order_id=f"paper-kalshi-{market_id}-{side}",
                market_id=market_id,
                side=side,
                size=size,
                price=price,
                status="filled",
                is_paper=True,
                filled_at=datetime.now(timezone.utc),
            )
        ticker = market_id.removeprefix("kalshi:")
        # Kalshi prices are in cents (0-100)
        kalshi_price = int(round(price * 100))
        payload = {
            "ticker": ticker,
            "action": "buy",
            "side": side.lower(),
            "count": int(size),
            "type": "limit",
            "yes_price": kalshi_price if side.upper() == "YES" else 100 - kalshi_price,
        }
        result = await self._post("/portfolio/orders", payload)
        order = result.get("order", {})
        return Order(
            order_id=order.get("order_id", ""),
            market_id=market_id,
            side=side,
            size=size,
            price=price,
            status=order.get("status", "open"),
            is_paper=False,
            filled_at=datetime.now(timezone.utc),
        )

    async def get_positions(self) -> list[Position]:
        try:
            data = await self._get("/portfolio/positions")
            result = []
            for pos in data.get("market_positions", []):
                ticker = pos.get("ticker", "")
                result.append(
                    Position(
                        market_id=f"kalshi:{ticker}",
                        side="YES" if pos.get("position", 0) > 0 else "NO",
                        size=abs(float(pos.get("position", 0))),
                        avg_price=float(pos.get("market_exposure", 0)),
                        current_price=0.0,
                        pnl=float(pos.get("realized_pnl", 0)),
                    )
                )
            return result
        except Exception as exc:
            log.error("Kalshi get_positions: %s", exc)
            return []

    async def get_resolved_markets(self, since: datetime) -> list[Market]:
        try:
            params = {
                "status": "finalized",
                "limit": 200,
                "min_close_ts": int(since.timestamp()),
            }
            data = await self._get("/markets", params=params)
            result = []
            for m in data.get("markets", []):
                ticker = m.get("ticker", "")
                result_str = m.get("result", "")
                outcome = None
                if result_str.lower() in ("yes", "b"):
                    outcome = 1
                elif result_str.lower() in ("no", "a"):
                    outcome = 0
                close_time = _parse_kalshi_dt(m.get("close_time", ""))
                result.append(
                    Market(
                        id=f"kalshi:{ticker}",
                        exchange="kalshi",
                        question=m.get("title", ""),
                        market_price=0.0,
                        volume_usd=float(m.get("volume", 0) or 0),
                        close_time=close_time or since,
                        resolved=True,
                        outcome=outcome,
                    )
                )
            return result
        except Exception as exc:
            log.error("Kalshi get_resolved_markets: %s", exc)
            return []

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


def _parse_kalshi_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.rstrip("Z"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None
