"""Quality checks for the final individual-AMC SQLite dataset."""

import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).parent.parent / "gift_city_amc_funds.db"


@pytest.fixture
def db():
    connection = sqlite3.connect(DB_PATH)
    yield connection
    connection.close()


def test_no_null_fund_names(db):
    assert db.execute("SELECT COUNT(*) FROM funds WHERE fund_name IS NULL OR TRIM(fund_name) = ''").fetchone()[0] == 0


def test_unique_fund_names(db):
    total, distinct = db.execute("SELECT COUNT(*), COUNT(DISTINCT fund_name) FROM funds").fetchone()
    assert total == distinct


def test_nav_is_positive_when_present(db):
    assert db.execute("SELECT COUNT(*) FROM funds WHERE nav IS NOT NULL AND nav <= 0").fetchone()[0] == 0


def test_expense_ratio_is_reasonable_when_present(db):
    assert db.execute("SELECT COUNT(*) FROM funds WHERE expense_ratio IS NOT NULL AND NOT expense_ratio BETWEEN 0 AND 5").fetchone()[0] == 0


def test_nav_has_currency_when_present(db):
    assert db.execute("SELECT COUNT(*) FROM funds WHERE nav IS NOT NULL AND nav_currency IS NULL").fetchone()[0] == 0


def test_each_fund_has_official_source_metadata(db):
    assert db.execute("SELECT COUNT(*) FROM funds WHERE source_url IS NULL OR source_name IS NULL").fetchone()[0] == 0


def test_scrape_attempts_are_logged(db):
    assert db.execute("SELECT COUNT(*) FROM scrape_audit").fetchone()[0] >= 5


def test_all_configured_sources_succeeded(db):
    """A valid row is not enough: every configured AMC source must scrape."""
    assert db.execute("SELECT COUNT(*) FROM scrape_audit WHERE success = 0").fetchone()[0] == 0
