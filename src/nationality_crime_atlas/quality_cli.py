"""CLI for source-profile validation of normalized JSONL datasets."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .errors import SchemaError
from .quality import load_quality_profiles, validate_jsonl


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nca-validate")
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("config/quality_profiles.json"),
    )
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Validate one normalized artifact and persist its pass/fail report."""

    arguments = _argument_parser().parse_args(argv)
    profiles = load_quality_profiles(arguments.profiles)
    if arguments.source_id not in profiles:
        raise SchemaError("Unknown quality profile source_id: %s" % arguments.source_id)
    artifact_manifest = None
    if arguments.artifact_manifest is not None:
        artifact_manifest = json.loads(
            arguments.artifact_manifest.read_text(encoding="utf-8")
        )
        if not isinstance(artifact_manifest, dict):
            raise SchemaError("Artifact manifest must be a JSON object")
    report = validate_jsonl(
        arguments.input,
        source_id=arguments.source_id,
        profile=profiles[arguments.source_id],
        artifact_manifest=artifact_manifest,
    )
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "record_count": report["record_count"],
                "source_id": arguments.source_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 1
