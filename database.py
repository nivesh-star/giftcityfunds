"""
database.py
Creates the SQLite schema and loads:
  1. data/funds_cleaned.csv -> funds table
  2. logs/scrape_audit.log  -> scrape_audit table

Schema is Girish's original design, extended with fields my cleaning
pipeline actually produces (min_ticket, k1_compliant, return_3m/6m/
since_inception, has_return_data, direction, grouping, min_investment,
fund_status) -- documented here rather than silently dropping data I
worked to extract. Core required fields (fund_name, amc_name, category,
launch_date, nav, expense_ratio, aum, inception_date, last_updated) are
unchanged from the original spec.

fund_name is UNIQUE and loaded with INSERT OR REPLACE, so re-running this
script after a fresh scrape/clean never creates duplicate rows.
"""

import csv
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("gift_city_funds.db")
CSV_PATH = Path("data/funds_cleaned.csv")
AUDIT_LOG_PATH = Path("logs/scrape_audit.log")

SCHEMA = """
CREATE TABLE IF NOT EXISTS funds (
    fund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_name TEXT NOT NULL UNIQUE,
    amc_name TEXT NOT NULL,
    category TEXT,
    launch_date DATE,
    nav DECIMAL(10, 4),
    expense_ratio DECIMAL(5, 2),
    aum DECIMAL(15, 2),
    inception_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Extended fields beyond the original spec, kept because the source
    -- data genuinely supports them -- see cleaner.py docstring for the
    -- reasoning behind each.
    min_ticket DECIMAL(15, 2),
    k1_compliant BOOLEAN,
    return_3m DECIMAL(6, 2),
    return_6m DECIMAL(6, 2),
    return_since_inception DECIMAL(6, 2),
    has_return_data BOOLEAN,
    min_investment DECIMAL(15, 2),
    fund_status TEXT,
    direction TEXT,
    grouping TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS scrape_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    http_status INTEGER,
    success BOOLEAN,
    error_message TEXT,
    scraped_at TIMESTAMP
);
"""


def create_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def _to_float_or_none(value):
    if value is None or value == "":
        return None
    # min_investment/aum sometimes carry commas (e.g. "5,000") depending
    # on which cleaning step produced them -- strip defensively.
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _to_bool_or_none(value):
    if value in (None, ""):
        return None
    return str(value).strip().upper() in ("TRUE", "1", "YES")


def load_funds(conn, csv_path=CSV_PATH):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    cursor = conn.cursor()
    loaded = 0
    for row in rows:
        cursor.execute(
            """
            INSERT OR REPLACE INTO funds (
                fund_name, amc_name, category, launch_date, nav,
                expense_ratio, aum, inception_date,
                min_ticket, k1_compliant, return_3m, return_6m,
                return_since_inception, has_return_data,
                min_investment, fund_status, direction, grouping, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("fund_name"),
                row.get("amc_name"),
                row.get("category"),
                row.get("launch_date") or None,
                _to_float_or_none(row.get("nav")),
                _to_float_or_none(row.get("expense_ratio")),
                _to_float_or_none(row.get("aum_crores")),
                row.get("inception_date") or None,
                _to_float_or_none(row.get("min_ticket")),
                _to_bool_or_none(row.get("k1_compliant")),
                _to_float_or_none(row.get("return_3m")),
                _to_float_or_none(row.get("return_6m")),
                _to_float_or_none(row.get("return_since_inception")),
                _to_bool_or_none(row.get("has_return_data")),
                _to_float_or_none(row.get("min_investment")),
                row.get("fund_status") or None,
                row.get("direction"),
                row.get("grouping"),
                row.get("source_url"),
            ),
        )
        loaded += 1

    conn.commit()
    return loaded


def load_audit_log(conn, log_path=AUDIT_LOG_PATH):
    if not log_path.exists():
        print(f"  Warning: {log_path} not found, skipping audit load.")
        return 0

    cursor = conn.cursor()
    loaded = 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            cursor.execute(
                """
                INSERT INTO scrape_audit (url, http_status, success, error_message, scraped_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.get("url"),
                    entry.get("http_status"),
                    entry.get("success"),
                    entry.get("error_message"),
                    entry.get("scraped_at"),
                ),
            )
            loaded += 1

    conn.commit()
    return loaded


def run_load():
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    funds_loaded = load_funds(conn)
    print(f"Loaded {funds_loaded} funds into '{DB_PATH}'")

    audit_loaded = load_audit_log(conn)
    print(f"Loaded {audit_loaded} scrape_audit entries")

    # Quick sanity check -- fund_name uniqueness should hold given the
    # UNIQUE constraint + INSERT OR REPLACE, but verify rather than assume.
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM funds")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT fund_name) FROM funds")
    distinct = cursor.fetchone()[0]
    print(f"funds table: {total} rows, {distinct} distinct fund_name values")
    if total != distinct:
        print("  WARNING: duplicate fund_name values detected despite UNIQUE constraint.")

    conn.close()


if __name__ == "__main__":
    run_load()
