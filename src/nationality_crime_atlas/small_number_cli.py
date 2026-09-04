"""CLI for reproducible small-number threshold sensitivity audits."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .small_numbers import generate_small_number_sensitivity_report


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-audit-small-numbers")
    parser.add_argument(
        "--indicator-latest",
        type=Path,
        default=Path("data/processed/_indicators/latest.json"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/small_number_sensitivity.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/_indicator_sensitivity"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Generate a sensitivity audit and print its machine-readable locations."""

    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_small_number_sensitivity_report(
        indicator_latest_path=arguments.indicator_latest,
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
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
