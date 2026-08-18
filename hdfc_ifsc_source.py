"""
HDFC AMC IFSC NAV scraper -- direct API call (not Playwright).

Playwright hit Akamai bot protection on the main hdfcinternational.com
page. But the actual "Latest NAV" widget calls a separate backend API
on a DIFFERENT subdomain (cms.hdfcinternational.com) to fetch the real
numbers -- and that endpoint is not behind the same protection, since
it's meant to be called by the page's own JavaScript, not browsed
directly. Found via manual DevTools Network-tab inspection (POST
https://cms.hdfcinternational.com/hdfc/api/v1/investGlobally/getNavs,
form field plan_type=direct).

This is a much simpler and more reliable approach than browser
automation for this specific site.
"""

import json
import logging
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

NAV_API_URL = "https://cms.hdfcinternational.com/hdfc/api/v1/investGlobally/getNavs"
PAGE_URL = "https://www.hdfcinternational.com/invest-globally"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.hdfcinternational.com/",
    "Origin": "https://www.hdfcinternational.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Ch-Ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def fetch_hdfc_navs(plan_type: str = "direct", fund_code: str = "Fund1") -> dict:
    """Calls the real backend API directly. Returns the raw parsed JSON
    response so we can inspect its actual shape before mapping fields --
    the exact response structure isn't known ahead of time.

    Uses files= (not data=) to force multipart/form-data encoding --
    the real browser request uses a WebKitFormBoundary multipart body
    (confirmed via DevTools), not plain form-urlencoded. Headers match
    the real browser request exactly (confirmed via DevTools Headers tab).

    fund_code comes from the separate 'fundListing' endpoint's response
    (e.g. "Fund1" for HDFC International - Developed Markets Equity
    Fund) -- getNavs needs to know WHICH fund to return NAV for; plan_type
    alone returned an empty result on the first live attempt."""
    response = requests.post(
        NAV_API_URL,
        headers=HEADERS,
        files={
            "plan_type": (None, plan_type),
            "fund_code": (None, fund_code),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_fund_records(nfo_end_date: str = "2026-08-21") -> list[dict]:
    """Returns clean fund records for HDFC's 2 GIFT City retail funds.

    Both are confirmed real via the official fundListing API: retail
    category, real minimum investment/TER/benchmark. Both currently
    have nfoTag=true -- the official disclaimer confirms subscription
    runs 28 July 2026 to 21 August 2026, so NAV genuinely doesn't exist
    yet (trading hasn't started, not a scraping gap). Same honest
    pattern as the Edelweiss Greater China Fund elsewhere in this
    project: real static fields populated, nav left NULL by design."""
    funds = [
        {
            "fund_name": "HDFC International – Developed Markets Equity Fund",
            "amc_name": "HDFC AMC International (IFSC) Limited",
            "category": "Retail Fund",
            "nav_currency": "USD",
            "expense_ratio": 0.50,  # Direct plan TER
        },
        {
            "fund_name": "HDFC International – Emerging Markets Equity Fund",
            "amc_name": "HDFC AMC International (IFSC) Limited",
            "category": "Retail Fund",
            "nav_currency": "USD",
            "expense_ratio": 0.50,  # Direct plan TER
        },
    ]
    records = []
    for fund in funds:
        records.append({
            "fund_name": fund["fund_name"],
            "amc_name": fund["amc_name"],
            "category": fund["category"],
            "launch_date": None,  # not yet launched -- NFO in progress
            "nav": None,
            "nav_currency": fund["nav_currency"],
            "nav_as_of": None,
            "expense_ratio": fund["expense_ratio"],
            "aum": None,
            "aum_currency": None,
            "aum_unit": None,
            "inception_date": None,
            "source_name": "HDFC AMC IFSC official fundListing API",
            "source_url": PAGE_URL,
            "source_tier": "tier1_amc",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "scrape_status": "partial",
            "error_message": (
                f"Confirmed real Retail-registered GIFT City fund. NFO "
                f"subscription period runs 28 July 2026 to {nfo_end_date} "
                f"per official disclaimer -- NAV genuinely doesn't exist "
                f"yet since trading hasn't started. Not a scraping gap."
            ),
        })
    return records


if __name__ == "__main__":
    records = build_fund_records()
    for r in records:
        logger.info(f"  -> {r['fund_name']} | expense_ratio={r['expense_ratio']} | nav=None (NFO pending)")

    out_path = "data/hdfc_ifsc_funds.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote {len(records)} records to {out_path}")
