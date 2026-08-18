"""
ALTPORT fund directory scraper.

ALTPORT (altportfunds.com) is a fund distributor that maintains a
directory of ~200 GIFT City funds, each with an individual page. This
is genuinely useful, but the pages come in two different shapes and
only one of them is trustworthy for our purposes:

1. AIF-registered funds (e.g. ASKWA India Opportunities Fund): show a
   real IFSCA "Registration Number" and "Date of Registration" in a
   Fund Snapshot table. This is authentic, GIFT-City-specific data --
   we extract fund_name, amc_name, category, and launch_date (from the
   registration date) from these.

2. Inbound feeder funds (e.g. ABSL India Flexicap Fund IFSC): show an
   "Inception Date" in their Fund Snapshot table, but this is the
   UNDERLYING DOMESTIC Indian mutual fund's inception date (e.g. 1998
   for ABSL Flexicap), not the GIFT City IFSC feeder's own launch date.
   Using this as launch_date would be actively misleading. For these
   pages we extract fund_name, amc_name, and category ONLY --
   launch_date is left NULL rather than populated with a wrong date.

The distinguishing signal: presence of "Registration Number" as a row
label in the Fund Snapshot table means type 1 (trustworthy date);
its absence (only "Inception Date" present) means type 2 (untrustworthy
date for our purposes, so we don't use it).
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}

BASE_URL = "https://www.altportfunds.com/investments/"

# Candidate fund slugs -- picked from the directory page, excluding
# funds we already have individually-verified sources for in scraper.py
# (Tata, DSP Global Equity, PPFAS x2, Edelweiss, Sundaram, Mirae Global
# Allocation, Bandhan Small Cap, Marcellus Global Equities, Baroda BNP
# Paribas, Nippon India Large Cap, Altus Quant, Nuvama India Edge,
# Phillip Pioneer, PPFAS PMS, NJ India Opportunities).
CANDIDATE_SLUGS = [
    "askwa-india-opportunities-fund",
    "askwa-global-opportunities-fund",
    "absl-global-bluechip-equity-fund-ifsc",
    "absl-global-emerging-market-equity-fund-ifsc",
    "absl-india-flexicap-fund-ifsc",
    "alchemy-india-long-term-fund",
    "ashoka-whiteoak-capital-india-opportunities-gift-fund",
    "ashoka-whiteoak-india-multi-cap-gift-fund",
    "axis-india-multicap-fund-2",
    "bandhan-india-government-securities-fund-ifsc",
    "bandhan-india-large-and-mid-cap-fund-ifsc",
    "carnelian-india-amritkaal-fund",
    "carnelian-india-multi-strategy-fund",
    "dsp-india-absolute-return-fund",
    "dsp-india-equity-opportunities-fund",
    "dsp-india-ifsc-fund",
    "hdfc-india-balanced-advantage-fund",
    "hdfc-india-flexi-cap-fund",
    "hdfc-india-mid-cap-opportunities-fund",
    "hdfc-india-nifty-50-fund",
    "hdfc-india-small-cap-fund",
    "kotak-equity-india-fund-of-fund-ifsc",
    "kotak-iconic-india-equity-feeder-fund",
    "rangoli-india-fund",
    "rational-asset-management-fund",
    "sbi-india-equity-advantage-fund-ifsc",
    "sbi-investment-opportunities-fund-ifsc",
    "uti-india-opportunities-ifsc-fund",
    # Second batch: more funds from AMCs we'd only picked one fund from,
    # plus a few new AMCs entirely -- all confirmed present on the
    # directory's own listing page, not guessed.
    "marcellus-global-compounders-fund",
    "mirae-asset-india-equity-allocation-fund",
    "nuvama-late-stage-growth-equity-fund-4",
    "dsp-india-strategic-bond-fund",
    "dsp-india-t-i-g-e-r-fund",
    "dsp-pre-ipo-fund",
    "kotak-real-estate-fund-x-ifsc",
    "kotak-real-estate-fund-xii-ifsc-i",
    "kotak-real-estate-fund-xii-ifsc-ii",
    "kotak-strategic-situations-fund-ii-ifsc",
    "kotak-real-estate-investment-fund-ifsc",
    "kotak-real-estate-investment-fund-ii-ifsc",
    "kotak-performing-re-credit-strategy-fund-ii-ifsc",
    "kotak-india-commercial-real-estate-fund-ifsc",
    "uti-india-opportunities-ifsc-fund-ii",
    "uti-india-opportunities-ifsc-fund-iii",
    "nippon-india-etf-nifty-50-bees-gift",
    "sage-one-india-growth-gift-fund",
    "girik-multicap-india-fund",
    "sameeksha-india-flexicap-equity-fund",
    "valuequest-india-g-i-f-t-fund",
    "aikyam-india-discovery-fund",
    "abc-india-equity-fund",
]


def _extract_fund_snapshot(soup: BeautifulSoup) -> dict:
    """Find the 'Fund Snapshot' table and return its rows as a dict of
    label -> value. Returns {} if no such table is found."""
    snapshot = {}
    heading = soup.find(lambda tag: tag.name in ("h2", "h3") and "Fund Snapshot" in tag.get_text())
    if not heading:
        return snapshot

    table = heading.find_next("table")
    if not table:
        return snapshot

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if label:
                snapshot[label] = value
    return snapshot


def get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def scrape_altport_fund(slug: str, session: requests.Session | None = None) -> dict:
    url = BASE_URL + slug + "/"
    record = {
        "fund_name": None,
        "amc_name": None,
        "category": None,
        "launch_date": None,
        "launch_date_type": None,  # "registration" (trustworthy) or None
        "source_name": "ALTPORT fund directory",
        "source_url": url,
        "source_tier": "tier2_directory",  # honest label: verified existence + category, not NAV-level verification
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scrape_status": "failed",
        "error_message": None,
    }

    client = session or requests
    try:
        response = client.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Fund name: the H1 heading
        h1 = soup.find("h1")
        fund_name = h1.get_text(strip=True) if h1 else None

        snapshot = _extract_fund_snapshot(soup)

        # AMC name extraction: multi-strategy DOM traversal
        INVALID_AMC_STRINGS = {
            "Fund Snapshot", "What This GIFT City Fund Represents", "About Company",
            "Quick Actions", "About Us", "About", "Fund Overview", "Investment Philosophy",
            "Get InTouchWithOur Investment Experts", "Let's connect", "Thank you",
        }
        amc_name = snapshot.get("Provider Name") or snapshot.get("AMC Name") or snapshot.get("Fund House")
        
        # 2. Company title class in company card
        if not amc_name:
            comp_title = soup.find(class_="company-title")
            if comp_title:
                val = comp_title.get_text(strip=True)
                if val not in INVALID_AMC_STRINGS and not val.startswith("What This"):
                    amc_name = val

        # 3. Heading inside company-card container
        if not amc_name:
            comp_card = soup.find(class_="company-card")
            if comp_card:
                h = comp_card.find(["h2", "h3", "h4"])
                if h:
                    val = h.get_text(strip=True)
                    if val not in INVALID_AMC_STRINGS and not val.startswith("What This"):
                        amc_name = val

        # 4. Heading following 'About Company' text
        if not amc_name:
            about_elem = soup.find(lambda tag: tag.name in ("p", "h2", "h3", "h4", "div") and "About Company" in tag.get_text())
            if about_elem:
                next_heading = about_elem.find_next(["h2", "h3", "h4"])
                if next_heading:
                    val = next_heading.get_text(strip=True)
                    if val not in INVALID_AMC_STRINGS and not val.startswith("What This"):
                        amc_name = val

        if amc_name in INVALID_AMC_STRINGS or (amc_name and amc_name.startswith("What This")):
            amc_name = None

        # Category: bounded-window text match or snapshot Category
        page_text = soup.get_text("\n", strip=True)
        search_start = page_text.find(fund_name) if fund_name else 0
        search_start = max(search_start, 0)
        window_text = page_text[search_start:search_start + 600]
        category_match = re.search(r"\nCategory\n([^\n]+)", window_text)
        category = category_match.group(1).strip() if category_match else None
        if not category:
            category = snapshot.get("Category")

        # Only trust "Date of Registration" (real IFSCA registration --
        # type 1 pages). Deliberately do NOT use "Inception Date" here,
        # since on feeder-fund pages that's the domestic underlying
        # fund's history, not the GIFT City wrapper's own launch date.
        launch_date = None
        launch_date_type = None
        if "Date of Registration" in snapshot:
            launch_date = snapshot["Date of Registration"]
            launch_date_type = "registration"

        record.update(
            fund_name=fund_name,
            amc_name=amc_name,
            category=category,
            launch_date=launch_date,
            launch_date_type=launch_date_type,
            scrape_status="success" if fund_name else "partial",
        )
        if not fund_name:
            record["error_message"] = "Page loaded but fund name (H1) could not be found."
        return record
    except Exception as exc:
        import traceback
        record["error_message"] = f"{type(exc).__name__}: {exc} | {traceback.format_exc(limit=2)}"
        return record


def run_altport_scrape() -> list[dict]:
    records = []
    session = get_http_session()
    for i, slug in enumerate(CANDIDATE_SLUGS):
        logger.info(f"[{i+1}/{len(CANDIDATE_SLUGS)}] Scraping: {slug}")
        record = scrape_altport_fund(slug, session=session)
        status = "OK" if record["scrape_status"] == "success" else "FAILED"
        logger.info(f"  -> {status} | fund={record['fund_name']} | amc={record['amc_name']} | "
                    f"launch_date={record['launch_date']} ({record['launch_date_type']})")
        records.append(record)
        time.sleep(0.5)  # be polite to the distributor's server

    success_count = sum(1 for r in records if r["scrape_status"] == "success")
    with_date = sum(1 for r in records if r["launch_date"])
    logger.info(f"ALTPORT scrape complete: {success_count}/{len(records)} succeeded, "
                f"{with_date} with a trustworthy (registration-based) launch_date")
    return records


if __name__ == "__main__":
    records = run_altport_scrape()
    out_path = "data/altport_tier2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote {len(records)} records to {out_path}")
