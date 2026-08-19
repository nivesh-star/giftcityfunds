"""
Mirae Asset India Equity Allocation Fund NAV scraper.

Found via DevTools Network-tab inspection (same technique as HDFC):
the fund's own page shows "Loading data..." for its NAV table, backed
by a hidden POST endpoint:

    POST https://www.miraeassetmf.co.in/AjaxService/GetGiftDebtIndexDetails
    Form field: schemeCode=MAIEAF IFSC GIFT

(The endpoint name mentions "Debt" but is confirmed via the real
schemeCode parameter to serve this equity fund too -- likely a shared/
generic endpoint across Mirae's GIFT City products, not literally
debt-specific.)
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

NAV_API_URL = "https://www.miraeassetmf.co.in/AjaxService/GetGiftDebtIndexDetails"
PAGE_URL = "https://giftcity.miraeassetmf.co.in/mirae-asset-india-equity-allocation-fund-ifsc-gift-city.html"
SCHEME_CODE = "MAIEAF IFSC GIFT"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": PAGE_URL,
    "Origin": "https://giftcity.miraeassetmf.co.in",
}


def fetch_raw() -> dict | list:
    response = requests.post(
        NAV_API_URL,
        headers=HEADERS,
        data={"schemeCode": SCHEME_CODE},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


PREFERRED_PLAN = "Class A1 Units"


def build_fund_record() -> dict:
    data = fetch_raw()
    chosen = next((d for d in data if d.get("PlanName") == PREFERRED_PLAN), None)
    if chosen is None and data:
        chosen = data[0]  # fallback: use whatever the first plan is

    nav = None
    nav_as_of = None
    plan_used = None
    if chosen:
        nav = chosen.get("NavAmount")
        nav_date_raw = chosen.get("NavDate")  # format: DD-MM-YYYY
        if nav_date_raw:
            try:
                day, month, year = nav_date_raw.split("-")
                nav_as_of = f"{year}-{month}-{day}"
            except (ValueError, AttributeError):
                nav_as_of = None
        plan_used = chosen.get("PlanName")

    return {
        "fund_name": "Mirae Asset India Equity Allocation Fund",
        "amc_name": "Mirae Asset Investment Managers (India) Private Limited (IFSC Branch)",
        "category": "Restricted Scheme (Non-Retail), Category III AIF",
        "launch_date": None,
        "nav": nav,
        "nav_currency": "USD",
        "nav_as_of": nav_as_of,
        "expense_ratio": None,
        "aum": None,
        "aum_currency": None,
        "aum_unit": None,
        "inception_date": None,
        "minimum_investment": "USD 151,000 (USD 10,000 for Accredited Investors)",  # confirmed on official page
        "source_name": f"Mirae Asset official NAV API ({plan_used or 'no plan found'})",
        "source_url": PAGE_URL,
        "source_tier": "tier1_amc",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scrape_status": "success" if nav is not None else "partial",
        "error_message": None if nav is not None else "No NAV value found for any share class.",
    }


if __name__ == "__main__":
    record = build_fund_record()
    logger.info(f"  -> {record['fund_name']} | nav={record['nav']} {record['nav_currency']} "
                f"as of {record['nav_as_of']} | status={record['scrape_status']}")
    with open("data/mirae_india_equity_alloc.json", "w", encoding="utf-8") as f:
        json.dump([record], f, indent=2, ensure_ascii=False)
    logger.info("Wrote data/mirae_india_equity_alloc.json")
