"""
normalize_db.py
One-time migration: pulls the repeated amc_name / category strings out of
`funds` into proper lookup tables (amcs, categories), so each AMC/category
is stored exactly once (3NF) instead of being duplicated on every fund row.

To keep every existing consumer (app.py's queries, database.py's CSV
importer, the Jinja templates) working unmodified, the real normalized
table is renamed to `funds_data`, and a view named `funds` is created on
top of it that re-joins amc_name/category back in under their original
column names. INSTEAD OF triggers on that view let INSERT/UPDATE/DELETE
statements that still target `funds` (as database.py's importer does)
keep working exactly as before -- the trigger resolves/creates the
amc_id and category_id behind the scenes.

Run once: python3 normalize_db.py
Safe to re-run: it's a no-op if `funds_data` already exists.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("gift_city_amc_funds.db")


def migrate(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "funds_data" in tables:
        print("Already normalized (funds_data exists). Nothing to do.")
        return

    conn.execute("PRAGMA foreign_keys = OFF")  # off for the duration of the migration itself

    print("1/8 Creating amcs and categories lookup tables...")
    conn.execute("""
        CREATE TABLE amcs (
            amc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amc_name TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("""
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
    """)

    print("2/8 Populating amcs from distinct funds.amc_name values...")
    conn.execute("""
        INSERT INTO amcs (amc_name)
        SELECT DISTINCT TRIM(amc_name) FROM funds
        WHERE amc_name IS NOT NULL AND TRIM(amc_name) != ''
    """)
    print("3/8 Populating categories from distinct funds.category values...")
    conn.execute("""
        INSERT INTO categories (category_name)
        SELECT DISTINCT TRIM(category) FROM funds
        WHERE category IS NOT NULL AND TRIM(category) != ''
    """)

    print("4/8 Renaming funds -> funds_data and adding FK columns...")
    conn.execute("ALTER TABLE funds RENAME TO funds_data")
    conn.execute("ALTER TABLE funds_data ADD COLUMN amc_id INTEGER REFERENCES amcs(amc_id)")
    conn.execute("ALTER TABLE funds_data ADD COLUMN category_id INTEGER REFERENCES categories(category_id)")

    print("5/8 Backfilling amc_id / category_id on every fund row...")
    conn.execute("""
        UPDATE funds_data
        SET amc_id = (SELECT amc_id FROM amcs WHERE amcs.amc_name = TRIM(funds_data.amc_name))
        WHERE amc_name IS NOT NULL AND TRIM(amc_name) != ''
    """)
    conn.execute("""
        UPDATE funds_data
        SET category_id = (SELECT category_id FROM categories WHERE categories.category_name = TRIM(funds_data.category))
        WHERE category IS NOT NULL AND TRIM(category) != ''
    """)

    print("6/8 Dropping the now-redundant amc_name / category TEXT columns...")
    conn.execute("ALTER TABLE funds_data DROP COLUMN amc_name")
    conn.execute("ALTER TABLE funds_data DROP COLUMN category")

    print("7/8 Creating compatibility view `funds` (same shape as before)...")
    conn.execute("""
        CREATE VIEW funds AS
        SELECT
            fd.*,
            a.amc_name AS amc_name,
            c.category_name AS category
        FROM funds_data fd
        LEFT JOIN amcs a ON fd.amc_id = a.amc_id
        LEFT JOIN categories c ON fd.category_id = c.category_id
    """)

    print("8/8 Creating INSTEAD OF triggers so old-style INSERT/UPDATE into `funds` still works...")
    # INSERT: resolve/create the amc + category row, then insert into funds_data.
    conn.execute("""
        CREATE TRIGGER funds_insert INSTEAD OF INSERT ON funds
        BEGIN
            INSERT OR IGNORE INTO amcs (amc_name)
                SELECT TRIM(NEW.amc_name) WHERE NEW.amc_name IS NOT NULL AND TRIM(NEW.amc_name) != '';
            INSERT OR IGNORE INTO categories (category_name)
                SELECT TRIM(NEW.category) WHERE NEW.category IS NOT NULL AND TRIM(NEW.category) != '';

            INSERT INTO funds_data (
                fund_id, fund_name, launch_date, nav, nav_currency, nav_as_of, expense_ratio,
                aum, aum_currency, aum_unit, inception_date, source_name, source_url,
                scraped_at, scrape_status, last_updated, source_tier, minimum_investment,
                lock_in_period, exit_load, benchmark_index, target_corpus_at_launch,
                fund_flow_type, fund_manager_name, underlying_fund_name, underlying_fund_manager,
                underlying_fund_domicile, fee_notes, isin, bloomberg_ticker, amc_id, category_id
            ) VALUES (
                NEW.fund_id, NEW.fund_name, NEW.launch_date, NEW.nav, NEW.nav_currency, NEW.nav_as_of, NEW.expense_ratio,
                NEW.aum, NEW.aum_currency, NEW.aum_unit, NEW.inception_date, NEW.source_name, NEW.source_url,
                NEW.scraped_at, NEW.scrape_status, NEW.last_updated, NEW.source_tier, NEW.minimum_investment,
                NEW.lock_in_period, NEW.exit_load, NEW.benchmark_index, NEW.target_corpus_at_launch,
                NEW.fund_flow_type, NEW.fund_manager_name, NEW.underlying_fund_name, NEW.underlying_fund_manager,
                NEW.underlying_fund_domicile, NEW.fee_notes, NEW.isin, NEW.bloomberg_ticker,
                (SELECT amc_id FROM amcs WHERE amc_name = TRIM(NEW.amc_name)),
                (SELECT category_id FROM categories WHERE category_name = TRIM(NEW.category))
            )
            ON CONFLICT(fund_name) DO UPDATE SET
                amc_id=excluded.amc_id, category_id=excluded.category_id,
                launch_date=excluded.launch_date, nav=excluded.nav,
                nav_currency=excluded.nav_currency, nav_as_of=excluded.nav_as_of,
                expense_ratio=excluded.expense_ratio, aum=excluded.aum,
                aum_currency=excluded.aum_currency, aum_unit=excluded.aum_unit,
                inception_date=excluded.inception_date,
                minimum_investment=excluded.minimum_investment,
                lock_in_period=excluded.lock_in_period, exit_load=excluded.exit_load,
                benchmark_index=excluded.benchmark_index,
                target_corpus_at_launch=excluded.target_corpus_at_launch,
                fund_flow_type=COALESCE(NULLIF(excluded.fund_flow_type, ''), funds_data.fund_flow_type),
                fund_manager_name=COALESCE(NULLIF(excluded.fund_manager_name, ''), funds_data.fund_manager_name),
                underlying_fund_name=COALESCE(NULLIF(excluded.underlying_fund_name, ''), funds_data.underlying_fund_name),
                underlying_fund_manager=COALESCE(NULLIF(excluded.underlying_fund_manager, ''), funds_data.underlying_fund_manager),
                underlying_fund_domicile=COALESCE(NULLIF(excluded.underlying_fund_domicile, ''), funds_data.underlying_fund_domicile),
                fee_notes=COALESCE(NULLIF(excluded.fee_notes, ''), funds_data.fee_notes),
                source_name=excluded.source_name,
                source_url=excluded.source_url, scraped_at=excluded.scraped_at,
                scrape_status=excluded.scrape_status, source_tier=excluded.source_tier,
                last_updated=CURRENT_TIMESTAMP;
        END
    """)
    # UPDATE: keep amc_id/category_id in sync if a caller ever updates funds.amc_name/category directly.
    conn.execute("""
        CREATE TRIGGER funds_update INSTEAD OF UPDATE ON funds
        BEGIN
            INSERT OR IGNORE INTO amcs (amc_name)
                SELECT TRIM(NEW.amc_name) WHERE NEW.amc_name IS NOT NULL AND TRIM(NEW.amc_name) != '';
            INSERT OR IGNORE INTO categories (category_name)
                SELECT TRIM(NEW.category) WHERE NEW.category IS NOT NULL AND TRIM(NEW.category) != '';

            UPDATE funds_data SET
                fund_name = NEW.fund_name,
                launch_date = NEW.launch_date, nav = NEW.nav, nav_currency = NEW.nav_currency,
                nav_as_of = NEW.nav_as_of, expense_ratio = NEW.expense_ratio, aum = NEW.aum,
                aum_currency = NEW.aum_currency, aum_unit = NEW.aum_unit, inception_date = NEW.inception_date,
                source_name = NEW.source_name, source_url = NEW.source_url, scraped_at = NEW.scraped_at,
                scrape_status = NEW.scrape_status, last_updated = NEW.last_updated, source_tier = NEW.source_tier,
                minimum_investment = NEW.minimum_investment, lock_in_period = NEW.lock_in_period,
                exit_load = NEW.exit_load, benchmark_index = NEW.benchmark_index,
                target_corpus_at_launch = NEW.target_corpus_at_launch, fund_flow_type = NEW.fund_flow_type,
                fund_manager_name = NEW.fund_manager_name, underlying_fund_name = NEW.underlying_fund_name,
                underlying_fund_manager = NEW.underlying_fund_manager,
                underlying_fund_domicile = NEW.underlying_fund_domicile, fee_notes = NEW.fee_notes,
                isin = NEW.isin, bloomberg_ticker = NEW.bloomberg_ticker,
                amc_id = (SELECT amc_id FROM amcs WHERE amc_name = TRIM(NEW.amc_name)),
                category_id = (SELECT category_id FROM categories WHERE category_name = TRIM(NEW.category))
            WHERE fund_id = OLD.fund_id;
        END
    """)
    conn.execute("""
        CREATE TRIGGER funds_delete INSTEAD OF DELETE ON funds
        BEGIN
            DELETE FROM funds_data WHERE fund_id = OLD.fund_id;
        END
    """)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("Done.")


def verify(conn: sqlite3.Connection) -> None:
    print("\n--- Verification ---")
    n_amcs = conn.execute("SELECT COUNT(*) FROM amcs").fetchone()[0]
    n_cats = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    n_funds = conn.execute("SELECT COUNT(*) FROM funds").fetchone()[0]
    n_funds_data = conn.execute("SELECT COUNT(*) FROM funds_data").fetchone()[0]
    print(f"amcs: {n_amcs} rows | categories: {n_cats} rows | funds view: {n_funds} rows | funds_data: {n_funds_data} rows")
    assert n_funds == n_funds_data, "row count mismatch between view and base table!"

    # Spot-check the view returns the exact same shape as the old flat table did.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(funds)")]
    assert "amc_name" in cols and "category" in cols, "view is missing amc_name/category!"
    print(f"funds view columns ({len(cols)}): {cols}")

    row = conn.execute("SELECT fund_id, fund_name, amc_name, category FROM funds LIMIT 1").fetchone()
    print("Sample row via view:", dict(zip(["fund_id", "fund_name", "amc_name", "category"], row)))


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    verify(conn)
    conn.close()
