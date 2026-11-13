"""
Paper execution engine with realistic CLOB fills, taker fees, latency, and empty-book handling.
Zero live execution paths exist.
"""
import time
import uuid
from typing import Optional
from config.settings import assert_paper_only, settings
from btc5m.models.market import OrderBook, Window
from btc5m.models.execution import (
    PaperOrder,
    PaperFill,
    PaperTradeResult,
    OrderStatus,
)
from btc5m.simulator.fee_model import TakerFeeModel
from btc5m.simulator.clob_book import SimulatedCLOB

class PaperExecutionEngine:
    def __init__(
        self,
        venue: str = "polymarket",
        taker_fee_rate: Optional[float] = None,
        c_multiplier: float = 1.0,
        simulated_latency_ms: float = 80.0,
        empty_book_warmup_seconds: float = 90.0,
    ):
        # Mandatory Step 0: Ensure strictly paper mode
        assert_paper_only()

        self.venue = venue.lower()
        self.fee_model = TakerFeeModel(
            venue=venue,
            rate=taker_fee_rate or (settings.PM_TAKER_FEE_RATE if "poly" in venue else settings.KALSHI_TAKER_FEE_RATE),
            c_multiplier=c_multiplier
        )
        self.simulated_latency_ms = simulated_latency_ms
        self.empty_book_warmup_seconds = empty_book_warmup_seconds

    def execute_order(
        self,
        order: PaperOrder,
        current_book: Optional[OrderBook],
        window: Optional[Window] = None,
        current_time: Optional[float] = None
    ) -> PaperTradeResult:
        """
        Simulate realistic execution of a paper order against CLOB.
        """
        assert_paper_only()
        t_now = current_time if current_time is not None else time.time()

        # 1. Check window warmup (First 1-2 minutes: market makers have not posted quotes)
        if window is not None:
            elapsed = t_now - window.start_time
            if elapsed < self.empty_book_warmup_seconds:
                # In early window, order book is empty
                order.status = OrderStatus.REJECTED_EMPTY_BOOK
                return PaperTradeResult(
                    order=order,
                    fill=None,
                    rejection_reason="NO_MM_QUOTES_EARLY_WINDOW_EMPTY_BOOK"
                )

        # 2. Check if order book exists or is empty
        if current_book is None or current_book.is_empty:
            order.status = OrderStatus.REJECTED_EMPTY_BOOK
            return PaperTradeResult(
                order=order,
                fill=None,
                rejection_reason="REJECTED_EMPTY_BOOK"
            )

        # 3. Simulate execution latency (e.g. 80ms network + exchange processing)
        execution_time = t_now + (self.simulated_latency_ms / 1000.0)

        # 4. CLOB Discrete Level Matching (MM Depth Walking)
        clob = SimulatedCLOB(current_book)
        success, exec_size, vwap_price, slippage, status_msg = clob.match_market_order(
            side=order.side,
            size=order.size,
            max_slippage=order.max_slippage
        )

        if not success:
            if status_msg == "REJECTED_EMPTY_BOOK":
                order.status = OrderStatus.REJECTED_EMPTY_BOOK
            elif status_msg == "EXCESSIVE_SLIPPAGE":
                order.status = OrderStatus.REJECTED_SLIPPAGE
            else:
                order.status = OrderStatus.REJECTED_LIQUIDITY
            return PaperTradeResult(
                order=order,
                fill=None,
                rejection_reason=status_msg
            )

        # 5. Realistic Taker Fee Calculation: fee = C * rate * p * (1 - p) * size
        total_fee = self.fee_model.calculate_total_fee(exec_size, vwap_price)
        top_nominal = current_book.best_ask if order.side == "BUY" else current_book.best_bid
        if top_nominal is None:
            top_nominal = vwap_price

        fill = PaperFill(
            fill_id=f"fill-{uuid.uuid4().hex[:10]}",
            order_id=order.order_id,
            window_id=order.window_id,
            timestamp=execution_time,
            executed_price=vwap_price,
            executed_size=exec_size,
            taker_fee=total_fee,
            nominal_top_price=top_nominal,
            slippage=slippage,
            latency_ms=self.simulated_latency_ms
        )

        order.status = OrderStatus.FILLED
        return PaperTradeResult(
            order=order,
            fill=fill,
            rejection_reason=None
        )

    def settle_trade(
        self,
        trade_result: PaperTradeResult,
        actual_outcome: str
    ) -> PaperTradeResult:
        """
        Settle an executed paper trade at window expiry and calculate net P&L.
        Binary contract payout: $1.0 if predicted direction matches actual outcome, else $0.0.
        Net P&L = Payout - (Executed_Price * Size + Taker_Fee)
        """
        trade_result.outcome = actual_outcome
        if trade_result.fill is None:
            trade_result.payout = 0.0
            trade_result.net_pnl = 0.0
            return trade_result

        fill = trade_result.fill
        won = (trade_result.order.target_direction.upper() == actual_outcome.upper())
        payout_per_contract = 1.0 if won else 0.0
        total_payout = payout_per_contract * fill.executed_size
        cost_basis = (fill.executed_price * fill.executed_size) + fill.taker_fee

        trade_result.payout = round(total_payout, 6)
        trade_result.net_pnl = round(total_payout - cost_basis, 6)
        return trade_result
