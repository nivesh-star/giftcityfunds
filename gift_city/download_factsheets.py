"""
Download GIFT City outbound fund factsheets from thefynprint.com.

Scrapes the page with Playwright to find Google Drive links, then downloads
each PDF. Safe to re-run — skips files that already exist and are > 10 KB.

Usage:
    python3 -m gift_city.download_factsheets
    python3 -m gift_city.download_factsheets --out-dir /tmp/gift_city_factsheets
"""
from __future__ import annotations
import argparse
import logging
import json
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

SOURCE_URL = "https://thefynprint.com/gift-city-outbound"
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "gift_city_factsheets"


def _scrape_links() -> list[tuple[str, str]]:
    """Return [(fund_name, google_drive_url), ...] by rendering the page with Playwright."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SOURCE_URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3_000)

        results = page.evaluate("""() => {
            const seen = new Set();
            const out = [];
            for (const link of document.querySelectorAll('a[href*="drive.google.com"]')) {
                if (seen.has(link.href)) continue;
                seen.add(link.href);
                let name = '';
                let el = link;
                for (let i = 0; i < 10; i++) {
                    el = el.parentElement;
                    if (!el) break;
                    const h = el.querySelector('h1,h2,h3,h4,h5,h6,[class*="name"],[class*="title"],[class*="fund"]');
                    if (h) { name = h.textContent.trim(); break; }
                }
                out.push([name || 'Unknown', link.href]);
            }
            return out;
        }""")

        browser.close()
    return results


def _file_id(drive_url: str) -> str | None:
    m = re.search(r"/file/d/([a-zA-Z0-9_\-]+)", drive_url)
    return m.group(1) if m else None


def _safe_filename(fund_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 &]+", "", fund_name).replace(" ", "_") + ".pdf"


def _download_one(session: requests.Session, file_id: str, dest: Path) -> bool:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(url, allow_redirects=True, timeout=60)

    # Large files return an HTML warning page instead of the PDF.
    # Detect by Content-Type (not by body text, which is unreliable).
    if "text/html" in resp.headers.get("Content-Type", ""):
        resp = session.get(f"{url}&confirm=t", allow_redirects=True, timeout=60)

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type or len(resp.content) < 10_000:
        logger.warning(
            "  %s: got %s (%d B) — Drive may be blocking download",
            dest.name, content_type, len(resp.content),
        )
        return False

    dest.write_bytes(resp.content)
    logger.info("  %s  (%.0f KB)", dest.name, len(resp.content) / 1024)
    return True


def _download_ppfas_pms_factsheet(out_dir: Path) -> Path | None:
    """Download the most recent PPFAS PPGIS monthly factsheet from gift.ppfas.com.

    The pitch deck (downloaded from thefynprint.com) has no performance data.
    The AMC publishes monthly factsheets at a predictable URL pattern.
    Tries the past 8 months and saves the most recent accessible one.
    """
    import calendar
    from datetime import date

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    session.headers["Referer"] = "https://gift.ppfas.com/"
    try:
        session.get("https://gift.ppfas.com/", timeout=15)
    except Exception:
        pass

    dest = out_dir / "PPFAS_PPGIS_Factsheet.pdf"
    today = date.today()

    for months_back in range(1, 9):
        yr = today.year
        mo = today.month - months_back
        while mo <= 0:
            mo += 12
            yr -= 1
        month_abbr = calendar.month_abbr[mo].lower()
        url = f"https://gift.ppfas.com/factsheet/{yr}/factsheet-{month_abbr}-{yr}.pdf"
        try:
            resp = session.get(url, timeout=20)
            ct = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and "pdf" in ct.lower() and len(resp.content) > 10_000:
                dest.write_bytes(resp.content)
                logger.info("PPFAS PPGIS monthly factsheet: %s → %s", url, dest.name)
                return dest
        except Exception as exc:
            logger.debug("PPFAS PPGIS factsheet attempt %s: %s", url, exc)

    logger.warning("PPFAS PPGIS: no accessible monthly factsheet found (last 8 months tried)")
    return None


def download_all(out_dir: Path = DEFAULT_OUT_DIR) -> list[Path]:
    """Scrape page, download all factsheets, return list of saved paths.

    Also writes out_dir/urls.json mapping each filename to its Google Drive URL
    so load_to_db.py can store the canonical source URL in the database.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Scraping %s …", SOURCE_URL)

    links = _scrape_links()
    logger.info("Found %d factsheet links", len(links))

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    saved: list[Path] = []
    url_map: dict[str, str] = {}

    for fund_name, drive_url in links:
        fid = _file_id(drive_url)
        if not fid:
            logger.warning("Could not parse file ID from %s", drive_url)
            continue

        dest = out_dir / _safe_filename(fund_name)
        url_map[dest.name] = drive_url

        if dest.exists() and dest.stat().st_size > 10_000:
            logger.info("  %s already exists — skipping", dest.name)
            saved.append(dest)
            continue

        logger.info("Downloading: %s", fund_name)
        try:
            if _download_one(session, fid, dest):
                saved.append(dest)
        except Exception as exc:
            logger.warning("  Failed: %s", exc)

        time.sleep(0.5)

    # Supplemental: PPFAS PPGIS monthly factsheet (not on thefynprint.com)
    ppfas_fs = _download_ppfas_pms_factsheet(out_dir)
    if ppfas_fs:
        saved.append(ppfas_fs)
        url_map[ppfas_fs.name] = "https://gift.ppfas.com/factsheet/"

    # Write sidecar so load_to_db can record where each PDF came from
    sidecar = out_dir / "urls.json"
    sidecar.write_text(json.dumps(url_map, indent=2))
    logger.info("Wrote URL map → %s", sidecar)

    logger.info("Downloaded %d factsheets to %s", len(saved), out_dir)
    return saved


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download GIFT City factsheets")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    download_all(args.out_dir)


if __name__ == "__main__":
    main()
