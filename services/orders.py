"""
services/orders.py
The demo "Buy" simulator: folio numbers, quote building, and the shared
validation used by both /api/buy/quote and /api/buy. Everything here is a
simulation -- see config.py's DEMO_* constants for the caveat that no real
money, FX, or bank rail is involved.

DATA SOURCE CHANGE: fund data (NAV, minimum investment) now comes from the
shared mf-engine-v2 API via services/mf_engine.py rather than a local SQLite
funds table. The resulting demo_holdings rows are still written to Postgres
by routes/api.py -- see services/demo_db.py.
"""

from typing import Any, Dict, Optional, Tuple

from flask import jsonify

from config import DEMO_FX_RATE, DEMO_LINKED_BANK, DEMO_TXN_FEE_USD
from services import adapters
from services.mf_engine import MfEngineError, fetch_fund


def build_demo_folio(user_id: int, fund_id: int) -> str:
    """Deterministic mock folio number, stable per user+fund, matching the
    'GFT' + digits format seen on real distributor platforms."""
    return f"GFT{100000 + (user_id * 97 + fund_id) % 900000}"


def build_quote(fund: Dict[str, Any], amount: float, user_id: int) -> dict:
    """Builds the fee/FX/GST breakdown shown at both the quote step and the
    final order confirmation, so the two always agree on the numbers.

    `fund` is an adapter-shaped dict (see services/adapters.fund_summary),
    not a database row."""
    fee = DEMO_TXN_FEE_USD
    subtotal_usd = round(amount + fee, 2)
    subtotal_inr = subtotal_usd * DEMO_FX_RATE
    forex_service_charge_inr = subtotal_inr * 0.01   # standard 1% forex margin
    gst_inr = round(forex_service_charge_inr * 0.18, 2)  # 18% GST on that margin
    payable_inr = round(subtotal_inr + gst_inr, 2)
    units = round(amount / fund["nav"], 4)
    return {
        "fund_id": fund["fund_id"],
        "fund_name": fund["fund_name"],
        "folio": build_demo_folio(user_id, fund["fund_id"]),
        "amount": amount,
        "nav": fund["nav"],
        "currency": fund.get("nav_currency") or "USD",
        "units": units,
        "transaction_fee": fee,
        "subtotal_usd": subtotal_usd,
        "fx_rate": DEMO_FX_RATE,
        "subtotal_inr": round(subtotal_inr, 2),
        "gst_inr": gst_inr,
        "payable_inr": payable_inr,
        "linked_bank": DEMO_LINKED_BANK,
    }


def validate_buy_request(data: dict) -> Tuple[Optional[Dict[str, Any]], Optional[float], Optional[Any]]:
    """Shared validation for /api/buy/quote and /api/buy. Returns
    (fund, amount, error_response) -- error_response is None on success,
    and is a ready-to-return (jsonify(...), status_code) tuple otherwise."""
    fund_id = data.get("fund_id")
    amount = data.get("amount")
    try:
        fund_id = int(fund_id)
        amount = float(amount)
    except (TypeError, ValueError):
        return None, None, (jsonify({"success": False, "error": "Invalid fund_id or amount"}), 400)

    try:
        raw = fetch_fund(fund_id)
    except MfEngineError as exc:
        return None, None, (jsonify({"success": False, "error": str(exc)}), 502)

    if not raw:
        return None, None, (jsonify({"success": False, "error": "Fund not found"}), 404)

    fund = adapters.fund_summary(raw)

    if fund.get("nav") is None:
        return None, None, (jsonify({
            "success": False,
            "error": "This fund has no live NAV yet (NFO / private placement) -- simulated purchase isn't available until a NAV is published."
        }), 400)

    # Minimum investment: prefer the fund-level figure, else the lowest
    # share-class minimum, else the configured floor. Same intent as the old
    # effective_min_investment_usd() helper, but sourced from the API payload
    # rather than a SQLite join.
    from config import MIN_BUY_AMOUNT_USD

    effective_min = fund.get("minimum_investment")
    if effective_min is None:
        class_minimums = [
            sc.get("min_investment_usd")
            for sc in (raw.get("share_classes") or [])
            if sc.get("min_investment_usd") is not None
        ]
        if class_minimums:
            effective_min = min(float(m) for m in class_minimums)
    if effective_min is None:
        effective_min = MIN_BUY_AMOUNT_USD

    if amount < effective_min:
        return None, None, (jsonify({
            "success": False,
            "error": f"Minimum investment for this fund is ${effective_min:,.0f}"
        }), 400)

    return fund, amount, None
