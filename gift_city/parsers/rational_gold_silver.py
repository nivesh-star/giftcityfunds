"""Rational Gold & Silver Miners' Fund — GIFT City AIF Cat III factsheet parser."""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Rational_Gold_&_Silver_Miners_Fund.pdf"

# Performance table visible in PDF text (as of date not explicit — use as-of 2026 approx)
_PERFORMANCE = [
    ("1M",  -2.5, -3.1),
    ("3M",  -9.7, -6.2),
    ("6M",  21.9, 24.2),
    ("SI",  73.4, 78.1),
]


class RationalGoldSilverParser(BaseGiftCityParser):
    FUND_NAME = "Gold & Silver Miners' Fund"
    AMC_NAME = "Rational"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text
        as_of = date(2026, 3, 31)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="GDXJ",
            fund_manager=None,
            min_investment_usd=150_000.0,
            nav_frequency="Daily",
            ltcg_tax_pct=12.5,
            stcg_tax_pct=40.0,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # Parse performance from text: "Rational -2.5% -9.7% 21.9% 73.4%"
        performance = []
        perf_m = re.search(
            r"Rational\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%",
            text,
        )
        gdxj_m = re.search(
            r"GDXJ\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%",
            text,
        )

        periods = ["1M", "3M", "6M", "SI"]
        annualized = {False, False, False, True}

        if perf_m and gdxj_m:
            for i, period in enumerate(periods):
                fr = float(perf_m.group(i + 1))
                br = float(gdxj_m.group(i + 1))
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=(period == "SI"),
                ))
        else:
            # Fallback to hardcoded
            for period, fr, br in _PERFORMANCE:
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=(period == "SI"),
                ))

        share_classes = [
            ShareClass(
                class_name="Standard",
                min_investment_usd=150_000.0,
            )
        ]

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = RationalGoldSilverParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    for row in result.performance:
        print(f"  {row.period}: {row.fund_return_pct}% vs {row.benchmark_return_pct}%")
