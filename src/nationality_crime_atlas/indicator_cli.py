"""CLI for generating provenance-first reference-ratio indicator outputs."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .indicators import generate_indicator_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-indicators")
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
        "--contracts",
        type=Path,
        default=Path("config/indicator_contracts.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_indicators"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_indicator_report(
        catalog_path=arguments.catalog,
        processed_root=arguments.processed_root,
        mapping_latest_path=arguments.mapping_latest,
        contracts_path=arguments.contracts,
        output_root=arguments.output_root,
        generated_at=generated_at,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "jsonl": str(result.jsonl_path),
                "csv": str(result.csv_path),
                "summary": str(result.summary_path),
                "latest": str(result.latest_path),
                "record_count": result.record_count,
                "status_counts": result.status_counts,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
