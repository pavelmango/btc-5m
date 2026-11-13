"""
Market and order book data models for CLOB prediction markets.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Venue(str, Enum):
    POLYMARKET = "polymarket"
    KALSHI = "kalshi"
    SPOT = "spot"

class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    YES = "YES"
    NO = "NO"

class WindowStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    SETTLED = "SETTLED"
    GAP = "GAP"

class BookLevel(BaseModel):
    price: float = Field(ge=0.0, le=1.0)
    size: float = Field(gt=0.0)

class OrderBook(BaseModel):
    venue: Venue
    window_id: str
    timestamp: float  # Unix epoch seconds
    bids: List[BookLevel] = Field(default_factory=list)  # sorted descending
    asks: List[BookLevel] = Field(default_factory=list)  # sorted ascending

    @property
    def is_empty(self) -> bool:
        return len(self.bids) == 0 or len(self.asks) == 0

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return round(self.best_ask - self.best_bid, 6)
        return None

class Window(BaseModel):
    window_id: str
    venue: Venue
    series: str
    start_time: int       # Unix timestamp (seconds)
    end_time: int         # Unix timestamp (seconds)
    strike_price: Optional[float] = None
    settlement_price: Optional[float] = None
    outcome: Optional[str] = None  # "UP" / "DOWN"
    status: WindowStatus = WindowStatus.INITIALIZED

class SpotTick(BaseModel):
    timestamp: float
    symbol: str = "BTC-USD"
    price: float
    source: str = "coinbase"

class WindowGap(BaseModel):
    window_id: str
    venue: Venue
    expected_time: int
    reason: str
    details: str = ""
    logged_at: float
