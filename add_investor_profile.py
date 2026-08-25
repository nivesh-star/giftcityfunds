"""
add_investor_profile.py
One-time migration: adds a demo_investor_profile table (1:1 with demo_users)
to hold the Bank Details + Nominee info collected by the new multi-step
signup wizard. DEMO ONLY -- no real KYC, no real bank verification; this is
purely so the signup flow can show a realistic-looking record afterward.

Run once: python3 add_investor_profile.py
Safe to re-run: no-op if the table already exists.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("gift_city_amc_funds.db")


def migrate(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='demo_investor_profile'"
    ).fetchone()
    if exists:
        print("Already migrated (demo_investor_profile exists). Nothing to do.")
        return

    print("Creating demo_investor_profile table...")
    conn.execute("""
        CREATE TABLE demo_investor_profile (
            user_id INTEGER PRIMARY KEY REFERENCES demo_users(user_id),
            mobile_number TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            nominee_name TEXT,
            nominee_relationship TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    print("Done.")


def verify(conn: sqlite3.Connection) -> None:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(demo_investor_profile)")]
    print("demo_investor_profile columns:", cols)


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    verify(conn)
    conn.close()
