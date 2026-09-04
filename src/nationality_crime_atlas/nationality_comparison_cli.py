"""CLI for generating the nationwide nationality comparison product."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .nationality_comparison import generate_nationality_comparison_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-nationality-comparison")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/processed/_catalog/artifacts.jsonl"),
    )
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--mapping-latest",
        type=Path,
        default=Path("data/processed/_mappings/latest.json"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/nationality_comparison_contract.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_nationality_comparison"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    report = generate_nationality_comparison_report(
        catalog_path=arguments.catalog,
        processed_root=arguments.processed_root,
        mapping_latest_path=arguments.mapping_latest,
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
                "status_counts": dict(report.status_counts),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
