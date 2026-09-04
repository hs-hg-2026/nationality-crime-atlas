"""CLI for promoting an acquired official artifact into immutable raw storage."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .errors import SchemaError
from .registry import load_source_registry
from .snapshot import snapshot_artifact


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-snapshot")
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--published-at")
    parser.add_argument("--revision")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Create or safely reuse one source-registered raw snapshot."""

    arguments = _argument_parser().parse_args(argv)
    sources = load_source_registry(arguments.registry)
    if arguments.source_id not in sources:
        raise SchemaError("Unknown source_id: %s" % arguments.source_id)
    result = snapshot_artifact(
        arguments.input,
        raw_root=arguments.raw_root,
        source_id=arguments.source_id,
        source_metadata=sources[arguments.source_id],
        retrieved_at=arguments.retrieved_at,
        published_at=arguments.published_at,
        revision=arguments.revision,
    )
    print(
        json.dumps(
            {
                "source_id": arguments.source_id,
                "snapshot_dir": str(result.snapshot_dir),
                "artifact_path": str(result.artifact_path),
                "manifest_path": str(result.manifest_path),
                "reused": result.reused,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0
