"""CLI for generating explicit cross-source dimension mapping audits."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .dimensions import generate_dimension_mapping_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-map-dimensions")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/processed/_catalog/artifacts.jsonl"),
    )
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/dimension_mappings.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_mappings"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Generate the mapping audit and print its paths and status counts."""

    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_dimension_mapping_report(
        catalog_path=arguments.catalog,
        processed_root=arguments.processed_root,
        config_path=arguments.config,
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
