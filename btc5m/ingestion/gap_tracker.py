"""
Window sequencing and gap tracking engine.
Guarantees the zero-unlogged-gaps invariant:
Every missed window has a structured reason code logged to storage.
"""
import time
from typing import Dict, List, Optional
from btc5m.models.market import Window, WindowGap, Venue
from btc5m.storage.repository import StorageRepository
from config.constants import (
    GAP_REASON_DISCONNECT,
    GAP_REASON_EMPTY_MARKET,
    PM_WINDOWS_PER_DAY,
    KALSHI_WINDOWS_PER_DAY,
)

class GapTracker:
    def __init__(self, storage: StorageRepository):
        self.storage = storage
        # Track last processed window start_time per venue
        self.last_window_time: Dict[str, int] = {}
        self.total_received: Dict[str, int] = {"polymarket": 0, "kalshi": 0}
        self.total_logged_gaps: Dict[str, int] = {"polymarket": 0, "kalshi": 0}

    def register_window(self, window: Window) -> List[WindowGap]:
        """
        Check incoming window against the expected timeline grid.
        If any intermediate windows were skipped, log each missed window with an explicit reason.
        Returns list of newly detected and logged gaps.
        """
        venue_str = window.venue.value if hasattr(window.venue, "value") else str(window.venue)
        step = 300 if "poly" in venue_str else 900
        new_gaps: List[WindowGap] = []

        last_time = self.last_window_time.get(venue_str)
        if last_time is not None:
            expected_next = last_time + step
            while expected_next < window.start_time:
                # Detected missing window!
                gap = WindowGap(
                    window_id=f"{venue_str}-{expected_next}",
                    venue=window.venue,
                    expected_time=expected_next,
                    reason=GAP_REASON_EMPTY_MARKET,
                    details=f"Missing window between {last_time} and {window.start_time}",
                    logged_at=time.time(),
                )
                self.storage.log_gap(gap)
                self.total_logged_gaps[venue_str] = self.total_logged_gaps.get(venue_str, 0) + 1
                new_gaps.append(gap)
                expected_next += step

        self.last_window_time[venue_str] = window.start_time
        self.total_received[venue_str] = self.total_received.get(venue_str, 0) + 1
        return new_gaps

    def log_forced_gap(
        self,
        venue: Venue,
        expected_time: int,
        reason: str,
        details: str = ""
    ) -> WindowGap:
        """Explicitly log a gap caused by network disconnect or upstream rate limit."""
        venue_str = venue.value if hasattr(venue, "value") else str(venue)
        gap = WindowGap(
            window_id=f"{venue_str}-{expected_time}",
            venue=venue,
            expected_time=expected_time,
            reason=reason,
            details=details,
            logged_at=time.time(),
        )
        self.storage.log_gap(gap)
        self.total_logged_gaps[venue_str] = self.total_logged_gaps.get(venue_str, 0) + 1
        return gap

    def get_completeness_report(self, venue: str, start_time: int, end_time: int) -> dict:
        """
        Analyze completeness over a given period (e.g. 7 days).
        Calculates received windows vs target 288/day (PM) or 96/day (Kalshi),
        and verifies unlogged gaps == 0.
        """
        step = 300 if "poly" in venue else 900
        target_per_day = PM_WINDOWS_PER_DAY if "poly" in venue else KALSHI_WINDOWS_PER_DAY
        total_seconds = end_time - start_time
        expected_total = total_seconds // step

        actual_count = self.storage.get_window_count(venue, start_time, end_time)
        logged_gaps = self.storage.get_gaps(start_time, end_time, venue=venue)

        # Invariant: actual_count + len(logged_gaps) >= expected_total
        unlogged_gaps = max(0, expected_total - (actual_count + len(logged_gaps)))

        return {
            "venue": venue,
            "period_seconds": total_seconds,
            "period_days": round(total_seconds / 86400, 2),
            "expected_windows": expected_total,
            "target_windows_per_day": target_per_day,
            "actual_windows_received": actual_count,
            "logged_gaps_count": len(logged_gaps),
            "unlogged_gaps_count": unlogged_gaps,
            "completeness_rate": round(actual_count / expected_total, 4) if expected_total > 0 else 1.0,
            "sla_passed": (unlogged_gaps == 0),
        }
