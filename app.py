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
      - sort: column name ('fund_name', 'amc_name', 'nav', 'expense_ratio', 'launch_date')
      - order: 'asc' / 'desc'
    """
    search_q = request.args.get("q", "").strip().lower()
    tier_filter = request.args.get("tier", "all").strip().lower()
    cat_filter = request.args.get("category", "all").strip()
    curr_filter = request.args.get("currency", "all").strip().upper()
    has_nav = request.args.get("has_nav", "all").strip().lower()
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
    """Returns single fund details with related funds from same AMC."""
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

    return jsonify({"success": True, "fund": fund_dict})


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

        # AMC breakdown (Top 10)
        amc_rows = conn.execute(
            """SELECT amc_name, COUNT(*) as count 
               FROM funds 
               WHERE amc_name IS NOT NULL 
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
    print("=" * 70)
    print("  GIFT360 — GIFT City (IFSC) Funds Intelligence Platform")
    print("  Serving live at http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="127.0.0.1", port=5000, debug=True)
