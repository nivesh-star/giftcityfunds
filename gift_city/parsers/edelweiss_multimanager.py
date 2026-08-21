"""Edelweiss India Multimanager Equity Fund -- GIFT City Cat III AIF factsheet parser.

NOTE: Unlike the other parsers in this package, this factsheet was not
downloaded as a local PDF for this pipeline -- it was read directly from the
AMC's hosted URL (https://www.edelweissmf.com/Files/Gift-City/Edelweiss_India
_Multimanager_Equity_Fund_Series.pdf) via a one-off fetch during AMC research,
not via pypdf against a local file. The values below are a sourced snapshot
transcribed from that fetch, not live regex extraction -- update this parser
to do live pypdf extraction if/when the PDF is downloaded locally.
"""
from __future__ import annotations
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, Holding, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Edelweiss_India_Multimanager_Equity_Fund_Series.pdf"
FACTSHEET_URL = (
    "https://www.edelweissmf.com/Files/Gift-City/"
    "Edelweiss_India_Multimanager_Equity_Fund_Series.pdf"
)

# Top-10 look-through stock holdings (consolidated across all underlying
# schemes this fund invests into), as disclosed in the Dec-2025 factsheet.
_TOP_HOLDINGS = [
    ("HDFC Bank Ltd", 4.29), ("ICICI Bank Ltd", 3.61), ("State Bank of India", 2.44),
    ("Axis Bank Ltd", 2.24), ("Bharti Airtel Ltd", 1.73), ("Infosys Ltd", 1.54),
    ("Bajaj Finance Ltd", 1.48), ("Max Financial Services Ltd", 1.42),
    ("Fortis Healthcare Ltd", 1.26), ("Persistent Systems Ltd", 1.21),
]

# Underlying-scheme (multimanager) weights -- the named domestic mutual fund
# schemes this fund actually allocates capital to.
_UNDERLYING_SCHEMES = [
    ("Edelweiss Flexi Cap Fund", 15.02), ("DSP Flexi Cap Fund", 14.87),
    ("HDFC Flexi Cap Fund", 14.82), ("Canara Robeco Flexi Cap Fund", 14.81),
    ("Edelweiss Mid Cap Fund", 9.99), ("HDFC Mid Cap Fund", 9.93),
    ("Kotak Mid Cap Fund", 9.91), ("Nippon India Growth Mid Cap Fund", 9.87),
    ("Cash", 0.78),
]


class EdelweissMultimanagerParser(BaseGiftCityParser):
    FUND_NAME = "Edelweiss India Multimanager Equity Fund"
    AMC_NAME = "Edelweiss Asset Management Limited (IFSC Branch)"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        as_of = date(2025, 12, 31)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="Nifty 500",
            fund_manager="Ajitkumar Paudel",
            nav_frequency="Daily",
            factsheet_url=FACTSHEET_URL,
            factsheet_date=as_of,
        )

        share_classes = [
            ShareClass(class_name="Series I", ter_pct=0.30),
        ]

        # Look-through stock holdings + the named underlying schemes, tagged
        # by basis so downstream consumers can tell the two apart.
        holdings = [
            Holding(holding_name=name, weight_pct=pct, holding_type="Equity",
                    as_of_date=as_of)
            for name, pct in _TOP_HOLDINGS
        ]

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            holdings=holdings,
        )

    def underlying_schemes(self):
        """Named underlying-scheme weights (not part of the base Holding
        model's usual look-through stocks) -- exposed separately since these
        represent the fund's multimanager allocation, not direct equity
        holdings."""
        return list(_UNDERLYING_SCHEMES)


if __name__ == "__main__":
    p = EdelweissMultimanagerParser(FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"Holdings (look-through stocks): {len(result.holdings)}")
    print(f"Underlying schemes: {len(p.underlying_schemes())}")
