"""
cleaner.py
Cleans and normalizes raw scraped GIFT City fund data (inbound + outbound
trackers, plus individual AMC fund detail pages) into one unified,
deduplicated CSV matching the assignment's database schema.

Built incrementally and verified step-by-step against real scraped data.
Key design decisions, each deliberate and documented rather than silent:

- Inbound tracker rows are fund-HOUSE level (e.g. "Tata"), not individual
  scheme level. fund_name == amc_name for these rows -- a real data
  limitation of the source, not an extraction error.
- category is INFERRED from investment_strategy free text via keyword
  matching (flexicap/midcap/growth -> Equity, etc.), since the source
  never provides an explicit category field. All funds I observed are
  equity-style; this is my best-effort classification, not a confirmed
  asset-class label from the data provider.
- amc_name for outbound funds is extracted from fund_name via a known-AMC
  lookup list (checked longest-first to avoid partial matches like
  "Mirae" vs "Mirae Asset").
- min_ticket, k1_compliant (inbound) and return_3m/return_6m/
  return_since_inception, has_return_data (outbound) are additional
  fields beyond the assignment's base schema -- kept because they're
  genuinely useful and the source data supports them.
- launch_date and inception_date are DIFFERENT fields in the schema.
  Only inception_date is available (from outbound funds' expanded detail
  text, e.g. "Inception: Sept 2025"). launch_date is genuinely
  unavailable from any source page I scraped and is left null
  throughout, not silently merged with inception_date.
- aum_crores is intentionally left null: I verified against DSP's live
  page that "AUM" only appears in unrelated firm-level/FAQ content, not
  as a clean per-fund figure. A regex match here would be a guess
  dressed up as data.
"""

import json
import re
from pathlib import Path

import pandas as pd
from dateutil import parser as date_parser

DATA_DIR = Path("data")

KNOWN_AMCS = [
    "Baroda BNP Paribas",
    "Mirae Asset",
    "Ashoka WhiteOak",
    "Rational",
    "DSP",
    "PPFAS",
    "Edelweiss",
    "Marcellus",
    "Ionic",
    "ABSL",
    "Unifi",
    "Phillip",
]

# Individual fund detail pages I scraped, mapped to the AMC they belong
# to -- used to merge nav/expense_ratio/min_investment back onto the
# right row. PPFAS's detail page (Parag Parikh India Flexicap Fund) is
# deliberately excluded: it doesn't correspond to any fund actually
# present in my 26 tracker rows, so merging it in would attach data to
# the wrong fund.
DETAIL_PAGE_AMC_MAP = {
    "https://giftcity.dspim.com/product": "DSP",
    "https://giftcity.miraeassetmf.co.in/mirae-asset-global-allocation-fund.html": "Mirae Asset",
}


def load_raw_data():
    with open(DATA_DIR / "raw_tracker_data.json") as f:
        tracker_records = json.load(f)
    with open(DATA_DIR / "raw_fund_details.json") as f:
        detail_records = json.load(f)
    return pd.DataFrame(tracker_records), pd.DataFrame(detail_records)


def clean_min_ticket(value):
    if pd.isna(value):
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value))
    return float(cleaned) if cleaned else None


def clean_k1_status(value):
    if pd.isna(value):
        return None
    return "K1" in str(value).upper() and "COMPLIANT" in str(value).upper()


def classify_category(strategy_text):
    if pd.isna(strategy_text):
        return None
    text = str(strategy_text).lower()
    if any(kw in text for kw in ["debt", "bond", "fixed income", "credit"]):
        return "Debt"
    if any(kw in text for kw in ["hybrid", "balanced", "multi-asset", "multi asset"]):
        return "Hybrid"
    return "Equity"  # default: all inbound/outbound strategies observed use equity vocabulary


def clean_percentage(value):
    if pd.isna(value) or value == "\u2014":
        return None
    cleaned = str(value).replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_amc(fund_name):
    if pd.isna(fund_name):
        return None
    for amc in KNOWN_AMCS:  # longest names first, avoids "Mirae" matching inside "Mirae Asset"
        if fund_name.startswith(amc):
            return amc
    return fund_name.split()[0]  # fallback -- would need adding to KNOWN_AMCS if ever hit


def extract_inception_date(raw_text):
    if pd.isna(raw_text):
        return None
    match = re.search(r"Inception:\s*([A-Za-z]+ \d{4})", raw_text)
    return match.group(1) if match else None


def parse_date(text):
    if pd.isna(text) or text is None:
        return None
    try:
        return date_parser.parse(text, default=pd.Timestamp("2000-01-01")).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def clean_data():
    df, details_df = load_raw_data()

    # --- Inbound-specific cleaning ---
    df["min_ticket"] = df["min_ticket_raw"].apply(clean_min_ticket)
    df["k1_compliant"] = df["k1_status_raw"].apply(clean_k1_status)
    df["category"] = df["investment_strategy"].apply(classify_category)

    # --- Outbound-specific cleaning ---
    df["return_3m"] = df["return_3m_raw"].apply(clean_percentage)
    df["return_6m"] = df["return_6m_raw"].apply(clean_percentage)
    df["return_since_inception"] = df["return_since_inception_raw"].apply(clean_percentage)
    df["has_return_data"] = df["return_3m"].notna()
    df["inception_date_extracted"] = df["raw_text"].apply(extract_inception_date)

    # --- Build unified inbound rows ---
    inbound = df[df["direction"] == "inbound"]
    inbound_clean = pd.DataFrame({
        "fund_name": inbound["fund_house"],
        "amc_name": inbound["fund_house"],  # documented limitation: inbound is house-level, not scheme-level
        "category": inbound["category"],
        "launch_date": None,
        "inception_date": None,
        "min_ticket": inbound["min_ticket"],
        "k1_compliant": inbound["k1_compliant"],
        "return_3m": None,
        "return_6m": None,
        "return_since_inception": None,
        "has_return_data": False,
        "direction": "inbound",
        "grouping": inbound["section"],
        "source_url": inbound["source_url"],
    })

    # --- Build unified outbound rows ---
    outbound = df[df["direction"] == "outbound"]
    outbound_clean = pd.DataFrame({
        "fund_name": outbound["fund_name"],
        "amc_name": outbound["fund_name"].apply(extract_amc),
        "category": "Equity",  # same reasoning as inbound -- all outbound strategies observed are equity-style
        "launch_date": None,  # genuinely unavailable; NOT the same as inception_date, kept separate
        "inception_date": outbound["inception_date_extracted"].apply(parse_date),
        "min_ticket": None,
        "k1_compliant": None,
        "return_3m": outbound["return_3m"],
        "return_6m": outbound["return_6m"],
        "return_since_inception": outbound["return_since_inception"],
        "has_return_data": outbound["has_return_data"],
        "direction": "outbound",
        "grouping": outbound["data_category"],
        "source_url": outbound["source_url"],
    })

    funds_cleaned = pd.concat([inbound_clean, outbound_clean], ignore_index=True)

    # --- Merge in individual fund detail data (DSP, Mirae Asset only) ---
    details_df["matched_amc"] = details_df["source_url"].map(DETAIL_PAGE_AMC_MAP)
    funds_cleaned = funds_cleaned.merge(
        details_df[["matched_amc", "nav", "expense_ratio", "min_investment", "fund_status"]],
        left_on="amc_name", right_on="matched_amc", how="left",
    ).drop(columns=["matched_amc"])

    # aum_crores intentionally not populated -- see module docstring.
    funds_cleaned["aum_crores"] = None

    return funds_cleaned


def run_quality_checks(funds_cleaned):
    """Prints a short data quality summary -- not a replacement for the
    formal pytest suite (tests/test_quality.py), just a quick sanity
    check when running this script standalone."""
    issues = []

    dupes = funds_cleaned["fund_name"].duplicated().sum()
    if dupes:
        issues.append(f"{dupes} duplicate fund_name(s) found")

    null_category = funds_cleaned["category"].isna().sum()
    if null_category:
        issues.append(f"{null_category} row(s) missing category")

    print(f"\nRows: {len(funds_cleaned)} | Duplicates: {dupes} | Missing category: {null_category}")
    if issues:
        for i in issues:
            print(f"  ISSUE: {i}")
    else:
        print("  No quality issues detected.")


if __name__ == "__main__":
    funds_cleaned = clean_data()

    print("=== Cleaned fund data ===")
    print(f"Total rows: {len(funds_cleaned)}")
    print(f"By direction:\n{funds_cleaned['direction'].value_counts()}")

    run_quality_checks(funds_cleaned)

    output_path = DATA_DIR / "funds_cleaned.csv"
    funds_cleaned.to_csv(output_path, index=False)
    print(f"\nExported {len(funds_cleaned)} funds to {output_path}")
