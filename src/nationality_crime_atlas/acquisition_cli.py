"""CLI for downloading and validating one registered official edition."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .acquisition import DEFAULT_MAX_BYTES, DEFAULT_TIMEOUT_SECONDS, acquire_source
from .errors import SchemaError
from .quality import load_quality_profiles
from .registry import load_source_registry


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-acquire")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/sources.json"))
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("config/quality_profiles.json"),
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument("--retrieved-at")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download again to detect a same-edition revision; identical content is reused.",
    )
    return parser


def _clock(value: Optional[str]):
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError("retrieved_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retrieved_at must include a timezone offset")
    return lambda: parsed


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Acquire one pinned edition and print its validated storage locations."""

    arguments = _argument_parser().parse_args(argv)
    sources = load_source_registry(arguments.registry)
    profiles = load_quality_profiles(arguments.profiles)
    if arguments.source_id not in sources:
        raise SchemaError("Unknown source_id: %s" % arguments.source_id)
    if arguments.source_id not in profiles:
        raise SchemaError("Unknown quality profile source_id: %s" % arguments.source_id)
    result = acquire_source(
        source_id=arguments.source_id,
        source_metadata=sources[arguments.source_id],
        quality_profile=profiles[arguments.source_id],
        raw_root=arguments.raw_root,
        processed_root=arguments.processed_root,
        now=_clock(arguments.retrieved_at),
        timeout=arguments.timeout,
        max_bytes=arguments.max_bytes,
        refresh=arguments.refresh,
    )
    print(
        json.dumps(
            {
                "source_id": arguments.source_id,
                "retrieved_at": result.retrieved_at,
                "raw_snapshot_dir": str(result.pipeline.raw_snapshot.snapshot_dir),
                "processed_dir": str(result.pipeline.processed_dir),
                "catalog_jsonl": str(result.catalog_jsonl),
                "catalog_csv": str(result.catalog_csv),
                "quality_passed": True,
                "reused": result.pipeline.reused,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0
