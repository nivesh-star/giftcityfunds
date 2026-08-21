"""
Parse all GIFT City factsheets and write structured JSON to gift_city_factsheets/all_funds.json.

Usage:
    python3 -m gift_city.export_json
    python3 -m gift_city.export_json --out gift_city_factsheets/funds.json
    python3 -m gift_city.export_json --fund dsp
"""
from __future__ import annotations
import argparse
import dataclasses
import json
import logging
from datetime import date
from pathlib import Path

from gift_city.load_to_db import PARSERS, FACTSHEET_DIR

logger = logging.getLogger(__name__)


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


def export(slugs: list[str], out_path: Path) -> None:
    result = {}
    for slug in slugs:
        parser_cls, filename = PARSERS[slug]
        pdf_path = FACTSHEET_DIR / filename
        if not pdf_path.exists():
            logger.warning("PDF not found, skipping: %s", pdf_path)
            continue
        try:
            fs = parser_cls(pdf_path).parse()
            result[slug] = dataclasses.asdict(fs)
            logger.info("Parsed %s", fs.fund_info.fund_name)
        except Exception as exc:
            logger.error("Failed %s: %s", slug, exc)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, cls=_Encoder, indent=2, ensure_ascii=False))
    logger.info("Written %d funds → %s", len(result), out_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fund", choices=list(PARSERS), help="Single fund slug")
    parser.add_argument(
        "--out",
        type=Path,
        default=FACTSHEET_DIR / "all_funds.json",
        help="Output path (default: gift_city_factsheets/all_funds.json)",
    )
    args = parser.parse_args()
    slugs = [args.fund] if args.fund else list(PARSERS)
    export(slugs, args.out)


if __name__ == "__main__":
    main()
