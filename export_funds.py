"""Export the final funds table to a single clean JSON file, ready to share."""

import json
import sqlite3

DB_PATH = "gift_city_amc_funds.db"
OUTPUT_PATH = "gift_city_funds_export.json"

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM funds ORDER BY source_tier, fund_name").fetchall()
    funds = [dict(row) for row in rows]

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(funds, f, indent=2, ensure_ascii=False, default=str)

print(f"Exported {len(funds)} funds to {OUTPUT_PATH}")
tier_counts = {}
for fund in funds:
    tier_counts[fund["source_tier"]] = tier_counts.get(fund["source_tier"], 0) + 1
print(f"Tier breakdown: {tier_counts}")
