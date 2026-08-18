"""
HDFC AMC IFSC "Invest in India" feeder fund NAV scraper.

Same technique as hdfc_ifsc_source.py (direct backend API call rather
than fighting Akamai on the main page), but a different, simpler
endpoint -- a plain GET with no parameters, found via DevTools Network
tab inspection of the "Invest in India" section:

    GET https://cms.hdfcinternational.com/hdfc/api/v1/home/getData

Returns real, current NAV data (confirmed live, dated 14-Aug-2026) for
HDFC's 5 domestic-focused GIFT City feeder funds, each with multiple
share classes. We use Class A1 specifically since it's the one class
present across all 5 funds, making it comparable across the set.
"""

import json
import logging
from datetime import datetime, timezone

import requests
from dateutil import parser as date_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

HOME_API_URL = "https://cms.hdfcinternational.com/hdfc/api/v1/home/getData"
PAGE_URL = "https://www.hdfcinternational.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": PAGE_URL,
    "Origin": "https://www.hdfcinternational.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Ch-Ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

PREFERRED_CLASS = "Class A1"


def fetch_and_build_records() -> list[dict]:
    response = requests.get(HOME_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()

    funds_data = payload.get("data", {})
    records = []
    for fund_name, classes in funds_data.items():
        chosen = next((c for c in classes if c.get("class_of_units") == PREFERRED_CLASS), None)
        if chosen is None and classes:
            # Fallback: if Class A1 isn't present for some fund, use
            # whatever the first listed class is rather than dropping
            # the fund entirely -- still real data, just noted.
            chosen = classes[0]

        nav = None
        nav_as_of = None
        class_used = None
        if chosen:
            try:
                nav = float(chosen["nav_amount"])
            except (KeyError, ValueError, TypeError):
                nav = None
            nav_date_raw = chosen.get("nav_date")
            if nav_date_raw:
                try:
                    nav_as_of = date_parser.parse(nav_date_raw, dayfirst=True).date().isoformat()
                except (ValueError, TypeError):
                    nav_as_of = None
            class_used = chosen.get("class_of_units")

        records.append({
            "fund_name": fund_name,
            "amc_name": "HDFC AMC International (IFSC) Limited",
            "category": "Retail Fund (inbound feeder)",
            "launch_date": None,
            "nav": nav,
            "nav_currency": "USD",
            "nav_as_of": nav_as_of,
            "expense_ratio": None,
            "aum": None,
            "aum_currency": None,
            "aum_unit": None,
            "inception_date": None,
            "source_name": f"HDFC AMC IFSC official home API ({class_used or 'no class found'})",
            "source_url": PAGE_URL,
            "source_tier": "tier1_amc",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "scrape_status": "success" if nav is not None else "partial",
            "error_message": None if nav is not None else "No NAV value found for any share class.",
        })

    return records


if __name__ == "__main__":
    records = fetch_and_build_records()
    for r in records:
        logger.info(f"  -> {r['fund_name']} | nav={r['nav']} {r['nav_currency']} "
                    f"as of {r['nav_as_of']} | status={r['scrape_status']}")

    out_path = "data/hdfc_india_feeder_funds.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote {len(records)} records to {out_path}")
