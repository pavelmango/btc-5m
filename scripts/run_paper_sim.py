"""
Paper simulation runner.
Runs consilium paper execution strategy over historical windows and reports net PnL.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings, assert_paper_only
from btc5m.storage.repository import StorageRepository
from btc5m.simulator.engine import PaperExecutionEngine
from btc5m.simulator.backtest import HistoricalBacktester

def main():
    assert_paper_only()
    print("=== BTC 5M PAPER SIMULATOR EXECUTION ===")
    storage = StorageRepository(settings.DB_PATH)

    # Fetch all stored windows
    windows = storage.get_windows(start_time=0, end_time=2147483647, venue="polymarket")
    print(f"Loaded {len(windows)} historical Polymarket windows from storage.")

    # Load order books for each window
    orderbooks = {}
    for w in windows:
        book = storage.get_latest_orderbook(w.window_id)
        if book:
            orderbooks[w.window_id] = book

    engine = PaperExecutionEngine(venue="polymarket")
    backtester = HistoricalBacktester(engine)

    report = backtester.run_backtest(windows, orderbooks)

    print("\n--- SIMULATION RESULTS ---")
    print(f"Windows Evaluated:         {report.total_windows_evaluated}")
    print(f"Orders Submitted:          {report.orders_submitted}")
    print(f"Orders Filled:             {report.orders_filled}")
    print(f"Empty Book Rejections:     {report.empty_book_rejections} (reproduced empty book in early window)")
    print(f"Slippage Rejections:       {report.slippage_rejections}")
    print(f"Gross P&L:                 ${report.gross_pnl:.4f}")
    print(f"Total Taker Fees Paid:     ${report.total_fees_paid:.4f} [fee = C * rate * p * (1 - p)]")
    print(f"Net P&L:                   ${report.net_pnl:.4f}")
    print(f"Win Rate:                  {report.win_rate * 100:.2f}%")
    print(f"Avg Slippage:              ${report.avg_slippage:.6f}")
    print("--------------------------\n")

if __name__ == "__main__":
    main()
