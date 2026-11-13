"""
Test suite verifying realistic empty-book reproduction in early window.
Acceptance Criterion:
"Пустая книга в первые 1–2 минуты окна воспроизводится: нет bid/ask — нет сделки."
"""
from btc5m.models.market import Window, OrderBook, BookLevel, Venue, WindowStatus
from btc5m.models.execution import PaperOrder, OrderSide, OrderStatus
from btc5m.simulator.engine import PaperExecutionEngine

def test_early_window_warmup_empty_book():
    engine = PaperExecutionEngine(venue="polymarket", empty_book_warmup_seconds=90.0)
    window = Window(
        window_id="pm-warmup-1",
        venue=Venue.POLYMARKET,
        series="btc-updown-5m",
        start_time=1000,
        end_time=1300,
        status=WindowStatus.ACTIVE,
    )
    order = PaperOrder(
        order_id="order-early",
        window_id=window.window_id,
        venue="polymarket",
        side=OrderSide.BUY,
        target_direction="UP",
        size=10.0,
        submitted_at=1030.0, # 30 seconds into candle (< 90s warmup)
    )

    result = engine.execute_order(
        order=order,
        current_book=None,
        window=window,
        current_time=1030.0
    )

    assert result.fill is None
    assert result.order.status == OrderStatus.REJECTED_EMPTY_BOOK
    assert "EMPTY_BOOK" in result.rejection_reason

def test_empty_book_object_rejection():
    engine = PaperExecutionEngine(venue="polymarket")
    empty_book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id="pm-empty-2",
        timestamp=1200.0,
        bids=[],
        asks=[],
    )
    order = PaperOrder(
        order_id="order-empty-book",
        window_id="pm-empty-2",
        venue="polymarket",
        side=OrderSide.BUY,
        target_direction="UP",
        size=5.0,
        submitted_at=1200.0,
    )

    result = engine.execute_order(
        order=order,
        current_book=empty_book,
        window=None,
        current_time=1200.0
    )

    assert result.fill is None
    assert result.order.status == OrderStatus.REJECTED_EMPTY_BOOK
    assert result.rejection_reason == "REJECTED_EMPTY_BOOK"

def test_post_warmup_successful_fill():
    engine = PaperExecutionEngine(venue="polymarket", empty_book_warmup_seconds=90.0)
    window = Window(
        window_id="pm-fill-3",
        venue=Venue.POLYMARKET,
        series="btc-updown-5m",
        start_time=1000,
        end_time=1300,
        status=WindowStatus.ACTIVE,
    )
    active_book = OrderBook(
        venue=Venue.POLYMARKET,
        window_id=window.window_id,
        timestamp=1260.0, # 4:20 into candle (260s > 90s)
        bids=[BookLevel(price=0.49, size=50.0)],
        asks=[BookLevel(price=0.51, size=50.0)],
    )
    order = PaperOrder(
        order_id="order-consilium",
        window_id=window.window_id,
        venue="polymarket",
        side=OrderSide.BUY,
        target_direction="UP",
        size=10.0,
        submitted_at=1260.0,
    )

    result = engine.execute_order(
        order=order,
        current_book=active_book,
        window=window,
        current_time=1260.0
    )

    assert result.fill is not None
    assert result.order.status == OrderStatus.FILLED
    assert result.fill.executed_price == 0.51
    assert result.fill.executed_size == 10.0
    assert result.fill.taker_fee > 0.0
