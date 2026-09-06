"""CLI for annual clearance-to-population reference ratios."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .clearance_population_trend import generate_clearance_population_trend


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-clearance-population-trend")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/processed/_catalog/artifacts.jsonl"),
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/clearance_population_trend_contract.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_clearance_population_trend"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_clearance_population_trend(
        catalog_path=arguments.catalog,
        raw_root=arguments.raw_root,
        contract_path=arguments.contract,
        output_root=arguments.output_root,
        generated_at=generated_at,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "records": str(result.jsonl_path),
                "records_csv": str(result.csv_path),
                "summary": str(result.summary_path),
                "latest": str(result.latest_path),
                "record_count": result.record_count,
                "calculated_count": result.calculated_count,
                "refused_count": result.refused_count,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
