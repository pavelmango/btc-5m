"""
Consilium schedule and decision timing architecture.
Requirement: Consilium meets every 4:20 of candle, decision is made 40 seconds before window close.
"""
from typing import Callable, Optional
from btc5m.models.market import Window
from config.constants import CANDLE_DURATION_SEC, CONSILIUM_TRIGGER_SEC, DECISION_WINDOW_SEC

class ConsiliumTiming:
    """
    Manages the 4:20 candle schedule.
    In a 300-second 5-minute window:
      - 00:00 -> Window opens (warmup / empty book)
      - 04:20 (260s) -> Consilium convenes and evaluates market state
      - 04:20 to 04:21 -> Decision finalized, paper order submitted
      - 05:00 (300s) -> Window close & settlement (Chainlink BTC/USD)
    """
    OFFSET_SECONDS = CONSILIUM_TRIGGER_SEC   # 260s (4:20)
    LEAD_TIME_SECONDS = DECISION_WINDOW_SEC  # 40s

    @classmethod
    def get_consilium_timestamp(cls, window_start_time: int) -> int:
        """Exact epoch seconds when consilium convenes for a given window."""
        return window_start_time + cls.OFFSET_SECONDS

    @classmethod
    def time_until_window_close(cls, current_time: float, window_start_time: int) -> float:
        """Seconds remaining until candle expiry."""
        close_time = window_start_time + CANDLE_DURATION_SEC
        return max(0.0, close_time - current_time)

    @classmethod
    def is_decision_time(cls, current_time: float, window_start_time: int, tolerance_sec: float = 2.0) -> bool:
        """
        True if current_time is at the 4:20 decision point (+/- tolerance).
        """
        target = cls.get_consilium_timestamp(window_start_time)
        return abs(current_time - target) <= tolerance_sec
