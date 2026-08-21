"""Marcellus Global Compounders Portfolio (GCP) — GIFT City AIF Cat III parser.

Performance data is embedded in charts/images in the PDF and cannot be
extracted via pypdf. Fund structure and fee data is parsed from text.
Geo/sector allocations are hardcoded from the latest factsheet snapshot.
"""
from __future__ import annotations
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Marcellus_GCP_Fund.pdf"

_GEO = [
    ("United States", 56.0), ("Rest of World", 44.0),
]

_SECTOR = [
    ("Industrials", 32.2), ("Information Technology", 32.2), ("Financials", 10.4),
    ("Health Care", 9.7), ("Consumer Discretionary", 5.9), ("Others", 5.5), ("Cash", 4.1),
]


class MarcellusGCPParser(BaseGiftCityParser):
    FUND_NAME = "Marcellus GCP Fund"
    AMC_NAME = "Marcellus"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text

        _date_m = re.search(
            r"(?:as\s+on|as\s+at|portfolio\s+date|factsheet)[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{4})",
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
            benchmark_index="S&P 500 Net Total Return",
            inception_date=date(2022, 10, 31),
            fund_manager="Prashant Mittal",
            min_investment_usd=75_000.0,
            exit_load_pct=0.0,
            lock_in_months=0,
            nav_frequency="Monthly",
            ltcg_tax_pct=12.5,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # Parse min ticket from text
        min_m = re.search(r"Minimum Ticket Size.*?USD\s*([\d,]+)", text, re.IGNORECASE)
        if min_m:
            fund_info.min_investment_usd = float(min_m.group(1).replace(",", ""))

        # Three fee options as share classes
        share_classes = [
            ShareClass(
                class_name="Fixed Fee",
                management_fee_pct=1.5,
                performance_fee_pct=0.0,
                hurdle_rate_pct=None,
                exit_load_pct=0.0,
                lock_in_months=0,
                min_investment_usd=75_000.0,
            ),
            ShareClass(
                class_name="Performance Fee",
                management_fee_pct=0.0,
                performance_fee_pct=20.0,
                hurdle_rate_pct=5.0,
                exit_load_pct=0.0,
                lock_in_months=0,
                min_investment_usd=75_000.0,
            ),
            ShareClass(
                class_name="Hybrid Fee",
                management_fee_pct=0.75,
                performance_fee_pct=15.0,
                hurdle_rate_pct=9.0,
                exit_load_pct=0.0,
                lock_in_months=0,
                min_investment_usd=75_000.0,
            ),
        ]

        # Performance is chart-based; not extractable from text
        performance = []

        logger.warning(
            "%s: using hardcoded geo/sector allocations (snapshot); update when PDF layout allows extraction",
            self.FUND_NAME,
        )
        allocations = [
            Allocation("Geography", cat, pct, as_of_date=as_of)
            for cat, pct in _GEO
        ] + [
            Allocation("Sector", cat, pct, as_of_date=as_of)
            for cat, pct in _SECTOR
        ]

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            allocations=allocations,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = MarcellusGCPParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"Share classes: {[sc.class_name for sc in result.share_classes]}")
