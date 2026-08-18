"""Normalize individual AMC fund records into one clean dataset."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from dateutil import parser as date_parser

DATA_DIR = Path("data")
RAW_PATH = DATA_DIR / "raw_amc_funds.json"
ALTPORT_PATH = DATA_DIR / "altport_tier2.json"
HDFC_PATH = DATA_DIR / "hdfc_ifsc_funds.json"
HDFC_FEEDER_PATH = DATA_DIR / "hdfc_india_feeder_funds.json"
OUTPUT_PATH = DATA_DIR / "funds_cleaned.csv"
FINAL_COLUMNS = [
    "fund_name", "amc_name", "category", "launch_date", "nav", "nav_currency",
    "nav_as_of", "expense_ratio", "aum", "aum_currency", "aum_unit",
    "inception_date", "source_name", "source_url", "scraped_at", "scrape_status",
    "source_tier",
]


def parse_date(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return date_parser.parse(str(value), dayfirst=False).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def clean_data(raw_path: Path = RAW_PATH, altport_path: Path = ALTPORT_PATH,
               hdfc_path: Path = HDFC_PATH, hdfc_feeder_path: Path = HDFC_FEEDER_PATH) -> pd.DataFrame:
    # Tier 1: individually-verified AMC sources (NAV-level verification).
    with raw_path.open(encoding="utf-8") as raw_file:
        tier1_funds = pd.DataFrame(json.load(raw_file))
    if not tier1_funds.empty:
        tier1_funds["source_tier"] = "tier1_amc"

    # HDFC's own official fundListing API -- also tier1_amc (individually
    # verified, real static fields), NAV correctly null because both
    # funds are still in their NFO subscription window, not because of
    # a scraping gap. Optional file -- pipeline works without it.
    if hdfc_path.exists():
        with hdfc_path.open(encoding="utf-8") as hdfc_file:
            hdfc_funds = pd.DataFrame(json.load(hdfc_file))
    else:
        hdfc_funds = pd.DataFrame()

    # HDFC's "Invest in India" feeder funds -- real, live NAV pulled
    # directly from their official backend home API. Genuine Tier 1
    # quality (real current NAV, not a directory listing).
    if hdfc_feeder_path.exists():
        with hdfc_feeder_path.open(encoding="utf-8") as hdfc_feeder_file:
            hdfc_feeder_funds = pd.DataFrame(json.load(hdfc_feeder_file))
    else:
        hdfc_feeder_funds = pd.DataFrame()

    # Tier 2: ALTPORT directory sources (existence + category verified via
    # real IFSCA registration numbers where available; NAV not published).
    # Optional -- pipeline still works if this file hasn't been generated.
    if altport_path.exists():
        with altport_path.open(encoding="utf-8") as altport_file:
            tier2_funds = pd.DataFrame(json.load(altport_file))
    else:
        tier2_funds = pd.DataFrame()

    funds = pd.concat([tier1_funds, hdfc_funds, hdfc_feeder_funds, tier2_funds], ignore_index=True, sort=False)
    if funds.empty:
        return pd.DataFrame(columns=FINAL_COLUMNS)

    funds = funds.reindex(columns=FINAL_COLUMNS)
    for column in ("nav", "expense_ratio", "aum"):
        funds[column] = pd.to_numeric(funds[column], errors="coerce")
    for column in ("launch_date", "nav_as_of", "inception_date"):
        funds[column] = funds[column].apply(parse_date)
    # Exact fund identity only: never merge records merely because AMC names match.
    # Prefer tier1 (NAV-verified) over tier2 (directory-verified) on name collision --
    # sort so tier1_amc sorts after tier2_directory alphabetically is NOT reliable,
    # so do it explicitly: keep tier1 rows on duplicate fund_name.
    funds["_tier_rank"] = funds["source_tier"].map({"tier1_amc": 0, "tier2_directory": 1, "tier2_aggregator": 1}).fillna(1)
    funds = funds.sort_values("_tier_rank").drop_duplicates(subset=["fund_name"], keep="first")
    return funds.drop(columns=["_tier_rank"]).reset_index(drop=True)


if __name__ == "__main__":
    cleaned = clean_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUTPUT_PATH, index=False)
    tier_counts = cleaned["source_tier"].value_counts().to_dict() if not cleaned.empty else {}
    print(f"Exported {len(cleaned)} normalized fund records to {OUTPUT_PATH}")
    print(f"  Tier breakdown: {tier_counts}")
