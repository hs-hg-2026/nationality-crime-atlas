"""CLI for nationality-specific clearance reference-ratio trends."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .nationality_trend import generate_nationality_trend_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-nationality-trend")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/processed/_catalog/artifacts.jsonl"),
    )
    parser.add_argument(
        "--processed-root", type=Path, default=Path("data/processed")
    )
    parser.add_argument(
        "--mapping-latest",
        type=Path,
        default=Path("data/processed/_mappings/latest.json"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/nationality_trend_contract.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_nationality_trend"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_nationality_trend_report(
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
                "output_dir": str(result.output_dir),
                "records": str(result.jsonl_path),
                "records_csv": str(result.csv_path),
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
