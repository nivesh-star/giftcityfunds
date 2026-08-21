"""
Run Girish's gift_city parsers directly against the factsheet PDFs,
bypassing his load_to_db.py (which targets a Postgres DB we don't have).
Dumps each parser's ParsedFactsheet as JSON for inspection/manual review
before anything gets applied to our SQLite DB.
"""
import json
import dataclasses
from datetime import date
from pathlib import Path

FACTSHEET_DIR = Path(__file__).parent / "gift_city_factsheets"

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

PARSERS = {
    "dsp":          (DSPGlobalEquityParser,      "DSP_Global_Equity_Fund.pdf"),
    "ppfas_nq":     (PPFASNasdaq100Parser,       "PPFAS_Nasdaq_100_Fund.pdf"),
    "ppfas_sp":     (PPFASSandP500Parser,        "PPFAS_S&P_500_Fund.pdf"),
    "ppfas_pms":    (PPFASGlobalPMSParser,       "PPFAS_Global_Investing_Strategy_PMS.pdf"),
    "edelweiss":    (EdelweissGreaterChinaParser,"Edelweiss_Greater_China_Fund.pdf"),
    "marcellus_ge": (MarcellusGlobalEquityParser,"Marcellus_Global_Equity_Fund.pdf"),
    "marcellus_gcp":(MarcellusGCPParser,         "Marcellus_GCP_Fund.pdf"),
    "mirae":        (MiraeGlobalAllocationParser,"Mirae_Asset_Global_Allocation_Fund.pdf"),
    "baroda":       (BarodaBNPUSSmallcapParser,  "Baroda_BNP_Paribas_US_Smallcap_Fund.pdf"),
    "absl":         (ABSLGlobalBluechipParser,   "ABSL_Global_Bluechip_Equity_Fund.pdf"),
    "rational":     (RationalGoldSilverParser,   "Rational_Gold_&_Silver_Miners_Fund.pdf"),
    "unifi":        (UnifiG20Parser,             "Unifi_G20_Fund.pdf"),
    "phillip":      (PhillipPioneerParser,       "Phillip_Int_Pioneer_Portfolio.pdf"),
    "ashoka":       (AshokaWhiteOakEMParser,     "Ashoka_WhiteOak_Emerging_Markets_Fund_Ex_India.pdf"),
}


def to_jsonable(obj):
    if dataclasses.is_dataclass(obj):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, list):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


results = {}
errors = {}
for slug, (parser_cls, filename) in PARSERS.items():
    pdf_path = FACTSHEET_DIR / filename
    try:
        parser = parser_cls(str(pdf_path))
        parsed = parser.parse()
        results[slug] = to_jsonable(parsed)
        print(f"OK   {slug:15s} -> fund_name={parsed.fund_info.fund_name!r} "
              f"holdings={len(parsed.holdings)} allocations={len(parsed.allocations)} "
              f"share_classes={len(parsed.share_classes)}")
    except Exception as e:
        errors[slug] = f"{type(e).__name__}: {e}"
        print(f"FAIL {slug:15s} -> {type(e).__name__}: {e}")

out_path = Path(__file__).parent / "parsed_output.json"
out_path.write_text(json.dumps({"results": results, "errors": errors}, indent=2))
print(f"\nWrote {out_path}")
