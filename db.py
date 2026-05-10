import sqlite3
import os
from contextlib import closing
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "stocks.db")


def _connect():
    return closing(sqlite3.connect(DB_PATH))


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                condition_type TEXT NOT NULL CHECK(condition_type IN ('gt', 'lt')),
                target_price REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                triggered_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT PRIMARY KEY,
                price REAL,
                change_pct REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def add_alert(symbol: str, condition_type: str, target_price: float) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO alerts (symbol, condition_type, target_price) VALUES (?, ?, ?)",
            (symbol.upper(), condition_type, target_price),
        )
        conn.commit()
        return cursor.lastrowid


def get_active_alerts():
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT id, symbol, condition_type, target_price FROM alerts WHERE is_active = 1"
        )
        return cursor.fetchall()


def get_all_alerts():
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT id, symbol, condition_type, target_price, is_active FROM alerts ORDER BY id DESC"
        )
        return cursor.fetchall()


def deactivate_alert(alert_id: int):
    with _connect() as conn:
        conn.execute(
            "UPDATE alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert_id),
        )
        conn.commit()


def delete_alert(alert_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()


def cache_price(symbol: str, price: float, change_pct: float = None):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO price_cache (symbol, price, change_pct, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                price=excluded.price,
                change_pct=excluded.change_pct,
                updated_at=excluded.updated_at
            """,
            (symbol.upper(), price, change_pct, datetime.now().isoformat()),
        )
        conn.commit()


def get_cached_price(symbol: str):
    with _connect() as conn:
        cursor = conn.execute(
            "SELECT price, change_pct, updated_at FROM price_cache WHERE symbol = ?",
            (symbol.upper(),),
        )
        return cursor.fetchone()
