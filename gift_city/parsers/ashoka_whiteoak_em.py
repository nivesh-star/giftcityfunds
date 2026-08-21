"""Ashoka WhiteOak Emerging Markets Equity Ex India Fund — Ireland UCITS parser.

All data (NAV, AUM, ISIN, TER, performance, geo allocations) is extracted from PDF text.
Page 1 has fund facts + full performance table.
Page 3 has the regional composition table with fund vs benchmark weights.
"""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Ashoka_WhiteOak_Emerging_Markets_Fund_Ex_India.pdf"

# Performance table column layout (11 values per row):
# 0=1M, 1=YTD, 2=FY24-25, 3=FY23-24, 4=CY24, 5=CY23, 6=Part2022,
# 7=Trailing_1Y, 8=Trailing_2Y, 9=SI_annualized, 10=SI_cumulative
_PERF_IDX = {
    "1M":  (0,  False),
    "YTD": (1,  False),
    "1Y":  (7,  True),
    "2Y":  (8,  True),
    "SI":  (9,  True),
}


class AshokaWhiteOakEMParser(BaseGiftCityParser):
    FUND_NAME = "Ashoka WhiteOak Emerging Markets Equity Ex India Fund"
    AMC_NAME = "Ashoka WhiteOak"
    FUND_TYPE = "UCITS"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        p1 = self._pages[0]   # fund facts + performance table
        p3 = self._pages[2]   # regional composition table

        # ── As-of date ────────────────────────────────────────────────────────
        date_m = re.search(r"As at (\d+ \w+ \d{4})", p1)
        as_of = self._parse_date(date_m.group(1)) if date_m else None

        # ── Fund metadata ─────────────────────────────────────────────────────
        nav_m  = re.search(r"NAV \(US\$\):\s*([\d\.]+)", p1)
        aum_m  = re.search(r"Fund AUM.*?\$\s*([\d\.]+)\s*million", p1, re.IGNORECASE)
        isin_m = re.search(r"ISIN:\s*([A-Z0-9]+)", p1)
        tick_m = re.search(r"Bloomberg Ticker:\s*(\S+)", p1)
        ter_m  = re.search(r"Total expense ratio.*?:\s*([\d]+)bps", p1, re.IGNORECASE)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="Ireland",
            base_currency="USD",
            benchmark_index="MSCI Emerging Markets ex India Net Total Returns Index (US$)",
            inception_date=date(2022, 12, 21),
            fund_manager="Prashant Khemka",
            isin=isin_m.group(1).strip() if isin_m else None,
            bloomberg_ticker=tick_m.group(1).strip() if tick_m else None,
            nav=float(nav_m.group(1)) if nav_m else None,
            nav_date=as_of,
            aum_usd=float(aum_m.group(1)) * 1_000_000 if aum_m else None,
            aum_date=as_of,
            exit_load_pct=0.0,
            nav_frequency="Daily",
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        ter_pct = float(ter_m.group(1)) / 100 if ter_m else 0.80
        share_classes = [
            ShareClass(
                class_name="Class A",
                management_fee_pct=0.65,
                ter_pct=ter_pct,
                nav=fund_info.nav,
                nav_date=as_of,
                exit_load_pct=0.0,
            )
        ]

        # ── Performance ───────────────────────────────────────────────────────
        # Fund and benchmark each appear as a single line with 11 space-separated values.
        fund_vals  = self._extract_perf_line(p1, "Class A Shares NAV")
        bench_vals = self._extract_perf_line(p1, "MSCI EM ex India")

        performance = []
        if fund_vals:
            for period, (idx, annualized) in _PERF_IDX.items():
                fr = fund_vals[idx]
                br = bench_vals[idx] if bench_vals else None
                performance.append(PerformanceRow(
                    period=period,
                    fund_return_pct=fr,
                    benchmark_return_pct=br,
                    excess_return_pct=round(fr - br, 4) if br is not None else None,
                    share_class="Class A",
                    currency="USD",
                    as_of_date=as_of,
                    is_annualized=annualized,
                ))

        # ── Geographic allocations (page 3 regional table) ────────────────────
        # Table format: "Region  MSCI_weight  Fund_weight  Active_weight ..."
        allocations = []
        for m in re.finditer(
            r"^(Asia|Europe and Africa|LATAM|Middle East|Developed Markets)"
            r"\s+([\d\.]+)\s+([\d\.]+)\s+([-\d\.]+)",
            p3,
            re.MULTILINE,
        ):
            region   = m.group(1)
            bench_w  = float(m.group(2))
            fund_w   = float(m.group(3))
            active_w = float(m.group(4))
            allocations.append(Allocation(
                allocation_type="Geography",
                category=region,
                weight_pct=fund_w,
                benchmark_weight_pct=bench_w,
                active_weight_pct=active_w,
                as_of_date=as_of,
            ))

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            allocations=allocations,
        )

    @staticmethod
    def _extract_perf_line(text: str, prefix: str) -> list[float] | None:
        """Find the line starting with `prefix` and return all numeric values from it."""
        for line in text.split("\n"):
            if prefix in line:
                vals = re.findall(r"[-\d]+\.[\d]+", line)
                if len(vals) >= 10:
                    return [float(v) for v in vals]
        return None


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = AshokaWhiteOakEMParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    fi = result.fund_info
    print(f"Fund: {fi.fund_name}")
    print(f"As of: {fi.factsheet_date}  NAV: {fi.nav}  AUM: ${fi.aum_usd/1e6:.2f}M" if fi.aum_usd else f"As of: {fi.factsheet_date}")
    print(f"ISIN: {fi.isin}  Ticker: {fi.bloomberg_ticker}")
    print(f"Performance ({len(result.performance)}):")
    for r in result.performance:
        print(f"  {r.period}: {r.fund_return_pct}% vs {r.benchmark_return_pct}% (excess {r.excess_return_pct}%)")
    print(f"Geo allocations ({len(result.allocations)}):")
    for a in result.allocations:
        print(f"  {a.category}: {a.weight_pct}% (active {a.active_weight_pct}%)")
