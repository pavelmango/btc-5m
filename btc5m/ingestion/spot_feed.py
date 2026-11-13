"""
BTC/USD spot feed collector for ground truth benchmark.
Settlement validation against Coinbase and Chainlink benchmarks.
"""
import asyncio
import logging
import time
from typing import Optional
import httpx
from btc5m.models.market import SpotTick
from btc5m.storage.repository import StorageRepository
from config.settings import settings

logger = logging.getLogger("ingestion.spot_feed")

class SpotIndexCollector:
    def __init__(self, storage: StorageRepository):
        self.storage = storage
        self.url = settings.COINBASE_SPOT_URL

    async def fetch_latest_tick(self) -> Optional[SpotTick]:
        """Fetch current BTC-USD spot price."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(self.url, headers={"User-Agent": "BTC-SpotFeed/0.1"})
                if resp.status_code == 200:
                    data = resp.json()
                    amount = float(data.get("data", {}).get("amount", 0.0))
                    tick = SpotTick(
                        timestamp=time.time(),
                        symbol="BTC-USD",
                        price=amount,
                        source="coinbase"
                    )
                    # DuckDB insert
                    self.storage.conn.execute("""
                        INSERT OR REPLACE INTO spot_ticks VALUES (?, ?, ?, ?, ?)
                    """, (
                        f"tick-{int(tick.timestamp * 1000)}",
                        tick.timestamp,
                        tick.symbol,
                        tick.price,
                        tick.source
                    ))
                    return tick
        except Exception as e:
            logger.warning("Error fetching spot tick: %s", e)
        return None
