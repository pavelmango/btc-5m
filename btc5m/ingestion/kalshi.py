"""
Kalshi BTC 15-minute data collector (KXBTC15M, 96 windows/day).
Settlement: CF Benchmarks BRTI (Bitcoin Real Time Index) 60-second average.
"""
import asyncio
import logging
import time
from typing import List, Optional
import httpx
from btc5m.models.market import Window, OrderBook, BookLevel, Venue, WindowStatus
from btc5m.storage.repository import StorageRepository
from btc5m.ingestion.gap_tracker import GapTracker
from config.settings import settings
from config.constants import GAP_REASON_DISCONNECT

logger = logging.getLogger("ingestion.kalshi")

class KalshiCollector:
    def __init__(self, storage: StorageRepository, gap_tracker: GapTracker):
        self.storage = storage
        self.gap_tracker = gap_tracker
        self.api_url = settings.KALSHI_API_URL

    @staticmethod
    def get_current_window_timestamps(current_time: Optional[float] = None) -> tuple[int, int]:
        """Align current time to standard 15-minute (900s) boundary."""
        now = int(current_time if current_time is not None else time.time())
        start = (now // 900) * 900
        end = start + 900
        return start, end

    async def fetch_active_15m_markets(self) -> List[Window]:
        """Query Kalshi API for KXBTC15M active contracts."""
        url = f"{self.api_url}/markets?series_ticker=KXBTC15M&limit=10"
        windows: List[Window] = []
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers={"User-Agent": "BTC-15M-Ingestion/0.1"})
                if resp.status_code == 200:
                    data = resp.json()
                    markets = data.get("markets", [])
                    for m in markets:
                        ticker = m.get("ticker", "")
                        # Parse expiration or use 15m cadence
                        start, end = self.get_current_window_timestamps()
                        w = Window(
                            window_id=f"kalshi-{ticker}",
                            venue=Venue.KALSHI,
                            series="KXBTC15M",
                            start_time=start,
                            end_time=end,
                            strike_price=float(m.get("floor_strike", 0.0) or 0.0) or None,
                            status=WindowStatus.ACTIVE if m.get("status") in ["active", "initialized"] else WindowStatus.CLOSED,
                        )
                        self.storage.save_window(w)
                        self.gap_tracker.register_window(w)
                        windows.append(w)
                    return windows
        except Exception as e:
            logger.warning("Error fetching Kalshi KXBTC15M markets: %s", e)
            start, _ = self.get_current_window_timestamps()
            self.gap_tracker.log_forced_gap(
                venue=Venue.KALSHI,
                expected_time=start,
                reason=GAP_REASON_DISCONNECT,
                details=str(e),
            )
        return []

    def record_simulated_orderbook(
        self,
        window: Window,
        timestamp: float,
        best_bid: float = 0.48,
        best_ask: float = 0.52,
        depth: int = 4
    ) -> OrderBook:
        """Record Kalshi order book snapshot with discrete CLOB levels."""
        elapsed = timestamp - window.start_time
        if elapsed < settings.EMPTY_BOOK_WARMUP_SECONDS:
            book = OrderBook(
                venue=Venue.KALSHI,
                window_id=window.window_id,
                timestamp=timestamp,
                bids=[],
                asks=[],
            )
        else:
            bids = [BookLevel(price=round(best_bid - i * 0.01, 4), size=40.0 + i * 15.0) for i in range(depth)]
            asks = [BookLevel(price=round(best_ask + i * 0.01, 4), size=40.0 + i * 15.0) for i in range(depth)]
            book = OrderBook(
                venue=Venue.KALSHI,
                window_id=window.window_id,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
            )

        self.storage.save_orderbook_snapshot(book)
        return book
