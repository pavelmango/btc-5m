"""
Polymarket BTC 5-minute data collector (btc-updown-5m, 288 windows/day).
Settlement: Chainlink BTC/USD price feed on Polygon.
"""
import asyncio
import json
import logging
import time
from typing import List, Optional
import httpx
from btc5m.models.market import Window, OrderBook, BookLevel, Venue, WindowStatus
from btc5m.storage.repository import StorageRepository
from btc5m.ingestion.gap_tracker import GapTracker
from config.settings import settings
from config.constants import GAP_REASON_DISCONNECT, GAP_REASON_EMPTY_MARKET

logger = logging.getLogger("ingestion.polymarket")

class PolymarketCollector:
    def __init__(self, storage: StorageRepository, gap_tracker: GapTracker):
        self.storage = storage
        self.gap_tracker = gap_tracker
        self.gamma_url = settings.PM_GAMMA_URL
        self.clob_ws_url = settings.PM_CLOB_WS_URL
        self._running = False

    @staticmethod
    def get_current_window_timestamps(current_time: Optional[float] = None) -> tuple[int, int]:
        """Align current time to standard 5-minute (300s) boundary."""
        now = int(current_time if current_time is not None else time.time())
        start = (now // 300) * 300
        end = start + 300
        return start, end

    async def fetch_active_5m_window(self) -> Optional[Window]:
        """
        Query Gamma API for current 5m BTC market.
        Falls back to deterministic window schema if market is rolling.
        """
        start, end = self.get_current_window_timestamps()
        slug = f"btc-updown-5m-{start}"
        url = f"{self.gamma_url}/events?slug={slug}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers={"User-Agent": "BTC-5M-Ingestion/0.1"})
                if resp.status_code == 200:
                    events = resp.json()
                    if events and len(events) > 0:
                        ev = events[0]
                        markets = ev.get("markets", [])
                        strike = None
                        if markets:
                            strike = float(markets[0].get("strikePrice", 0.0) or 0.0) or None
                        w = Window(
                            window_id=f"pm-5m-{start}",
                            venue=Venue.POLYMARKET,
                            series="btc-updown-5m",
                            start_time=start,
                            end_time=end,
                            strike_price=strike,
                            status=WindowStatus.ACTIVE,
                        )
                        self.storage.save_window(w)
                        self.gap_tracker.register_window(w)
                        return w

            # Even if Gamma index is lagging, initialize window deterministically for 24/7 continuity
            w = Window(
                window_id=f"pm-5m-{start}",
                venue=Venue.POLYMARKET,
                series="btc-updown-5m",
                start_time=start,
                end_time=end,
                status=WindowStatus.ACTIVE,
            )
            self.storage.save_window(w)
            self.gap_tracker.register_window(w)
            return w

        except Exception as e:
            logger.warning("Error fetching Polymarket 5m window: %s", e)
            self.gap_tracker.log_forced_gap(
                venue=Venue.POLYMARKET,
                expected_time=start,
                reason=GAP_REASON_DISCONNECT,
                details=str(e),
            )
            return None

    def record_simulated_orderbook(
        self,
        window: Window,
        timestamp: float,
        best_bid: float = 0.49,
        best_ask: float = 0.51,
        depth: int = 5
    ) -> OrderBook:
        """
        Record order book snapshot for the window.
        Respects empty book warmup in first 90 seconds.
        """
        elapsed = timestamp - window.start_time
        if elapsed < settings.EMPTY_BOOK_WARMUP_SECONDS:
            # Empty book during early window
            book = OrderBook(
                venue=Venue.POLYMARKET,
                window_id=window.window_id,
                timestamp=timestamp,
                bids=[],
                asks=[],
            )
        else:
            # Competitive market makers arrive with discrete depth
            bids = [BookLevel(price=round(best_bid - i * 0.01, 4), size=50.0 + i * 20.0) for i in range(depth)]
            asks = [BookLevel(price=round(best_ask + i * 0.01, 4), size=50.0 + i * 20.0) for i in range(depth)]
            book = OrderBook(
                venue=Venue.POLYMARKET,
                window_id=window.window_id,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
            )

        self.storage.save_orderbook_snapshot(book)
        return book
