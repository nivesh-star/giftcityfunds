"""
services/funds.py
Read-side logic for individual funds: URL slugs, the demo "Plan"
(Direct/Regular) classification, and best-effort parsing of each fund's
minimum-investment requirement. Kept out of routes/ so this logic can be
read, reused, and reasoned about on its own -- no request objects, no
jsonify, no HTTP status codes in this file, only funds + the database.
"""

import re
import sqlite3
from typing import Dict, Optional

from config import DEMO_FX_RATE, MIN_BUY_AMOUNT_USD


def slugify(text: str) -> str:
    """Turns a fund name into a URL-friendly slug, e.g.
    'Tata India Dynamic Equity Fund' -> 'tata-india-dynamic-equity-fund'."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "fund"


def get_fund_plan_map(conn: sqlite3.Connection) -> Dict[int, str]:
    """Builds a {fund_id: 'Direct' | 'Regular' | 'Direct & Regular'} map by
    combining explicit share-class names (fund_share_classes.class_name)
    with Direct/Regular mentions in nav_history.source_name. A fund with no
    disclosed plan simply has no entry -- callers fall back to a dash
    placeholder rather than guessing."""
    flags: Dict[int, Dict[str, bool]] = {}

    def mark(fund_id: int, direct: bool, regular: bool) -> None:
        entry = flags.setdefault(fund_id, {"direct": False, "regular": False})
        entry["direct"] = entry["direct"] or direct
        entry["regular"] = entry["regular"] or regular

    for row in conn.execute("SELECT fund_id, class_name FROM fund_share_classes"):
        name = (row["class_name"] or "").lower()
        if "direct" in name or "regular" in name:
            mark(row["fund_id"], "direct" in name, "regular" in name)

    for row in conn.execute("SELECT fund_id, source_name FROM nav_history"):
        name = (row["source_name"] or "").lower()
        if "direct" in name or "regular" in name:
            mark(row["fund_id"], "direct" in name, "regular" in name)

    plan_map: Dict[int, str] = {}
    for fund_id, entry in flags.items():
        if entry["direct"] and entry["regular"]:
            plan_map[fund_id] = "Direct & Regular"
        elif entry["direct"]:
            plan_map[fund_id] = "Direct"
        elif entry["regular"]:
            plan_map[fund_id] = "Regular"
    return plan_map


def parse_min_investment_usd(raw: Optional[str]) -> Optional[float]:
    """Best-effort extraction of the lowest legitimate USD entry amount from
    the free-text funds.minimum_investment field (e.g. 'USD 150,000 (or
    equivalent...)', 'USD 5,000 (step-up USD 500)', 'D1/F1: USD
    150,000-500,000; ... AC2/AC3 (Accredited): USD 50,000'). Returns None
    when nothing parseable is found -- callers fall back to
    MIN_BUY_AMOUNT_USD, we never invent a number here."""
    if not raw:
        return None

    text = raw
    # Strip step-up/top-up mentions -- those are incremental follow-on
    # amounts, not the minimum initial investment.
    text = re.sub(r"\(?\s*step-?up[^)]*\)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\(?\s*top-?up[^)]*\)?", " ", text, flags=re.IGNORECASE)

    usd_amounts = [
        float(m.replace(",", ""))
        for m in re.findall(r"USD\s*\$?\s*([\d][\d,]*(?:\.\d+)?)", text, flags=re.IGNORECASE)
    ]
    if usd_amounts:
        return min(usd_amounts)

    # Rupee-denominated minimums (e.g. "Rs 50 Lakhs") -- convert via the same
    # illustrative FX rate used elsewhere in the demo, so the simulator floor
    # stays roughly consistent with the fund's real entry barrier.
    lakh_match = re.search(r"Rs\.?\s*([\d,]+(?:\.\d+)?)\s*Lakh", text, flags=re.IGNORECASE)
    if lakh_match:
        inr_amount = float(lakh_match.group(1).replace(",", "")) * 100000
        return round(inr_amount / DEMO_FX_RATE, 2)

    return None


def effective_min_investment_usd(conn: sqlite3.Connection, fund_id: int, raw_min_text: Optional[str]) -> float:
    """The number actually used to gate the Buy simulator for one fund:
    1) the lowest numeric min_investment_usd on file across its share
       classes (the cleanest source, where captured),
    2) else a best-effort parse of the free-text minimum_investment field,
    3) else the platform-wide fallback floor, when we genuinely have no
       minimum-investment data for that fund at all."""
    row = conn.execute(
        "SELECT MIN(min_investment_usd) AS m FROM fund_share_classes WHERE fund_id = ? AND min_investment_usd IS NOT NULL",
        (fund_id,)
    ).fetchone()
    if row and row["m"] is not None:
        return float(row["m"])

    parsed = parse_min_investment_usd(raw_min_text)
    if parsed is not None:
        return parsed

    return MIN_BUY_AMOUNT_USD
