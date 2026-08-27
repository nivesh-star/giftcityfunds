"""
db.py
Single point of contact between the app and SQLite. Every route and service
module opens its connections through get_db_connection() so there is
exactly one place that knows the file path and row-factory setup -- if the
database ever moves or the connection needs tuning (e.g. WAL mode), it
changes here only.
"""

import sqlite3

from config import DB_PATH


def get_db_connection() -> sqlite3.Connection:
    """Opens a SQLite connection with dict-like row access enabled, so
    callers can use both row["column"] and dict(row) on the same result."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
