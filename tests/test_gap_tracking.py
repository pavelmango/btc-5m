"""
Test suite verifying 24/7 window sequencing and zero-unlogged-gaps invariant.
Acceptance Criterion:
"Сбор непрерывно 24/7 не менее 7 суток подряд без пропусков: 288 PM-окон + 96 Kalshi-окон в сутки;
каждый пропуск залогирован с причиной, незалогированных пропусков — 0."
"""
from btc5m.models.market import Window, Venue, WindowStatus
from btc5m.storage.repository import StorageRepository
from btc5m.ingestion.gap_tracker import GapTracker

def test_seven_day_polymarket_full_sequence_no_gaps():
    storage = StorageRepository(":memory:")
    tracker = GapTracker(storage)
    base_time = 1700000000

    # 7 days * 288 windows/day = 2016 windows
    total_expected = 7 * 288
    for i in range(total_expected):
        start = base_time + i * 300
        w = Window(
            window_id=f"pm-7d-{i}",
            venue=Venue.POLYMARKET,
            series="btc-updown-5m",
            start_time=start,
            end_time=start + 300,
            status=WindowStatus.CLOSED
        )
        storage.save_window(w)
        gaps = tracker.register_window(w)
        assert len(gaps) == 0

    report = tracker.get_completeness_report(
        venue="polymarket",
        start_time=base_time,
        end_time=base_time + 7 * 86400
    )

    assert report["expected_windows"] == 2016
    assert report["actual_windows_received"] == 2016
    assert report["logged_gaps_count"] == 0
    assert report["unlogged_gaps_count"] == 0
    assert report["completeness_rate"] == 1.0
    assert report["sla_passed"] is True

def test_seven_day_kalshi_full_sequence_no_gaps():
    storage = StorageRepository(":memory:")
    tracker = GapTracker(storage)
    base_time = 1700000000

    # 7 days * 96 windows/day = 672 windows
    total_expected = 7 * 96
    for i in range(total_expected):
        start = base_time + i * 900
        w = Window(
            window_id=f"kalshi-7d-{i}",
            venue=Venue.KALSHI,
            series="KXBTC15M",
            start_time=start,
            end_time=start + 900,
            status=WindowStatus.CLOSED
        )
        storage.save_window(w)
        gaps = tracker.register_window(w)
        assert len(gaps) == 0

    report = tracker.get_completeness_report(
        venue="kalshi",
        start_time=base_time,
        end_time=base_time + 7 * 86400
    )

    assert report["expected_windows"] == 672
    assert report["actual_windows_received"] == 672
    assert report["logged_gaps_count"] == 0
    assert report["unlogged_gaps_count"] == 0
    assert report["completeness_rate"] == 1.0
    assert report["sla_passed"] is True

def test_gap_detection_and_automatic_logging():
    storage = StorageRepository(":memory:")
    tracker = GapTracker(storage)
    base_time = 1700000000

    # Window 0 arrives
    w0 = Window(
        window_id="pm-w0",
        venue=Venue.POLYMARKET,
        series="btc-updown-5m",
        start_time=base_time,
        end_time=base_time + 300,
        status=WindowStatus.CLOSED
    )
    storage.save_window(w0)
    tracker.register_window(w0)

    # Windows 1 and 2 are skipped due to upstream issue! Window 3 arrives (start_time = base + 900)
    w3 = Window(
        window_id="pm-w3",
        venue=Venue.POLYMARKET,
        series="btc-updown-5m",
        start_time=base_time + 900,
        end_time=base_time + 1200,
        status=WindowStatus.CLOSED
    )
    storage.save_window(w3)
    detected_gaps = tracker.register_window(w3)

    # Exactly 2 gaps detected and logged with reason
    assert len(detected_gaps) == 2
    assert detected_gaps[0].expected_time == base_time + 300
    assert detected_gaps[1].expected_time == base_time + 600

    stored_gaps = storage.get_gaps(venue="polymarket")
    assert len(stored_gaps) == 2
    for g in stored_gaps:
        assert g.reason is not None
        assert len(g.reason) > 0

    # Completeness check: all missing windows are accounted for as logged gaps
    report = tracker.get_completeness_report(
        venue="polymarket",
        start_time=base_time,
        end_time=base_time + 1200
    )
    assert report["expected_windows"] == 4
    assert report["actual_windows_received"] == 2
    assert report["logged_gaps_count"] == 2
    assert report["unlogged_gaps_count"] == 0  # CRITICAL INVARIANT
    assert report["sla_passed"] is True
