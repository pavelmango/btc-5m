"""
Backtest engine running paper trading strategies over historical windows.
Computes P&L net of realistic taker fees, slippage, and empty-book rejections.
"""
from typing import List, Callable, Optional
from btc5m.models.market import Window, OrderBook
from btc5m.models.execution import (
    PaperOrder,
    PaperTradeResult,
    BacktestReport,
    OrderSide,
)
from btc5m.simulator.engine import PaperExecutionEngine

class HistoricalBacktester:
    def __init__(
        self,
        engine: PaperExecutionEngine,
        strategy_fn: Optional[Callable[[Window, OrderBook, float], Optional[PaperOrder]]] = None
    ):
        self.engine = engine
        self.strategy_fn = strategy_fn or self.default_consilium_strategy

    @staticmethod
    def default_consilium_strategy(
        window: Window,
        book: OrderBook,
        decision_time: float
    ) -> Optional[PaperOrder]:
        """
        Default consilium strategy:
        At 4:20 into candle (40s before expiration), evaluate book and trade toward best momentum.
        """
        if book.is_empty:
            return None

        # Predict UP if best ask <= 0.50, else DOWN
        direction = "UP" if (book.best_ask or 0.5) <= 0.50 else "DOWN"
        return PaperOrder(
            order_id=f"order-{window.window_id}",
            window_id=window.window_id,
            venue=window.venue.value if hasattr(window.venue, "value") else str(window.venue),
            side=OrderSide.BUY,
            target_direction=direction,
            size=10.0,
            max_slippage=0.05,
            submitted_at=decision_time
        )

    def run_backtest(
        self,
        windows: List[Window],
        orderbooks_by_window: dict,
        decision_offset_sec: int = 260
    ) -> BacktestReport:
        """
        Run backtest across list of historical windows.
        """
        trades: List[PaperTradeResult] = []
        orders_submitted = 0
        orders_filled = 0
        empty_rejections = 0
        slippage_rejections = 0
        total_fees = 0.0
        gross_pnl = 0.0
        net_pnl = 0.0
        wins = 0

        for w in windows:
            # Consilium decision point: 4:20 into the window
            decision_time = w.start_time + decision_offset_sec
            book = orderbooks_by_window.get(w.window_id)

            # Strategy creates order
            order = self.strategy_fn(w, book if book else OrderBook(venue=w.venue, window_id=w.window_id, timestamp=decision_time), decision_time)
            if order is None:
                continue

            orders_submitted += 1
            result = self.engine.execute_order(
                order=order,
                current_book=book,
                window=w,
                current_time=decision_time
            )

            # Check rejection reasons
            if result.rejection_reason:
                if "EMPTY" in result.rejection_reason:
                    empty_rejections += 1
                elif "SLIPPAGE" in result.rejection_reason:
                    slippage_rejections += 1

            if result.fill:
                orders_filled += 1
                total_fees += result.fill.taker_fee

                # Settle if window has known outcome
                if w.outcome:
                    self.engine.settle_trade(result, actual_outcome=w.outcome)
                    net_pnl += result.net_pnl
                    # Gross PnL excludes fee
                    cost_without_fee = result.fill.executed_price * result.fill.executed_size
                    gross_pnl += (result.payout - cost_without_fee)
                    if (result.order.target_direction.upper() == w.outcome.upper()):
                        wins += 1

            trades.append(result)

        win_rate = (wins / orders_filled) if orders_filled > 0 else 0.0
        avg_slippage = (
            sum(t.fill.slippage for t in trades if t.fill) / orders_filled
            if orders_filled > 0 else 0.0
        )

        return BacktestReport(
            venue=self.engine.venue,
            total_windows_evaluated=len(windows),
            orders_submitted=orders_submitted,
            orders_filled=orders_filled,
            empty_book_rejections=empty_rejections,
            slippage_rejections=slippage_rejections,
            gross_pnl=round(gross_pnl, 4),
            total_fees_paid=round(total_fees, 4),
            net_pnl=round(net_pnl, 4),
            win_rate=round(win_rate, 4),
            avg_slippage=round(avg_slippage, 6),
            trades=trades
        )
