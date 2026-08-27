"""
add_aum_history.py
One-time migration: adds an aum_history table (mirrors nav_history's shape)
and backfills it with every AUM figure we currently have on file -- one row
per fund that has a non-null funds.aum, dated to when we captured it
(last_updated), carrying the same source_name/source_url provenance already
on the fund record. No AUM value is fabricated; this is purely a structural
change plus a straight copy of what's already in the funds table.

Run once: python3 add_aum_history.py
Safe to re-run: skips a (fund_id, aum_date) pair already present.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("gift_city_amc_funds.db")


def migrate(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='aum_history'"
    ).fetchone()
    if not exists:
        print("Creating aum_history table...")
        conn.execute("""
            CREATE TABLE aum_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_id INTEGER NOT NULL REFERENCES funds(fund_id),
                aum_date DATE NOT NULL,
                aum REAL NOT NULL,
                aum_currency TEXT,
                aum_unit TEXT,
                source_name TEXT,
                source_url TEXT,
                UNIQUE(fund_id, aum_date)
            )
        """)
        conn.commit()
    else:
        print("aum_history already exists.")

    print("Backfilling from funds.aum (one snapshot per fund, dated to last_updated)...")
    rows = conn.execute("""
        SELECT fund_id, aum, aum_currency, aum_unit, source_name, source_url, last_updated
        FROM funds WHERE aum IS NOT NULL
    """).fetchall()

    written = 0
    for fund_id, aum, aum_currency, aum_unit, source_name, source_url, last_updated in rows:
        aum_date = (last_updated or "")[:10]  # 'YYYY-MM-DD HH:MM:SS' -> 'YYYY-MM-DD'
        if not aum_date:
            continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO aum_history
               (fund_id, aum_date, aum, aum_currency, aum_unit, source_name, source_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fund_id, aum_date, aum, aum_currency, aum_unit, source_name, source_url),
        )
        written += cur.rowcount
    conn.commit()
    print(f"Wrote {written} new aum_history row(s).")


def verify(conn: sqlite3.Connection) -> None:
    total = conn.execute("SELECT COUNT(*) FROM aum_history").fetchone()[0]
    funds_covered = conn.execute("SELECT COUNT(DISTINCT fund_id) FROM aum_history").fetchone()[0]
    print(f"aum_history now has {total} row(s) across {funds_covered} fund(s).")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    verify(conn)
    conn.close()
