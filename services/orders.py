"""
services/orders.py
The demo "Buy" simulator: folio numbers, quote building, and the shared
validation used by both /api/buy/quote and /api/buy. Everything here is a
simulation -- see config.py's DEMO_* constants for the caveat that no real
money, FX, or bank rail is involved (full context in demo_holdings' table
comment in database.py).
"""

import sqlite3
from typing import Any, Optional, Tuple

from flask import jsonify

from config import DEMO_FX_RATE, DEMO_LINKED_BANK, DEMO_TXN_FEE_USD
from db import get_db_connection
from services.funds import effective_min_investment_usd


def build_demo_folio(user_id: int, fund_id: int) -> str:
    """Deterministic mock folio number, stable per user+fund, matching the
    'GFT' + digits format seen on real distributor platforms."""
    return f"GFT{100000 + (user_id * 97 + fund_id) % 900000}"


def build_quote(fund_row: sqlite3.Row, amount: float, user_id: int) -> dict:
    """Builds the fee/FX/GST breakdown shown at both the quote step and the
    final order confirmation, so the two always agree on the numbers."""
    fee = DEMO_TXN_FEE_USD
    subtotal_usd = round(amount + fee, 2)
    subtotal_inr = subtotal_usd * DEMO_FX_RATE
    forex_service_charge_inr = subtotal_inr * 0.01  # standard 1% forex margin
    gst_inr = round(forex_service_charge_inr * 0.18, 2)  # 18% GST on that margin
    payable_inr = round(subtotal_inr + gst_inr, 2)
    units = round(amount / fund_row["nav"], 4)
    return {
        "fund_id": fund_row["fund_id"],
        "fund_name": fund_row["fund_name"],
        "folio": build_demo_folio(user_id, fund_row["fund_id"]),
        "amount": amount,
        "nav": fund_row["nav"],
        "currency": fund_row["nav_currency"] or "USD",
        "units": units,
        "transaction_fee": fee,
        "subtotal_usd": subtotal_usd,
        "fx_rate": DEMO_FX_RATE,
        "subtotal_inr": round(subtotal_inr, 2),
        "gst_inr": gst_inr,
        "payable_inr": payable_inr,
        "linked_bank": DEMO_LINKED_BANK,
    }


def validate_buy_request(data: dict) -> Tuple[Optional[sqlite3.Row], Optional[float], Optional[Any]]:
    """Shared validation for /api/buy/quote and /api/buy. Returns
    (fund_row, amount, error_response) -- error_response is None on success,
    and is a ready-to-return (jsonify(...), status_code) tuple otherwise."""
    fund_id = data.get("fund_id")
    amount = data.get("amount")
    try:
        fund_id = int(fund_id)
        amount = float(amount)
    except (TypeError, ValueError):
        return None, None, (jsonify({"success": False, "error": "Invalid fund_id or amount"}), 400)

    with get_db_connection() as conn:
        fund = conn.execute(
            "SELECT fund_id, fund_name, nav, nav_currency, minimum_investment FROM funds WHERE fund_id = ?",
            (fund_id,)
        ).fetchone()
        if not fund:
            return None, None, (jsonify({"success": False, "error": "Fund not found"}), 404)

        effective_min = effective_min_investment_usd(conn, fund_id, fund["minimum_investment"])

    if amount < effective_min:
        return None, None, (jsonify({
            "success": False,
            "error": f"Minimum investment for this fund is ${effective_min:,.0f}"
        }), 400)
    if fund["nav"] is None:
        return None, None, (jsonify({
            "success": False,
            "error": "This fund has no live NAV yet (NFO / private placement) -- simulated purchase isn't available until a NAV is published."
        }), 400)

    return fund, amount, None
