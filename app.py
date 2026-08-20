"""
app.py
Production-grade Flask server for GIFT360 — GIFT City (IFSC) Funds Intelligence Platform.
Connects to SQLite (gift_city_amc_funds.db) and serves dynamic REST APIs and the interactive UI.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, Response

app = Flask(__name__, static_folder="static", template_folder="templates")
DB_PATH = Path("gift_city_amc_funds.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    """Renders the main GIFT360 Dashboard UI."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Outbound / Inbound flow-type pages
#
# Sir asked that outbound and inbound GIFT City funds be presented as
# distinct sections (mirroring thefynprint.com's own /gift-city-outbound and
# /gift-city-inbound pages), each with its own FAQ content, rather than only
# a badge inside the shared Tier 1/Tier 2 dashboard. These two routes render
# that split. Funds are classified via `fund_flow_type` on the `funds` table
# (set only when explicitly confirmed against a fund's own factsheet or a
# corroborating source such as thefynprint's trackers -- never inferred from
# a fund's name alone), so a fund with no confirmed classification simply
# does not appear on either page instead of being guessed into one.
OUTBOUND_FAQS = [
    {
        "question": "What are GIFT City outbound funds?",
        "answer": [
            "Outbound funds in GIFT City IFSC allow Indian and NRI investors to invest in global markets through fund structures domiciled in India's IFSC.",
            "These funds invest in international equities, ETFs, and alternative assets across the US, Europe, Asia, and emerging markets.",
            "They provide a regulated, tax-efficient route for global diversification without needing an overseas brokerage account.",
        ],
    },
    {
        "question": "What is the difference between AIFs, PMS, and Retail funds in GIFT City?",
        "answer": [
            "AIFs (Alternative Investment Funds) are pooled investment vehicles for sophisticated investors — typically with higher minimum investments and lock-in periods.",
            "PMS (Portfolio Management Services) offer personalised portfolio management with a minimum ticket size of $75,000 in GIFT City.",
            "Retail funds have lower entry barriers (as low as $5,000) and are structured as open-ended funds accessible to a broader investor base.",
        ],
    },
    {
        "question": "What are the tax implications of investing through GIFT City outbound funds?",
        "answer": [
            "Funds structured through Irish-domiciled UCITS or Cayman routes can avoid churn tax — no tax on internal portfolio rebalancing.",
            "Some fund structures may be subject to fund-level taxation where investor exits can increase tax burden for remaining investors.",
            "Tax treatment varies by fund structure — AIF, PMS, and retail fund routes each have different implications. Consult a tax advisor.",
        ],
    },
    {
        "question": "What is 'churn tax' and why does it matter?",
        "answer": [
            "Churn tax refers to capital gains tax triggered when a fund buys and sells securities within its portfolio.",
            "Funds routed through Cayman Islands or Irish UCITS structures can avoid this tax, making them more tax-efficient.",
            "Direct PMS strategies may be subject to churn tax since trades happen in the investor's name, potentially reducing net returns.",
        ],
    },
    {
        "question": "What are the lock-in periods for GIFT City outbound funds?",
        "answer": [
            "AIFs typically have lock-in periods ranging from 2 to 4 years depending on the fund strategy.",
            "PMS strategies generally offer more flexibility with lower or no lock-in periods and zero exit loads.",
            "Retail funds usually have no lock-in and offer daily or weekly redemption options.",
        ],
    },
    {
        "question": "How do I choose between different GIFT City outbound fund options?",
        "answer": [
            "Consider your investment horizon — AIFs suit long-term investors comfortable with 2-4 year lock-ins.",
            "Evaluate geographic allocation — some funds focus on US markets while others offer broader global diversification.",
            "Compare fee structures, tax efficiency (churn tax vs fund-level tax), and minimum ticket sizes to match your requirements.",
        ],
    },
]

INBOUND_FAQS = [
    {
        "question": "What is GIFT City and why are inbound funds important?",
        "answer": [
            "GIFT City (Gujarat International Finance Tec-City) is India's first International Financial Services Centre (IFSC) located in Gandhinagar, Gujarat.",
            "Inbound funds in GIFT City allow foreign portfolio investors and NRIs to invest in Indian markets through a regulatory-friendly IFSC framework.",
            "These funds enjoy benefits like tax exemptions, no STT, no CTT, and a simplified compliance structure under IFSCA regulations.",
        ],
    },
    {
        "question": "How are GIFT City inbound funds different from regular mutual funds?",
        "answer": [
            "GIFT City inbound funds are denominated in foreign currencies (primarily USD) and regulated by IFSCA instead of SEBI.",
            "They offer tax advantages — no capital gains tax, no STT, no dividend distribution tax for eligible investors.",
            "They provide a bridge for global investors to access Indian equities, debt, and alternative assets under international best practices.",
        ],
    },
    {
        "question": "Who can invest in GIFT City inbound funds?",
        "answer": [
            "Non-Resident Indians (NRIs) and Persons of Indian Origin (PIOs) can invest through these funds.",
            "Foreign Portfolio Investors (FPIs) and institutional investors can access Indian markets via GIFT City.",
            "Some funds also allow resident Indians who qualify under the Liberalised Remittance Scheme (LRS).",
        ],
    },
    {
        "question": "What are the tax benefits of investing through GIFT City?",
        "answer": [
            "No Securities Transaction Tax (STT) or Commodities Transaction Tax (CTT) on transactions.",
            "Exemption from capital gains tax for units held in IFSC for 10 years under certain conditions.",
            "No Dividend Distribution Tax — dividends are tax-free at the fund level.",
            "GST exemptions on certain financial services within the IFSC.",
        ],
    },
    {
        "question": "What is K1 compliance and why does it matter for US NRIs?",
        "answer": [
            "K-1 is an IRS tax form used to report a partner's share of income, deductions, and credits from a partnership or S corporation.",
            "For US-based NRIs, investing in K1-compliant funds simplifies tax reporting to the IRS.",
            "Non-K1 funds may require complex PFIC (Passive Foreign Investment Company) reporting, which can be burdensome.",
            "K1-compliant GIFT City funds are structured to issue Schedule K-1 forms, making US tax filing straightforward.",
        ],
    },
    {
        "question": "What types of funds operate from GIFT City?",
        "answer": [
            "Equity funds investing in Indian listed securities (large, mid, small cap) through feeder structures.",
            "Debt funds targeting Indian government securities and corporate bonds.",
            "Hybrid and multi-asset funds combining equity, debt, and alternative strategies.",
            "Category III AIFs offering long-short, arbitrage, and other sophisticated strategies.",
        ],
    },
]

# Sourced from thefynprint.com/gift-city-outbound and /gift-city-inbound (both
# pages state "Data sourced from fund house disclosures ... may be subject to
# delays" -- carried here verbatim as our own attribution to that source).
FAQ_SOURCE_ATTRIBUTION = "FAQ content sourced from thefynprint.com's GIFT City Outbound/Inbound Funds Trackers."


@app.route("/gift-city-outbound")
def gift_city_outbound():
    """Dedicated page for outbound GIFT City funds (India/GIFT-domiciled
    capital investing abroad), with FAQ content specific to outbound
    investing (churn tax, lock-ins, AIF/PMS/Retail structure differences)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM funds WHERE fund_flow_type = 'outbound' ORDER BY fund_name"
        ).fetchall()
        funds = [dict(r) for r in rows]
    return render_template(
        "flow_page.html",
        flow_type="outbound",
        page_title="GIFT City Outbound Funds",
        page_subtitle="India/GIFT-domiciled capital investing abroad — AIFs, PMS, and retail fund strategies for global investing.",
        funds=funds,
        faqs=OUTBOUND_FAQS,
        faq_source=FAQ_SOURCE_ATTRIBUTION,
        other_flow_url="/gift-city-inbound",
        other_flow_label="Inbound Funds",
    )


@app.route("/gift-city-inbound")
def gift_city_inbound():
    """Dedicated page for inbound GIFT City funds (foreign/NRI capital
    investing into India via GIFT), with FAQ content specific to inbound
    investing (K1 compliance, IFSCA tax benefits, investor eligibility)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM funds WHERE fund_flow_type = 'inbound' ORDER BY fund_name"
        ).fetchall()
        funds = [dict(r) for r in rows]
    return render_template(
        "flow_page.html",
        flow_type="inbound",
        page_title="GIFT City Inbound Funds",
        page_subtitle="Foreign and NRI capital investing into India through GIFT City IFSC — fund houses, strategies, and tax structure.",
        funds=funds,
        faqs=INBOUND_FAQS,
        faq_source=FAQ_SOURCE_ATTRIBUTION,
        other_flow_url="/gift-city-outbound",
        other_flow_label="Outbound Funds",
    )


@app.route("/api/funds")
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

    return jsonify({
        "success": True,
        "count": len(funds),
        "funds": funds,
    })


@app.route("/api/fund/<int:fund_id>")
def get_fund_detail(fund_id: int):
    """Returns single fund details with related funds from same AMC, plus
    portfolio composition (holdings) where the source discloses it."""
    with get_db_connection() as conn:
        fund = conn.execute("SELECT * FROM funds WHERE fund_id = ?", (fund_id,)).fetchone()
        if not fund:
            return jsonify({"success": False, "error": "Fund not found"}), 404

        fund_dict = dict(fund)
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
        holdings_rows = conn.execute(
            """SELECT holding_name, weight_pct, rank, as_of_date, source_name, holdings_basis
               FROM portfolio_holdings WHERE fund_id = ? ORDER BY rank ASC""",
            (fund_id,)
        ).fetchall()
        fund_dict["holdings"] = [dict(r) for r in holdings_rows]

        # Geographic/sector allocation -- only populated where a factsheet
        # actually publishes the breakdown (see fund_allocation schema
        # comment in database.py). Split into two lists by breakdown_type.
        allocation_rows = conn.execute(
            """SELECT breakdown_type, category, weight_pct, as_of_date, source_name, holdings_basis
               FROM fund_allocation WHERE fund_id = ? ORDER BY weight_pct DESC""",
            (fund_id,)
        ).fetchall()
        fund_dict["geographic_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "geographic"]
        fund_dict["sector_allocation"] = [dict(r) for r in allocation_rows if r["breakdown_type"] == "sector"]

        # Taxation as actually disclosed on the source -- see fund_taxation
        # schema comment. None (not fabricated defaults) when not captured.
        tax_row = conn.execute(
            """SELECT ltcg_rate, stcg_rate, dividend_rate, tax_notes, as_of_date, source_name
               FROM fund_taxation WHERE fund_id = ?""",
            (fund_id,)
        ).fetchone()
        fund_dict["taxation"] = dict(tax_row) if tax_row else None

    return jsonify({"success": True, "fund": fund_dict})


@app.route("/api/fund/<int:fund_id>/nav-history")
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


@app.route("/api/compare")
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


@app.route("/api/stats")
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


@app.route("/api/export/csv")
def export_csv():
    """Exports the filtered dataset as a downloadable CSV."""
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


@app.route("/api/export/json")
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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print("=" * 70)
    print("  GIFT360 — GIFT City (IFSC) Funds Intelligence Platform")
    print(f"  Serving live on port {port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)
