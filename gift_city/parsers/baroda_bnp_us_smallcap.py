"""Baroda BNP Paribas GIFT US Small Cap Fund — GIFT City AIF Cat III parser."""
from __future__ import annotations
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, RiskMetrics, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Baroda_BNP_Paribas_US_Smallcap_Fund.pdf"

# Underlying BNP Paribas US Small Cap Fund performance (Oct 31, 2025, gross)
_PERF_GROSS = [
    ("YTD", 10.37, 12.39),
    ("1Y",  12.35, 14.41),
    ("3Y",  13.40, 11.93),
    ("5Y",  12.20, 11.48),
    ("SI",  11.04,  8.61),
]

# Risk stats (5-year, as of Sep 30, 2025)
_RISK = RiskMetrics(
    period="5Y",
    alpha_pct=1.62,
    beta=0.91,
    r_squared=0.95,
    tracking_error_pct=5.10,
    information_ratio=0.17,
    upside_capture_pct=91.0,
    downside_capture_pct=90.2,
    batting_average_pct=55.0,
    active_share_pct=92.0,
    as_of_date=date(2025, 9, 30),
)


def _parse_holdings_and_sectors(page_text: str, holdings_date: date):
    """Parse page 28: names listed first, then weights in separate blocks."""
    # Holdings: all names between "Main Holdings" and "No. of holdings"
    names_m = re.search(r"Main Holdings\n(.*?)No\. of holdings", page_text, re.DOTALL)
    # Weights: percentages immediately after "No. of holdings in portfolio:\n"
    wts_m = re.search(r"No\. of holdings in portfolio:\n((?:[\d\.]+%\n)+)", page_text)

    holdings: list[Holding] = []
    if names_m and wts_m:
        names = [l.strip() for l in names_m.group(1).strip().split("\n") if l.strip()]
        weights = re.findall(r"([\d\.]+)%", wts_m.group(1))
        holdings = [
            Holding(name, weight_pct=float(w), holding_type="Equity", as_of_date=holdings_date)
            for name, w in zip(names, weights)
        ]

    # Sectors: names between "Index\n" and first signed %, then active weights, then absolute weights
    sector_m = re.search(r"Index\n(.*?)(?:As of )", page_text, re.DOTALL)
    allocations: list[Allocation] = []
    if sector_m:
        lines = [l.strip() for l in sector_m.group(1).split("\n") if l.strip()]
        sector_names, numbers = [], []
        for line in lines:
            m = re.match(r"^([+\-]?[\d\.]+)%$", line)
            if m:
                numbers.append(float(m.group(1)))
            elif not re.match(r"^\d+$", line):
                sector_names.append(line)
        n = len(sector_names)
        # First n numbers = active weights (vs benchmark), next n = absolute fund weights
        if len(numbers) >= 2 * n:
            absolute_weights = numbers[n : 2 * n]
            allocations = [
                Allocation("Sector", name, weight_pct=abs_w, as_of_date=holdings_date)
                for name, abs_w in zip(sector_names, absolute_weights)
            ]

    return holdings, allocations


class BarodaBNPUSSmallcapParser(BaseGiftCityParser):
    FUND_NAME = "Baroda BNP Paribas GIFT US Small Cap Fund"
    AMC_NAME = "Baroda BNP Paribas"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended Feeder"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text

        # Try to extract factsheet date from text
        _date_m = re.search(
            r"(?:as\s+on|as\s+at|factsheet)[:\s]+(\w+\s+\d{4}|\d{1,2}\s+\w+\s+\d{4})",
            text, re.IGNORECASE,
        )
        as_of = self._parse_date(_date_m.group(1)) if _date_m else None
        if as_of is None:
            logger.warning(
                "%s: could not extract as-of date from PDF; using None",
                self.FUND_NAME,
            )

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="Russell 2000",
            fund_manager="BNP Paribas Asset Management USA (Boston team)",
            min_investment_usd=150_000.0,
            ltcg_tax_pct=12.5,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # Try to parse min investment from text
        min_m = re.search(
            r"Share Class T.*?USD\s*([\d,]+)", text, re.IGNORECASE | re.DOTALL
        )
        if min_m:
            fund_info.min_investment_usd = float(min_m.group(1).replace(",", ""))

        share_classes = [
            ShareClass(
                class_name="Class T",
                min_investment_usd=175_000.0,
                management_fee_pct=1.65,
                exit_load_pct=1.0,
                exit_load_months=12,
                lock_in_months=0,
            ),
            ShareClass(
                class_name="Class U",
                min_investment_usd=150_000.0,
                management_fee_pct=1.75,
                exit_load_pct=0.0,
                lock_in_months=24,
            ),
            ShareClass(
                class_name="Class I",
                min_investment_usd=250_000.0,
                management_fee_pct=0.75,
                exit_load_pct=0.0,
                lock_in_months=0,
            ),
        ]

        # Performance of the underlying BNP Paribas US Small Cap Fund (hardcoded snapshot)
        logger.warning(
            "%s: using hardcoded performance data (underlying fund, snapshot as of Oct 2025)",
            self.FUND_NAME,
        )
        performance = []
        for period, fund_ret, bench_ret in _PERF_GROSS:
            performance.append(PerformanceRow(
                period=period,
                fund_return_pct=fund_ret,
                benchmark_return_pct=bench_ret,
                excess_return_pct=round(fund_ret - bench_ret, 4),
                currency="USD",
                as_of_date=as_of,
                is_annualized=(period in {"1Y", "3Y", "5Y", "SI"}),
            ))

        # Holdings and sector breakdown from page 28 (as of Sep 30, 2025)
        p28 = self._pages[27]
        holdings_date = date(2025, 9, 30)
        date_m = re.search(r"As of (\w+ \d+, \d{4})", p28)
        if date_m:
            parsed_d = self._parse_date(date_m.group(1))
            if parsed_d:
                holdings_date = parsed_d
        holdings, allocations = _parse_holdings_and_sectors(p28, holdings_date)

        logger.warning(
            "%s: using hardcoded risk metrics (5Y snapshot as of Sep 2025)",
            self.FUND_NAME,
        )
        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            holdings=holdings,
            allocations=allocations,
            risk_metrics=[_RISK],
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = BarodaBNPUSSmallcapParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"Share classes: {[sc.class_name for sc in result.share_classes]}")
    for row in result.performance:
        print(f"  {row.period}: {row.fund_return_pct}% vs {row.benchmark_return_pct}%")
