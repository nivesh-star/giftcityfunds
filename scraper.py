"""
scraper.py
Production-grade scraper for GIFT City fund data.

Sources:
  - thefynprint.com/gift-city-inbound  (JS-rendered React app)
  - thefynprint.com/gift-city-outbound (JS-rendered React app)
  - Individual AMC fund detail pages (e.g. gift.ppfas.com)

Design notes:
  - Playwright is required (not requests/BeautifulSoup) because the tracker
    pages render fund data client-side via JavaScript.
  - The tracker markup is a Tailwind CSS div-grid, not a semantic <table>.
    Confirmed via DevTools: rows live under
    `#gift-city-fund-list div.space-y-3.md\\:space-y-0`.
  - Selectors are tried in priority order (most specific -> most generic)
    and the scraper logs exactly which strategy succeeded/failed, so a
    site redesign produces a clear, diagnosable failure rather than a
    silent empty result.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    sync_playwright,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ScraperConfig:
    tracker_urls: dict = field(default_factory=lambda: {
        "inbound": "https://thefynprint.com/gift-city-inbound",
        "outbound": "https://thefynprint.com/gift-city-outbound",
    })
    fund_detail_urls: tuple = (
        "https://gift.ppfas.com/product/inbound/parag_parikh_india_flexicap_fund/",
        "https://giftcity.dspim.com/product",
        "https://giftcity.miraeassetmf.co.in/mirae-asset-global-allocation-fund.html",
        # Each URL above corresponds to a fund actually present in my
        # scraped tracker data (PPFAS, DSP, Mirae Asset) -- chosen
        # deliberately, not padded for count. See README for rationale.
    )
    output_dir: Path = Path("data")
    log_dir: Path = Path("logs")
    page_timeout_ms: int = 30_000
    selector_timeout_ms: int = 15_000
    max_retries: int = 3
    retry_backoff_base_s: float = 2.0  # exponential: 2s, 4s, 8s
    polite_delay_s: float = 1.0
    headless: bool = True


CONFIG = ScraperConfig()

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("gift_city_scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_dir / "scraper.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging(CONFIG.log_dir)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Retry helper
# --------------------------------------------------------------------------

def with_retries(func, *args, max_retries=CONFIG.max_retries, label="operation", **kwargs):
    """Runs func with exponential backoff retries. Raises the last exception
    if all attempts fail, so the caller can log a definitive audit failure."""
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (PlaywrightTimeoutError, Exception) as e:
            last_exc = e
            wait = CONFIG.retry_backoff_base_s * (2 ** (attempt - 1))
            if attempt < max_retries:
                logger.warning(
                    f"{label} failed (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {wait:.0f}s..."
                )
                time.sleep(wait)
            else:
                logger.warning(
                    f"{label} failed (attempt {attempt}/{max_retries}): {e}. Giving up."
                )
    raise last_exc


# --------------------------------------------------------------------------
# Tracker page scraping
# --------------------------------------------------------------------------

# Known section header labels on the tracker pages.
SECTION_LABELS = ["RETAIL FUNDS", "INSTITUTIONAL & HNI FUNDS", "K1 COMPLIANT FUNDS", "NON-K1 FUNDS"]

# Row container candidates, in priority order (most specific/confirmed first).
# NOTE: inbound and outbound use DIFFERENT container IDs (confirmed via
# DevTools) -- inbound tracks fund HOUSES (name/strategy/min-ticket/K1),
# outbound tracks individual funds with performance data (type/strategy/
# 3M/6M/since-inception returns/benchmark). They are parsed with separate
# functions below rather than forced into one shared shape.
ROW_CONTAINER_SELECTORS = [
    "#gift-city-fund-list div.space-y-3.md\\:space-y-0 > div",  # inbound, confirmed via DevTools
    "#gift-city-fund-list div.space-y-3 > div",                  # inbound fallback: relaxed responsive modifier
    "#gift-city-fund-list [class*='space-y'] > div",             # inbound fallback: any space-y wrapper
    "table tr",                                                   # fallback: in case markup changes to a real table
]

# Outbound-specific: section blocks are tagged with data-category, and each
# section's rows live in a nested div.space-y-3 wrapper (confirmed via DevTools).
OUTBOUND_ROW_SELECTOR = "#outbound-fund-list [data-category] div.space-y-3 > div.bg-white"


def _extract_rows(page: Page) -> list[dict]:
    """Tries each row-container selector strategy until one yields rows.
    Logs which strategy was used (or that all failed) for diagnosability."""
    for selector in ROW_CONTAINER_SELECTORS:
        try:
            locator = page.locator(selector)
            count = locator.count()
        except Exception as e:
            logger.debug(f"Selector strategy failed to evaluate: {selector} ({e})")
            continue

        if count > 0:
            logger.info(f"Row extraction strategy succeeded: '{selector}' ({count} elements)")
            return _parse_rows(locator, count)

        logger.debug(f"Row extraction strategy yielded 0 elements: '{selector}'")

    logger.error("All row extraction strategies failed -- 0 elements found by any selector.")
    return []


def _parse_rows(locator, count: int) -> list[dict]:
    records = []
    current_section: Optional[str] = None
    seen_fund_houses: set[str] = set()

    for i in range(count):
        el = locator.nth(i)
        try:
            text = el.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        upper_text = text.upper()
        if any(label in upper_text for label in SECTION_LABELS) and "$" not in text:
            current_section = text.strip()
            continue

        # A fund row is expected to contain a "$" (min ticket amount).
        if "$" not in text:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        fund_house = lines[0] if lines else None
        if not fund_house or fund_house in seen_fund_houses:
            continue

        strategy = lines[1] if len(lines) > 1 else None
        min_ticket = next((l for l in lines if "$" in l), None)
        k1_status = next(
            (l for l in lines if "K1" in l.upper() or l.strip().upper() == "NO"), None
        )

        # Validation guard: a real row's min_ticket looks like a clean
        # dollar amount (e.g. "$500", "$150,000"). Rows where this doesn't
        # hold are duplicate/garbage elements picked up by the selector
        # (e.g. tooltip/expand content bundled with a row) -- discard them
        # rather than passing corrupted data downstream.
        if not min_ticket or not re.match(r"^\$[\d,]+$", min_ticket.strip()):
            logger.warning(f"  [inbound] discarding malformed row (bad min_ticket): {fund_house[:60]!r}")
            continue

        seen_fund_houses.add(fund_house)

        records.append({
            "fund_house": fund_house,
            "investment_strategy": strategy,
            "min_ticket_raw": min_ticket,
            "k1_status_raw": k1_status,
            "section": current_section,
            "raw_text": text,  # kept for cleaner.py to re-parse if field splitting above is imperfect
        })

    return records


def _parse_outbound_rows(page: Page) -> list[dict]:
    """Outbound rows carry performance data (3M/6M/Since inception returns,
    benchmark) rather than inbound's min-ticket/K1 fields. The page renders
    a desktop layout AND a separate mobile card layout for the same data
    (responsive design), so a naive full-row inner_text() would capture
    every value twice. Regex .search() naturally takes the first match,
    which sidesteps the duplication without needing to pick apart which
    responsive layout is "active"."""
    import re

    records = []
    seen_funds: set[str] = set()

    # Section wrappers: data-category div and the space-y-3 row container
    # are SIBLINGS under a shared unlabeled parent div (confirmed via
    # DevTools) -- NOT nested inside each other. So I iterate the shared
    # parents, then pull the category attribute and rows separately from
    # within each.
    section_parents = page.locator("#outbound-fund-list > div")
    section_count = section_parents.count()
    logger.info(f"  [outbound debug] section parent blocks found: {section_count}")

    for s in range(section_count):
        parent_el = section_parents.nth(s)

        category_el = parent_el.locator("[data-category]")
        try:
            category = category_el.first.get_attribute("data-category") if category_el.count() > 0 else None
        except Exception:
            category = None

        rows = parent_el.locator("div.space-y-3 > div.bg-white")
        row_count = rows.count()
        logger.info(f"  [outbound debug] section='{category}' rows found: {row_count}")

        for i in range(row_count):
            row = rows.nth(i)
            try:
                text = row.inner_text().strip()
            except Exception:
                continue
            if not text:
                continue

            fund_name_match = re.search(r"^([A-Za-z0-9 &\-\.'()]+?)\n", text)
            fund_name = fund_name_match.group(1).strip() if fund_name_match else None
            if not fund_name:
                logger.warning(f"  [outbound debug] fund name regex failed on row text: {text[:120]!r}")
                continue
            if fund_name in seen_funds:
                continue
            seen_funds.add(fund_name)

            # Return values appear positionally (3M, then 6M, then Since
            # Inception), NOT preceded by a "3M"/"6M" label in this
            # rendering -- confirmed from real raw_text: e.g.
            # "...agnostic\n\n1.80%\n-3.20%\n\u2014\nvs World Index...".
            # A missing/unavailable value renders as an em-dash "\u2014".
            # Match the block of exactly 3 consecutive value lines that
            # sits right before "\nvs <benchmark>".
            metrics_match = re.search(
                r"\n\n([+-]?\d+\.?\d*%|\u2014)\n([+-]?\d+\.?\d*%|\u2014)\n([+-]?\d+\.?\d*%|\u2014)\nvs\s+([A-Za-z0-9 ]+)",
                text,
            )
            if metrics_match:
                return_3m, return_6m, return_since_inception, benchmark = metrics_match.groups()
            else:
                return_3m = return_6m = return_since_inception = benchmark = None
                logger.warning(f"  [outbound debug] metrics regex failed on '{fund_name}': {text[:150]!r}")

            records.append({
                "fund_name": fund_name,
                "data_category": category,
                "return_3m_raw": return_3m,
                "return_6m_raw": return_6m,
                "return_since_inception_raw": return_since_inception,
                "benchmark": benchmark.strip() if benchmark else None,
                "raw_text": text,
            })

    return records


def scrape_tracker_page(page: Page, direction: str, url: str) -> tuple[list[dict], dict]:
    audit = {
        "url": url,
        "http_status": None,
        "success": False,
        "error_message": None,
        "scraped_at": _now_iso(),
    }

    # Inbound and outbound use different container IDs and data shapes
    # (confirmed via DevTools) -- route to the matching wait-condition and
    # parser rather than forcing one shared code path.
    container_id = "gift-city-fund-list" if direction == "inbound" else "outbound-fund-list"

    def _load_and_extract():
        response = page.goto(url, wait_until="networkidle", timeout=CONFIG.page_timeout_ms)
        audit["http_status"] = response.status if response else None

        # Wait for the actual fund-list container to be attached, then poll
        # until it has children -- this avoids guessing page-specific copy
        # (e.g. "10 fund houses" on inbound may read differently on
        # outbound). Waiting on real DOM content is more robust than
        # waiting on text that can vary page-to-page.
        page.wait_for_selector(f"#{container_id}", timeout=CONFIG.selector_timeout_ms)
        page.wait_for_function(
            f"document.querySelector('#{container_id}')?.children?.length > 0",
            timeout=CONFIG.selector_timeout_ms,
        )
        page.wait_for_timeout(500)  # settle time for any lazy-loaded rows

        if direction == "outbound":
            return _parse_outbound_rows(page)
        return _extract_rows(page)

    try:
        records = with_retries(_load_and_extract, label=f"scrape_tracker_page({direction})")
        for r in records:
            r["direction"] = direction
            r["source_url"] = url
            r["scraped_at"] = _now_iso()
        audit["success"] = len(records) > 0
        if not records:
            audit["error_message"] = "0 rows extracted after all retries and selector strategies."
        return records, audit
    except Exception as e:
        audit["error_message"] = str(e)
        return [], audit


# --------------------------------------------------------------------------
# Fund detail page scraping
# --------------------------------------------------------------------------

def scrape_fund_detail_page(page: Page, url: str) -> tuple[dict, dict]:
    import re

    audit = {
        "url": url,
        "http_status": None,
        "success": False,
        "error_message": None,
        "scraped_at": _now_iso(),
    }
    record = {
        "source_url": url,
        "nav": None,
        "expense_ratio": None,
        "aum_crores": None,
        "min_investment": None,
        "inception_date": None,
        "fund_status": None,
        "scraped_at": _now_iso(),
    }

    def _load_and_extract():
        response = page.goto(url, wait_until="networkidle", timeout=CONFIG.page_timeout_ms)
        audit["http_status"] = response.status if response else None
        page.wait_for_timeout(500)
        return page.inner_text("body")

    try:
        body_text = with_retries(_load_and_extract, label=f"scrape_fund_detail({url})")

        if "coming soon" in body_text.lower():
            record["fund_status"] = "Coming Soon"
        else:
            record["fund_status"] = "Live"

        def find_after_label(patterns, max_gap=30):
            for pat in patterns:
                # Two real bugs fixed here:
                # 1. [\d,]+ wrongly matched a lone "," with zero actual
                #    digits (found on the PPFAS page -- nav came back as
                #    just ","). Fixed by requiring the match to START
                #    with a real digit: \d[\d,]*\.?\d*
                # 2. Open-ended \D*? let the regex wander arbitrarily far
                #    past the label and grab an unrelated number if the
                #    label word appeared again in unrelated prose
                #    elsewhere on the page (found "aum_crores": "1,000,000"
                #    on DSP's page, and "nav": "90" on Mirae's -- neither
                #    matches anything real on those pages). Fixed by
                #    bounding the gap to `max_gap` characters.
                m = re.search(
                    pat + rf".{{0,{max_gap}}}?(\d[\d,]*\.?\d*)",
                    body_text, re.IGNORECASE | re.DOTALL,
                )
                if m:
                    return m.group(1)
            return None

        record["nav"] = find_after_label([r"Subscription NAV", r"NAV"])
        record["expense_ratio"] = find_after_label([r"Expense Ratio"])
        record["min_investment"] = find_after_label([r"Min\. Investment", r"Minimum Investment"])
        # aum_crores deliberately NOT extracted via regex: verified against
        # the live DSP page that "AUM" only appears in unrelated FAQ/tax
        # copy, not as a clean labeled figure -- a regex match here would
        # be a guess dressed up as data. Left as None; documented in
        # README as genuinely unavailable from these source pages rather
        # than a scraping failure.
        record["aum_crores"] = None

        date_match = re.search(
            r"Inception Date[:\s]+([A-Za-z0-9,\s/-]+)", body_text, re.IGNORECASE
        )
        if date_match:
            record["inception_date"] = date_match.group(1).strip()

        audit["success"] = True
        return record, audit

    except Exception as e:
        audit["error_message"] = str(e)
        return record, audit


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def run_scrape(config: ScraperConfig = CONFIG) -> dict:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    all_audits: list[dict] = []
    detail_records: list[dict] = []

    run_started = _now_iso()
    logger.info(f"=== Scrape run started at {run_started} ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        page = browser.new_page()

        for direction, url in config.tracker_urls.items():
            logger.info(f"Scraping tracker [{direction}]: {url}")
            records, audit = scrape_tracker_page(page, direction, url)
            all_records.extend(records)
            all_audits.append(audit)
            logger.info(f"  -> {len(records)} fund rows | success={audit['success']}")
            time.sleep(config.polite_delay_s)

        for url in config.fund_detail_urls:
            logger.info(f"Scraping fund detail: {url}")
            record, audit = scrape_fund_detail_page(page, url)
            detail_records.append(record)
            all_audits.append(audit)
            logger.info(f"  -> success={audit['success']} | status={record.get('fund_status')}")
            time.sleep(config.polite_delay_s)

        browser.close()

    # Write outputs
    tracker_path = config.output_dir / "raw_tracker_data.json"
    detail_path = config.output_dir / "raw_fund_details.json"
    audit_path = config.log_dir / "scrape_audit.log"

    tracker_path.write_text(json.dumps(all_records, indent=2))
    detail_path.write_text(json.dumps(detail_records, indent=2))
    with open(audit_path, "w") as f:
        for a in all_audits:
            f.write(json.dumps(a) + "\n")

    success_count = sum(1 for a in all_audits if a["success"])
    logger.info(
        f"=== Scrape run finished. {len(all_records)} tracker rows, "
        f"{len(detail_records)} detail pages, "
        f"{success_count}/{len(all_audits)} audit entries successful ==="
    )

    return {
        "records": all_records,
        "detail_records": detail_records,
        "audits": all_audits,
    }


if __name__ == "__main__":
    run_scrape()
