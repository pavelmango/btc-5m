"""
Test suite verifying historical storage range queries.
Acceptance Criterion:
"История доступна для чтения paper-движком: запрос по диапазону возвращает все окна."
"""
from btc5m.models.market import Window, OrderBook, BookLevel, Venue, WindowStatus
from btc5m.storage.repository import StorageRepository

def test_storage_range_query_all_windows():
    storage = StorageRepository(":memory:")
    base_time = 1700000000

    # Insert 288 5-minute windows (1 full 24h day)
    for i in range(288):
        start = base_time + i * 300
        end = start + 300
        w = Window(
            window_id=f"pm-win-{i}",
            venue=Venue.POLYMARKET,
            series="btc-updown-5m",
            start_time=start,
            end_time=end,
            strike_price=90000.0 + i,
            status=WindowStatus.CLOSED,
            outcome="UP" if i % 2 == 0 else "DOWN"
        )
        storage.save_window(w)

    # 1. Query full day
    all_windows = storage.get_windows(base_time, base_time + 86400, venue="polymarket")
    assert len(all_windows) == 288

    # 2. Query arbitrary 1-hour range (12 windows: 3600 / 300 = 12)
    hour_windows = storage.get_windows(base_time, base_time + 3599, venue="polymarket")
    assert len(hour_windows) == 12
    assert hour_windows[0].window_id == "pm-win-0"
    assert hour_windows[-1].window_id == "pm-win-11"

    # 3. Query specific window by ID
    single = storage.get_window("pm-win-42")
    assert single is not None
    assert single.window_id == "pm-win-42"
    assert single.strike_price == 90042.0

def test_orderbook_snapshot_retrieval():
    storage = StorageRepository(":memory:")
    book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id="pm-win-10",
        timestamp=1700003000.0,
        bids=[BookLevel(price=0.49, size=100.0)],
        asks=[BookLevel(price=0.51, size=100.0)],
    )
    storage.save_orderbook_snapshot(book)

    latest = storage.get_latest_orderbook("pm-win-10")
    assert latest is not None
    assert latest.window_id == "pm-win-10"
    assert latest.best_bid == 0.49
    assert latest.best_ask == 0.51
    assert abs(latest.spread - 0.02) < 1e-6
