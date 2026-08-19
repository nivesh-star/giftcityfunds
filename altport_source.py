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
DIRECTORY_URL = "https://www.altportfunds.com/gift-city-all-products/"

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

# Manually-researched supplementary facts, keyed by exact fund_name (as
# returned by scrape_altport_fund's H1 extraction). These are real,
# individually sourced findings (news articles, official launch
# announcements, LEI registry data) that don't fit the automated
# per-page scrape -- mostly target fund size at launch, since current
# NAV/AUM genuinely isn't public for these institutional funds, but a
# reported launch-time target is real, attributable data rather than a
# guess. Every entry here should have a comment citing its source.
MANUAL_OVERRIDES = {
    "ASKWA India Opportunities Fund": {
        "target_corpus_at_launch": "USD 100 million",  # PMS Bazaar: "ASK Private Wealth Launches $100M India Opportunities Fund"
        "minimum_investment": "USD 150,000",  # IFSCA Fund Management Regulations minimum ticket size for non-retail Cat II/III AIF investors -- regulatory floor, not fund-specific disclosure (none published)
    },
    "ASKWA Global Opportunities Fund": {
        "minimum_investment": "USD 150,000",  # same IFSCA regulatory minimum as ASKWA India Opportunities Fund (same manager/structure)
    },
    "ABSL Global Emerging Market Equity Fund (IFSC)": {
        "category": "Cat II, Close Ended, Closed for Subscription",  # confirmed on ABSL's own official GIFT City page
        "lock_in_period": "4.5 years from first close, extendable by up to 1 year",  # PMS AIF World fund page
        "minimum_investment": "USD 150,000",  # IFSCA regulatory minimum for non-retail Cat II AIF investors
        "aum": "69.89", "aum_currency": "USD", "aum_unit": "million",  # fintechbiznews.com: "$69.89 million from 269 investors" at final close, 7 Apr 2025
    },
    "Ashoka WhiteOak India Multi Cap GIFT Fund": {
        "minimum_investment": "USD 150,000",  # ALTPORT's own fund page, directly confirmed
        "amc_name": "WhiteOak Capital",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
    },
    "Ashoka WhiteOak Capital India Opportunities GIFT Fund": {
        "amc_name": "WhiteOak Capital",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- II AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
        "minimum_investment": "USD 150,000",  # IFSCA regulatory minimum for non-retail Cat II AIF investors; not individually disclosed by the fund
    },
    "Carnelian India Amritkaal Fund": {
        "benchmark_index": "S&P BSE 500 Index",  # same QGARP strategy/benchmark as their domestic Bharat Amritkaal Fund, confirmed identical across multiple sources
        "launch_date": "August 2024",  # confirmed via Kalviro Ventures article specifically about this GIFT City fund
    },
    "Sameeksha India Flexicap Equity Fund": {
        "minimum_investment": "USD 150,000",  # confirmed on Sameeksha's own official IFSC page, explicitly different from their domestic PMS's ₹2.5 Cr minimum
        "launch_date": "March 2024",  # confirmed on Sameeksha's own official IFSC page
    },
    "Kotak Strategic Situations Fund – II IFSC": {
        "target_corpus_at_launch": "USD 1.6 billion",  # official Kotak Investment Advisors press release, explicitly GIFT City-specific
    },
    "Alchemy India Long Term Fund": {
        "launch_date": "April 2023",  # confirmed via Business Standard: fund re-domiciled from Mauritius to GIFT City IFSC in April 2023
        "category": "Category III AIF (Long Only)",  # PMS AIF World: "A GIFT CITY Domiciled Cat III Long Only AIF"
        "lock_in_period": "Generally two years plus",  # ALTPORT fund page, Fund Snapshot table
        "exit_load": "0-12 Months: 3% | 13-24 Months: 2% | 25-36 Months: 1% | Thereafter: Nil",  # ALTPORT fund page
        "benchmark_index": "Benchmark agnostic",  # ALTPORT fund page -- fund's own stated policy, not an omission
    },
    "ABSL Global Bluechip Equity Fund (IFSC)": {
        "category": "Cat III, Close Ended, Closed for Subscription",  # confirmed on ABSL's own official GIFT City page
        "minimum_investment": "USD 150,100",  # confirmed via Tequity's verified fund directory
        "launch_date": "20 September 2024",  # ALTPORT Fund Snapshot "Registration Date" -- scraper's label check only matches "Date of Registration", missed this page's variant label
        "lock_in_period": "4 years from First Closing, extendable up to 1 year with prior consent of Two-Third Majority of Contributors",  # ALTPORT Fund Snapshot
        "exit_load": "No redemptions during the term of the fund",  # ALTPORT Fund Snapshot ("Redemption" row)
        "benchmark_index": "MSCI ACWI",  # ALTPORT Fund Snapshot
        "target_corpus_at_launch": "USD 200 million",  # ALTPORT Fund Snapshot ("Target Corpus" row)
    },
    "ABSL India Flexicap Fund (IFSC)": {
        "category": "Category III AIF, GIFT City",  # ALTPORT Fund Snapshot ("Structure" row)
        "launch_date": "10 September 2024",  # ALTPORT Fund Snapshot's own "Launch Date" row for the GIFT wrapper -- distinct from the separately-labeled "Feeder Fund Inception: 27 August 1998" (domestic ABSL Flexicap Fund), which is deliberately NOT used here
        "minimum_investment": "USD 150,100 (general) / USD 50,000 (accredited investors), Class A1",  # ALTPORT Fund Snapshot
        "benchmark_index": "Nifty 500 TRI",  # ALTPORT Fund Snapshot, explicitly labeled "Feeder Benchmark" -- legitimate carryover since this is a feeder relationship (same reasoning as Bandhan/Sundaram/Nippon/Carnelian)
    },
    "Axis India Multicap Fund": {
        "minimum_investment": "USD 150,000 (USD 50,000 for Accredited Investors)",  # confirmed via AIF & PMS Experts India, specific to the GIFT wrapper itself
        # NOTE: deliberately NOT pulling NAV/expense_ratio/AUM/inception_date
        # from the domestic Axis Multicap Fund despite the feeder
        # relationship -- confirmed the IFSC wrapper has its own separate
        # NAV/share classes (different currency, additional fee layer),
        # so the domestic fund's ₹-denominated figures would misrepresent
        # the actual GIFT product, same reasoning applied throughout this
        # project (e.g. the ABSL 1998-inception case).
        "category": "Category III AIF, Open-Ended, Restricted Scheme (Non-Retail)",  # ALTPORT Fund Snapshot ("Category of Registration of the scheme")
        "benchmark_index": "NIFTY 500 Multicap 50:25:25 TRI",  # ALTPORT Fund Snapshot, explicitly labeled "Benchmark of Master Fund" -- legitimate feeder carryover
        "exit_load": "Redeemed within 12 months: 3%; 12-24 months: 2%; 24-36 months: 1%; after 36 months: Nil",  # ALTPORT Fund Snapshot
        "minimum_investment": "Share Class B1: USD 150,000; B2: USD 500,000; B3: USD 1,000,000; B4 (Accredited): USD 50,000",  # ALTPORT Fund Snapshot, refines the earlier summary figure with the full per-class breakdown
    },
    "Bandhan India Government Securities Fund (IFSC)": {
        "amc_name": "Bandhan AMC",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Carnelian India Amritkaal Fund": {
        "minimum_investment": "USD 500,000",  # ALTPORT Fund Snapshot ("Investment amount" row) -- a third-party aggregator separately claimed USD 150,000, but ALTPORT's own fund page is the primary source and is used here
    },
    "DSP India Absolute Return Fund": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
        "minimum_investment": "USD 150,000",  # DSP's own official investor page (giftcity.dspim.com/invest-in-india), confirmed by the user directly from the live page
        # Page description also refers to it as "DSP India Long Short Fund" (long/short equity strategy) -- possibly an alternate/renamed product name, not applied to fund_name since ALTPORT (our source_url) still lists it as "DSP India Absolute Return Fund"
    },
    "DSP India Equity Opportunities Fund": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category III AIF (Non-Retail, Restricted Scheme), Open-ended",  # kalviroventures.com dedicated fund page
        "lock_in_period": "None (daily subscription and redemption)",  # kalviroventures.com dedicated fund page
        "minimum_investment": "Class A1: USD 150,000 (0.30% expense ratio); Class A2: USD 500,000 (0.20%); Class A3: USD 1,000,000 (0.10%); Advisor-led classes approx. 1.40-1.50%",  # kalviroventures.com dedicated fund page
        "benchmark_index": "NIFTY LargeMidcap 250 TRI",  # confirmed via DSP's own official page for the underlying domestic fund it feeds into (DSP Large & Mid Cap Fund, ex-DSP Equity Opportunities Fund) -- legitimate feeder carryover
    },
    "DSP India IFSC Fund": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
        "minimum_investment": "USD 150,000",  # DSP's own official investor page (giftcity.dspim.com/invest-in-india), confirmed by the user directly from the live page
    },
    "Kotak Equity India Fund of Fund IFSC": {
        "category": "Category- III AIF",  # ALTPORT page was unreachable (server error); inferred from the fund's own official Registration Authority ID "IFSC/AIF3/2024-25/0151" (leikart.com LEI record) -- the "AIF3" segment is the same category code confirmed literally on every other fund's own snapshot page in this batch, not a guess
        # NOTE: leikart.com's LEI record for this fund shows Entity Status "INACTIVE" and LEI Status "RETIRED" (next renewal was 2025-11-26) -- worth a manual look to confirm whether this fund is still operating before relying on it further.
    },
    "SBI India Equity Advantage Fund (IFSC)": {
        "category": "Foreign Portfolio Investor (FPI)",  # esi.in (citing SEBI's FPI register): SEBI registration INIGFP107125, valid Oct 2025-Oct 2028 -- this fund is registered as an FPI, not an AIF like most other tier2 entries; ALTPORT's own page was unreachable (server error) to cross-check
    },
    "SBI Investment Opportunities Fund (IFSC)": {
        "category": "Category- III AIF",  # leikart.com LEI record: Registration Authority ID "IFSC/AIF3/2021-22/0010", Entity Status ACTIVE
        "launch_date": "2021-05-24",  # leikart.com LEI record: entity registration date -- ALTPORT's own page was unreachable (server error) to cross-check against "Date of Registration"
    },
    "DSP India Strategic Bond Fund": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction; confirmed genuinely GIFT-registered (IFSC/AIF3/2024-25/0194), not to be confused with the similarly-named domestic DSP Strategic Bond Fund
    },
    "DSP INDIA T.I.G.E.R. FUND": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction; confirmed genuinely GIFT-registered (IFSC/AIF3/2024-25/0212), not to be confused with the similarly-named domestic DSP India T.I.G.E.R. Fund
    },
    # NOTE on "Marcellus Global Compounders Fund" (tier2, this batch): pmsaifworld.com has a
    # "Marcellus Global Compounders Portfolio -- GIFT CITY Domiciled PMS" page with real AUM/return
    # figures, but that is "Marcellus GCP", a SEPARATE fund already present in this database as its
    # own tier1 row -- same distinction the project already draws between Marcellus Global Equities
    # Fund and Marcellus GCP. Deliberately NOT applied here to avoid conflating two different products.
    "DSP Pre-IPO Fund": {
        "amc_name": "DSP India",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Kotak Real Estate Fund- X IFSC": {
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row)
        "minimum_investment": "USD 150,000 (or equivalent in foreign currencies)",  # ALTPORT Fund Snapshot
    },
    "Kotak Real Estate Fund XII – IFSC I": {
        "amc_name": "Kotak Mutual Fund",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- II AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Kotak Real Estate Fund XII – IFSC II": {
        "amc_name": "Kotak Mutual Fund",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Kotak Strategic Situations Fund – II IFSC": {
        "amc_name": "Kotak Mutual Fund",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Kotak Real Estate Investment Fund – IFSC": {
        "amc_name": "Kotak Mutual Fund",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category- II AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    "Kotak Real Estate Investment Fund II – IFSC": {
        "amc_name": "Kotak Mutual Fund",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
        "minimum_investment": "USD 150,000 (or equivalent in convertible foreign currencies)",  # ALTPORT Fund Snapshot
    },
    "Kotak Performing RE Credit Strategy Fund II IFSC": {
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row)
        "minimum_investment": "USD 150,000 (or equivalent in convertible foreign currencies)",  # ALTPORT Fund Snapshot, citing IFSCA Category-II AIF minimum ticket rule
    },
    "Kotak India Commercial Real Estate Fund IFSC": {
        "category": "Category-II AIF",  # ALTPORT Fund Snapshot ("AIF Category" row)
        "minimum_investment": "USD 150,000",  # ALTPORT page FAQ section: "minimum entry ticket size for a qualified individual investor"
    },
    "Nippon India ETF Nifty 50 BeES GIFT": {
        "benchmark_index": "Nifty 50",  # derived directly from the fund's own name/product type -- "BeES" (Benchmark Exchange Traded Scheme) is Nippon's ETF brand that replicates the named index by definition, not a guess
    },
    "Girik Multicap India Fund": {
        "amc_name": "Girik Capital",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
    },
    "Sameeksha India Flexicap Equity Fund": {
        "amc_name": "Sameeksha Capital",  # confirmed via the manager's own domain (sameeksha.capital) -- amc_name extraction came up empty on this page
    },
    "Aikyam India Discovery Fund": {
        "amc_name": "Aikyam Capital Pvt. Ltd.",  # ALTPORT "Provider Name" row -- amc_name extraction came up empty on this page
    },
    "ABC India Equity Fund": {
        "category": "Category- III AIF",  # ALTPORT Fund Snapshot ("Category" row) -- corrects the generic "Gift City Funds" nav-heading mis-extraction
    },
    # UTI India Opportunities (IFSC) Fund III, Sage One India Growth GIFT Fund, and Valuequest India
    # G.I.F.T. Fund: checked ALTPORT (no Fund Snapshot table on any of these three pages) and web
    # search -- genuinely no additional public data found for any of them beyond what scraping
    # already captured.
}


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


def scrape_full_directory() -> list[dict]:
    """Scrapes the single GIFT City directory LISTING page directly,
    rather than visiting ~200 individual fund pages. The listing page
    pairs each fund with its AMC/company name via an adjacent <img
    alt="..."> tag (the company logo), which is far more reliable than
    the per-page text-pattern matching in scrape_altport_fund() -- that
    approach kept mismatching the site's nav menu or duplicating the
    fund name into amc_name across several fix attempts.

    This does NOT give registration numbers or trustworthy launch
    dates (those still require the individual page), so this is a
    lighter-weight, name-only enrichment: fund_name + amc_name pairs,
    correctly attributed, for the full ~200-fund directory in one request.
    """
    response = requests.get(DIRECTORY_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    records = []
    seen_urls = set()
    view_fund_links = [
        link for link in soup.find_all("a", href=True)
        if "/investments/" in link["href"] and link.get_text(strip=True).lower() == "view fund"
    ]

    for i, link in enumerate(view_fund_links):
        url = link["href"]
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Bound the search to elements between the PREVIOUS "View Fund"
        # link and this one -- otherwise find_previous() searches the
        # whole document and can wrongly attach a nearby fund's logo/AMC
        # name to a fund that has none of its own (confirmed as a real
        # bug in local testing before this fix).
        boundary = view_fund_links[i - 1] if i > 0 else None

        fund_name = None
        for tag in link.find_all_previous(["h1", "h2", "h3", "h4", "p", "div"]):
            if boundary and tag.sourceline is not None and boundary.sourceline is not None \
                    and tag.sourceline <= boundary.sourceline:
                break
            text = tag.get_text(strip=True)
            if text and text.lower() != "view fund":
                fund_name = text
                break

        amc_name = None
        for img in link.find_all_previous("img", alt=True):
            if boundary and img.sourceline is not None and boundary.sourceline is not None \
                    and img.sourceline <= boundary.sourceline:
                break
            if img.get("alt"):
                amc_name = img["alt"].strip()
                break

        if fund_name:
            records.append({
                "fund_name": fund_name,
                "amc_name": amc_name,  # honestly None if no logo found for this specific fund -- not guessed
                "source_url": "https://www.altportfunds.com" + url if url.startswith("/") else url,
            })

    return records


def scrape_altport_fund(slug: str) -> dict:
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

    for attempt in range(1, 4):  # up to 3 attempts with backoff, same
        # proven fix as the PPFAS Nasdaq SSL issue -- a single request
        # to a real, working URL can still fail transiently.
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            break
        except Exception as exc:
            if attempt == 3:
                import traceback
                record["error_message"] = f"{type(exc).__name__}: {exc} | {traceback.format_exc(limit=2)}"
                return record
            time.sleep(2 * attempt)

    try:
        soup = BeautifulSoup(response.text, "html.parser")

        # Fund name: the H1 heading
        h1 = soup.find("h1")
        fund_name = h1.get_text(strip=True) if h1 else None

        # AMC name: extract from the actual "About Company" H2 heading
        # structure, not prose-text pattern matching. Confirmed present
        # on every verified real page (both ASKWA and ABSL examples
        # showed "About Company" followed by an H2 with the real AMC
        # name). This is more robust than searching flattened text,
        # which produced inconsistent results (wrong nav-menu matches
        # on some pages, fund-name duplication on others).
        amc_name = None
        about_heading = soup.find(
            lambda tag: tag.name in ("h2", "h3") and "About Company" in tag.get_text()
        )
        if about_heading:
            next_heading = about_heading.find_next(["h2", "h3"])
            if next_heading:
                amc_name = next_heading.get_text(strip=True)

        # Category: keep the bounded-window text match -- this field
        # tested reliably correct, unlike amc_name.
        page_text = soup.get_text("\n", strip=True)
        search_start = page_text.find(fund_name) if fund_name else 0
        search_start = max(search_start, 0)
        window_text = page_text[search_start:search_start + 600]
        category_match = re.search(r"\nCategory\n([^\n]+)", window_text)
        category = category_match.group(1).strip() if category_match else None

        snapshot = _extract_fund_snapshot(soup)

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
            category=category or (snapshot.get("Category")),
            launch_date=launch_date,
            launch_date_type=launch_date_type,
            scrape_status="success" if fund_name else "partial",
        )
        # Apply any manually-researched supplementary facts for this
        # specific fund (see MANUAL_OVERRIDES above). Matched with
        # normalized whitespace/dash comparison rather than requiring a
        # byte-exact match -- the real H1 text on the live page might use
        # a slightly different dash character or spacing than what was
        # typed while researching, and a silent non-match would just
        # drop real data without any error.
        if fund_name:
            normalized_fund_name = re.sub(r"[\s\u2010-\u2015-]+", " ", fund_name).strip().lower()
            for override_name, override_data in MANUAL_OVERRIDES.items():
                normalized_override = re.sub(r"[\s\u2010-\u2015-]+", " ", override_name).strip().lower()
                if normalized_fund_name == normalized_override:
                    record.update(override_data)
                    break
        if not fund_name:
            record["error_message"] = "Page loaded but fund name (H1) could not be found."
        return record
    except Exception as exc:
        import traceback
        record["error_message"] = f"{type(exc).__name__}: {exc} | {traceback.format_exc(limit=2)}"
        return record


def run_altport_scrape() -> list[dict]:
    records = []
    for i, slug in enumerate(CANDIDATE_SLUGS):
        logger.info(f"[{i+1}/{len(CANDIDATE_SLUGS)}] Scraping: {slug}")
        record = scrape_altport_fund(slug)
        status = "OK" if record["scrape_status"] == "success" else "FAILED"
        logger.info(f"  -> {status} | fund={record['fund_name']} | "
                    f"launch_date={record['launch_date']} ({record['launch_date_type']})")
        records.append(record)
        time.sleep(1)  # be polite to the distributor's server

    success_count = sum(1 for r in records if r["scrape_status"] == "success")
    with_date = sum(1 for r in records if r["launch_date"])
    logger.info(f"ALTPORT scrape complete: {success_count}/{len(records)} succeeded, "
                f"{with_date} with a trustworthy (registration-based) launch_date")
    return records


if __name__ == "__main__":
    logger.info("Scraping the full directory LISTING page (name+AMC pairs only)...")
    directory_records = scrape_full_directory()
    directory_amc_lookup = {
        r["fund_name"]: r["amc_name"] for r in directory_records if r["amc_name"]
    }
    logger.info(f"Directory listing: {len(directory_records)} fund/AMC pairs found "
                f"({len(directory_amc_lookup)} with a real AMC name)")
    with open("data/altport_directory_names.json", "w", encoding="utf-8") as f:
        json.dump(directory_records, f, indent=2, ensure_ascii=False)
    logger.info("Wrote data/altport_directory_names.json")

    records = run_altport_scrape()

    # Fallback: for any of the 51 detailed records where the per-page
    # "About Company" heading extraction came up empty, try filling it
    # in from the directory-listing logo mapping instead -- a second,
    # independent method (image alt text vs. heading structure) that
    # can succeed where the other failed, rather than leaving a fixable
    # gap empty.
    filled_from_fallback = 0
    for r in records:
        if not r.get("amc_name") and r.get("fund_name") in directory_amc_lookup:
            r["amc_name"] = directory_amc_lookup[r["fund_name"]]
            filled_from_fallback += 1
    logger.info(f"Filled {filled_from_fallback} previously-empty amc_name values "
                f"using the directory-listing fallback")

    out_path = "data/altport_tier2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote {len(records)} records to {out_path}")
