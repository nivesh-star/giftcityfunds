"""Unifi G20 Fund — GIFT City AIF Cat III factsheet parser."""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    ParsedFactsheet,
)

FACTSHEET_FILENAME = "Unifi_G20_Fund.pdf"

_PERFORMANCE_USD = [
    ("1M",  16.33, 9.77),
    ("3M",   6.83, 2.91),
    ("6M",   1.47, 5.84),
    ("SI",  10.22, 20.64),   # absolute since inception
]

_PERFORMANCE_INR = [
    ("1M",  17.06, 10.45),
    ("3M",  10.72,  6.65),
    ("6M",   8.93, 13.62),
    ("SI",  21.20, 32.65),
]

class UnifiG20Parser(BaseGiftCityParser):
    FUND_NAME = "Unifi G20 Fund"
    AMC_NAME = "Unifi"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text
        as_of = date(2026, 4, 30)  # April 2026 data (April return shown)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="MSCI World Large Cap",
            min_investment_usd=150_000.0,
            exit_load_pct=0.0,
            lock_in_months=24,
            nav_frequency="Monthly",
            ltcg_tax_pct=12.5,
            stcg_tax_pct=40.0,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # Inception: "Inception: 30th Sep 2024" (PMS) or June 2024 (AIF — first entry Jun 2024)
        inc_m = re.search(r"Inception.*?(\d+\w*\s+\w+\s+\d{4})", text, re.IGNORECASE)
        if inc_m:
            fund_info.inception_date = self._parse_date(inc_m.group(1))

        # Min investment
        min_m = re.search(r"Minimum Investment\s*\$?([\d,]+)", text, re.IGNORECASE)
        if min_m:
            fund_info.min_investment_usd = float(min_m.group(1).replace(",", ""))

        # Try to parse performance from text table
        performance = []
        perf_block = re.search(
            r"Unifi G20 Fund\*\s+Benchmark\s+1m\s+([-\d\.]+)%\s+([-\d\.]+)%"
            r"\s+3m\s+([-\d\.]+)%\s+([-\d\.]+)%"
            r"\s+6m\s+([-\d\.]+)%\s+([-\d\.]+)%"
            r"\s+CYTD.*?Since Inception.*?Absolute\s+([-\d\.]+)%\s+([-\d\.]+)%",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if perf_block:
            perf_data = [
                ("1M", float(perf_block.group(1)), float(perf_block.group(2))),
                ("3M", float(perf_block.group(3)), float(perf_block.group(4))),
                ("6M", float(perf_block.group(5)), float(perf_block.group(6))),
                ("SI", float(perf_block.group(7)), float(perf_block.group(8))),
            ]
        else:
            perf_data = [(p, fr, br) for p, fr, br in _PERFORMANCE_USD]

        for period, fr, br in perf_data:
            performance.append(PerformanceRow(
                period=period, fund_return_pct=fr, benchmark_return_pct=br,
                excess_return_pct=round(fr - br, 4),
                currency="USD", as_of_date=as_of,
                is_annualized=(period in {"1Y", "2Y", "3Y"}),
            ))
        for period, fr, br in _PERFORMANCE_INR:
            performance.append(PerformanceRow(
                period=period, fund_return_pct=fr, benchmark_return_pct=br,
                excess_return_pct=round(fr - br, 4),
                currency="INR", as_of_date=as_of,
                is_annualized=(period in {"1Y", "2Y", "3Y"}),
            ))

        share_classes = [
            ShareClass(
                class_name="Standard",
                min_investment_usd=150_000.0,
                exit_load_pct=0.0,
                lock_in_months=24,
            )
        ]

        # No geo/sector allocation table exists in the current factsheet (a pitch
        # deck) — a previous version of this parser had a hardcoded _GEO/_SECTOR
        # snapshot here that was actually copy-pasted from Phillip Pioneer's
        # factsheet (identical values), not Unifi's own data. Removed rather than
        # replaced, since Unifi doesn't disclose this breakdown at all.
        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = UnifiG20Parser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"Performance rows: {len(result.performance)}")
    for row in result.performance[:4]:
        print(f"  [{row.currency}] {row.period}: {row.fund_return_pct}%")
