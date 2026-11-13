"""
Paper execution models: orders, fills, positions, and backtest metrics.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED_EMPTY_BOOK = "REJECTED_EMPTY_BOOK"
    REJECTED_SLIPPAGE = "REJECTED_SLIPPAGE"
    REJECTED_LIQUIDITY = "REJECTED_LIQUIDITY"

class PaperOrder(BaseModel):
    order_id: str
    window_id: str
    venue: str
    side: OrderSide
    target_direction: str    # "UP" or "DOWN" (YES/NO)
    size: float              # Number of contracts
    max_slippage: float = 0.05
    submitted_at: float      # Timestamp when consilium triggers order
    status: OrderStatus = OrderStatus.PENDING

class PaperFill(BaseModel):
    fill_id: str
    order_id: str
    window_id: str
    timestamp: float         # Execution timestamp (after simulated latency)
    executed_price: float    # Effective VWAP price paid
    executed_size: float
    taker_fee: float         # Fee = C * rate * p * (1 - p) * size
    nominal_top_price: float # Best quote at arrival time
    slippage: float          # executed_price - nominal_top_price
    latency_ms: float

class PaperTradeResult(BaseModel):
    order: PaperOrder
    fill: Optional[PaperFill] = None
    rejection_reason: Optional[str] = None
    outcome: Optional[str] = None       # Actual resolved window outcome ("UP" or "DOWN")
    payout: float = 0.0                # Final payout ($1.0 per winning share, $0 per losing share)
    net_pnl: float = 0.0               # payout - (size * price + fee)

class BacktestReport(BaseModel):
    venue: str
    total_windows_evaluated: int
    orders_submitted: int
    orders_filled: int
    empty_book_rejections: int
    slippage_rejections: int
    gross_pnl: float
    total_fees_paid: float
    net_pnl: float
    win_rate: float
    avg_slippage: float
    trades: List[PaperTradeResult] = Field(default_factory=list)
