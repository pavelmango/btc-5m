"""
24/7 Ingestion Orchestrator.
Coordinates Polymarket 5m, Kalshi 15m, and Spot Feed collection loops.
Logs gaps automatically upon disconnects or errors.
"""
import asyncio
import logging
import signal
from typing import Optional
from btc5m.storage.repository import StorageRepository
from btc5m.ingestion.gap_tracker import GapTracker
from btc5m.ingestion.polymarket import PolymarketCollector
from btc5m.ingestion.kalshi import KalshiCollector
from btc5m.ingestion.spot_feed import SpotIndexCollector

logger = logging.getLogger("ingestion.orchestrator")

class IngestionOrchestrator:
    def __init__(self, storage: StorageRepository):
        self.storage = storage
        self.gap_tracker = GapTracker(storage)
        self.polymarket = PolymarketCollector(storage, self.gap_tracker)
        self.kalshi = KalshiCollector(storage, self.gap_tracker)
        self.spot = SpotIndexCollector(storage)
        self._shutdown_event = asyncio.Event()

    async def run_polymarket_loop(self) -> None:
        logger.info("Starting Polymarket 5m 24/7 ingestion loop (288 windows/day)...")
        while not self._shutdown_event.is_set():
            try:
                window = await self.polymarket.fetch_active_5m_window()
                if window:
                    logger.info("Polymarket 5m window active: %s", window.window_id)
            except Exception as e:
                logger.error("Unexpected error in PM loop: %s", e)
            await asyncio.sleep(60.0)

    async def run_kalshi_loop(self) -> None:
        logger.info("Starting Kalshi 15m 24/7 ingestion loop (96 windows/day)...")
        while not self._shutdown_event.is_set():
            try:
                windows = await self.kalshi.fetch_active_15m_markets()
                logger.info("Kalshi 15m fetched %d markets", len(windows))
            except Exception as e:
                logger.error("Unexpected error in Kalshi loop: %s", e)
            await asyncio.sleep(120.0)

    async def run_spot_loop(self) -> None:
        logger.info("Starting BTC/USD spot feed ground truth loop...")
        while not self._shutdown_event.is_set():
            try:
                tick = await self.spot.fetch_latest_tick()
                if tick:
                    logger.debug("Spot BTC-USD: %.2f", tick.price)
            except Exception as e:
                logger.error("Unexpected error in spot loop: %s", e)
            await asyncio.sleep(10.0)

    async def start(self) -> None:
        tasks = [
            asyncio.create_task(self.run_polymarket_loop()),
            asyncio.create_task(self.run_kalshi_loop()),
            asyncio.create_task(self.run_spot_loop()),
        ]
        await asyncio.gather(*tasks)

    def stop(self) -> None:
        self._shutdown_event.set()
