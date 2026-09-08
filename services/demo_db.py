"""
services/demo_db.py

The one place that opens a Postgres connection for the demo account /
portfolio tables. Replaces the old db.py, which used a local SQLite file --
SQLite can't work on Vercel (serverless filesystems are read-only apart from
/tmp, which is wiped between invocations), so demo signups and holdings would
have silently vanished.

FUND DATA DOES NOT COME FROM HERE. Funds, NAVs, holdings, allocations and
performance all come from the shared mf-engine-v2 API via
services/mf_engine.py. This module only stores the demo-specific rows that
have no home in that API: demo_users, demo_investor_profile, demo_holdings.

Connection settings come from the environment; nothing is hardcoded:

    DEMO_DATABASE_URL   full Postgres connection string for the demo tables

A connection is opened per request rather than pooled, because serverless
containers are frozen between invocations and a pooled socket would usually
be dead by the time the next request arrives.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras


class DemoDbError(RuntimeError):
    """Raised when the demo database isn't configured or can't be reached."""


def _dsn() -> str:
    dsn = os.environ.get("DEMO_DATABASE_URL")
    if not dsn:
        raise DemoDbError(
            "DEMO_DATABASE_URL is not set. The demo account/portfolio features "
            "need a Postgres connection; refusing to guess one."
        )
    return dsn


@contextmanager
def get_db_connection():
    """Yields a Postgres connection whose cursors return dict-like rows, so
    existing `row["column"]` access keeps working unchanged from the SQLite
    version. Commits on clean exit, rolls back on exception."""
    try:
        conn = psycopg2.connect(_dsn(), cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.Error as exc:
        raise DemoDbError(f"Could not connect to the demo database: {exc}") from exc

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(conn, sql: str, params: tuple = ()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(conn, sql: str, params: tuple = ()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(conn, sql: str, params: tuple = ()):
    """Runs a statement. If the SQL ends with RETURNING, returns that row."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if "returning" in sql.lower():
            return cur.fetchone()
        return None
