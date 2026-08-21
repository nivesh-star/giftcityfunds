"""Base class for GIFT City outbound fund factsheet parsers."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from pypdf import PdfReader


@dataclass
class FundInfo:
    fund_name: str
    amc_name: Optional[str] = None
    fund_type: Optional[str] = None          # 'Retail MF', 'AIF Cat III', 'UCITS', 'PMS'
    structure: Optional[str] = None          # 'Open-ended', 'Close-ended', 'FoF', 'Feeder'
    domicile: str = "GIFT City"
    base_currency: str = "USD"
    benchmark_index: Optional[str] = None
    inception_date: Optional[date] = None
    isin: Optional[str] = None
    bloomberg_ticker: Optional[str] = None
    fund_manager: Optional[str] = None
    aum_usd: Optional[float] = None
    aum_date: Optional[date] = None
    nav: Optional[float] = None
    nav_date: Optional[date] = None
    min_investment_usd: Optional[float] = None
    exit_load_pct: Optional[float] = None
    exit_load_months: Optional[int] = None
    lock_in_months: Optional[int] = None
    nav_frequency: Optional[str] = None
    ltcg_tax_pct: Optional[float] = None
    stcg_tax_pct: Optional[float] = None
    factsheet_url: Optional[str] = None          # Google Drive / source URL (durable)
    factsheet_path: Optional[str] = None         # local path (transient, empty on ECS)
    factsheet_date: Optional[date] = None


@dataclass
class ShareClass:
    class_name: str
    investor_type: Optional[str] = None
    min_investment_usd: Optional[float] = None
    management_fee_pct: Optional[float] = None
    performance_fee_pct: Optional[float] = None
    hurdle_rate_pct: Optional[float] = None
    ter_pct: Optional[float] = None
    nav: Optional[float] = None
    nav_date: Optional[date] = None
    exit_load_pct: Optional[float] = None
    exit_load_months: Optional[int] = None
    lock_in_months: Optional[int] = None


@dataclass
class PerformanceRow:
    period: str                              # '1M', '3M', '6M', '1Y', '2Y', '3Y', 'SI'
    fund_return_pct: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    excess_return_pct: Optional[float] = None
    share_class: Optional[str] = None
    currency: str = "USD"
    as_of_date: Optional[date] = None
    is_annualized: Optional[bool] = None


@dataclass
class Holding:
    holding_name: str
    weight_pct: Optional[float] = None
    holding_type: Optional[str] = None      # 'Equity', 'ETF', 'Cash', 'Money Market'
    country: Optional[str] = None
    sector: Optional[str] = None
    isin: Optional[str] = None
    contribution_alpha_bps: Optional[float] = None
    as_of_date: Optional[date] = None


@dataclass
class Allocation:
    allocation_type: str                     # 'Geography', 'Sector', 'MarketCap', 'Theme'
    category: str
    weight_pct: Optional[float] = None
    benchmark_weight_pct: Optional[float] = None
    active_weight_pct: Optional[float] = None
    as_of_date: Optional[date] = None


@dataclass
class RiskMetrics:
    period: Optional[str] = None
    alpha_pct: Optional[float] = None
    beta: Optional[float] = None
    r_squared: Optional[float] = None
    tracking_error_pct: Optional[float] = None
    information_ratio: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    upside_capture_pct: Optional[float] = None
    downside_capture_pct: Optional[float] = None
    active_share_pct: Optional[float] = None
    batting_average_pct: Optional[float] = None
    as_of_date: Optional[date] = None


@dataclass
class ParsedFactsheet:
    fund_info: FundInfo
    share_classes: list[ShareClass] = field(default_factory=list)
    performance: list[PerformanceRow] = field(default_factory=list)
    holdings: list[Holding] = field(default_factory=list)
    allocations: list[Allocation] = field(default_factory=list)
    risk_metrics: list[RiskMetrics] = field(default_factory=list)


class BaseGiftCityParser:
    """
    Base parser for GIFT City outbound fund factsheets.
    Subclasses override parse() and may call helpers from this class.
    """
    FUND_NAME: str = ""
    AMC_NAME: str = ""
    FUND_TYPE: str = ""      # 'Retail MF', 'AIF Cat III', 'UCITS', 'PMS'
    STRUCTURE: str = ""      # 'Open-ended', 'Close-ended', 'FoF', 'Feeder'
    FACTSHEET_FILENAME: str = ""

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self._pages: list[str] = []
        self._full_text: str = ""

    def _load(self) -> None:
        if self._pages:
            return
        reader = PdfReader(str(self.pdf_path))
        self._pages = [p.extract_text() or "" for p in reader.pages]
        self._full_text = "\n".join(self._pages)

    def parse(self) -> ParsedFactsheet:
        raise NotImplementedError

    # ── Regex helpers ──────────────────────────────────────────────────────

    def _find(self, pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
        """Return first capture group match from full text."""
        m = re.search(pattern, self._full_text, flags)
        return m.group(1).strip() if m else None

    def _find_float(self, pattern: str) -> Optional[float]:
        val = self._find(pattern)
        if val is None:
            return None
        val = val.replace(",", "").replace("%", "").strip()
        # Some PDFs' text layer renders overlapping table cells as a doubled
        # string (e.g. "9.569.56" for a NAV of 9.56) -- if the string is an
        # exact self-concatenation of its own first half, take just the half.
        if len(val) % 2 == 0 and val[: len(val) // 2] == val[len(val) // 2 :]:
            val = val[: len(val) // 2]
        try:
            return float(val)
        except ValueError:
            return None

    def _parse_date(self, text: str) -> Optional[date]:
        """Try common date formats used in Indian/GIFT City factsheets."""
        if not text:
            return None
        text = text.strip()
        fmts = [
            "%d %B %Y", "%B %d, %Y", "%d-%b-%Y", "%d/%m/%Y",
            "%B %Y", "%b %Y", "%d %b %Y", "%d-%m-%Y",
        ]
        for fmt in fmts:
            try:
                from datetime import datetime
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_aum(self, text: str) -> Optional[float]:
        """Parse AUM strings like 'USD 32 M', 'US$ 11.85 Mn', 'USD 1.33 Million'."""
        if not text:
            return None
        text = text.strip().upper()
        m = re.search(r"([\d,\.]+)\s*(MN|MILLION|M\b|B\b|BILLION)", text)
        if not m:
            return None
        val = float(m.group(1).replace(",", ""))
        mult = {"MN": 1e6, "MILLION": 1e6, "M": 1e6, "B": 1e9, "BILLION": 1e9}
        return val * mult.get(m.group(2), 1e6)

    def _parse_period_returns(
        self,
        text: str,
        as_of_date: Optional[date] = None,
        share_class: Optional[str] = None,
        currency: str = "USD",
    ) -> list[PerformanceRow]:
        """
        Generic parser for lines like:
          1 Month  0.3%  0.3%
          Since Inception  25.80%  27.03%
        Returns list of PerformanceRow. Subclasses can call this on a
        relevant page/section of text.
        """
        period_map = {
            r"1\s*month": "1M",
            r"3\s*month": "3M",
            r"6\s*month": "6M",
            r"1\s*year": "1Y",
            r"2\s*year": "2Y",
            r"3\s*year": "3Y",
            r"since\s*inception": "SI",
            r"\bsi\b": "SI",
            r"ytd": "YTD",
            r"qtd": "QTD",
        }
        annualized_periods = {"1Y", "2Y", "3Y", "SI"}
        rows = []
        for pat, period_code in period_map.items():
            m = re.search(
                pat + r"[:\s]+([-\d\.]+)%?\s+([-\d\.]+)%?",
                text,
                re.IGNORECASE,
            )
            if m:
                try:
                    fund_ret = float(m.group(1))
                    bench_ret = float(m.group(2))
                    rows.append(PerformanceRow(
                        period=period_code,
                        fund_return_pct=fund_ret,
                        benchmark_return_pct=bench_ret,
                        excess_return_pct=round(fund_ret - bench_ret, 4),
                        share_class=share_class,
                        currency=currency,
                        as_of_date=as_of_date,
                        is_annualized=period_code in annualized_periods,
                    ))
                except ValueError:
                    continue
        return rows
