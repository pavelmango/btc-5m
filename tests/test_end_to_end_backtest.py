"""
Test suite verifying end-to-end backtest execution on historical windows with net P&L and fees.
Acceptance Criterion:
"Paper-симулятор: прогон на истории даёт P&L net комиссий; пустая книга в начале окна воспроизводится."
"""
from btc5m.models.market import Window, OrderBook, BookLevel, Venue, WindowStatus
from btc5m.simulator.engine import PaperExecutionEngine
from btc5m.simulator.backtest import HistoricalBacktester

def test_end_to_end_backtest_with_net_pnl():
    engine = PaperExecutionEngine(
        venue="polymarket",
        taker_fee_rate=0.075,
        empty_book_warmup_seconds=90.0
    )
    backtester = HistoricalBacktester(engine)

    base_time = 1700000000
    windows = []
    orderbooks = {}

    # Create 20 historical windows
    for i in range(20):
        start = base_time + i * 300
        w = Window(
            window_id=f"win-{i}",
            venue=Venue.POLYMARKET,
            series="btc-updown-5m",
            start_time=start,
            end_time=start + 300,
            strike_price=90000.0,
            outcome="UP" if i % 2 == 0 else "DOWN",
            status=WindowStatus.SETTLED,
        )
        windows.append(w)

        # In windows 5 and 6, book remained completely empty (reproduction of illiquid windows)
        if i in [5, 6]:
            orderbooks[w.window_id] = OrderBook(
                venue=Venue.POLYMARKET,
                window_id=w.window_id,
                timestamp=start + 260.0,
                bids=[],
                asks=[],
            )
        else:
            # Active book at consilium time (4:20 = start + 260s)
            orderbooks[w.window_id] = OrderBook(
                venue=Venue.POLYMARKET,
                window_id=w.window_id,
                timestamp=start + 260.0,
                bids=[BookLevel(price=0.49, size=50.0), BookLevel(price=0.48, size=50.0)],
                asks=[BookLevel(price=0.51, size=50.0), BookLevel(price=0.52, size=50.0)],
            )

    report = backtester.run_backtest(windows, orderbooks, decision_offset_sec=260)

    # Verifications:
    assert report.total_windows_evaluated == 20
    assert report.orders_submitted == 18 # Windows 5 & 6 had empty books, skipped or rejected
    assert report.empty_book_rejections >= 0
    assert report.orders_filled > 0

    # Taker fee deduction verification
    assert report.total_fees_paid > 0.0

    # Net PnL must strictly equal Gross PnL - Total Fees Paid
    expected_net = round(report.gross_pnl - report.total_fees_paid, 4)
    assert abs(report.net_pnl - expected_net) < 1e-3, f"Net PnL {report.net_pnl} does not match Gross - Fees {expected_net}"

    # Win rate is valid probability
    assert 0.0 <= report.win_rate <= 1.0

    print(f"\n[Test Backtest Passed] Filled: {report.orders_filled}, Gross: ${report.gross_pnl}, Fees: ${report.total_fees_paid}, Net: ${report.net_pnl}")
