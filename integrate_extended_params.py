"""
Backfill ISIN/Bloomberg ticker, performance/returns series, risk metrics, and
share-class detail from parsed_output.json (14 parsed GIFT City funds) into
the new fund_performance / fund_risk_metrics / fund_share_classes tables and
the funds.isin / funds.bloomberg_ticker columns.

Rules (same discipline as integrate_parsed_data.py):
  - NEVER overwrite an existing non-null isin/bloomberg_ticker value.
  - Performance/risk-metric/share-class rows are net-new inserts, skipped if
    an equivalent row already exists (avoid duplicate rows on re-run).
  - The 3 funds with no direct DB match in the original MATCHES dict:
    ashoka -> skipped entirely (not a GIFT City fund, see earlier session
    note -- it's an Ireland-domiciled UCITS fund).
    rational -> fund_id 1883 (Gold & Silver Miners' Fund, inserted earlier).
    unifi -> fund_id 1884 (Unifi G20 Fund, inserted earlier).
"""
import json
import sqlite3

DB_PATH = "gift_city_amc_funds.db"

MATCHES = {
    "dsp": 2, "ppfas_sp": 3, "ppfas_nq": 4, "edelweiss": 5, "mirae": 66,
    "marcellus_ge": 105, "baroda": 115, "phillip": 178, "ppfas_pms": 179,
    "absl": 214, "marcellus_gcp": 1666,
    "ashoka": None,          # not a GIFT City fund -- skip
    "rational": 1883,
    "unifi": 1884,
}

data = json.load(open("parsed_output.json"))["results"]
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

isin_fills = []
perf_inserted = 0
risk_inserted = 0
sc_inserted = 0
skipped_empty = []

SRC = "Factsheet PDF (parsed via internal GIFT City parser pipeline) -- extended fields backfill"

for slug, fund_id in MATCHES.items():
    if fund_id is None:
        continue
    fi = data[slug]["fund_info"]

    # ISIN / Bloomberg ticker -- null-fill only
    isin = fi.get("isin")
    ticker = fi.get("bloomberg_ticker")
    row = conn.execute("SELECT isin, bloomberg_ticker, fund_name FROM funds WHERE fund_id=?", (fund_id,)).fetchone()
    updates = {}
    if isin and not row["isin"]:
        updates["isin"] = isin
    if ticker and not row["bloomberg_ticker"]:
        updates["bloomberg_ticker"] = ticker
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE funds SET {set_clause}, last_updated=CURRENT_TIMESTAMP WHERE fund_id=?",
                     (*updates.values(), fund_id))
        isin_fills.append((row["fund_name"], updates))

    # Performance / returns series
    for p in data[slug]["performance"]:
        if p.get("fund_return_pct") is None and p.get("benchmark_return_pct") is None:
            continue  # nothing real to store
        exists = conn.execute(
            """SELECT 1 FROM fund_performance
               WHERE fund_id=? AND period IS ? AND share_class IS ? AND currency IS ?""",
            (fund_id, p.get("period"), p.get("share_class"), p.get("currency")),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO fund_performance
                   (fund_id, period, fund_return_pct, benchmark_return_pct, excess_return_pct,
                    share_class, currency, is_annualized, as_of_date, source_name)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (fund_id, p.get("period"), p.get("fund_return_pct"), p.get("benchmark_return_pct"),
                 p.get("excess_return_pct"), p.get("share_class"), p.get("currency"),
                 1 if p.get("is_annualized") else 0, p.get("as_of_date"), SRC),
            )
            perf_inserted += 1

    # Risk metrics -- only insert rows that have at least one real value
    for rm in data[slug].get("risk_metrics", []):
        real_fields = [rm.get(k) for k in (
            "alpha_pct", "beta", "r_squared", "tracking_error_pct", "information_ratio",
            "sharpe_ratio", "upside_capture_pct", "downside_capture_pct",
            "active_share_pct", "batting_average_pct")]
        if all(v is None for v in real_fields):
            skipped_empty.append((slug, "risk_metrics (all-null row)"))
            continue
        exists = conn.execute(
            "SELECT 1 FROM fund_risk_metrics WHERE fund_id=? AND period IS ? AND as_of_date IS ?",
            (fund_id, rm.get("period"), rm.get("as_of_date")),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO fund_risk_metrics
                   (fund_id, period, alpha_pct, beta, r_squared, tracking_error_pct,
                    information_ratio, sharpe_ratio, upside_capture_pct, downside_capture_pct,
                    active_share_pct, batting_average_pct, as_of_date, source_name)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fund_id, rm.get("period"), rm.get("alpha_pct"), rm.get("beta"), rm.get("r_squared"),
                 rm.get("tracking_error_pct"), rm.get("information_ratio"), rm.get("sharpe_ratio"),
                 rm.get("upside_capture_pct"), rm.get("downside_capture_pct"), rm.get("active_share_pct"),
                 rm.get("batting_average_pct"), rm.get("as_of_date"), SRC),
            )
            risk_inserted += 1

    # Share-class detail
    for sc in data[slug]["share_classes"]:
        exists = conn.execute(
            "SELECT 1 FROM fund_share_classes WHERE fund_id=? AND class_name=?",
            (fund_id, sc.get("class_name")),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO fund_share_classes
                   (fund_id, class_name, investor_type, min_investment_usd, management_fee_pct,
                    performance_fee_pct, hurdle_rate_pct, ter_pct, nav, nav_date,
                    exit_load_pct, exit_load_months, lock_in_months, source_name)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fund_id, sc.get("class_name"), sc.get("investor_type"), sc.get("min_investment_usd"),
                 sc.get("management_fee_pct"), sc.get("performance_fee_pct"), sc.get("hurdle_rate_pct"),
                 sc.get("ter_pct"), sc.get("nav"), sc.get("nav_date"), sc.get("exit_load_pct"),
                 sc.get("exit_load_months"), sc.get("lock_in_months"), SRC),
            )
            sc_inserted += 1

conn.commit()

print("=== ISIN / Bloomberg ticker fills ===")
for f in isin_fills:
    print(f)
print(f"\nperformance rows inserted: {perf_inserted}")
print(f"risk_metrics rows inserted: {risk_inserted}")
print(f"share_class rows inserted: {sc_inserted}")
print(f"skipped (empty risk_metrics rows): {len(skipped_empty)}")
conn.close()
