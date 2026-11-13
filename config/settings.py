"""
Core system configuration and safety invariants.
"""
from typing import Literal
from pydantic import BaseModel, Field

class SystemSettings(BaseModel):
    # CRITICAL INVARIANT: LIVE_MODE MUST DEFAULT TO FALSE.
    # No path exists to place real live orders.
    LIVE_MODE: bool = Field(
        default=False,
        description="Strict safety flag. Live order routing is permanently disabled in Phase 0."
    )
    
    # Environment
    ENVIRONMENT: Literal["paper", "development", "staging"] = "paper"
    
    # Storage settings
    DB_PATH: str = "data/btc5m_history.duckdb"
    PARQUET_EXPORT_DIR: str = "data/parquet"
    
    # Ingestion schedules
    PM_WINDOW_SECONDS: int = 300       # 5 minutes -> 288 windows/day
    KALSHI_WINDOW_SECONDS: int = 900   # 15 minutes -> 96 windows/day
    
    # Consilium timing
    CONSILIUM_DECISION_OFFSET_SECONDS: int = 260  # 4m 20s into candle
    CONSILIUM_LEAD_TIME_SECONDS: int = 40         # 40s before window close
    
    # Paper simulation realistic parameters
    PM_TAKER_FEE_RATE: float = 0.075   # Within PM range [0.0695, 0.095]
    KALSHI_TAKER_FEE_RATE: float = 0.07
    FEE_C_MULTIPLIER: float = 1.0
    DEFAULT_SIMULATED_LATENCY_MS: int = 80
    EMPTY_BOOK_WARMUP_SECONDS: int = 90  # 1.5 minutes empty book warmup
    
    # Endpoints
    PM_GAMMA_URL: str = "https://gamma-api.polymarket.com"
    PM_CLOB_WS_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    KALSHI_API_URL: str = "https://api.elections.kalshi.com/trade-api/v2"
    COINBASE_SPOT_URL: str = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
    
    # Observability
    METRICS_PORT: int = 9102

settings = SystemSettings()

def assert_paper_only() -> None:
    """Hard safety assertion preventing live execution."""
    if settings.LIVE_MODE is not False:
        raise RuntimeError("FATAL SAFETY VIOLATION: LIVE_MODE must be False. Phase 0 has $0 capital and no live path.")
