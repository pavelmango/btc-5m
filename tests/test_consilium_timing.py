"""
Test suite verifying consilium cadence: meeting at 4:20 of candle, decision 40 seconds before close.
"""
from btc5m.consilium.schedule import ConsiliumTiming
from config.constants import CANDLE_DURATION_SEC, CONSILIUM_TRIGGER_SEC, DECISION_WINDOW_SEC

def test_consilium_timing_exact_constants():
    assert CANDLE_DURATION_SEC == 300       # 5 minutes
    assert CONSILIUM_TRIGGER_SEC == 260     # 4 minutes 20 seconds
    assert DECISION_WINDOW_SEC == 40        # 40 seconds remaining
    assert CANDLE_DURATION_SEC - CONSILIUM_TRIGGER_SEC == DECISION_WINDOW_SEC

def test_consilium_timestamp_calculation():
    window_start = 1700000000
    expected_consilium_time = 1700000260

    ts = ConsiliumTiming.get_consilium_timestamp(window_start)
    assert ts == expected_consilium_time

    time_left = ConsiliumTiming.time_until_window_close(ts, window_start)
    assert time_left == 40.0

def test_is_decision_time_evaluator():
    window_start = 1700000000
    consilium_ts = window_start + 260

    # Right on time
    assert ConsiliumTiming.is_decision_time(consilium_ts, window_start) is True

    # Too early (e.g. 2:00 into candle)
    assert ConsiliumTiming.is_decision_time(window_start + 120, window_start) is False

    # After close
    assert ConsiliumTiming.is_decision_time(window_start + 301, window_start) is False
