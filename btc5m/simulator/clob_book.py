"""
Central Limit Order Book (CLOB) matching and market maker liquidity simulation.
Exclusively models discrete limit order books; strictly NOT an AMM.
"""
from typing import List, Tuple, Optional
from btc5m.models.market import OrderBook, BookLevel
from btc5m.models.execution import OrderSide

class SimulatedCLOB:
    """
    CLOB matching engine with discrete price levels, spread, and market maker depth.
    """
    def __init__(self, book: OrderBook):
        self.venue = book.venue
        self.window_id = book.window_id
        self.timestamp = book.timestamp
        # Sort bids descending, asks ascending
        self.bids: List[BookLevel] = sorted(book.bids, key=lambda x: x.price, reverse=True)
        self.asks: List[BookLevel] = sorted(book.asks, key=lambda x: x.price, reverse=False)

    @property
    def is_empty(self) -> bool:
        return len(self.bids) == 0 or len(self.asks) == 0

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return round(self.best_ask - self.best_bid, 6)
        return None

    def match_market_order(
        self,
        side: OrderSide,
        size: float,
        max_slippage: float = 0.05
    ) -> Tuple[bool, float, float, float, str]:
        """
        Match an incoming market/taker order against the order book levels.
        Returns:
            (success, executed_size, vwap_price, slippage, reason_or_status)
        """
        # 1. Empty book check: In CLOB, no MM quotes means NO trade can occur.
        if self.is_empty:
            return False, 0.0, 0.0, 0.0, "REJECTED_EMPTY_BOOK"

        levels = self.asks if side == OrderSide.BUY else self.bids
        if not levels:
            return False, 0.0, 0.0, 0.0, "REJECTED_EMPTY_BOOK"

        initial_best_price = levels[0].price
        remaining_size = size
        total_cost = 0.0
        filled_size = 0.0

        # 2. Walk book depth across discrete limit levels
        for level in levels:
            available = level.size
            take_qty = min(remaining_size, available)
            total_cost += take_qty * level.price
            filled_size += take_qty
            remaining_size -= take_qty

            if remaining_size <= 1e-9:
                break

        if filled_size <= 1e-9:
            return False, 0.0, 0.0, 0.0, "INSUFFICIENT_LIQUIDITY"

        vwap_price = total_cost / filled_size
        slippage = abs(vwap_price - initial_best_price)

        # 3. Check slippage tolerance
        if slippage > max_slippage:
            return False, 0.0, 0.0, slippage, "EXCESSIVE_SLIPPAGE"

        if remaining_size > 1e-9:
            return True, filled_size, round(vwap_price, 6), round(slippage, 6), "PARTIAL_FILL"

        return True, filled_size, round(vwap_price, 6), round(slippage, 6), "FILLED"
