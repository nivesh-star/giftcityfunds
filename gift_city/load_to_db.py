"""
Load parsed GIFT City factsheet data into the database.

Usage:
    python3 -m gift_city.load_to_db                  # run all parsers
    python3 -m gift_city.load_to_db --fund dsp       # run single parser by slug

Tables written to: gift_city_funds, gift_city_share_classes, gift_city_performance,
                   gift_city_holdings, gift_city_allocations, gift_city_risk_metrics
"""
from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path

import psycopg2
import psycopg2.extras

from database_config import resolve_dsn

from gift_city.parsers.base import BaseGiftCityParser, ParsedFactsheet
from gift_city.parsers.dsp_global_equity import DSPGlobalEquityParser
from gift_city.parsers.ppfas_nasdaq100 import PPFASNasdaq100Parser
from gift_city.parsers.ppfas_sp500 import PPFASSandP500Parser
from gift_city.parsers.ppfas_global_pms import PPFASGlobalPMSParser
from gift_city.parsers.edelweiss_greater_china import EdelweissGreaterChinaParser
from gift_city.parsers.marcellus_global_equity import MarcellusGlobalEquityParser
from gift_city.parsers.marcellus_gcp import MarcellusGCPParser
from gift_city.parsers.mirae_global_allocation import MiraeGlobalAllocationParser
from gift_city.parsers.baroda_bnp_us_smallcap import BarodaBNPUSSmallcapParser
from gift_city.parsers.absl_global_bluechip import ABSLGlobalBluechipParser
from gift_city.parsers.rational_gold_silver import RationalGoldSilverParser
from gift_city.parsers.unifi_g20 import UnifiG20Parser
from gift_city.parsers.phillip_pioneer import PhillipPioneerParser
from gift_city.parsers.ashoka_whiteoak_em import AshokaWhiteOakEMParser

logger = logging.getLogger(__name__)

FACTSHEET_DIR = Path(__file__).parent.parent / "gift_city_factsheets"

PARSERS: dict[str, tuple[type[BaseGiftCityParser], str]] = {
    "dsp":          (DSPGlobalEquityParser,     "DSP_Global_Equity_Fund.pdf"),
    "ppfas_nq":     (PPFASNasdaq100Parser,      "PPFAS_Nasdaq_100_Fund.pdf"),
    "ppfas_sp":     (PPFASSandP500Parser,       "PPFAS_S&P_500_Fund.pdf"),
    "ppfas_pms":    (PPFASGlobalPMSParser,      "PPFAS_Global_Investing_Strategy_PMS.pdf"),
    "edelweiss":    (EdelweissGreaterChinaParser,"Edelweiss_Greater_China_Fund.pdf"),
    "marcellus_ge": (MarcellusGlobalEquityParser,"Marcellus_Global_Equity_Fund.pdf"),
    "marcellus_gcp":(MarcellusGCPParser,        "Marcellus_GCP_Fund.pdf"),
    "mirae":        (MiraeGlobalAllocationParser,"Mirae_Asset_Global_Allocation_Fund.pdf"),
    "baroda":       (BarodaBNPUSSmallcapParser,  "Baroda_BNP_Paribas_US_Smallcap_Fund.pdf"),
    "absl":         (ABSLGlobalBluechipParser,   "ABSL_Global_Bluechip_Equity_Fund.pdf"),
    "rational":     (RationalGoldSilverParser,   "Rational_Gold_&_Silver_Miners_Fund.pdf"),
    "unifi":        (UnifiG20Parser,             "Unifi_G20_Fund.pdf"),
    "phillip":      (PhillipPioneerParser,       "Phillip_Int_Pioneer_Portfolio.pdf"),
    "ashoka":       (AshokaWhiteOakEMParser,     "Ashoka_WhiteOak_Emerging_Markets_Fund_Ex_India.pdf"),
}


def _upsert_fund(cur, fs: ParsedFactsheet) -> int:
    fi = fs.fund_info
    params = {
        "fund_name":        fi.fund_name,
        "amc_name":         fi.amc_name,
        "fund_type":        fi.fund_type,
        "structure":        fi.structure,
        "domicile":         fi.domicile,
        "base_currency":    fi.base_currency,
        "benchmark_index":  fi.benchmark_index,
        "inception_date":   fi.inception_date,
        "isin":             fi.isin,
        "bloomberg_ticker": fi.bloomberg_ticker,
        "fund_manager":     fi.fund_manager,
        "aum_usd":          fi.aum_usd,
        "aum_date":         fi.aum_date,
        "nav":              fi.nav,
        "nav_date":         fi.nav_date,
        "min_investment_usd": fi.min_investment_usd,
        "exit_load_pct":    fi.exit_load_pct,
        "exit_load_months": fi.exit_load_months,
        "lock_in_months":   fi.lock_in_months,
        "nav_frequency":    fi.nav_frequency,
        "ltcg_tax_pct":     fi.ltcg_tax_pct,
        "stcg_tax_pct":     fi.stcg_tax_pct,
        "factsheet_url":    fi.factsheet_url,
        "factsheet_path":   fi.factsheet_path,
        "factsheet_date":   fi.factsheet_date,
    }
    cur.execute("""
        INSERT INTO gift_city_funds (
            fund_name, amc_name, fund_type, structure, domicile, base_currency,
            benchmark_index, inception_date, isin, bloomberg_ticker, fund_manager,
            aum_usd, aum_date, nav, nav_date, min_investment_usd,
            exit_load_pct, exit_load_months, lock_in_months, nav_frequency,
            ltcg_tax_pct, stcg_tax_pct, factsheet_url, factsheet_path, factsheet_date,
            updated_at
        ) VALUES (
            %(fund_name)s, %(amc_name)s, %(fund_type)s, %(structure)s, %(domicile)s,
            %(base_currency)s, %(benchmark_index)s, %(inception_date)s, %(isin)s,
            %(bloomberg_ticker)s, %(fund_manager)s, %(aum_usd)s, %(aum_date)s,
            %(nav)s, %(nav_date)s, %(min_investment_usd)s, %(exit_load_pct)s,
            %(exit_load_months)s, %(lock_in_months)s, %(nav_frequency)s,
            %(ltcg_tax_pct)s, %(stcg_tax_pct)s, %(factsheet_url)s, %(factsheet_path)s,
            %(factsheet_date)s, NOW()
        )
        -- COALESCE(EXCLUDED.x, existing.x): if the new parse returns NULL for an
        -- optional field (e.g. isin not yet issued, nav not in this PDF), keep the
        -- previously stored non-null value rather than overwriting it with NULL.
        -- Consequence: a field that genuinely becomes NULL cannot be cleared via a
        -- re-scrape; use a direct UPDATE if you need to blank a field intentionally.
        ON CONFLICT (fund_name) DO UPDATE SET
            amc_name          = EXCLUDED.amc_name,
            fund_type         = EXCLUDED.fund_type,
            structure         = EXCLUDED.structure,
            domicile          = EXCLUDED.domicile,
            benchmark_index   = EXCLUDED.benchmark_index,
            inception_date    = COALESCE(EXCLUDED.inception_date, gift_city_funds.inception_date),
            isin              = COALESCE(EXCLUDED.isin, gift_city_funds.isin),
            bloomberg_ticker  = COALESCE(EXCLUDED.bloomberg_ticker, gift_city_funds.bloomberg_ticker),
            fund_manager      = COALESCE(EXCLUDED.fund_manager, gift_city_funds.fund_manager),
            aum_usd           = COALESCE(EXCLUDED.aum_usd, gift_city_funds.aum_usd),
            aum_date          = COALESCE(EXCLUDED.aum_date, gift_city_funds.aum_date),
            nav               = COALESCE(EXCLUDED.nav, gift_city_funds.nav),
            nav_date          = COALESCE(EXCLUDED.nav_date, gift_city_funds.nav_date),
            min_investment_usd= COALESCE(EXCLUDED.min_investment_usd, gift_city_funds.min_investment_usd),
            exit_load_pct     = COALESCE(EXCLUDED.exit_load_pct, gift_city_funds.exit_load_pct),
            exit_load_months  = COALESCE(EXCLUDED.exit_load_months, gift_city_funds.exit_load_months),
            lock_in_months    = COALESCE(EXCLUDED.lock_in_months, gift_city_funds.lock_in_months),
            ltcg_tax_pct      = COALESCE(EXCLUDED.ltcg_tax_pct, gift_city_funds.ltcg_tax_pct),
            stcg_tax_pct      = COALESCE(EXCLUDED.stcg_tax_pct, gift_city_funds.stcg_tax_pct),
            factsheet_url     = COALESCE(EXCLUDED.factsheet_url, gift_city_funds.factsheet_url),
            factsheet_path    = EXCLUDED.factsheet_path,
            factsheet_date    = EXCLUDED.factsheet_date,
            updated_at        = NOW()
        RETURNING id
    """, params)
    return cur.fetchone()[0]


def _upsert_share_classes(cur, fund_id: int, fs: ParsedFactsheet) -> None:
    for sc in fs.share_classes:
        cur.execute("""
            INSERT INTO gift_city_share_classes (
                fund_id, class_name, investor_type, min_investment_usd,
                management_fee_pct, performance_fee_pct, hurdle_rate_pct, ter_pct,
                nav, nav_date, exit_load_pct, exit_load_months, lock_in_months
            ) VALUES (
                %(fund_id)s, %(class_name)s, %(investor_type)s, %(min_investment_usd)s,
                %(management_fee_pct)s, %(performance_fee_pct)s, %(hurdle_rate_pct)s,
                %(ter_pct)s, %(nav)s, %(nav_date)s, %(exit_load_pct)s,
                %(exit_load_months)s, %(lock_in_months)s
            )
            ON CONFLICT (fund_id, class_name) DO UPDATE SET
                investor_type       = EXCLUDED.investor_type,
                min_investment_usd  = COALESCE(EXCLUDED.min_investment_usd, gift_city_share_classes.min_investment_usd),
                management_fee_pct  = COALESCE(EXCLUDED.management_fee_pct, gift_city_share_classes.management_fee_pct),
                performance_fee_pct = COALESCE(EXCLUDED.performance_fee_pct, gift_city_share_classes.performance_fee_pct),
                hurdle_rate_pct     = COALESCE(EXCLUDED.hurdle_rate_pct, gift_city_share_classes.hurdle_rate_pct),
                ter_pct             = COALESCE(EXCLUDED.ter_pct, gift_city_share_classes.ter_pct),
                nav                 = COALESCE(EXCLUDED.nav, gift_city_share_classes.nav),
                nav_date            = COALESCE(EXCLUDED.nav_date, gift_city_share_classes.nav_date),
                exit_load_pct       = COALESCE(EXCLUDED.exit_load_pct, gift_city_share_classes.exit_load_pct),
                exit_load_months    = COALESCE(EXCLUDED.exit_load_months, gift_city_share_classes.exit_load_months),
                lock_in_months      = COALESCE(EXCLUDED.lock_in_months, gift_city_share_classes.lock_in_months)
        """, {"fund_id": fund_id, **sc.__dict__})


def _upsert_performance(cur, fund_id: int, fs: ParsedFactsheet) -> None:
    if not fs.performance:
        return
    rows = [
        (fund_id, r.share_class, r.period, r.fund_return_pct, r.benchmark_return_pct,
         r.excess_return_pct, r.currency, r.as_of_date, r.is_annualized)
        for r in fs.performance
    ]
    psycopg2.extras.execute_values(cur, """
        INSERT INTO gift_city_performance (
            fund_id, share_class, period, fund_return_pct, benchmark_return_pct,
            excess_return_pct, currency, as_of_date, is_annualized
        ) VALUES %s
        ON CONFLICT (fund_id, COALESCE(share_class, ''), period,
                     COALESCE(currency, 'USD'), COALESCE(as_of_date, '1900-01-01'::date))
        DO UPDATE SET
            fund_return_pct      = EXCLUDED.fund_return_pct,
            benchmark_return_pct = EXCLUDED.benchmark_return_pct,
            excess_return_pct    = EXCLUDED.excess_return_pct,
            is_annualized        = EXCLUDED.is_annualized
    """, rows)


def _upsert_holdings(cur, fund_id: int, fs: ParsedFactsheet) -> None:
    if not fs.holdings:
        return
    rows = [
        (fund_id, h.as_of_date, h.holding_name, h.holding_type, h.weight_pct,
         h.country, h.sector, h.isin, h.contribution_alpha_bps)
        for h in fs.holdings
    ]
    psycopg2.extras.execute_values(cur, """
        INSERT INTO gift_city_holdings (
            fund_id, as_of_date, holding_name, holding_type, weight_pct,
            country, sector, isin, contribution_alpha_bps
        ) VALUES %s
        ON CONFLICT (fund_id, COALESCE(as_of_date, '1900-01-01'::date), holding_name) DO UPDATE SET
            holding_type           = EXCLUDED.holding_type,
            weight_pct             = EXCLUDED.weight_pct,
            country                = EXCLUDED.country,
            sector                 = EXCLUDED.sector,
            isin                   = EXCLUDED.isin,
            contribution_alpha_bps = EXCLUDED.contribution_alpha_bps
    """, rows)


def _upsert_allocations(cur, fund_id: int, fs: ParsedFactsheet) -> None:
    if not fs.allocations:
        return
    rows = [
        (fund_id, a.as_of_date, a.allocation_type, a.category,
         a.weight_pct, a.benchmark_weight_pct, a.active_weight_pct)
        for a in fs.allocations
    ]
    psycopg2.extras.execute_values(cur, """
        INSERT INTO gift_city_allocations (
            fund_id, as_of_date, allocation_type, category,
            weight_pct, benchmark_weight_pct, active_weight_pct
        ) VALUES %s
        ON CONFLICT (fund_id, COALESCE(as_of_date, '1900-01-01'::date), allocation_type, category) DO UPDATE SET
            weight_pct           = EXCLUDED.weight_pct,
            benchmark_weight_pct = EXCLUDED.benchmark_weight_pct,
            active_weight_pct    = EXCLUDED.active_weight_pct
    """, rows)


def _upsert_risk_metrics(cur, fund_id: int, fs: ParsedFactsheet) -> None:
    if not fs.risk_metrics:
        return
    for rm in fs.risk_metrics:
        cur.execute("""
            INSERT INTO gift_city_risk_metrics (
                fund_id, as_of_date, period, alpha_pct, beta, r_squared,
                tracking_error_pct, information_ratio, sharpe_ratio,
                upside_capture_pct, downside_capture_pct, active_share_pct, batting_average_pct
            ) VALUES (
                %(fund_id)s, %(as_of_date)s, %(period)s, %(alpha_pct)s, %(beta)s,
                %(r_squared)s, %(tracking_error_pct)s, %(information_ratio)s, %(sharpe_ratio)s,
                %(upside_capture_pct)s, %(downside_capture_pct)s, %(active_share_pct)s,
                %(batting_average_pct)s
            )
            ON CONFLICT (fund_id, COALESCE(as_of_date, '1900-01-01'::date), COALESCE(period, ''))
            DO UPDATE SET
                alpha_pct            = COALESCE(EXCLUDED.alpha_pct, gift_city_risk_metrics.alpha_pct),
                beta                 = COALESCE(EXCLUDED.beta, gift_city_risk_metrics.beta),
                r_squared            = COALESCE(EXCLUDED.r_squared, gift_city_risk_metrics.r_squared),
                tracking_error_pct   = COALESCE(EXCLUDED.tracking_error_pct, gift_city_risk_metrics.tracking_error_pct),
                information_ratio    = COALESCE(EXCLUDED.information_ratio, gift_city_risk_metrics.information_ratio),
                sharpe_ratio         = COALESCE(EXCLUDED.sharpe_ratio, gift_city_risk_metrics.sharpe_ratio),
                upside_capture_pct   = COALESCE(EXCLUDED.upside_capture_pct, gift_city_risk_metrics.upside_capture_pct),
                downside_capture_pct = COALESCE(EXCLUDED.downside_capture_pct, gift_city_risk_metrics.downside_capture_pct),
                active_share_pct     = COALESCE(EXCLUDED.active_share_pct, gift_city_risk_metrics.active_share_pct),
                batting_average_pct  = COALESCE(EXCLUDED.batting_average_pct, gift_city_risk_metrics.batting_average_pct)
        """, {"fund_id": fund_id, **rm.__dict__})


def _load_url_map() -> dict[str, str]:
    """Read the sidecar urls.json written by download_factsheets.py (filename → drive URL)."""
    path = FACTSHEET_DIR / "urls.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def load_factsheet(slug: str, dry_run: bool = False) -> ParsedFactsheet:
    parser_cls, filename = PARSERS[slug]
    pdf_path = FACTSHEET_DIR / filename
    parser = parser_cls(pdf_path)
    fs = parser.parse()

    # Inject the canonical source URL if the downloader recorded it
    url_map = _load_url_map()
    if filename in url_map and fs.fund_info.factsheet_url is None:
        fs.fund_info.factsheet_url = url_map[filename]

    logger.info("Parsed %s: %d holdings, %d perf rows, %d alloc rows",
                fs.fund_info.fund_name, len(fs.holdings),
                len(fs.performance), len(fs.allocations))
    if dry_run:
        return fs

    conn = psycopg2.connect(resolve_dsn())
    try:
        with conn:
            with conn.cursor() as cur:
                fund_id = _upsert_fund(cur, fs)
                _upsert_share_classes(cur, fund_id, fs)
                _upsert_performance(cur, fund_id, fs)
                _upsert_holdings(cur, fund_id, fs)
                _upsert_allocations(cur, fund_id, fs)
                _upsert_risk_metrics(cur, fund_id, fs)
        logger.info("Loaded %s (fund_id=%d)", fs.fund_info.fund_name, fund_id)
    finally:
        conn.close()
    return fs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load GIFT City factsheets to DB")
    parser.add_argument("--fund", choices=list(PARSERS), help="Load single fund only")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write to DB")
    args = parser.parse_args()

    slugs = [args.fund] if args.fund else list(PARSERS)
    for slug in slugs:
        try:
            load_factsheet(slug, dry_run=args.dry_run)
        except Exception as exc:
            logger.error("Failed to load %s: %s", slug, exc)


if __name__ == "__main__":
    main()
