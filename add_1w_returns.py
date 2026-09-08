"""
add_1w_returns.py
One-time backfill: adds a genuine 1-week (1W) trailing return for every fund
that has enough real recorded NAV history to support one, regardless of
whether that fund already has other disclosed/computed periods (1M, 3M,
SI, etc.) -- 1W is simply a period nobody had captured yet.

Prompted by comparing against getbelong.com's GIFT City Mutual Funds tool,
which shows 1W/1M/3M/All returns computed the same way: from a fund's own
recorded NAV history, not from a factsheet. We do the same here, honestly:

    return_pct = (latest_nav / nav_from_7_days_ago - 1) * 100

Skips any fund that: (a) has no nav_history, (b) has less than 7 days of
history span, or (c) already has a 1W row. Never overwrites or duplicates
an existing period for any fund.

Run once: python3 add_1w_returns.py
Safe to re-run: idempotent, skips funds that already have a 1W row.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("gift_city_amc_funds.db")

SOURCE_NAME = "GIFT360-computed from recorded nav_history (not AMC-disclosed)"


def already_has_1w(conn: sqlite3.Connection, fund_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM fund_performance WHERE fund_id = ? AND (period = '1W' OR period LIKE '1 Week%')",
        (fund_id,)
    ).fetchone() is not None


def compute_1w(conn: sqlite3.Connection, fund_id: int) -> dict | None:
    rows = conn.execute(
        "SELECT nav_date, nav, nav_currency FROM nav_history WHERE fund_id = ? ORDER BY nav_date",
        (fund_id,)
    ).fetchall()
    if len(rows) < 2:
        return None

    dates = [datetime.strptime(r[0], "%Y-%m-%d") for r in rows]
    navs = [r[1] for r in rows]
    currency = rows[-1][2] or "USD"
    latest_date, latest_nav = dates[-1], navs[-1]

    target = latest_date - timedelta(days=7)
    candidates = [(d, n) for d, n in zip(dates, navs) if d <= target]
    if not candidates:
        return None  # not enough history to reach 7 days back -- skip

    start_date, start_nav = candidates[-1]
    if start_date == latest_date:
        return None

    return {
        "fund_id": fund_id,
        "period": "1W",
        "fund_return_pct": round((latest_nav / start_nav - 1) * 100, 2),
        "currency": currency,
        "is_annualized": 0,
        "as_of_date": latest_date.strftime("%Y-%m-%d"),
        "source_name": SOURCE_NAME,
    }


def migrate(conn: sqlite3.Connection) -> None:
    fund_ids = [r[0] for r in conn.execute("SELECT DISTINCT fund_id FROM nav_history")]
    written = 0
    for fund_id in sorted(fund_ids):
        if already_has_1w(conn, fund_id):
            continue
        row = compute_1w(conn, fund_id)
        if row is None:
            continue
        conn.execute(
            """INSERT INTO fund_performance
               (fund_id, period, fund_return_pct, currency, is_annualized, as_of_date, source_name)
               VALUES (:fund_id, :period, :fund_return_pct, :currency, :is_annualized, :as_of_date, :source_name)""",
            row
        )
        written += 1
    conn.commit()
    print(f"Wrote {written} new 1W fund_performance row(s).")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    conn.close()
