"""
Ingestion daemon entry point.
Runs 24/7 continuous collection for Polymarket 5m, Kalshi 15m, and Spot BTC-USD feeds.
"""
import asyncio
import logging
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings, assert_paper_only
from btc5m.storage.repository import StorageRepository
from btc5m.ingestion.orchestrator import IngestionOrchestrator
from btc5m.observability.health import run_health_server
from btc5m.observability.metrics import ObservabilityManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("collector.main")

async def main():
    assert_paper_only()
    logger.info("Initializing Storage at %s...", settings.DB_PATH)
    storage = StorageRepository(settings.DB_PATH)
    orchestrator = IngestionOrchestrator(storage)

    # Start healthcheck and metrics HTTP endpoint
    obs_manager = ObservabilityManager(storage, orchestrator.gap_tracker)
    server = run_health_server(obs_manager, port=settings.METRICS_PORT)
    logger.info("Observability server listening on :%d (/health, /metrics)", settings.METRICS_PORT)

    logger.info("Starting 24/7 ingestion pipeline...")
    try:
        await orchestrator.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down collector...")
        orchestrator.stop()
    finally:
        server.shutdown()
        storage.close()

if __name__ == "__main__":
    asyncio.run(main())
