#!/usr/bin/env python3
"""
Daily NAV feeder for the GIFT City Funds ETL database.

Hits each AMC's own public NAV endpoint (the same ones a browser calls when
you visit their official GIFT City NAV pages) and upserts today's real,
published NAV into nav_history. This script NEVER invents, estimates, or
carries forward a NAV value -- if a source can't be reached, or its response
doesn't parse the way we expect, that fund is skipped for the day and logged.
No fabricated numbers are ever written.

Run manually:  python3 scripts/daily_nav_update.py
Run by CI:     see .github/workflows/daily-nav-update.yml (daily cron)
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("daily_nav_update")

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "gift_city_amc_funds.db"

HTTP_TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def upsert_nav(conn, fund_id, nav_date, nav, nav_currency, source_name):
    """Insert or update a single real NAV data point. Returns True if a row
    was actually written (new or changed), False if it was already there
    with the same value (nothing to do) or the write was skipped."""
    if nav_date is None or nav is None:
        return False
    try:
        nav = float(nav)
    except (TypeError, ValueError):
        log.warning("  fund_id=%s: could not parse NAV value %r -- skipping", fund_id, nav)
        return False

    cur = conn.cursor()
    cur.execute(
        "SELECT nav FROM nav_history WHERE fund_id=? AND nav_date=?",
        (fund_id, nav_date),
    )
    existing = cur.fetchone()
    if existing is not None and abs(existing[0] - nav) < 1e-9:
        return False  # already have this exact real value, nothing to do

    cur.execute(
        """
        INSERT INTO nav_history (fund_id, nav_date, nav, nav_currency, source_name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(fund_id, nav_date) DO UPDATE SET
            nav=excluded.nav,
            source_name=excluded.source_name
        """,
        (fund_id, nav_date, nav, nav_currency, source_name),
    )
    return True


def fetch_hdfc(conn):
    """HDFC AMC International -- one public endpoint returns today's NAV for
    every 'Invest in India' fund and every share class at once."""
    url = "https://cms.hdfcinternational.com/hdfc/api/v1/home/getData"
    fund_map = {
        "HDFC India Balanced Advantage Fund": 228,
        "HDFC India Flexi Cap Fund": 229,
        "HDFC India Small Cap Fund": 232,
        "HDFC India Mid-cap Opportunities Fund": 326,
        "HDFC India NIFTY 50 Fund": 329,
    }
    written = 0
    try:
        resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json().get("data", {})
    except Exception as exc:
        log.error("HDFC: request failed (%s) -- skipping all HDFC funds today", exc)
        return 0

    for fund_name, fund_id in fund_map.items():
        classes = data.get(fund_name)
        if not classes:
            log.warning("HDFC: no data returned for %r -- skipping", fund_name)
            continue
        a1 = next((c for c in classes if c.get("class_of_units") == "Class A1"), None)
        if not a1:
            log.warning("HDFC: Class A1 not found for %r -- skipping", fund_name)
            continue
        try:
            nav_date = _ddmonyyyy_to_iso(a1["nav_date"])
        except Exception:
            log.warning("HDFC: unparseable nav_date %r for %r -- skipping", a1.get("nav_date"), fund_name)
            continue
        if upsert_nav(
            conn, fund_id, nav_date, a1["nav_amount"], "USD",
            "HDFC AMC International official site (hdfcinternational.com), Historical NAV Data API, Class A1",
        ):
            written += 1
            log.info("HDFC: %s -> %s NAV=%s", fund_name, nav_date, a1["nav_amount"])
    return written


def fetch_sundaram(conn):
    """Sundaram Asset Management -- current-NAV ajax endpoint, Direct plan."""
    url = (
        "https://www.sundarammutual.com/ajax/Views_Gift_City_Main,App_Web_zb1m5ed1.ashx"
        "?_method=LoadCurrentNAV&_session=rw"
    )
    fund_id = 51
    try:
        resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json={}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        text = resp.text.strip()
        # The API wraps its JSON array in a stray leading/trailing quote.
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        rows = json.loads(text)
    except Exception as exc:
        log.error("Sundaram: request failed (%s) -- skipping", exc)
        return 0

    direct_row = next((r for r in rows if r.get("SERIES_CODE") == "DIR"), None)
    if not direct_row:
        log.warning("Sundaram: Direct plan row not found -- skipping")
        return 0
    try:
        nav_date = _ddmmyyyy_dash_to_iso(direct_row["NAV_DATE"].split(" ")[0])
    except Exception:
        log.warning("Sundaram: unparseable NAV_DATE %r -- skipping", direct_row.get("NAV_DATE"))
        return 0

    if upsert_nav(
        conn, fund_id, nav_date, direct_row["NAV_PER_UNIT"], direct_row.get("SCY", "USD"),
        "Sundaram Asset Management official site (sundarammutual.com/gift-city), Historical NAV Data tool, Direct Plan",
    ):
        log.info("Sundaram: India Mid Cap -> %s NAV=%s", nav_date, direct_row["NAV_PER_UNIT"])
        return 1
    return 0


def fetch_ppfas(conn):
    """PPFAS GIFT City -- paginated NAV history API, latest record at offset 0."""
    funds = [
        {
            "fund_id": 4,
            "slug": "parag_parikh_ifsc_nasdaq_100_fof",
            "field": "direct_subscription_nav",
            "source_name": "PPFAS GIFT City official NAV history (gift.ppfas.com), Direct Plan Subscription NAV",
            "label": "Parag Parikh IFSC Nasdaq 100 Fund of Fund",
        },
        {
            "fund_id": 3,
            "slug": "parag_parikh_ifsc_sp500_fof",
            "field": "direct_redemption_nav_long_term",
            "source_name": "PPFAS GIFT City official NAV history (gift.ppfas.com), Direct Plan Redemption (Long Term) NAV",
            "label": "Parag Parikh IFSC S&P 500 Fund of Fund",
        },
    ]
    written = 0
    for f in funds:
        url = f"https://gift.ppfas.com/giftdesk/api/nav/{f['slug']}?offset=0&limit=1"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            log.error("PPFAS: request failed for %s (%s) -- skipping", f["label"], exc)
            continue
        if not payload.get("success") or not payload.get("records"):
            log.warning("PPFAS: no records for %s -- skipping", f["label"])
            continue
        record = payload["records"][0]
        nav_value = record.get(f["field"])
        nav_date = record.get("nav_date")  # already YYYY-MM-DD
        if upsert_nav(conn, f["fund_id"], nav_date, nav_value, "USD", f["source_name"]):
            written += 1
            log.info("PPFAS: %s -> %s NAV=%s", f["label"], nav_date, nav_value)
    return written


def fetch_dsp(conn):
    """DSP GIFT City -- nav-history API, Regular Plan Class A, redemption NAV."""
    import datetime

    fund_id = 2
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    url = (
        "https://giftcity.dspim.com/api/v1/nav-history"
        f"?schemeCode=101&schemePlan=Regular&schemeClass=A"
        f"&from={week_ago.strftime('%d-%b-%Y')}&to={today.strftime('%d-%b-%Y')}"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        history = payload.get("navHistory", [])
    except Exception as exc:
        log.error("DSP: request failed (%s) -- skipping", exc)
        return 0
    if not history:
        log.warning("DSP: no navHistory rows returned -- skipping")
        return 0

    written = 0
    for row in history:
        try:
            nav_date = _ddmonyyyy_to_iso(row["date"])
        except Exception:
            continue
        if upsert_nav(conn, fund_id, nav_date, row.get("nav_redemption"), "USD",
                       "DSP GIFT City official NAV history (giftcity.dspim.com/nav), Regular Plan Class A"):
            written += 1
            log.info("DSP: Global Equity Fund -> %s NAV=%s", nav_date, row.get("nav_redemption"))
    return written


_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}


def _ddmonyyyy_to_iso(s):
    """'19-Aug-2026' -> '2026-08-19'"""
    day, mon, year = s.split("-")
    return f"{year}-{_MONTHS[mon]:02d}-{int(day):02d}"


def _ddmmyyyy_dash_to_iso(s):
    """'20-08-2026' -> '2026-08-20'"""
    day, month, year = s.split("-")
    return f"{year}-{int(month):02d}-{int(day):02d}"


def main():
    if not DB_PATH.exists():
        log.error("Database not found at %s", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    total_written = 0
    sources = [
        ("HDFC AMC International", fetch_hdfc),
        ("Sundaram Asset Management", fetch_sundaram),
        ("PPFAS GIFT City", fetch_ppfas),
        ("DSP GIFT City", fetch_dsp),
    ]

    for name, fn in sources:
        log.info("--- %s ---", name)
        try:
            total_written += fn(conn)
            conn.commit()
        except Exception as exc:
            log.error("%s: unexpected error (%s) -- skipping this source today", name, exc)
            conn.rollback()

    conn.close()
    log.info("Done. %d new/updated NAV row(s) written.", total_written)

    # Exit code 0 always -- a source being temporarily unreachable is not a
    # pipeline failure, it just means fewer funds got a fresh point today.
    # (git diff in the workflow decides whether there's anything to commit.)


if __name__ == "__main__":
    main()
