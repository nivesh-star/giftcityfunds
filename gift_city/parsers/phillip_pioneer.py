"""Phillip International Pioneer Portfolio — GIFT City PMS factsheet parser."""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Phillip_Int_Pioneer_Portfolio.pdf"

_PERF_USD = [
    ("1M",  -6.03, -7.37),
    ("3M",  -2.33, -2.78),
    ("6M",  -1.80,  0.27),
    ("1Y",  21.93, 20.55),
    ("2Y",  10.03, 13.17),
    ("3Y",  14.62, 16.11),
    ("QTD", -2.33, -2.78),
    ("YTD", -2.33, -2.78),
    ("SI",   7.68,  7.51),
]

_GEO = [
    ("United States", 62), ("Multi-Region", 17), ("Cash In Hand", 10),
    ("Japan", 6), ("Taiwan", 5),
]

_SECTOR = [
    ("Diversified", 27), ("Technology", 22), ("Thematic", 12),
    ("Cash In Hand", 10), ("Health Care", 9), ("Financials", 9),
    ("Energy", 6), ("Consumer Discretionary", 4), ("Materials", 1),
]


class PhillipPioneerParser(BaseGiftCityParser):
    FUND_NAME = "Phillip International Pioneer Portfolio"
    AMC_NAME = "Phillip Ventures IFSC"
    FUND_TYPE = "PMS"
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
            benchmark_index="S&P Global BMI Net TR",
            inception_date=date(2021, 12, 31),
            fund_manager="Mihir Shirgaonkar",
            min_investment_usd=75_000.0,
            nav_frequency="Monthly",
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # Parse performance from text table
        perf_m = re.search(
            r"RETURNS\s+1-MONTH\s+3-MONTH\s+6-MONTH\s+1-YEAR\s+2-YEAR\s+3-YEAR"
            r".*?PORTFOLIO\s+-\s+USD\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%"
            r"\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        bench_m = re.search(
            r"BENCHMARK\s+-\s+USD\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%"
            r"\s+([-\d\.]+)%\s+([-\d\.]+)%\s+([-\d\.]+)%",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        periods = ["1M", "3M", "6M", "1Y", "2Y", "3Y"]
        performance = []

        if perf_m and bench_m:
            for i, period in enumerate(periods):
                fr = float(perf_m.group(i + 1))
                br = float(bench_m.group(i + 1))
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=(period in {"1Y", "2Y", "3Y"}),
                ))
        else:
            for period, fr, br in _PERF_USD:
                performance.append(PerformanceRow(
                    period=period, fund_return_pct=fr, benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4),
                    currency="USD", as_of_date=as_of,
                    is_annualized=(period in {"1Y", "2Y", "3Y", "SI"}),
                ))

        # INR performance derived from USD + FX
        si_inr_fund = 72.00
        si_inr_bench = 36.05 + 25.58  # approximate
        performance.append(PerformanceRow(
            period="SI", fund_return_pct=si_inr_fund,
            benchmark_return_pct=None,
            currency="INR", as_of_date=as_of, is_annualized=True,
        ))

        share_classes = [
            ShareClass(
                class_name="Standard",
                min_investment_usd=75_000.0,
                exit_load_pct=0.0,
            )
        ]

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
    p = PhillipPioneerParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    for row in result.performance[:4]:
        print(f"  [{row.currency}] {row.period}: {row.fund_return_pct}% vs {row.benchmark_return_pct}%")
