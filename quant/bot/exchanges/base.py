"""
Abstract base class for exchange clients.
All exchange implementations must satisfy this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Market:
    id: str                          # "{exchange}:{market_id}"
    exchange: str                    # "polymarket" | "kalshi"
    question: str
    market_price: float              # YES probability (0-1)
    volume_usd: float
    close_time: datetime
    url: str = ""
    domain: Optional[str] = None
    resolved: bool = False
    outcome: Optional[int] = None    # 1=YES, 0=NO

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exchange": self.exchange,
            "question": self.question,
            "market_price": self.market_price,
            "volume_usd": self.volume_usd,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "url": self.url,
            "domain": self.domain,
            "resolved": 1 if self.resolved else 0,
            "outcome": self.outcome,
            "dedup_group": None,
        }


@dataclass
class Order:
    order_id: str
    market_id: str
    side: str                        # "YES" | "NO"
    size: float
    price: float
    status: str                      # "filled" | "open" | "cancelled"
    is_paper: bool = True
    filled_at: Optional[datetime] = None


@dataclass
class Position:
    market_id: str
    side: str
    size: float
    avg_price: float
    current_price: float
    pnl: float = 0.0


class ExchangeClient(ABC):
    """Abstract exchange client. Implement for each venue."""

    @abstractmethod
    async def get_markets(self) -> list[Market]:
        """Return all tradeable markets passing the configured filters."""

    @abstractmethod
    async def get_market_price(self, market_id: str) -> float:
        """Return current YES price (0-1) for a market."""

    @abstractmethod
    async def place_order(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
    ) -> Order:
        """Submit an order. Raises if exchange rejects it."""

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Return current open positions."""

    @abstractmethod
    async def get_resolved_markets(self, since: datetime) -> list[Market]:
        """Return markets that resolved after `since`."""

    @abstractmethod
    async def close(self) -> None:
        """Clean up any open connections / sessions."""
