"""
Test suite verifying CLOB market maker modeling (NOT AMM), spread, depth walking, and slippage.
"""
from btc5m.models.market import OrderBook, BookLevel, Venue
from btc5m.models.execution import OrderSide
from btc5m.simulator.clob_book import SimulatedCLOB

def test_clob_spread_and_levels():
    book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id="pm-test-1",
        timestamp=1000.0,
        bids=[BookLevel(price=0.48, size=10.0), BookLevel(price=0.47, size=20.0)],
        asks=[BookLevel(price=0.52, size=15.0), BookLevel(price=0.53, size=25.0)],
    )
    clob = SimulatedCLOB(book)
    assert clob.best_bid == 0.48
    assert clob.best_ask == 0.52
    assert abs(clob.spread - 0.04) < 1e-6
    assert not clob.is_empty

def test_clob_depth_walking_and_slippage():
    # Order book with limited top level: 10 contracts at 0.50, 10 contracts at 0.52
    book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id="pm-test-2",
        timestamp=1000.0,
        bids=[BookLevel(price=0.48, size=20.0)],
        asks=[BookLevel(price=0.50, size=10.0), BookLevel(price=0.52, size=10.0)],
    )
    clob = SimulatedCLOB(book)

    # Buy 20 contracts -> takes 10 at 0.50 + 10 at 0.52
    # VWAP = (10*0.50 + 10*0.52) / 20 = 10.20 / 20 = 0.51
    # Slippage = 0.51 - 0.50 = 0.01
    success, size, vwap, slippage, status = clob.match_market_order(
        side=OrderSide.BUY,
        size=20.0,
        max_slippage=0.05
    )
    assert success is True
    assert size == 20.0
    assert abs(vwap - 0.51) < 1e-5
    assert abs(slippage - 0.01) < 1e-5
    assert status == "FILLED"

def test_clob_slippage_rejection():
    # Attempting to buy with tight max_slippage = 0.005 should reject
    book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id="pm-test-3",
        timestamp=1000.0,
        bids=[BookLevel(price=0.48, size=20.0)],
        asks=[BookLevel(price=0.50, size=5.0), BookLevel(price=0.60, size=20.0)],
    )
    clob = SimulatedCLOB(book)
    success, size, vwap, slippage, status = clob.match_market_order(
        side=OrderSide.BUY,
        size=15.0,
        max_slippage=0.005
    )
    assert success is False
    assert status == "EXCESSIVE_SLIPPAGE"
