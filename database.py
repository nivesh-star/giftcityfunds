"""Load the normalized individual-AMC dataset into SQLite idempotently."""

import csv
import json
import sqlite3
from pathlib import Path

# Kept separate from the earlier Fynprint-first database so prior work remains
# available for comparison while this source-first pipeline is validated.
DB_PATH = Path("gift_city_amc_funds.db")
CSV_PATH = Path("data/funds_cleaned.csv")
AUDIT_PATH = Path("logs/scrape_audit.log")
NAV_HISTORY_PATH = Path("data/nav_history.json")
HOLDINGS_PATH = Path("data/portfolio_holdings.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS funds (
    fund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_name TEXT NOT NULL UNIQUE, amc_name TEXT NOT NULL, category TEXT,
    launch_date DATE, nav REAL, nav_currency TEXT, nav_as_of DATE,
    expense_ratio REAL, aum REAL, aum_currency TEXT, aum_unit TEXT,
    inception_date DATE, minimum_investment TEXT, lock_in_period TEXT,
    exit_load TEXT, benchmark_index TEXT, target_corpus_at_launch TEXT,
    source_name TEXT NOT NULL, source_url TEXT NOT NULL,
    scraped_at TIMESTAMP NOT NULL, scrape_status TEXT NOT NULL,
    source_tier TEXT NOT NULL DEFAULT 'tier1_amc',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scrape_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL,
    http_status INTEGER, success BOOLEAN NOT NULL, error_message TEXT,
    scraped_at TIMESTAMP NOT NULL
);
-- NAV history: one row per (fund, date). Populated two ways -- (1) a real
-- multi-date series where a source actually publishes one (currently only
-- PPFAS Nasdaq 100's own "nav-history" page, via load_nav_history), and
-- (2) a same-day snapshot of whatever the funds table's current nav/nav_as_of
-- is, taken every time this script runs (snapshot_current_nav). (2) means
-- real, non-fabricated history accumulates naturally across future runs for
-- every fund that has a live NAV, rather than inventing past values.
CREATE TABLE IF NOT EXISTS nav_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(fund_id),
    nav_date DATE NOT NULL,
    nav REAL NOT NULL,
    nav_currency TEXT,
    source_name TEXT,
    UNIQUE(fund_id, nav_date)
);
-- Portfolio holdings: only populated for funds whose official factsheet
-- actually discloses individual security names (confirmed by hand for each
-- source -- most GIFT City factsheets show sector allocation or "invests
-- 99%+ in [domestic master fund]" instead, not stock-level holdings, and
-- institutional tier2 AIFs never disclose holdings publicly at all). A
-- snapshot per load, not a history -- weight_pct is NULL where a source
-- lists holding names without individual weights (e.g. PPFAS PMS).
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(fund_id),
    holding_name TEXT NOT NULL,
    weight_pct REAL,
    rank INTEGER,
    as_of_date DATE,
    source_name TEXT
);
"""


def nullable_float(value):
    return None if value in (None, "") else float(value)


def create_schema(conn):
    conn.executescript(SCHEMA)
    # Migration: the funds table may already exist from an earlier run of
    # this pipeline (before these columns existed). CREATE TABLE IF NOT
    # EXISTS won't add columns to an already-existing table, so add them
    # explicitly and ignore errors for columns that are already there.
    new_columns = [
        ("source_tier", "TEXT NOT NULL DEFAULT 'tier1_amc'"),
        ("minimum_investment", "TEXT"),
        ("lock_in_period", "TEXT"),
        ("exit_load", "TEXT"),
        ("benchmark_index", "TEXT"),
        ("target_corpus_at_launch", "TEXT"),
    ]
    for col_name, col_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE funds ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    # Drop exit_load_description -- dropped from the schema since it was
    # empty for nearly every fund (only HDFC populated it). Safe no-op if
    # the column was never created (e.g. on a brand-new database).
    try:
        conn.execute("ALTER TABLE funds DROP COLUMN exit_load_description")
    except sqlite3.OperationalError:
        pass  # column doesn't exist -- fine, nothing to drop


def load_funds(conn, csv_path=CSV_PATH):
    with open(csv_path, newline="", encoding="utf-8") as data_file:
        rows = list(csv.DictReader(data_file))
    # Clean up any stale rows from prior broken/partial runs -- e.g. a
    # NULL fund_name row from an earlier failure never gets overwritten
    # by ON CONFLICT (SQLite treats multiple NULLs as non-conflicting
    # under a UNIQUE constraint), so it would otherwise persist forever.
    conn.execute("DELETE FROM funds WHERE fund_name IS NULL OR TRIM(fund_name) = ''")
    for row in rows:
        conn.execute(
            """INSERT INTO funds (
                fund_name, amc_name, category, launch_date, nav, nav_currency,
                nav_as_of, expense_ratio, aum, aum_currency, aum_unit,
                inception_date, minimum_investment, lock_in_period, exit_load,
                benchmark_index, target_corpus_at_launch,
                source_name, source_url, scraped_at, scrape_status,
                source_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fund_name) DO UPDATE SET
                amc_name=excluded.amc_name, category=excluded.category,
                launch_date=excluded.launch_date, nav=excluded.nav,
                nav_currency=excluded.nav_currency, nav_as_of=excluded.nav_as_of,
                expense_ratio=excluded.expense_ratio, aum=excluded.aum,
                aum_currency=excluded.aum_currency, aum_unit=excluded.aum_unit,
                inception_date=excluded.inception_date,
                minimum_investment=excluded.minimum_investment,
                lock_in_period=excluded.lock_in_period, exit_load=excluded.exit_load,
                benchmark_index=excluded.benchmark_index,
                target_corpus_at_launch=excluded.target_corpus_at_launch,
                source_name=excluded.source_name,
                source_url=excluded.source_url, scraped_at=excluded.scraped_at,
                scrape_status=excluded.scrape_status, source_tier=excluded.source_tier,
                last_updated=CURRENT_TIMESTAMP""",
            (row["fund_name"], row["amc_name"], row["category"] or None,
             row["launch_date"] or None, nullable_float(row["nav"]), row["nav_currency"] or None,
             row["nav_as_of"] or None, nullable_float(row["expense_ratio"]),
             nullable_float(row["aum"]), row["aum_currency"] or None, row["aum_unit"] or None,
             row["inception_date"] or None,
             row.get("minimum_investment") or None, row.get("lock_in_period") or None,
             row.get("exit_load") or None,
             row.get("benchmark_index") or None,
             row.get("target_corpus_at_launch") or None,
             row["source_name"], row["source_url"],
             row["scraped_at"], row["scrape_status"], row.get("source_tier") or "tier1_amc"),
        )
    return len(rows)


def load_audit(conn, audit_path=AUDIT_PATH):
    with open(audit_path, encoding="utf-8") as audit_file:
        rows = [json.loads(line) for line in audit_file if line.strip()]
    # The log is a snapshot of the current run, so replace the prior snapshot.
    conn.execute("DELETE FROM scrape_audit")
    conn.executemany(
        "INSERT INTO scrape_audit (url, http_status, success, error_message, scraped_at) VALUES (?, ?, ?, ?, ?)",
        [(row["url"], row["http_status"], row["success"], row["error_message"], row["scraped_at"]) for row in rows],
    )
    return len(rows)


def _fund_id_by_name(conn, fund_name):
    row = conn.execute("SELECT fund_id FROM funds WHERE fund_name = ?", (fund_name,)).fetchone()
    return row[0] if row else None


def load_nav_history(conn, path=NAV_HISTORY_PATH):
    """Loads a real multi-date NAV series where a source publishes one
    (currently only PPFAS Nasdaq 100's own nav-history page -- see
    scraper.py's scrape_ppfas_nasdaq_fund). Optional file: most funds have
    no such source, so a missing file is not an error, just zero rows."""
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    inserted = 0
    for row in rows:
        fund_id = _fund_id_by_name(conn, row["fund_name"])
        if fund_id is None or not row.get("nav_date") or row.get("nav") is None:
            continue
        conn.execute(
            """INSERT INTO nav_history (fund_id, nav_date, nav, nav_currency, source_name)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(fund_id, nav_date) DO UPDATE SET
                   nav=excluded.nav, nav_currency=excluded.nav_currency, source_name=excluded.source_name""",
            (fund_id, row["nav_date"], nullable_float(row["nav"]), row.get("nav_currency"), row.get("source_name")),
        )
        inserted += 1
    return inserted


def snapshot_current_nav(conn):
    """Appends today's (fund.nav, fund.nav_as_of) as one nav_history row for
    every fund that currently has a live NAV. Runs on every pipeline run --
    UNIQUE(fund_id, nav_date) means re-running the same day is a no-op, but
    running on a NEW day adds a new real data point. This is how a fund with
    no historical source (e.g. HDFC's, Mirae's live-NAV APIs, which only ever
    return today's value) still accumulates genuine history over time,
    instead of history being backfilled with invented past values."""
    rows = conn.execute(
        "SELECT fund_id, nav, nav_currency, nav_as_of, source_name FROM funds WHERE nav IS NOT NULL AND nav_as_of IS NOT NULL"
    ).fetchall()
    inserted = 0
    for fund_id, nav, nav_currency, nav_as_of, source_name in rows:
        conn.execute(
            """INSERT INTO nav_history (fund_id, nav_date, nav, nav_currency, source_name)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(fund_id, nav_date) DO UPDATE SET nav=excluded.nav""",
            (fund_id, nav_as_of, nav, nav_currency, source_name),
        )
        inserted += 1
    return inserted


def load_portfolio_holdings(conn, path=HOLDINGS_PATH):
    """Loads portfolio holdings for the small set of funds whose official
    factsheet actually discloses individual security names (see the
    schema comment on portfolio_holdings for why most funds have none).
    A snapshot, not a history -- each load replaces prior holdings for
    exactly the funds present in this file, leaving every other fund's
    holdings (i.e. none) untouched. Optional file, missing = 0 rows."""
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    fund_ids_touched = set()
    inserted = 0
    for row in rows:
        fund_id = _fund_id_by_name(conn, row["fund_name"])
        if fund_id is None or not row.get("holding_name"):
            continue
        if fund_id not in fund_ids_touched:
            conn.execute("DELETE FROM portfolio_holdings WHERE fund_id = ?", (fund_id,))
            fund_ids_touched.add(fund_id)
        conn.execute(
            """INSERT INTO portfolio_holdings (fund_id, holding_name, weight_pct, rank, as_of_date, source_name)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fund_id, row["holding_name"], nullable_float(row.get("weight_pct")),
             row.get("rank"), row.get("as_of_date"), row.get("source_name")),
        )
        inserted += 1
    return inserted


if __name__ == "__main__":
    with sqlite3.connect(DB_PATH) as conn:
        create_schema(conn)
        funds_count = load_funds(conn)
        audit_count = load_audit(conn)
        history_count = load_nav_history(conn)
        snapshot_count = snapshot_current_nav(conn)
        holdings_count = load_portfolio_holdings(conn)
        print(f"Loaded {funds_count} funds and {audit_count} audit entries into {DB_PATH}")
        print(f"  nav_history: {history_count} rows from a real published series, "
              f"{snapshot_count} rows from today's snapshot (existing dates are no-ops)")
        print(f"  portfolio_holdings: {holdings_count} rows")
