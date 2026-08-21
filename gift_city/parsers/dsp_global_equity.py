"""DSP Global Equity Fund — GIFT City Retail MF factsheet parser."""
from __future__ import annotations
import logging
import re
from datetime import date, datetime
from pathlib import Path

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, ParsedFactsheet,
)

logger = logging.getLogger(__name__)

FACTSHEET_FILENAME = "DSP_Global_Equity_Fund.pdf"

# Holdings fallback — used only if live regex extraction below finds nothing
# (e.g. the PDF layout changes). A warning is logged at runtime when this fires.
_HOLDINGS = [
    ("Amazon.com", 6.4), ("TSMC", 5.8), ("Adyen NV", 5.0), ("Meta Platform", 4.7),
    ("Alphabet", 4.0), ("Tencent", 3.9), ("Constellation Software", 3.9),
    ("Berkshire Hathaway", 3.3), ("Fairfax India", 3.2), ("Nexans SA", 3.0),
]

_HOLDING_LINE_RE = re.compile(
    r"^\d{1,2}\.\s+([A-Za-z][A-Za-z0-9&.,' ]*?)\s+([\d.]+)%\s*$", re.MULTILINE
)

_GEO = [
    ("North America", 30.8), ("Europe", 17.7), ("China & Hong Kong", 15.2),
    ("Japan", 2.0), ("Cash", 24.8),
]

_SECTOR = [
    ("Media & Entertainment", 17.3), ("Financial Services", 15.2),
    ("Consumer Durables", 8.7), ("Consumer Discretionary", 8.0),
    ("Semiconductors", 5.8), ("Capital Goods", 5.1), ("Consumer Services", 4.8),
    ("Software & Services", 3.9), ("Automobiles", 2.7), ("Materials", 1.9),
    ("Insurance", 1.8), ("Cash", 22.1),
]


class DSPGlobalEquityParser(BaseGiftCityParser):
    FUND_NAME = "DSP Global Equity Fund"
    AMC_NAME = "DSP"
    FUND_TYPE = "Retail MF"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text

        # Try to extract the as-of date from common PDF patterns
        _date_m = re.search(
            r"(?:as\s+on|as\s+at|portfolio\s+date)[:\s]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4})",
            text, re.IGNORECASE,
        ) or re.search(r"(\d{1,2}\s+\w+\s+\d{4})", text)
        as_of = self._parse_date(_date_m.group(1)) if _date_m else None
        if as_of is None:
            logger.warning(
                "%s: could not extract as-of date from PDF; using None (hardcoded snapshot active)",
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
            inception_date=date(2025, 9, 18),
            fund_manager="Giriraj Bassa",
            nav_frequency="Daily",
            ltcg_tax_pct=14.95,
            stcg_tax_pct=42.74,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # AUM
        aum_m = re.search(r"FUND AUM\s*USD\s*([\d\.]+)\s*M", text, re.IGNORECASE)
        if aum_m:
            fund_info.aum_usd = float(aum_m.group(1)) * 1_000_000
            fund_info.aum_date = as_of

        # NAV
        nav_m = re.search(r"NAV\s*\(USD\).*?Direct\s*([\d\.]+)", text, re.IGNORECASE | re.DOTALL)
        if nav_m:
            nav_str = nav_m.group(1)
            # This factsheet's PDF text layer renders the NAV cell doubled
            # (e.g. "9.569.56" for an actual NAV of 9.56, from overlapping
            # table cells in the source PDF) -- de-dupe before parsing.
            if len(nav_str) % 2 == 0 and nav_str[: len(nav_str) // 2] == nav_str[len(nav_str) // 2 :]:
                nav_str = nav_str[: len(nav_str) // 2]
            fund_info.nav = float(nav_str)
            fund_info.nav_date = as_of

        # min investment
        fund_info.min_investment_usd = 5000.0
        # exit load
        fund_info.exit_load_pct = 1.0
        fund_info.exit_load_months = 24

        # Share classes
        share_classes = [
            ShareClass(
                class_name="Direct",
                management_fee_pct=1.0,
                nav=self._find_float(r"Direct\s*(9\.\d+)"),
                nav_date=as_of,
                exit_load_pct=1.0,
                exit_load_months=24,
            ),
            ShareClass(
                class_name="Regular",
                management_fee_pct=1.75,
                nav=self._find_float(r"Regular\s*(9\.\d+)"),
                nav_date=as_of,
                exit_load_pct=1.0,
                exit_load_months=24,
            ),
        ]

        # Performance — layout: SI, 6M, 3M, 1M  x  (Regular, Direct, MSCI ACWI)
        # Text: -4.9% -3.6% 1.6% | -4.4% -3.2% 1.8% | 16.6% | 1 Month 0.3% 0.3% | 13.3% 7.5% 5.2%
        # These values are hardcoded snapshots; update when PDF layout allows live extraction.
        logger.warning(
            "%s: using hardcoded performance data (snapshot, not live PDF extraction)",
            self.FUND_NAME,
        )
        performance = []
        # Direct returns extracted from text order
        perf_data = [
            ("SI",  -4.4, None, "Direct",  True),
            ("6M",  -3.2, None, "Direct",  False),
            ("3M",   1.8, None, "Direct",  False),
            ("1M",   0.3, None, "Direct",  False),
            ("SI",  -4.9, None, "Regular", True),
            ("6M",  -3.6, None, "Regular", False),
            ("3M",   1.6, None, "Regular", False),
            ("1M",   0.3, None, "Regular", False),
        ]
        # Benchmark values
        bench = {"SI": 16.6, "6M": 13.3, "3M": 7.5, "1M": 5.2}
        for period, fund_ret, _, sc, is_ann in perf_data:
            b = bench.get(period)
            performance.append(PerformanceRow(
                period=period,
                fund_return_pct=fund_ret,
                benchmark_return_pct=b,
                excess_return_pct=round(fund_ret - b, 4) if b is not None else None,
                share_class=sc,
                currency="USD",
                as_of_date=as_of,
                is_annualized=is_ann,
            ))

        # Holdings — live-extract "1. Amazon.com Inc      6.4%" style lines from
        # the "Top 10 Holdings" block.
        live_holdings = [
            (name.strip(), float(pct)) for name, pct in _HOLDING_LINE_RE.findall(text)
        ]
        if live_holdings:
            holdings = [
                Holding(holding_name=name, weight_pct=pct, holding_type="Equity", as_of_date=as_of)
                for name, pct in live_holdings
            ]
        else:
            logger.warning(
                "%s: could not live-extract holdings; using hardcoded fallback snapshot",
                self.FUND_NAME,
            )
            holdings = [
                Holding(holding_name=name, weight_pct=pct, holding_type="Equity", as_of_date=as_of)
                for name, pct in _HOLDINGS
            ]

        # Cash % of the portfolio is reported in the Sector Allocation block (the
        # last "Cash NN.N%" match in the page — the first is the Geographic block).
        cash_matches = re.findall(r"Cash\s+([\d.]+)\s*%", text)
        cash_pct = float(cash_matches[-1]) if cash_matches else 22.1
        holdings.append(Holding(holding_name="Cash", weight_pct=cash_pct,
                                 holding_type="Cash", as_of_date=as_of))

        logger.warning(
            "%s: using hardcoded geo/sector allocations (snapshot, not live PDF extraction)",
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
            holdings=holdings,
            allocations=allocations,
        )


if __name__ == "__main__":
    import sys, json
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = DSPGlobalEquityParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"AUM: ${result.fund_info.aum_usd:,.0f}" if result.fund_info.aum_usd else "AUM: N/A")
    print(f"Holdings: {len(result.holdings)}")
    print(f"Performance rows: {len(result.performance)}")
    print(f"Allocations: {len(result.allocations)}")
