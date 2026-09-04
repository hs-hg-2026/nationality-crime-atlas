"""CLI for generating the nationality offense composition product."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .offense_composition import generate_offense_composition_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-offense-composition")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/processed/_catalog/artifacts.jsonl"),
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/offense_composition_contract.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_offense_composition"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    report = generate_offense_composition_report(
        catalog_path=arguments.catalog,
        raw_root=arguments.raw_root,
        processed_root=arguments.processed_root,
        contract_path=arguments.contract,
        output_root=arguments.output_root,
        generated_at=generated_at,
    )
    print(
        json.dumps(
            {
                "output_dir": str(report.output_dir),
                "jsonl": str(report.jsonl_path),
                "csv": str(report.csv_path),
                "summary": str(report.summary_path),
                "latest": str(report.latest_path),
                "record_count": report.record_count,
                "entity_count": report.entity_count,
                "status_counts": dict(report.status_counts),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
