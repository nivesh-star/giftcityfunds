"""PPFAS IFSC NASDAQ 100 Fund of Fund — GIFT City Retail MF factsheet parser."""
from __future__ import annotations
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "PPFAS_Nasdaq_100_Fund.pdf"

_SECTOR = [
    ("Information Technology", 53.60), ("Communication Services", 15.10),
    ("Consumer Discretionary", 12.20), ("Consumer Staples", 7.70),
    ("Health Care", 4.20), ("Industrials", 3.90), ("Utilities", 1.40),
    ("Materials", 1.10), ("Energy", 0.60), ("Others", 0.20),
]

# Holdings fallback — used only if live extraction below finds nothing.
_HOLDINGS_FALLBACK = [
    ("Invesco NASDAQ-100 Swap UCITS ETF Acc", 99.97, "ETF"),
    ("Cash & Money Market Instruments", 0.03, "Cash"),
]

# "Security Name % of Net Assets" table at the top of the factsheet:
#   Invesco NASDAQ-100 Swap UCITS ETF Acc 99.97%
#   Cash & Money Market Instruments 0.03%
_HOLDINGS_BLOCK_RE = re.compile(
    r"Security Name\s*%\s*of\s*Net Assets\s*\n((?:.+\n)+?)(?=About |$)"
)
_HOLDINGS_LINE_RE = re.compile(r"^(.+?)\s+([\d.]+)%\s*$")


class PPFASNasdaq100Parser(BaseGiftCityParser):
    FUND_NAME = "Parag Parikh IFSC NASDAQ 100 Fund of Fund"
    AMC_NAME = "PPFAS"
    FUND_TYPE = "Retail MF"
    STRUCTURE = "Open-ended FoF"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text

        _date_m = re.search(
            r"(?:as\s+on|as\s+at|nav\s+date)[:\s]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4}|\w+\s+\d{4})",
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
            benchmark_index="Nasdaq 100 Notional Net Total Return Index",
            inception_date=date(2026, 3, 20),
            fund_manager="Akshay Falgunia",
            min_investment_usd=5000.0,
            exit_load_pct=0.0,
            exit_load_months=0,
            lock_in_months=0,
            nav_frequency="Daily",
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # AUM
        aum_m = re.search(r"AUM.*?US\$?\s*([\d\.]+)\s*Mn", text, re.IGNORECASE)
        if aum_m:
            fund_info.aum_usd = float(aum_m.group(1)) * 1_000_000
            fund_info.aum_date = date(2026, 5, 31)

        # NAV
        nav_m = re.search(r"Subscription NAV:\s*([\d\.]+)", text)
        if nav_m:
            fund_info.nav = float(nav_m.group(1))
            fund_info.nav_date = as_of

        share_classes = [
            ShareClass(
                class_name="Class A (Direct)",
                ter_pct=0.50,
                management_fee_pct=0.30,
                nav=fund_info.nav,
                nav_date=as_of,
                exit_load_pct=0.0,
                lock_in_months=0,
            )
        ]

        # Performance — only "Since Inception" available
        si_m = re.search(r"Since Inception\s+([\d\.]+)%?\s+([\d\.]+)%?", text)
        performance = []
        if si_m:
            fund_ret = float(si_m.group(1))
            bench_ret = float(si_m.group(2))
            performance.append(PerformanceRow(
                period="SI",
                fund_return_pct=fund_ret,
                benchmark_return_pct=bench_ret,
                excess_return_pct=round(fund_ret - bench_ret, 4),
                share_class="Class A (Direct)",
                currency="USD",
                as_of_date=as_of,
                is_annualized=False,  # short history, absolute
            ))

        holdings = []
        block_m = _HOLDINGS_BLOCK_RE.search(text)
        if block_m:
            for line in block_m.group(1).splitlines():
                line_m = _HOLDINGS_LINE_RE.match(line.strip())
                if line_m:
                    name = line_m.group(1).strip()
                    holding_type = "Cash" if "cash" in name.lower() else "ETF"
                    holdings.append(Holding(name, float(line_m.group(2)), holding_type,
                                             as_of_date=as_of))
        if not holdings:
            logger.warning(
                "%s: could not live-extract holdings; using hardcoded fallback snapshot",
                self.FUND_NAME,
            )
            holdings = [
                Holding(name, pct, htype, as_of_date=as_of)
                for name, pct, htype in _HOLDINGS_FALLBACK
            ]

        logger.warning(
            "%s: using hardcoded sector allocations (Nasdaq-100 snapshot); update when PDF is parseable",
            self.FUND_NAME,
        )
        allocations = [
            Allocation("Sector", cat, pct, as_of_date=None)
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
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = PPFASNasdaq100Parser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"AUM: ${result.fund_info.aum_usd:,.0f}" if result.fund_info.aum_usd else "AUM: N/A")
    print(f"SI return: {result.performance[0].fund_return_pct}%")
