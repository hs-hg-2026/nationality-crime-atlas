"""CLI for compact dashboard export bundles."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .compact_export import generate_compact_export


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-build-compact-export")
    parser.add_argument(
        "--indicator-latest",
        type=Path,
        default=Path("data/processed/_indicators/latest.json"),
    )
    parser.add_argument(
        "--all-resident-latest",
        type=Path,
        default=Path("data/processed/_all_resident_context/latest.json"),
    )
    parser.add_argument(
        "--nationality-comparison-latest",
        type=Path,
        default=Path("data/processed/_nationality_comparison/latest.json"),
    )
    parser.add_argument(
        "--offense-composition-latest",
        type=Path,
        default=Path("data/processed/_offense_composition/latest.json"),
    )
    parser.add_argument(
        "--clearance-share-latest",
        type=Path,
        default=Path("data/processed/_clearance_share_trend/latest.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/compact_export"),
    )
    parser.add_argument("--generated-at")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    generated_at = arguments.generated_at or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    result = generate_compact_export(
        indicator_latest_path=arguments.indicator_latest,
        all_resident_latest_path=arguments.all_resident_latest,
        nationality_comparison_latest_path=arguments.nationality_comparison_latest,
        offense_composition_latest_path=arguments.offense_composition_latest,
        clearance_share_latest_path=arguments.clearance_share_latest,
        output_root=arguments.output_root,
        generated_at=generated_at,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "dashboard_export": str(result.export_path),
                "summary": str(result.summary_path),
                "latest": str(result.latest_path),
                "record_counts": dict(result.record_counts),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
