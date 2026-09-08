"""
add_computed_returns.py
One-time backfill: computes trailing returns (1M/3M/6M/YTD/1Y) for funds
that have real daily NAV history in nav_history but no AMC-disclosed
performance figures in fund_performance yet.

This does NOT touch any fund that already has factsheet-disclosed
performance data -- those numbers are the authoritative source and are
left alone. It only fills the gap for funds where we have nothing else to
show, using nothing but that fund's own real recorded NAVs:

    return_pct = (latest_nav / nav_from_N_days_ago - 1) * 100

A period is only written if nav_history actually has a snapshot at or
before the target lookback date -- e.g. a fund with 6 months of history
gets 1M/3M/6M/YTD but not 1Y, rather than guessing. source_name is set to
a distinct "GIFT360-computed" label (never mixed with real AMC-disclosed
rows) so anyone looking at fund_performance can tell at a glance which
figures came from an official factsheet and which were derived here.

Run once: python3 add_computed_returns.py
Safe to re-run: skips a (fund_id, period, share_class) row already present.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("gift_city_amc_funds.db")

PERIODS = {
    "1M": timedelta(days=30),
    "3M": timedelta(days=91),
    "6M": timedelta(days=182),
    "1Y": timedelta(days=365),
}

# fund_id -> which NAV share class the automation actually tracks for it,
# so the computed row is labeled accurately rather than left ambiguous.
SHARE_CLASS_BY_FUND = {
    228: "Class A1",
    229: "Class A1",
    232: "Class A1",
    326: "Class A1",
    329: "Class A1",
}

SOURCE_NAME = "GIFT360-computed from recorded nav_history (not AMC-disclosed)"


def eligible_funds(conn: sqlite3.Connection) -> list[int]:
    """Funds with nav_history but zero rows in fund_performance already --
    we never overwrite or supplement a fund that has real disclosed data."""
    nav_funds = {r[0] for r in conn.execute("SELECT DISTINCT fund_id FROM nav_history")}
    perf_funds = {r[0] for r in conn.execute("SELECT DISTINCT fund_id FROM fund_performance")}
    return sorted(nav_funds - perf_funds)


def compute_for_fund(conn: sqlite3.Connection, fund_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT nav_date, nav, nav_currency FROM nav_history WHERE fund_id = ? ORDER BY nav_date",
        (fund_id,)
    ).fetchall()
    if len(rows) < 2:
        return []  # a single snapshot has nothing to compare against

    dates = [datetime.strptime(r[0], "%Y-%m-%d") for r in rows]
    navs = [r[1] for r in rows]
    currency = rows[-1][2] or "USD"
    latest_date, latest_nav = dates[-1], navs[-1]

    out = []

    def add_row(period_label: str, target_date: datetime):
        candidates = [(d, n) for d, n in zip(dates, navs) if d <= target_date]
        if not candidates:
            return  # not enough history for this period -- skip, don't guess
        start_date, start_nav = candidates[-1]
        if start_date == latest_date:
            return  # target resolved to the same point -- nothing to measure
        return_pct = round((latest_nav / start_nav - 1) * 100, 2)
        out.append({
            "fund_id": fund_id,
            "period": period_label,
            "fund_return_pct": return_pct,
            "share_class": SHARE_CLASS_BY_FUND.get(fund_id),
            "currency": currency,
            "is_annualized": 0,
            "as_of_date": latest_date.strftime("%Y-%m-%d"),
            "source_name": SOURCE_NAME,
        })

    add_row("YTD", datetime(latest_date.year, 1, 1))
    for label, delta in PERIODS.items():
        add_row(label, latest_date - delta)

    return out


def migrate(conn: sqlite3.Connection) -> None:
    written = 0
    for fund_id in eligible_funds(conn):
        for row in compute_for_fund(conn, fund_id):
            existing = conn.execute(
                """SELECT 1 FROM fund_performance
                   WHERE fund_id = ? AND period = ? AND COALESCE(share_class, '') = COALESCE(?, '')""",
                (row["fund_id"], row["period"], row["share_class"])
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO fund_performance
                   (fund_id, period, fund_return_pct, share_class, currency,
                    is_annualized, as_of_date, source_name)
                   VALUES (:fund_id, :period, :fund_return_pct, :share_class, :currency,
                           :is_annualized, :as_of_date, :source_name)""",
                row
            )
            written += 1
    conn.commit()
    print(f"Wrote {written} new computed fund_performance row(s).")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    conn.close()
