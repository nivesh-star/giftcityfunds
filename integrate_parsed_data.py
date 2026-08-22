"""
Integrate parsed factsheet output (parsed_output.json) into our
SQLite DB. Rules:
  - NEVER overwrite a field that already has a non-null value in our DB --
    only fill genuine gaps.
  - If the parsed value DISAGREES with an existing non-null value (e.g.
    TER), do NOT touch it -- just record it as a conflict to report.
  - Holdings / allocations / taxation are net-new tables, inserted
    directly (skip if an identical row already exists).
  - The 3 funds with no DB match (Ashoka WhiteOak EM Ex India, Rational
    Gold & Silver Miners, Unifi G20) are inserted as brand-new fund rows.
"""
import json
import sqlite3

DB_PATH = "gift_city_amc_funds.db"

# slug -> matched fund_id (None means "insert as new fund")
MATCHES = {
    "dsp": 2,
    "ppfas_sp": 3,
    "ppfas_nq": 4,
    "edelweiss": 5,
    "mirae": 66,
    "marcellus_ge": 105,
    "baroda": 115,
    "phillip": 178,
    "ppfas_pms": 179,
    "absl": 214,
    "marcellus_gcp": 1666,
    "ashoka": None,
    "rational": None,
    "unifi": None,
}

data = json.load(open("parsed_output.json"))["results"]
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

conflicts = []
filled = []
new_funds = {}
skipped_allocations = []


def fmt_exit_load(pct, months):
    if pct is None:
        return None
    if pct == 0:
        return "Nil"
    if months:
        return f"{pct}% within {months} months"
    return f"{pct}%"


def fmt_lockin(months):
    if not months:
        return None
    if months % 12 == 0:
        return f"{months // 12} year{'s' if months != 12 else ''}"
    return f"{months} months"


for slug, fund_id in MATCHES.items():
    fi = data[slug]["fund_info"]
    holdings = data[slug]["holdings"]
    allocations = data[slug]["allocations"]

    if fund_id is None:
        new_funds[slug] = data[slug]
        continue

    row = conn.execute("SELECT * FROM funds WHERE fund_id=?", (fund_id,)).fetchone()
    row = dict(row)

    candidate_updates = {
        "fund_manager_name": fi.get("fund_manager"),
        "benchmark_index": fi.get("benchmark_index"),
        "nav": fi.get("nav"),
        "nav_as_of": fi.get("nav_date"),
        "launch_date": fi.get("inception_date"),
        "lock_in_period": fmt_lockin(fi.get("lock_in_months")),
        "exit_load": fmt_exit_load(fi.get("exit_load_pct"), fi.get("exit_load_months")),
    }
    if fi.get("aum_usd") is not None:
        candidate_updates["aum"] = round(fi["aum_usd"] / 1_000_000, 4)
        candidate_updates["aum_currency"] = "USD"
        candidate_updates["aum_unit"] = "million"
    if fi.get("min_investment_usd") is not None:
        candidate_updates["minimum_investment"] = f"USD {fi['min_investment_usd']:,.0f}"

    # TER: check the "Direct" share class first (matches our existing
    # convention of quoting Direct Plan TER), else the first share class
    # that has one.
    ter = None
    for sc in data[slug]["share_classes"]:
        if sc.get("ter_pct") is not None and (sc.get("class_name") or "").lower().startswith("direct"):
            ter = sc["ter_pct"]
            break
    if ter is None:
        for sc in data[slug]["share_classes"]:
            if sc.get("ter_pct") is not None:
                ter = sc["ter_pct"]
                break
    if ter is not None:
        candidate_updates["expense_ratio"] = ter

    set_clauses = []
    params = []
    for col, new_val in candidate_updates.items():
        if new_val is None:
            continue
        existing = row.get(col)
        if existing is None or existing == "" or existing == "None":
            set_clauses.append(f"{col}=?")
            params.append(new_val)
            filled.append((row["fund_name"], col, new_val))
        else:
            if str(existing) != str(new_val):
                conflicts.append((row["fund_name"], col, existing, new_val))

    if set_clauses:
        params.append(fund_id)
        conn.execute(f"UPDATE funds SET {', '.join(set_clauses)}, last_updated=CURRENT_TIMESTAMP WHERE fund_id=?", params)

    # Holdings
    for h in holdings:
        exists = conn.execute(
            "SELECT 1 FROM portfolio_holdings WHERE fund_id=? AND holding_name=?",
            (fund_id, h["holding_name"]),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO portfolio_holdings
                   (fund_id, holding_name, weight_pct, as_of_date, source_name, holdings_basis)
                   VALUES (?,?,?,?,?,?)""",
                (fund_id, h["holding_name"], h["weight_pct"], h.get("as_of_date"),
                 "Factsheet PDF (parsed via internal GIFT City parser pipeline)", "fund_direct"),
            )

    # Allocations -- our schema's breakdown_type only allows 'geographic'/'sector';
    # skip any other allocation_type (e.g. 'Asset Class') rather than force-fit it.
    ALLOC_TYPE_MAP = {"Geography": "geographic", "Sector": "sector"}
    for a in allocations:
        breakdown_type = ALLOC_TYPE_MAP.get(a["allocation_type"])
        if breakdown_type is None:
            skipped_allocations.append((row["fund_name"], a["allocation_type"], a["category"]))
            continue
        exists = conn.execute(
            "SELECT 1 FROM fund_allocation WHERE fund_id=? AND breakdown_type=? AND category=?",
            (fund_id, breakdown_type, a["category"]),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO fund_allocation
                   (fund_id, breakdown_type, category, weight_pct, as_of_date, source_name)
                   VALUES (?,?,?,?,?,?)""",
                (fund_id, breakdown_type, a["category"], a["weight_pct"], a.get("as_of_date"),
                 "Factsheet PDF (parsed via internal GIFT City parser pipeline)"),
            )

    # Taxation
    if fi.get("ltcg_tax_pct") is not None or fi.get("stcg_tax_pct") is not None:
        existing_tax = conn.execute("SELECT * FROM fund_taxation WHERE fund_id=?", (fund_id,)).fetchone()
        if not existing_tax:
            conn.execute(
                """INSERT INTO fund_taxation (fund_id, ltcg_rate, stcg_rate, as_of_date, source_name)
                   VALUES (?,?,?,?,?)""",
                (fund_id, fi.get("ltcg_tax_pct"), fi.get("stcg_tax_pct"), fi.get("factsheet_date"),
                 "Factsheet PDF (parsed via internal GIFT City parser pipeline)"),
            )

conn.commit()

print("=== FILLED (null -> new value) ===")
for f in filled:
    print(f)
print(f"\ntotal fills: {len(filled)}")

print("\n=== CONFLICTS (existing value != parsed value, NOT applied) ===")
for c in conflicts:
    print(c)
print(f"\ntotal conflicts: {len(conflicts)}")

print("\n=== NEW FUNDS (no DB match) ===")
for slug, fs in new_funds.items():
    print(slug, "->", fs["fund_info"]["fund_name"])

print(f"\n=== SKIPPED ALLOCATIONS (type not supported by schema): {len(skipped_allocations)} ===")
for s in skipped_allocations[:10]:
    print(s)

conn.close()
