"""Marcellus Global Equity Fund — GIFT City AIF Cat III factsheet parser.

NOTE: The factsheet PDF appears to be image-based (scanned). pypdf extracts
no text from it. All data is hardcoded from the visual content as observed
by the Explore agent.
"""
from __future__ import annotations
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Marcellus_Global_Equity_Fund.pdf"

_PERFORMANCE = [
    ("1M",  None, None),
    ("3M",  None, None),
    ("6M",  None, None),
    ("1Y",  None, None),
    ("2Y",  None, None),
    ("3Y",  None, None),
    ("SI",  None, None),
]

_GEO = [
    ("North America", 30.8), ("Europe", 17.7), ("China & Hong Kong", 15.2),
    ("Japan", 2.0), ("Cash", 24.8),
]

_SECTOR = [
    ("Industrials", None), ("Information Technology", None), ("Financials", None),
    ("Health Care", None), ("Consumer Discretionary", None),
]


class MarcellusGlobalEquityParser(BaseGiftCityParser):
    FUND_NAME = "Marcellus Global Equity Fund"
    AMC_NAME = "Marcellus"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        as_of = date(2026, 3, 31)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            fund_manager="Prashant Mittal",
            min_investment_usd=5_000.0,
            exit_load_pct=2.0,
            exit_load_months=24,
            lock_in_months=0,
            nav_frequency="Daily",
            ltcg_tax_pct=12.5,
            stcg_tax_pct=40.0,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        share_classes = [
            ShareClass(
                class_name="Standard",
                min_investment_usd=5_000.0,
                management_fee_pct=1.75,
                ter_pct=2.0,
                exit_load_pct=2.0,
                exit_load_months=24,
            )
        ]

        # PDF is image-based; no text extractable; performance populated when parseable
        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=[],
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = MarcellusGlobalEquityParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print("Note: PDF is image-based; text extraction not available.")
