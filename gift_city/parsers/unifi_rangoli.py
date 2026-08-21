"""Unifi Rangoli India Fund -- GIFT City AIF Cat III factsheet parser.

NOTE: Like edelweiss_multimanager.py, this is not parsed from a local PDF --
it's a sourced snapshot transcribed from Unifi's own monthly "Portfolio
Disclosure" PDF, fetched directly from their site during AMC research:
https://unifiinvestment.com/wp-content/uploads/2026/07/Rangoli-India-Fund-
Portfolio-Disclosure-June-2026.pdf
Unifi publishes a new one of these most months -- rerun against the latest
URL and update _HOLDINGS below to refresh.
"""
from __future__ import annotations
from datetime import date

from gift_city.parsers.base import (
    BaseGiftCityParser, FundInfo, Holding, Allocation, ParsedFactsheet,
)

FACTSHEET_FILENAME = "Rangoli-India-Fund-Portfolio-Disclosure-June-2026.pdf"
FACTSHEET_URL = (
    "https://unifiinvestment.com/wp-content/uploads/2026/07/"
    "Rangoli-India-Fund-Portfolio-Disclosure-June-2026.pdf"
)

# Full 29-stock holdings table + cash, as disclosed in the June-2026
# Portfolio Disclosure. (sector, market_cap) kept alongside weight so the
# allocation breakdown below can be derived from the same source rather than
# re-typed separately.
_HOLDINGS = [
    ("Redington Ltd.", 9.3, "Information Technology", "Small Cap"),
    ("Narayana Hrudayalaya Ltd.", 8.7, "Health Care", "Mid Cap"),
    ("Sagility Ltd.", 7.0, "Industrials", "Small Cap"),
    ("Bank Of Baroda Ltd.", 6.9, "Financials", "Large Cap"),
    ("The South Indian Bank Ltd.", 5.4, "Financials", "Small Cap"),
    ("Mahindra & Mahindra Ltd.", 4.8, "Consumer Discretionary", "Large Cap"),
    ("Kotak Mahindra Bank Ltd.", 4.7, "Financials", "Large Cap"),
    ("Marksans Pharma Ltd.", 4.5, "Health Care", "Small Cap"),
    ("Kovai Medical Center And Hospital Ltd.", 4.0, "Health Care", "Small Cap"),
    ("Alivus Life Sciences Ltd.", 3.7, "Health Care", "Small Cap"),
    ("Caplin Point Laboratories Ltd.", 3.2, "Health Care", "Small Cap"),
    ("RPG Life Sciences Ltd.", 2.7, "Health Care", "Small Cap"),
    ("Garware Technical Fibres Ltd.", 2.6, "Consumer Discretionary", "Small Cap"),
    ("S.J.S. Enterprises Ltd.", 2.6, "Consumer Discretionary", "Small Cap"),
    ("Macrotech Developers Ltd.", 2.5, "Real Estate", "Large Cap"),
    ("Pearl Global Industries Ltd.", 2.5, "Consumer Discretionary", "Small Cap"),
    ("Coromandel International Ltd.", 2.4, "Materials", "Mid Cap"),
    ("Bayer Cropscience Ltd.", 2.3, "Materials", "Small Cap"),
    ("Aditya Birla Sun Life AMC Ltd.", 2.1, "Financials", "Small Cap"),
    ("Can Fin Homes Ltd.", 2.1, "Financials", "Small Cap"),
    ("HDFC AMC", 1.8, "Financials", "Large Cap"),
    ("Apar Industries Ltd.", 1.7, "Industrials", "Mid Cap"),
    ("Home First Finance Company India Ltd.", 1.6, "Financials", "Small Cap"),
    ("Indraprastha Medical Corporation Ltd.", 1.5, "Health Care", "Small Cap"),
    ("Fedbank Financial Services Ltd.", 1.3, "Financials", "Small Cap"),
    ("Dixon Technologies Ltd.", 1.2, "Consumer Discretionary", "Mid Cap"),
    ("Centum Electronics Ltd.", 1.1, "Information Technology", "Small Cap"),
    ("Godrej Agrovet Ltd.", 0.9, "Consumer Staples", "Small Cap"),
    ("Asm Technologies Ltd", 0.7, "Information Technology", "Small Cap"),
]
_CASH_PCT = 4.3
_AUM_USD_MILLION = 117.48


class UnifiRangoliParser(BaseGiftCityParser):
    FUND_NAME = "Rangoli India Fund"
    AMC_NAME = "Unifi Investment Management LLP"
    FUND_TYPE = "AIF Cat III"
    STRUCTURE = "Open-ended"
    FACTSHEET_FILENAME = FACTSHEET_FILENAME

    def parse(self) -> ParsedFactsheet:
        as_of = date(2026, 6, 30)

        fund_info = FundInfo(
            fund_name=self.FUND_NAME,
            amc_name=self.AMC_NAME,
            fund_type=self.FUND_TYPE,
            structure=self.STRUCTURE,
            domicile="GIFT City",
            base_currency="USD",
            benchmark_index="MSCI India (USD)",
            aum_usd=_AUM_USD_MILLION * 1_000_000,
            aum_date=as_of,
            factsheet_url=FACTSHEET_URL,
            factsheet_date=as_of,
        )

        holdings = [
            Holding(holding_name=name, weight_pct=pct, holding_type="Equity",
                    sector=sector, as_of_date=as_of)
            for name, pct, sector, _cap in _HOLDINGS
        ]
        holdings.append(Holding(holding_name="Cash", weight_pct=_CASH_PCT,
                                 holding_type="Cash", as_of_date=as_of))

        # Sector allocation aggregated from the same holdings table.
        sector_totals: dict[str, float] = {}
        for _name, pct, sector, _cap in _HOLDINGS:
            sector_totals[sector] = sector_totals.get(sector, 0.0) + pct
        allocations = [
            Allocation("Sector", sector, round(pct, 2), as_of_date=as_of)
            for sector, pct in sector_totals.items()
        ]
        allocations.append(Allocation("Sector", "Cash", _CASH_PCT, as_of_date=as_of))

        return ParsedFactsheet(
            fund_info=fund_info,
            holdings=holdings,
            allocations=allocations,
        )


if __name__ == "__main__":
    p = UnifiRangoliParser(FACTSHEET_FILENAME)
    result = p.parse()
    print(f"Fund: {result.fund_info.fund_name}")
    print(f"AUM: ${result.fund_info.aum_usd:,.0f}")
    print(f"Holdings: {len(result.holdings)}")
    print(f"Allocations: {len(result.allocations)}")
