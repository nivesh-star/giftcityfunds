"""PPFAS Global Investing Strategy PMS — GIFT City PMS factsheet parser.

The primary PDF on thefynprint.com is a 27-page marketing pitch deck with no
portfolio data. The AMC publishes separate monthly factsheets at gift.ppfas.com,
downloaded by download_factsheets._download_ppfas_pms_factsheet() and saved as
PPFAS_PPGIS_Factsheet.pdf alongside the pitch deck.

When the monthly factsheet is present this parser extracts:
  - Performance (SI, 1M, 3M vs S&P 500 benchmark)
  - Portfolio allocation (Equity %, Cash %)
  - Top-10 holding names (no individual weights — shown as chart in PDF)

When it is absent (no internet / download failed), fund metadata is returned from
the pitch deck text with empty performance/holdings.
"""
from __future__ import annotations
import calendar
import logging
import re
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "PPFAS_Global_Investing_Strategy_PMS.pdf"
MONTHLY_FACTSHEET_FILENAME = "PPFAS_PPGIS_Factsheet.pdf"

_BENCH = "S&P 500 Net Total Return Index"
_PERIOD_MAP = {
    "since inception": "SI",
    "last 1 month": "1M",
    "last 3 months": "3M",
    "last 6 months": "6M",
    "last 1 year": "1Y",
}


def _parse_monthly_factsheet(pdf_path: Path) -> tuple[
    date | None, list[PerformanceRow], list[Holding], list[Allocation]
]:
    """Read the PPFAS PPGIS monthly factsheet and return (as_of, performance, holdings, allocations)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = [pg.extract_text() or "" for pg in reader.pages]
    full_text = "\n".join(pages)

    # ── As-of date ────────────────────────────────────────────────────────────
    # "Factsheet - November, 2025"
    date_m = re.search(r"Factsheet\s*[-–]\s*(\w+),?\s*(\d{4})", full_text, re.IGNORECASE)
    as_of: date | None = None
    if date_m:
        month_name = date_m.group(1)
        year = int(date_m.group(2))
        month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
        mo = month_map.get(month_name.lower())
        if mo:
            last_day = calendar.monthrange(year, mo)[1]
            as_of = date(year, mo, last_day)

    # ── Performance ───────────────────────────────────────────────────────────
    # "Since Inception (August 27, 2025) 4.45% 6.16%"
    # "Last 1 Month 0.14% 0.03%"
    performance: list[PerformanceRow] = []
    perf_block_m = re.search(r"PPGIS Performance(.*?)(?:Investment Team|Registered)", full_text, re.DOTALL | re.IGNORECASE)
    if perf_block_m:
        block = perf_block_m.group(1)
        for pattern, period in _PERIOD_MAP.items():
            m = re.search(
                rf"{re.escape(pattern)}.*?([-\d\.]+)%\s+([-\d\.]+)%",
                block, re.IGNORECASE | re.DOTALL,
            )
            if m:
                fr, br = float(m.group(1)), float(m.group(2))
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=(period in {"SI", "1Y"}),
                ))

    # ── Portfolio allocations (equity / cash) ─────────────────────────────────
    allocations: list[Allocation] = []
    for label, alloc_type in [
        (r"Equity\s*&?\s*related\s+Instrument", "Equity"),
        (r"Cash\s*&?\s*Equivalents?", "Cash"),
    ]:
        m = re.search(rf"{label}\s+([\d\.]+)%", full_text, re.IGNORECASE)
        if m:
            allocations.append(Allocation(
                allocation_type="Asset Class",
                category=alloc_type,
                weight_pct=float(m.group(1)),
                as_of_date=as_of,
            ))

    # ── Holdings (names only — weights are in a chart image) ──────────────────
    # Names appear after the last "Note" paragraph and before "Disclaimer".
    # Layout: Top 10 header → *date → Note1 → *date → Note2 → [names] → Disclaimer
    holdings: list[Holding] = []
    disc_m = re.search(r"Disclaimer", full_text, re.IGNORECASE)
    if disc_m:
        before_disc = full_text[:disc_m.start()]
        # Find all lines at the end of the block that look like company names
        lines = [l.strip() for l in before_disc.split("\n") if l.strip()]
        name_lines: list[str] = []
        for line in reversed(lines):
            if re.match(r"^[A-Z][A-Za-z\s&\.]+$", line) and len(line) > 2:
                name_lines.insert(0, line)
            elif name_lines:
                break  # stop once we hit a non-name line after accumulating names
        for name in name_lines:
            holdings.append(Holding(
                holding_name=name,
                weight_pct=None,  # individual weights not disclosed (chart only)
                holding_type="Equity",
                as_of_date=as_of,
            ))

    return as_of, performance, holdings, allocations


class PPFASGlobalPMSParser(BaseGiftCityParser):
    FUND_NAME = "Parag Parikh Global Investing Strategy (PMS)"
    AMC_NAME = "PPFAS"
    FUND_TYPE = "PMS"
    STRUCTURE = "Discretionary"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text
        as_of = date.today().replace(day=1) - timedelta(days=1)  # last day of prev month; overwritten if monthly factsheet found

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index=_BENCH,
            fund_manager="Akshay Falgunia",
            min_investment_usd=75_000.0,
            exit_load_pct=0.0,
            lock_in_months=0,
            ltcg_tax_pct=12.5,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        min_m = re.search(r"Minimum (?:Ticket|Investment)\s*Size\s*US\$\s*([\d,]+)", text, re.IGNORECASE)
        if min_m:
            fund_info.min_investment_usd = float(min_m.group(1).replace(",", ""))

        share_classes = [
            ShareClass(
                class_name="Standard",
                investor_type="Resident Individual",
                min_investment_usd=75_000.0,
                management_fee_pct=None,
                exit_load_pct=0.0,
                lock_in_months=0,
            )
        ]

        # ── Try to read the monthly factsheet for real data ───────────────────
        monthly_path = self.pdf_path.parent / MONTHLY_FACTSHEET_FILENAME
        performance: list[PerformanceRow] = []
        holdings: list[Holding] = []
        allocations: list[Allocation] = []

        if monthly_path.exists():
            try:
                monthly_as_of, performance, holdings, allocations = _parse_monthly_factsheet(monthly_path)
                if monthly_as_of:
                    as_of = monthly_as_of
                    fund_info.factsheet_date = as_of
                fund_info.factsheet_path = str(monthly_path)
            except Exception as exc:
                logger.warning("PPFAS PPGIS: failed to parse monthly factsheet: %s", exc)

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            holdings=holdings,
            allocations=allocations,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = PPFASGlobalPMSParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    fi = result.fund_info
    print(f"Fund: {fi.fund_name}  as of {fi.factsheet_date}")
    print(f"Holdings ({len(result.holdings)}): {[h.holding_name for h in result.holdings]}")
    print(f"Performance ({len(result.performance)}):")
    for r in result.performance:
        print(f"  {r.period}: {r.fund_return_pct}% vs {r.benchmark_return_pct}%")
    print(f"Allocations ({len(result.allocations)}):")
    for a in result.allocations:
        print(f"  {a.category}: {a.weight_pct}%")
