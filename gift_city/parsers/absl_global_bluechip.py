"""ABSL Global Bluechip Equity Fund (IFSC) — GIFT City AIF Cat III Close-ended parser.

Holdings, country exposure, and performance are extracted from PDF text on pages 25 and 27.
Share class fee structure is stable for the fund's 4-year closed-end tenure (Apr 2025–Apr 2029).
"""
from __future__ import annotations
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, RiskMetrics, ParsedFactsheet,
)

FACTSHEET_FILENAME = "ABSL_Global_Bluechip_Equity_Fund.pdf"

# Fee tiers — stable for the full 4-year closed-end tenure; no need to re-parse monthly
_SHARE_CLASSES = [
    ("A1", "Resident Individual/Entity",  150_100,  249_999, 1.50),
    ("A2", "Resident Individual/Entity",  250_000,  999_999, 1.25),
    ("A3", "Resident Individual/Entity", 1_000_000,    None, 1.00),
    ("A4", "Accredited Resident",          75_000,     None, 1.75),
    ("B1", "NRI/Foreign National",        150_100,  249_999, 1.50),
    ("B2", "NRI/Foreign National",        250_000,  999_999, 1.25),
    ("B3", "NRI/Foreign National",       1_000_000,   None, 1.00),
    ("B4", "Accredited NRI",               75_000,    None, 1.75),
]


def _strip_ordinal(s: str) -> str:
    return re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)


def _parse_holdings(page_text: str) -> list[tuple[str, float]]:
    """Parse the top-10 holdings table from page 25 text.

    Handles multi-line company names (e.g. Taiwan Semiconductor spans two lines).
    """
    sec_m = re.search(
        r"Company Name Net Assets\(%\)(.*?)Country Exposure", page_text, re.DOTALL
    )
    if not sec_m:
        return []
    lines = [l.strip() for l in sec_m.group(1).strip().split("\n") if l.strip()]
    result = []
    pending = ""
    for line in lines:
        m = re.match(r"^(.*?)\s+([\d]+(?:\.[\d]+)?)\s*$", line)
        if m:
            name = (pending + " " + m.group(1)).strip()
            result.append((name, float(m.group(2))))
            pending = ""
        else:
            pending = (pending + " " + line).strip()
    return result


def _parse_country(page_text: str) -> list[tuple[str, float]]:
    """Parse country exposure table from page 25 text."""
    sec_m = re.search(r"Country Fund \(%\)(.*?)Source", page_text, re.DOTALL)
    if not sec_m:
        return []
    result = []
    for m in re.finditer(r"^(.+?)\s+([\d\.]+)\s*$", sec_m.group(1), re.MULTILINE):
        name = m.group(1).strip()
        if name:
            result.append((name, float(m.group(2))))
    return result


class ABSLGlobalBluechipParser(BaseGiftCityParser):
    FUND_NAME = "ABSL Global Bluechip Equity Fund (IFSC)"
    AMC_NAME = "ABSL"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Close-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        p25 = self._pages[24]  # holdings + country exposure
        p27 = self._pages[26]  # performance

        # ── As-of date ────────────────────────────────────────────────────────
        date_m = re.search(r"Performance as on (\d+\w* \w+ \d{4})", p27)
        as_of = self._parse_date(_strip_ordinal(date_m.group(1))) if date_m else None
        if as_of is None:
            logger.warning(
                "%s: could not extract as-of date from page 27; holdings/performance will have NULL dates",
                self.FUND_NAME,
            )

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="MSCI ACWI",
            inception_date=date(2025, 4, 16),
            fund_manager="Rudy Gopalakrishnan",
            min_investment_usd=75_000.0,
            lock_in_months=48,
            nav_frequency="Weekly",
            ltcg_tax_pct=12.5,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # ── Share classes (fees stable for closed-end tenure) ─────────────────
        share_classes = [
            ShareClass(
                class_name=cls,
                investor_type=inv_type,
                min_investment_usd=float(min_inv),
                management_fee_pct=fee,
                exit_load_pct=0.0,
                lock_in_months=48,
            )
            for cls, inv_type, min_inv, _, fee in _SHARE_CLASSES
        ]

        # ── Performance ───────────────────────────────────────────────────────
        # Page 27 has a bar chart: 6 numbers (fund 1M/3M/SI, then bench 1M/3M/SI)
        # appear just before the "ABSL Global Bluechip..." label in the PDF stream.
        perf_m = re.search(
            r"([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%\s+"
            r"([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%\s+"
            r"ABSL Global Bluechip",
            p27,
        )
        performance = []
        if perf_m:
            fund_vals  = [float(perf_m.group(i)) for i in (1, 2, 3)]
            bench_vals = [float(perf_m.group(i)) for i in (4, 5, 6)]
            for period, fr, br in zip(["1M", "3M", "SI"], fund_vals, bench_vals):
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    share_class="A1",
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=(period == "SI"),
                ))

        # ── Holdings ──────────────────────────────────────────────────────────
        raw_holdings = _parse_holdings(p25)
        holdings = [
            Holding(name, weight_pct=pct, holding_type="Equity", as_of_date=as_of)
            for name, pct in raw_holdings
        ]

        # ── Allocations (geography) ───────────────────────────────────────────
        raw_country = _parse_country(p25)
        allocations = [
            Allocation("Geography", cat, weight_pct=pct, as_of_date=as_of)
            for cat, pct in raw_country
        ]

        risk_metrics = [RiskMetrics(
            active_share_pct=70.0,
            beta=1.0,
            as_of_date=as_of,
        )]

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            holdings=holdings,
            allocations=allocations,
            risk_metrics=risk_metrics,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = ABSLGlobalBluechipParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"As of: {result.fund_info.factsheet_date}")
    print(f"Holdings ({len(result.holdings)}):")
    for h in result.holdings:
        print(f"  {h.holding_name}: {h.weight_pct}%")
    print(f"Geo ({len(result.allocations)}):")
    for a in result.allocations:
        print(f"  {a.category}: {a.weight_pct}%")
    print(f"Performance ({len(result.performance)}):")
    for r in result.performance:
        print(f"  {r.period}: {r.fund_return_pct}% vs {r.benchmark_return_pct}%")
