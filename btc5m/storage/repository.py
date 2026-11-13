"""
Time-series and historical market storage engine backed by DuckDB / SQLite.
Supports range queries across all historical windows, order books, and gap logs.
"""
import json
import os
from typing import List, Optional
import duckdb
from btc5m.models.market import (
    Window,
    OrderBook,
    BookLevel,
    SpotTick,
    WindowGap,
    Venue,
    WindowStatus,
)

class StorageRepository:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables for windows, orderbook snapshots, spot ticks, and gaps."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS windows (
                window_id VARCHAR PRIMARY KEY,
                venue VARCHAR NOT NULL,
                series VARCHAR NOT NULL,
                start_time BIGINT NOT NULL,
                end_time BIGINT NOT NULL,
                strike_price DOUBLE,
                settlement_price DOUBLE,
                outcome VARCHAR,
                status VARCHAR NOT NULL
            );
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS orderbooks (
                id VARCHAR PRIMARY KEY,
                window_id VARCHAR NOT NULL,
                venue VARCHAR NOT NULL,
                timestamp DOUBLE NOT NULL,
                bids_json VARCHAR NOT NULL,
                asks_json VARCHAR NOT NULL,
                best_bid DOUBLE,
                best_ask DOUBLE,
                spread DOUBLE
            );
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS spot_ticks (
                id VARCHAR PRIMARY KEY,
                timestamp DOUBLE NOT NULL,
                symbol VARCHAR NOT NULL,
                price DOUBLE NOT NULL,
                source VARCHAR NOT NULL
            );
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS window_gaps (
                window_id VARCHAR NOT NULL,
                venue VARCHAR NOT NULL,
                expected_time BIGINT NOT NULL,
                reason VARCHAR NOT NULL,
                details VARCHAR,
                logged_at DOUBLE NOT NULL
            );
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_windows_range ON windows(venue, start_time, end_time);
        """)

    def save_window(self, window: Window) -> None:
        venue_str = window.venue.value if hasattr(window.venue, "value") else str(window.venue)
        status_str = window.status.value if hasattr(window.status, "value") else str(window.status)
        self.conn.execute("""
            INSERT OR REPLACE INTO windows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            window.window_id,
            venue_str,
            window.series,
            window.start_time,
            window.end_time,
            window.strike_price,
            window.settlement_price,
            window.outcome,
            status_str,
        ))

    def get_window(self, window_id: str) -> Optional[Window]:
        rel = self.conn.execute("SELECT * FROM windows WHERE window_id = ?", (window_id,)).fetchall()
        if not rel:
            return None
        row = rel[0]
        return Window(
            window_id=row[0],
            venue=Venue(row[1]),
            series=row[2],
            start_time=row[3],
            end_time=row[4],
            strike_price=row[5],
            settlement_price=row[6],
            outcome=row[7],
            status=WindowStatus(row[8]),
        )

    def get_windows(
        self,
        start_time: int,
        end_time: int,
        venue: Optional[str] = None
    ) -> List[Window]:
        """Range query returning all windows within [start_time, end_time]."""
        if venue:
            query = "SELECT * FROM windows WHERE venue = ? AND start_time >= ? AND start_time <= ? ORDER BY start_time ASC"
            rows = self.conn.execute(query, (venue, start_time, end_time)).fetchall()
        else:
            query = "SELECT * FROM windows WHERE start_time >= ? AND start_time <= ? ORDER BY start_time ASC"
            rows = self.conn.execute(query, (start_time, end_time)).fetchall()

        windows = []
        for row in rows:
            windows.append(Window(
                window_id=row[0],
                venue=Venue(row[1]),
                series=row[2],
                start_time=row[3],
                end_time=row[4],
                strike_price=row[5],
                settlement_price=row[6],
                outcome=row[7],
                status=WindowStatus(row[8]),
            ))
        return windows

    def save_orderbook_snapshot(self, book: OrderBook) -> None:
        import uuid
        snap_id = f"snap-{uuid.uuid4().hex[:12]}"
        venue_str = book.venue.value if hasattr(book.venue, "value") else str(book.venue)
        bids_json = json.dumps([{"price": b.price, "size": b.size} for b in book.bids])
        asks_json = json.dumps([{"price": a.price, "size": a.size} for a in book.asks])
        self.conn.execute("""
            INSERT OR REPLACE INTO orderbooks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snap_id,
            book.window_id,
            venue_str,
            book.timestamp,
            bids_json,
            asks_json,
            book.best_bid,
            book.best_ask,
            book.spread,
        ))

    def get_latest_orderbook(self, window_id: str) -> Optional[OrderBook]:
        rows = self.conn.execute("""
            SELECT venue, window_id, timestamp, bids_json, asks_json
            FROM orderbooks
            WHERE window_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (window_id,)).fetchall()
        if not rows:
            return None
        row = rows[0]
        bids = [BookLevel(**item) for item in json.loads(row[3])]
        asks = [BookLevel(**item) for item in json.loads(row[4])]
        return OrderBook(
            venue=Venue(row[0]),
            window_id=row[1],
            timestamp=row[2],
            bids=bids,
            asks=asks,
        )

    def log_gap(self, gap: WindowGap) -> None:
        venue_str = gap.venue.value if hasattr(gap.venue, "value") else str(gap.venue)
        self.conn.execute("""
            INSERT INTO window_gaps VALUES (?, ?, ?, ?, ?, ?)
        """, (
            gap.window_id,
            venue_str,
            gap.expected_time,
            gap.reason,
            gap.details,
            gap.logged_at,
        ))

    def get_gaps(
        self,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        venue: Optional[str] = None
    ) -> List[WindowGap]:
        query = "SELECT window_id, venue, expected_time, reason, details, logged_at FROM window_gaps WHERE 1=1"
        params = []
        if start_time is not None:
            query += " AND expected_time >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND expected_time <= ?"
            params.append(end_time)
        if venue is not None:
            query += " AND venue = ?"
            params.append(venue)
        query += " ORDER BY expected_time ASC"

        rows = self.conn.execute(query, tuple(params)).fetchall()
        gaps = []
        for row in rows:
            gaps.append(WindowGap(
                window_id=row[0],
                venue=Venue(row[1]),
                expected_time=row[2],
                reason=row[3],
                details=row[4] or "",
                logged_at=row[5],
            ))
        return gaps

    def get_window_count(self, venue: str, start_time: int, end_time: int) -> int:
        res = self.conn.execute("""
            SELECT COUNT(*) FROM windows
            WHERE venue = ? AND start_time >= ? AND start_time <= ?
        """, (venue, start_time, end_time)).fetchone()
        return res[0] if res else 0

    def close(self) -> None:
        self.conn.close()
