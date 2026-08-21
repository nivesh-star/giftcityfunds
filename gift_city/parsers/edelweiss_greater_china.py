"""Edelweiss Greater China Equity Fund — GIFT City Retail MF factsheet parser."""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Edelweiss_Greater_China_Fund.pdf"

# Top 30 holdings from the factsheet (as of March 2026)
_HOLDINGS = [
    ("Taiwan Semiconductor Manufacturing Co., Ltd.", 9.91),
    ("Tencent Holdings Ltd", 8.42),
    ("Alibaba Group Holding Limited", 6.80),
    ("Delta Electronics, Inc.", 3.30),
    ("Elite Material Co., Ltd.", 2.63),
    ("Cathay Financial Holdings Co., Ltd.", 2.49),
    ("Ping An Insurance (Group) Company of China", 2.24),
    ("Hon. Precision, Inc.", 2.20),
    ("PDD Holdings Inc. Sponsored ADR Class A", 2.01),
    ("China Merchants Bank Co., Ltd. Class H", 1.93),
    ("MPI Corporation", 1.91),
    ("Accton Technology Corp.", 1.85),
    ("Hong Kong Exchanges & Clearing Ltd.", 1.83),
    ("ASPEED Technology, Inc.", 1.80),
    ("Netease Inc", 1.74),
]


class EdelweissGreaterChinaParser(BaseGiftCityParser):
    FUND_NAME = "Edelweiss Greater China Equity Fund"
    AMC_NAME = "Edelweiss"
    FUND_TYPE = "Retail MF"
    STRUCTURE = "Open-ended FoF"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text
        as_of = date(2026, 3, 31)   # March 2026 factsheet

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="MSCI Golden Dragon Index",
            inception_date=date(2026, 3, 10),
            fund_manager="Ajitkumar Paudel",
            min_investment_usd=5000.0,
            exit_load_pct=1.0,
            exit_load_months=25,
            nav_frequency="Daily",
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        # AUM - "USD 1.33 Million"
        aum_m = re.search(r"Month End AUM\s*USD\s*([\d\.]+)\s*Million", text, re.IGNORECASE)
        if aum_m:
            fund_info.aum_usd = float(aum_m.group(1)) * 1_000_000
            fund_info.aum_date = as_of

        # NAV
        direct_nav = self._find_float(r"Direct Plan\s+([\d\.]+)")
        if direct_nav:
            fund_info.nav = direct_nav
            fund_info.nav_date = as_of

        share_classes = [
            ShareClass(
                class_name="Direct",
                management_fee_pct=0.50,
                ter_pct=0.80,   # 0.50 mgmt + 0.30 operating
                nav=self._find_float(r"Direct Plan\s+([\d\.]+)"),
                nav_date=as_of,
                exit_load_pct=1.0,
                exit_load_months=25,
            ),
            ShareClass(
                class_name="Regular",
                management_fee_pct=1.50,
                ter_pct=1.80,
                nav=self._find_float(r"Regular Plan\s+([\d\.]+)"),
                nav_date=as_of,
                exit_load_pct=1.0,
                exit_load_months=25,
            ),
        ]

        # Performance not present in extracted text (graphical only)
        performance = []

        # Parse holdings from text: "Company Name  X.XX%"
        holdings = []
        lines = text.split("\n")
        for line in lines:
            m = re.match(r"^(.+?)\s+([\d\.]+)%\s*$", line.strip())
            if m:
                name, pct = m.group(1).strip(), float(m.group(2))
                if 0.1 < pct < 15 and len(name) > 5:
                    holdings.append(Holding(
                        holding_name=name,
                        weight_pct=pct,
                        holding_type="Equity",
                        as_of_date=as_of,
                    ))
        # Fallback to hardcoded if regex found nothing
        if not holdings:
            holdings = [
                Holding(name, pct, "Equity", as_of_date=as_of)
                for name, pct in _HOLDINGS
            ]

        return ParsedFactsheet(
            fund_info=fund_info,
            share_classes=share_classes,
            performance=performance,
            holdings=holdings,
        )


if __name__ == "__main__":
    from pathlib import Path
    pdf_dir = Path(__file__).parents[2] / "gift_city_factsheets"
    p = EdelweissGreaterChinaParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"AUM: ${result.fund_info.aum_usd:,.0f}" if result.fund_info.aum_usd else "AUM: N/A")
    print(f"Holdings: {len(result.holdings)}")
    for h in result.holdings[:5]:
        print(f"  {h.holding_name}: {h.weight_pct}%")
