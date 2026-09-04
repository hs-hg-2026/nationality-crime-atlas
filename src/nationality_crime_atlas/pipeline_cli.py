"""CLI for the complete offline snapshot, parse, and validation pipeline."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .errors import SchemaError
from .pipeline import run_offline_pipeline
from .quality import load_quality_profiles
from .registry import load_source_registry


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-pipeline")
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/sources.json"))
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("config/quality_profiles.json"),
    )
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--published-at")
    parser.add_argument("--revision")
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=Path("data/processed"),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the complete offline pipeline for one registered source artifact."""

    arguments = _argument_parser().parse_args(argv)
    sources = load_source_registry(arguments.registry)
    profiles = load_quality_profiles(arguments.profiles)
    if arguments.source_id not in sources:
        raise SchemaError("Unknown source_id: %s" % arguments.source_id)
    if arguments.source_id not in profiles:
        raise SchemaError("Unknown quality profile source_id: %s" % arguments.source_id)
    result = run_offline_pipeline(
        arguments.input,
        source_id=arguments.source_id,
        source_metadata=sources[arguments.source_id],
        quality_profile=profiles[arguments.source_id],
        retrieved_at=arguments.retrieved_at,
        raw_root=arguments.raw_root,
        processed_root=arguments.processed_root,
        published_at=arguments.published_at,
        revision=arguments.revision,
    )
    print(
        json.dumps(
            {
                "source_id": arguments.source_id,
                "processed_dir": str(result.processed_dir),
                "normalized_path": str(result.normalized_path),
                "quality_report_path": str(result.quality_report_path),
                "quality_passed": True,
                "reused": result.reused,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0
