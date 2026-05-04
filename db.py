import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "stocks.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            symbol TEXT PRIMARY KEY,
            price REAL,
            change_pct REAL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_alert(symbol: str, condition_type: str, target_price: float) -> int:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (symbol, condition_type, target_price) VALUES (?, ?, ?)",
        (symbol.upper(), condition_type, target_price),
    )
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_active_alerts():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, symbol, condition_type, target_price FROM alerts WHERE is_active = 1"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_alerts():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, symbol, condition_type, target_price, is_active FROM alerts ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def deactivate_alert(alert_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
        (datetime.now().isoformat(), alert_id),
    )
    conn.commit()
    conn.close()


def delete_alert(alert_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def cache_price(symbol: str, price: float, change_pct: float = None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
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
    conn.close()


def get_cached_price(symbol: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price, change_pct, updated_at FROM price_cache WHERE symbol = ?",
        (symbol.upper(),),
    )
    row = cursor.fetchone()
    conn.close()
    return row
