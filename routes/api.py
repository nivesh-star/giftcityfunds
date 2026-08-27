"""
routes/api.py
The JSON REST API consumed by the frontend's own JavaScript (static/js/*).
Registered under the /api prefix in app.py, so every route here is written
relative to that (e.g. "/funds" serves GET /api/funds).

View functions stay thin: parse query params/JSON body, run the query or
delegate to services/, return jsonify(...). Anything reusable or non-trivial
(fund plan classification, minimum-investment parsing, order quoting) lives
in services/ instead.
"""

import csv
import io
import json
from typing import Any, List

from flask import Blueprint, Response, jsonify, request, session

from db import get_db_connection
from routes.auth import login_required
from services.funds import effective_min_investment_usd, get_fund_plan_map
from services.orders import build_quote, validate_buy_request

api_bp = Blueprint("api", __name__)


# --- Fund listing, detail, history, comparison ---------------------------

@api_bp.route("/funds")
def get_funds():
    """
    Returns filtered and sorted fund list.
    Query params:
      - q: search term (fund_name, amc_name, category)
      - tier: 'tier1_amc', 'tier2_directory', or 'all'
      - category: category filter
      - currency: 'USD', 'INR', or 'all'
      - has_nav: 'true' / 'false'
      - flow: 'outbound', 'inbound', or 'all' -- see funds.fund_flow_type
      - sort: column name ('fund_name', 'amc_name', 'nav', 'expense_ratio', 'launch_date')
      - order: 'asc' / 'desc'
    """
    search_q = request.args.get("q", "").strip().lower()
    tier_filter = request.args.get("tier", "all").strip().lower()
    cat_filter = request.args.get("category", "all").strip()
    curr_filter = request.args.get("currency", "all").strip().upper()
    has_nav = request.args.get("has_nav", "all").strip().lower()
    flow_filter = request.args.get("flow", "all").strip().lower()
    sort_by = request.args.get("sort", "fund_name").strip().lower()
    order = request.args.get("order", "asc").strip().lower()

    allowed_sort = {
        "fund_name": "fund_name",
        "amc_name": "amc_name",
        "nav": "nav",
        "expense_ratio": "expense_ratio",
        "launch_date": "launch_date",
        "category": "category",
        "source_tier": "source_tier",
    }
    sort_col = allowed_sort.get(sort_by, "fund_name")
    order_dir = "DESC" if order == "desc" else "ASC"

    query = "SELECT * FROM funds WHERE 1=1"
    params: List[Any] = []

    if search_q:
        query += " AND (LOWER(fund_name) LIKE ? OR LOWER(amc_name) LIKE ? OR LOWER(COALESCE(category, '')) LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"])

    if tier_filter in ("tier1_amc", "tier2_directory"):
        query += " AND source_tier = ?"
        params.append(tier_filter)

    if cat_filter and cat_filter != "all":
        query += " AND LOWER(COALESCE(category, '')) LIKE ?"
        params.append(f"%{cat_filter.lower()}%")

    if curr_filter and curr_filter != "ALL":
        query += " AND (nav_currency = ? OR aum_currency = ?)"
        params.extend([curr_filter, curr_filter])

    if has_nav == "true":
        query += " AND nav IS NOT NULL"
    elif has_nav == "false":
        query += " AND nav IS NULL"

    if flow_filter in ("outbound", "inbound"):
        query += " AND fund_flow_type = ?"
        params.append(flow_filter)

    # Sorting with NULLs last for numeric/date columns
    if sort_col in ("nav", "expense_ratio", "launch_date"):
        query += f" ORDER BY CASE WHEN {sort_col} IS NULL THEN 1 ELSE 0 END, {sort_col} {order_dir}"
    else:
        query += f" ORDER BY {sort_col} {order_dir}"

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        funds = [dict(row) for row in rows]
        plan_map = get_fund_plan_map(conn)

    for fund in funds:
        fund["plan_type"] = plan_map.get(fund["fund_id"], "—")

    return jsonify({
        "success": True,
        "count": len(funds),
        "funds": funds,
    })


@api_bp.route("/fund/<int:fund_id>")
def get_fund_detail(fund_id: int):
    """Returns single fund details with related funds from same AMC, plus
    portfolio composition (holdings) where the source discloses it."""
    with get_db_connection() as conn:
        fund = conn.execute("SELECT * FROM funds WHERE fund_id = ?", (fund_id,)).fetchone()
        if not fund:
            return jsonify({"success": False, "error": "Fund not found"}), 404

        fund_dict = dict(fund)
        fund_dict["effective_min_investment_usd"] = effective_min_investment_usd(
            conn, fund_id, fund_dict.get("minimum_investment")
        )
        # Fetch related funds from same AMC
        related = conn.execute(
            "SELECT fund_id, fund_name, nav, nav_currency, category, source_tier FROM funds WHERE amc_name = ? AND fund_id != ? LIMIT 5",
            (fund_dict["amc_name"], fund_id)
        ).fetchall()
        fund_dict["related_funds"] = [dict(r) for r in related]

        # Portfolio composition -- only populated for the small set of funds
        # whose official factsheet actually discloses individual security
        # names (see portfolio_holdings schema comment in database.py).
        # Empty list, not an error, for every other fund.
        # Order fund-direct holdings before look-through/underlying-fund holdings
        # (both groups restart their own rank at 1) so the two layers of a
        # feeder-fund structure never interleave in the UI.
        holdings_rows = conn.execute(
            """SELECT holding_name, weight_pct, rank, as_of_date, source_name, holdings_basis
               FROM portfolio_holdings WHERE fund_id = ?
               ORDER BY CASE holdings_basis WHEN 'fund_direct' THEN 0 ELSE 1 END, rank ASC""",
            (fund_id,)
        ).fetchall()
        fund_dict["holdings"] = [dict(r) for r in holdings_rows]

        # Geographic/sector/market-cap/asset-class allocation -- only populated
        # where a factsheet actually publishes the breakdown (see fund_allocation
        # schema comment in database.py). Split into lists by breakdown_type.
        allocation_rows = conn.execute(
            """SELECT breakdown_type, category, weight_pct, as_of_date, source_name, holdings_basis
               FROM fund_allocation WHERE fund_id = ? ORDER BY weight_pct DESC""",
            (fund_id,)
        ).fetchall()
        fund_dict["geographic_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "geographic"]
        fund_dict["sector_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "sector"]
        fund_dict["market_cap_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "market_cap"]
        fund_dict["asset_class_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "asset_class"]
        fund_dict["credit_quality_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "credit_quality"]

        # Taxation as actually disclosed on the source -- see fund_taxation
        # schema comment. None (not fabricated defaults) when not captured.
        tax_row = conn.execute(
            """SELECT ltcg_rate, stcg_rate, dividend_rate, tax_notes, as_of_date, source_name
               FROM fund_taxation WHERE fund_id = ?""",
            (fund_id,)
        ).fetchone()
        fund_dict["taxation"] = dict(tax_row) if tax_row else None

        # Performance / returns series -- only populated where a factsheet
        # actually discloses period-by-period fund vs. benchmark returns.
        # Empty list, not an error, for every other fund.
        performance_rows = conn.execute(
            """SELECT period, fund_return_pct, benchmark_return_pct, excess_return_pct,
                      share_class, currency, is_annualized, as_of_date, source_name
               FROM fund_performance WHERE fund_id = ? ORDER BY share_class, performance_id""",
            (fund_id,)
        ).fetchall()
        fund_dict["performance"] = [dict(r) for r in performance_rows]

        # Risk metrics (alpha/beta/Sharpe/etc.) -- rare; most factsheets
        # don't disclose these at all.
        risk_rows = conn.execute(
            """SELECT period, alpha_pct, beta, r_squared, tracking_error_pct, information_ratio,
                      sharpe_ratio, upside_capture_pct, downside_capture_pct, active_share_pct,
                      batting_average_pct, as_of_date, source_name
               FROM fund_risk_metrics WHERE fund_id = ?""",
            (fund_id,)
        ).fetchall()
        fund_dict["risk_metrics"] = [dict(r) for r in risk_rows]

        # Share-class detail -- multiple NAV classes per fund (Direct/Regular,
        # Class A1/A5/etc.), each potentially with its own fee/exit-load terms.
        share_class_rows = conn.execute(
            """SELECT class_name, investor_type, min_investment_usd, management_fee_pct,
                      performance_fee_pct, hurdle_rate_pct, ter_pct, nav, nav_date,
                      subscription_nav, redemption_nav_long_term, redemption_nav_short_term,
                      exit_load_pct, exit_load_months, lock_in_months, isin, source_name
               FROM fund_share_classes WHERE fund_id = ? ORDER BY share_class_id""",
            (fund_id,)
        ).fetchall()
        fund_dict["share_classes"] = [dict(r) for r in share_class_rows]

    return jsonify({"success": True, "fund": fund_dict})


@api_bp.route("/fund/<int:fund_id>/nav-history")
def get_fund_nav_history(fund_id: int):
    """Returns the NAV time series for a fund, oldest first.

    History accumulates two ways (see database.py's nav_history schema
    comment): a real multi-date series where a source actually publishes
    one (currently only PPFAS Nasdaq 100), and a same-day snapshot of the
    fund's current NAV taken on every pipeline run for every fund that has
    a live NAV -- so most funds will show a short, real, growing series
    rather than a long fabricated one. Funds with no live NAV at all
    return an empty list.
    """
    with get_db_connection() as conn:
        fund = conn.execute(
            "SELECT fund_id, fund_name, nav_currency FROM funds WHERE fund_id = ?", (fund_id,)
        ).fetchone()
        if not fund:
            return jsonify({"success": False, "error": "Fund not found"}), 404

        rows = conn.execute(
            """SELECT nav_date, nav, nav_currency, source_name
               FROM nav_history WHERE fund_id = ? ORDER BY nav_date ASC""",
            (fund_id,)
        ).fetchall()
        history = [dict(r) for r in rows]

    return jsonify({
        "success": True,
        "fund_id": fund_id,
        "fund_name": fund["fund_name"],
        "count": len(history),
        "nav_history": history,
    })


@api_bp.route("/compare")
def compare_funds():
    """Compares multiple fund IDs passed as comma-separated `ids` parameter."""
    ids_raw = request.args.get("ids", "").strip()
    if not ids_raw:
        return jsonify({"success": False, "error": "No fund IDs provided"}), 400

    try:
        fund_ids = [int(i.strip()) for i in ids_raw.split(",") if i.strip().isdigit()]
    except ValueError:
        return jsonify({"success": False, "error": "Invalid fund IDs format"}), 400

    if not fund_ids:
        return jsonify({"success": False, "error": "No valid IDs provided"}), 400

    placeholders = ",".join("?" * len(fund_ids))
    with get_db_connection() as conn:
        rows = conn.execute(f"SELECT * FROM funds WHERE fund_id IN ({placeholders})", fund_ids).fetchall()
        funds = [dict(r) for r in rows]

    return jsonify({"success": True, "count": len(funds), "funds": funds})


@api_bp.route("/stats")
def get_stats():
    """Returns aggregated intelligence statistics and data series for Chart.js charts."""
    with get_db_connection() as conn:
        total_funds = conn.execute("SELECT COUNT(*) FROM funds").fetchone()[0]
        tier1_count = conn.execute("SELECT COUNT(*) FROM funds WHERE source_tier = 'tier1_amc'").fetchone()[0]
        tier2_count = conn.execute("SELECT COUNT(*) FROM funds WHERE source_tier = 'tier2_directory'").fetchone()[0]
        with_nav = conn.execute("SELECT COUNT(*) FROM funds WHERE nav IS NOT NULL").fetchone()[0]
        with_launch = conn.execute("SELECT COUNT(*) FROM funds WHERE launch_date IS NOT NULL").fetchone()[0]
        distinct_amcs = conn.execute("SELECT COUNT(DISTINCT amc_name) FROM funds WHERE amc_name IS NOT NULL").fetchone()[0]
        outbound_count = conn.execute("SELECT COUNT(*) FROM funds WHERE fund_flow_type = 'outbound'").fetchone()[0]
        inbound_count = conn.execute("SELECT COUNT(*) FROM funds WHERE fund_flow_type = 'inbound'").fetchone()[0]

        # AMC breakdown (Top 10)
        amc_rows = conn.execute(
            """SELECT amc_name, COUNT(*) as count
               FROM funds
               WHERE amc_name IS NOT NULL AND TRIM(amc_name) != '' AND amc_name != 'Not Publicly Disclosed'
               GROUP BY amc_name
               ORDER BY count DESC
               LIMIT 10"""
        ).fetchall()
        amc_distribution = [{"amc": r["amc_name"], "count": r["count"]} for r in amc_rows]

        # Category breakdown
        cat_rows = conn.execute(
            """SELECT COALESCE(category, 'Unclassified') as cat, COUNT(*) as count
               FROM funds
               GROUP BY cat
               ORDER BY count DESC"""
        ).fetchall()
        category_distribution = [{"category": r["cat"], "count": r["count"]} for r in cat_rows]

        # Launch timeline by year
        timeline_rows = conn.execute(
            """SELECT strftime('%Y', launch_date) as year, COUNT(*) as count
               FROM funds
               WHERE launch_date IS NOT NULL
               GROUP BY year
               ORDER BY year ASC"""
        ).fetchall()
        launch_timeline = [{"year": r["year"], "count": r["count"]} for r in timeline_rows if r["year"]]

        # Live NAV performers
        nav_rows = conn.execute(
            """SELECT fund_id, fund_name, amc_name, nav, nav_currency, nav_as_of, expense_ratio
               FROM funds
               WHERE nav IS NOT NULL
               ORDER BY nav DESC"""
        ).fetchall()
        nav_performers = [dict(r) for r in nav_rows]

    return jsonify({
        "success": True,
        "summary": {
            "total_funds": total_funds,
            "tier1_verified": tier1_count,
            "tier2_directory": tier2_count,
            "funds_with_live_nav": with_nav,
            "funds_with_launch_date": with_launch,
            "total_amcs": distinct_amcs,
            "outbound_funds": outbound_count,
            "inbound_funds": inbound_count,
            "unclassified_flow_funds": total_funds - outbound_count - inbound_count,
        },
        "charts": {
            "amc_distribution": amc_distribution,
            "category_distribution": category_distribution,
            "launch_timeline": launch_timeline,
            "nav_performers": nav_performers,
        }
    })


# --- Demo portfolio & "Buy" simulator -------------------------------------

@api_bp.route("/portfolio")
@login_required
def api_portfolio():
    """Returns the logged-in demo user's simulated holdings, with current
    value computed from each fund's latest known NAV. DEMO DATA ONLY."""
    user_id = session["user_id"]
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT h.holding_id, h.fund_id, h.units, h.invested_amount, h.buy_nav,
                      h.currency, h.purchase_date, h.status,
                      f.fund_name, f.amc_name, f.nav AS current_nav, f.nav_currency, f.nav_as_of
               FROM demo_holdings h JOIN funds f ON f.fund_id = h.fund_id
               WHERE h.user_id = ?
               ORDER BY h.purchase_date DESC""",
            (user_id,)
        ).fetchall()

        holdings = []
        total_invested = 0.0
        total_current = 0.0
        for r in rows:
            d = dict(r)
            current_nav = d["current_nav"] if d["current_nav"] is not None else d["buy_nav"]
            current_value = round(d["units"] * current_nav, 2)
            d["current_value"] = current_value
            d["gain_loss"] = round(current_value - d["invested_amount"], 2)
            d["gain_loss_pct"] = round((current_value - d["invested_amount"]) / d["invested_amount"] * 100, 2) if d["invested_amount"] else 0
            total_invested += d["invested_amount"]
            total_current += current_value
            holdings.append(d)

    return jsonify({
        "success": True,
        "user": {"name": session.get("user_name"), "email": session.get("user_email")},
        "holdings": holdings,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_gain_loss": round(total_current - total_invested, 2),
            "total_gain_loss_pct": round((total_current - total_invested) / total_invested * 100, 2) if total_invested else 0,
            "holdings_count": len(holdings),
        }
    })


@api_bp.route("/buy/quote", methods=["POST"])
@login_required
def api_buy_quote():
    """Returns a Payment Summary quote (fee/FX/GST breakdown + demo folio)
    WITHOUT recording anything -- mirrors the real distributor platform's
    'Proceed' step before the final 'Notify for Payment' confirmation.
    DEMO ONLY, no real money or real FX/bank data involved."""
    data = request.get_json(silent=True) or {}
    fund, amount, error = validate_buy_request(data)
    if error:
        return error
    return jsonify({"success": True, "quote": build_quote(fund, amount, session["user_id"])})


@api_bp.route("/buy", methods=["POST"])
@login_required
def api_buy():
    """Simulates a fund purchase order ('Notify for Payment' in the real
    flow). DEMO ONLY -- no real money moves, no real fund units are
    allotted, nothing is sent to any AMC, bank, or transfer agent. Purely
    records a row in demo_holdings against the fund's current displayed
    NAV so the demo portfolio can show a realistic position."""
    data = request.get_json(silent=True) or {}
    fund, amount, error = validate_buy_request(data)
    if error:
        return error

    user_id = session["user_id"]
    quote = build_quote(fund, amount, user_id)

    with get_db_connection() as conn:
        cur = conn.execute(
            """INSERT INTO demo_holdings (user_id, fund_id, units, invested_amount, buy_nav, currency, status)
               VALUES (?, ?, ?, ?, ?, ?, 'completed')""",
            (user_id, fund["fund_id"], quote["units"], amount, fund["nav"], fund["nav_currency"] or "USD")
        )
        conn.commit()
        holding_id = cur.lastrowid

    quote["holding_id"] = holding_id
    return jsonify({
        "success": True,
        "message": "Payment notification sent",
        "order": quote,
    })


# --- Bulk export -----------------------------------------------------------

@api_bp.route("/export/csv")
def export_csv():
    """Exports the full dataset as a downloadable CSV."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM funds ORDER BY source_tier ASC, fund_name ASC").fetchall()
        if not rows:
            return "No data", 404

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(list(row))

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=gift_city_funds_intelligence.csv"}
        )


@api_bp.route("/export/json")
def export_json():
    """Exports the complete dataset as downloadable JSON."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM funds ORDER BY source_tier ASC, fund_name ASC").fetchall()
        funds = [dict(r) for r in rows]
        return Response(
            json.dumps(funds, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment;filename=gift_city_funds_intelligence.json"}
        )
