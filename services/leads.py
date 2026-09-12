"""
services/leads.py
Lead-generation form storage: phone, email, and an optional note, submitted
from the "Talk to an Expert" modal available on every page.

Uses the same Postgres database as the demo account tables
(services/demo_db.py, DEMO_DATABASE_URL) -- there's no separate database for
this, just one more table in the one Postgres instance already provisioned
for anything that isn't fund data.
"""

from __future__ import annotations

import re

from services.demo_db import DemoDbError, execute, get_db_connection

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id SERIAL PRIMARY KEY,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    notes TEXT,
    source_page TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)


def validate_lead(data: dict) -> tuple[dict, str | None]:
    """Returns (cleaned_fields, error). error is None when the submission is valid."""
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    notes = (data.get("notes") or "").strip() or None
    source_page = (data.get("source_page") or "").strip() or None
    fields = {"phone": phone, "email": email, "notes": notes, "source_page": source_page}

    if not phone or not email:
        return fields, "Phone and email are required."
    if not _EMAIL_RE.match(email):
        return fields, "Enter a valid email address."
    if len(phone) < 7:
        return fields, "Enter a valid phone number."
    return fields, None


def save_lead(phone: str, email: str, notes: str | None, source_page: str | None) -> int:
    """Inserts a lead row, creating the table on first use. Returns the new
    lead_id. Raises DemoDbError on any connection/database problem."""
    with get_db_connection() as conn:
        ensure_schema(conn)
        row = execute(
            conn,
            """INSERT INTO leads (phone, email, notes, source_page)
               VALUES (%s, %s, %s, %s) RETURNING lead_id""",
            (phone, email, notes, source_page),
        )
        return row["lead_id"]
