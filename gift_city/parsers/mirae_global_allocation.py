"""Mirae Asset Global Allocation Fund — GIFT City AIF Cat III Close-ended parser.

ETF holdings from page 21 (last column = most recent month).
Country & sector allocations from page 22 (first column = most recent month).
Performance by share class from page 25 (1M / 3M / 6M / SI).
"""
from __future__ import annotations
import re
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, ShareClass, PerformanceRow,
    Holding, Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Mirae_Asset_Global_Allocation_Fund.pdf"

_SHARE_CLASS_DEFS = [
    ("D1", "Resident"),
    ("D2", "Resident"),
    ("P",  "Institutional"),
    ("R1", "NRI"),
    ("R2", "NRI"),
    ("A",  "Accredited"),
    ("I",  "Institutional"),
]

_PERF_PERIODS = ["1M", "3M", "6M", "SI"]

# Words that indicate a line is a section header, not a name continuation
_HEADER_RE = re.compile(
    r"\b(?:Allocation|Weightage|Exposure|Portfolio|Source|Performance|20\d\d)\b",
    re.IGNORECASE,
)


def _fix_wrapped_lines(text: str) -> str:
    """Join a line with the previous when it's a name continuation.

    Joins when: prev has no %, current has %, and prev doesn't look like a header.
    This fixes multi-line country/sector names without merging header rows.
    """
    fixed: list[str] = []
    for line in text.split("\n"):
        if (
            fixed
            and "%" not in fixed[-1]
            and "%" in line
            and not _HEADER_RE.search(fixed[-1])
        ):
            fixed[-1] = fixed[-1].rstrip() + " " + line.strip()
        else:
            fixed.append(line)
    return "\n".join(fixed)


def _parse_etf_holdings(page_text: str, as_of: date) -> list[Holding]:
    """Page 21: ETF name, type keyword, then monthly % columns.

    We take the last % on each data row (most recent month = right-most column).
    Multi-line names like "Global X Rare Earth...\\nETF Tactical..." are pre-joined.
    """
    text = re.sub(r"\n(ETF\s+(?:Core|Tactical|Defensive))", r" \1", page_text)
    holdings = []
    for line in text.split("\n"):
        m = re.match(r"^(.+?)\s+(Core|Tactical|Defensive)\s+(.*)", line)
        if not m:
            continue
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        rest = m.group(3)
        pcts = re.findall(r"([\d\.]+)%", rest)
        if not pcts:
            continue
        holding_type = "Cash" if name.lower() == "cash" else "ETF"
        holdings.append(Holding(
            holding_name=name,
            weight_pct=float(pcts[-1]),
            holding_type=holding_type,
            as_of_date=as_of,
        ))
    return holdings


def _parse_country_sector(page_text: str, as_of: date) -> list[Allocation]:
    """Page 22: country then sector tables; first % on each row is most recent month."""
    text = _fix_wrapped_lines(page_text)
    allocations = []
    mode: str | None = None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Section triggers
        if "Country Allocation" in line:
            mode = "country"
        elif "Top 5 GICS" in line or re.search(r"\bSector\s+Mar\b", line):
            mode = "sector"
        elif line.startswith("Source:") or line.startswith("➢"):
            mode = None

        if mode and "%" in line:
            m = re.match(r"^(.+?)\s+([\d\.]+)%", line)
            if not m:
                continue
            category = m.group(1).strip()
            # Skip header-like content (date strings, keywords)
            if re.search(r"(?:Mar|Feb|Jan)\s+20\d\d|Allocation|GICS", category):
                continue
            allocations.append(Allocation(
                allocation_type="Geography" if mode == "country" else "Sector",
                category=re.sub(r"\s+", " ", category),
                weight_pct=float(m.group(2)),
                as_of_date=as_of,
            ))

    return allocations


def _parse_performance(page_text: str, as_of: date) -> list[PerformanceRow]:
    """Page 25: performance table with 7 share classes × 4 periods."""
    valid_cls = {c for c, _ in _SHARE_CLASS_DEFS}
    rows = []
    for line in page_text.split("\n"):
        line = line.strip()
        m = re.match(r"^([A-Z][A-Z0-9]?)\*?\s+(.*)", line)
        if not m or m.group(1) not in valid_cls:
            continue
        cls_name = m.group(1)
        vals_raw = m.group(2).strip().split()
        parsed: list[float | None] = []
        for v in vals_raw:
            if v.upper() in {"NA", "-", "N/A"}:
                parsed.append(None)
            else:
                try:
                    parsed.append(float(v.rstrip("%")))
                except ValueError:
                    pass
        for period, val in zip(_PERF_PERIODS, parsed):
            if val is None:
                continue
            rows.append(PerformanceRow(
                period=period,
                fund_return_pct=val,
                benchmark_return_pct=None,
                currency="USD",
                share_class=cls_name,
                as_of_date=as_of,
                is_annualized=False,
            ))
    return rows


class MiraeGlobalAllocationParser(BaseGiftCityParser):
    FUND_NAME = "Mirae Asset Global Allocation Fund"
    AMC_NAME = "Mirae Asset"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Close-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        self._load()
        text = self._full_text
        as_of = date(2026, 3, 31)

        date_m = re.search(r"Data as on (\d+ \w+ \d{4})", text)
        if date_m:
            d = self._parse_date(date_m.group(1))
            if d:
                as_of = d

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="MSCI ACWI",
            inception_date=date(2025, 9, 10),
            fund_manager=None,
            min_investment_usd=151_000.0,
            nav_frequency="Weekly",
            lock_in_months=36,
            ltcg_tax_pct=12.5,
            factsheet_path=str(self.pdf_path),
            factsheet_date=as_of,
        )

        min_m = re.search(r"Minimum Subscription.*?USD\s*([\d,]+)", text, re.IGNORECASE)
        if min_m:
            fund_info.min_investment_usd = float(min_m.group(1).replace(",", ""))

        share_classes = [
            ShareClass(class_name=cls, investor_type=inv_type, min_investment_usd=151_000.0)
            for cls, inv_type in _SHARE_CLASS_DEFS
        ]

        pages = self._pages
        holdings = _parse_etf_holdings(pages[20], as_of) if len(pages) > 20 else []
        allocations = _parse_country_sector(pages[21], as_of) if len(pages) > 21 else []
        performance = _parse_performance(pages[24], as_of) if len(pages) > 24 else []

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
    p = MiraeGlobalAllocationParser(pdf_dir / FACTSHEET_FILENAME)
    result = p.parse()
    fi = result.fund_info
    print(f"Fund: {fi.fund_name}  as of {fi.factsheet_date}")
    print(f"ETF holdings ({len(result.holdings)}):")
    for h in result.holdings:
        print(f"  {h.holding_name}: {h.weight_pct}%")
    print(f"Allocations ({len(result.allocations)}):")
    for a in result.allocations:
        print(f"  [{a.allocation_type}] {a.category}: {a.weight_pct}%")
    print(f"Performance ({len(result.performance)} rows):")
    by_cls: dict[str, list[str]] = {}
    for r in result.performance:
        by_cls.setdefault(r.share_class, []).append(f"{r.period}:{r.fund_return_pct}%")
    for cls, vals in sorted(by_cls.items()):
        print(f"  {cls}: {', '.join(vals)}")
