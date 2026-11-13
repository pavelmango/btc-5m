"""
Ingestion module exports.
"""
from btc5m.ingestion.gap_tracker import GapTracker
from btc5m.ingestion.polymarket import PolymarketCollector
from btc5m.ingestion.kalshi import KalshiCollector
from btc5m.ingestion.spot_feed import SpotIndexCollector
from btc5m.ingestion.orchestrator import IngestionOrchestrator

__all__ = [
    "GapTracker",
    "PolymarketCollector",
    "KalshiCollector",
    "SpotIndexCollector",
    "IngestionOrchestrator",
]
