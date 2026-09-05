"""Atomic offline pipeline from a local official artifact to validated JSONL."""

import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

from .errors import PipelineConflictError, QualityGateError, SchemaError
from .npa_all_residents import (
    parse_npa_overall_prefecture_crime,
    parse_npa_prefecture_population,
    parse_statistics_bureau_intercensal_population,
    parse_statistics_bureau_japanese_population,
)
from .npa_nationality import parse_npa_nationality_totals
from .npa_prefecture import parse_npa_prefecture_table13
from .population import parse_population_nationality_totals, parse_population_t1
from .provenance import sha256_file
from .quality import validate_jsonl
from .snapshot import RawSnapshot, snapshot_artifact


PIPELINE_SCHEMA_VERSION = 2
PARSER_CONTRACT_VERSIONS = {
    "population-t1": 1,
    "population-nationality-totals": 1,
    "npa-nationality": 2,
    "npa-prefecture-table13": 1,
    "npa-overall-prefecture-crime": 1,
    "npa-prefecture-population": 1,
    "statistics-bureau-japanese-population": 2,
    "statistics-bureau-intercensal-population": 1,
}


@dataclass(frozen=True)
class PipelineResult:
    """Locations and reuse status for one validated offline pipeline run."""

    raw_snapshot: RawSnapshot
    processed_dir: Path
    normalized_path: Path
    artifact_manifest_path: Path
    quality_report_path: Path
    run_manifest_path: Path
    reused: bool


def _profile_sha256(profile: Mapping[str, object]) -> str:
    encoded = json.dumps(
        profile,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parser_contract_version(source_metadata: Mapping[str, object]) -> int:
    parser = source_metadata.get("parser")
    try:
        return PARSER_CONTRACT_VERSIONS[str(parser)]
    except KeyError as error:
        raise SchemaError("Unsupported parser in source metadata: %r" % parser) from error


def _records_for_source(
    artifact: Path,
    *,
    source_id: str,
    source_metadata: Mapping[str, object],
) -> Iterable[object]:
    parser = source_metadata.get("parser")
    if parser == "population-t1":
        return parse_population_t1(artifact, source_id=source_id)
    if parser == "population-nationality-totals":
        return parse_population_nationality_totals(artifact, source_id=source_id)
    if parser == "npa-nationality":
        return parse_npa_nationality_totals(
            artifact,
            table_id=str(source_metadata.get("source_table")),
            source_id=source_id,
        )
    if parser == "npa-prefecture-table13":
        return parse_npa_prefecture_table13(artifact, source_id=source_id)
    if parser == "npa-overall-prefecture-crime":
        return parse_npa_overall_prefecture_crime(artifact, source_id=source_id)
    if parser == "npa-prefecture-population":
        return parse_npa_prefecture_population(artifact, source_id=source_id)
    if parser == "statistics-bureau-japanese-population":
        return parse_statistics_bureau_japanese_population(
            artifact, source_id=source_id
        )
    if parser == "statistics-bureau-intercensal-population":
        return parse_statistics_bureau_intercensal_population(
            artifact, source_id=source_id
        )
    raise SchemaError("Unsupported parser in source metadata: %r" % parser)


def _write_jsonl(records: Iterable[object], path: Path) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _conflict(processed_dir: Path) -> PipelineConflictError:
    return PipelineConflictError(
        "Existing processed run failed verification and was not overwritten: %s"
        % processed_dir
    )


def _existing_result(
    processed_dir: Path,
    *,
    raw_snapshot: RawSnapshot,
    raw_manifest: Mapping[str, object],
    source_id: str,
    profile_hash: str,
    parser_contract_version: int,
) -> PipelineResult:
    normalized_path = processed_dir / "normalized.jsonl"
    artifact_manifest_path = processed_dir / "artifact.manifest.json"
    quality_report_path = processed_dir / "quality.json"
    run_manifest_path = processed_dir / "run.json"
    try:
        artifact_manifest = json.loads(
            artifact_manifest_path.read_text(encoding="utf-8")
        )
        quality = json.loads(quality_report_path.read_text(encoding="utf-8"))
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        normalized_hash = sha256_file(normalized_path)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise _conflict(processed_dir) from error

    checks = (
        run_manifest.get("pipeline_schema_version") == PIPELINE_SCHEMA_VERSION,
        run_manifest.get("parser_contract_version") == parser_contract_version,
        run_manifest.get("source_id") == source_id,
        run_manifest.get("raw_artifact_sha256") == raw_manifest.get("sha256"),
        run_manifest.get("quality_profile_sha256") == profile_hash,
        run_manifest.get("normalized_sha256") == normalized_hash,
        run_manifest.get("quality_passed") is True,
        artifact_manifest.get("sha256") == raw_manifest.get("sha256"),
        artifact_manifest.get("normalized_sha256") == normalized_hash,
        quality.get("input_sha256") == normalized_hash,
        quality.get("passed") is True,
        quality.get("record_count") == artifact_manifest.get("record_count"),
    )
    if not all(checks):
        raise _conflict(processed_dir)
    return PipelineResult(
        raw_snapshot=raw_snapshot,
        processed_dir=processed_dir,
        normalized_path=normalized_path,
        artifact_manifest_path=artifact_manifest_path,
        quality_report_path=quality_report_path,
        run_manifest_path=run_manifest_path,
        reused=True,
    )


def run_offline_pipeline(
    source_path: Path,
    *,
    source_id: str,
    source_metadata: Mapping[str, object],
    quality_profile: Mapping[str, object],
    retrieved_at: str,
    raw_root: Path,
    processed_root: Path,
    published_at: Optional[str] = None,
    revision: Optional[str] = None,
    acquisition: Optional[Mapping[str, object]] = None,
) -> PipelineResult:
    """Snapshot, parse, validate, and atomically promote one local artifact."""

    raw_snapshot = snapshot_artifact(
        source_path,
        raw_root=raw_root,
        source_id=source_id,
        source_metadata=source_metadata,
        retrieved_at=retrieved_at,
        published_at=published_at,
        revision=revision,
        acquisition=acquisition,
    )
    raw_manifest = json.loads(
        raw_snapshot.manifest_path.read_text(encoding="utf-8")
    )
    profile_hash = _profile_sha256(quality_profile)
    parser_contract_version = _parser_contract_version(source_metadata)
    snapshot_relative_dir = raw_snapshot.snapshot_dir.relative_to(Path(raw_root))
    processed_dir = Path(processed_root) / snapshot_relative_dir
    processed_source_root = processed_dir.parent
    if processed_dir.exists():
        return _existing_result(
            processed_dir,
            raw_snapshot=raw_snapshot,
            raw_manifest=raw_manifest,
            source_id=source_id,
            profile_hash=profile_hash,
            parser_contract_version=parser_contract_version,
        )

    processed_source_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=".pipeline-", dir=str(processed_source_root))
    )
    try:
        normalized_path = staging_dir / "normalized.jsonl"
        record_count = _write_jsonl(
            _records_for_source(
                raw_snapshot.artifact_path,
                source_id=source_id,
                source_metadata=source_metadata,
            ),
            normalized_path,
        )
        normalized_hash = sha256_file(normalized_path)
        artifact_manifest = dict(raw_manifest)
        artifact_manifest.update(
            {
                "record_count": record_count,
                "normalized_filename": normalized_path.name,
                "normalized_sha256": normalized_hash,
            }
        )
        artifact_manifest_path = staging_dir / "artifact.manifest.json"
        _write_json(artifact_manifest_path, artifact_manifest)
        quality = validate_jsonl(
            normalized_path,
            source_id=source_id,
            profile=quality_profile,
            artifact_manifest=artifact_manifest,
        )
        if not quality["passed"]:
            raise QualityGateError(quality)
        quality_report_path = staging_dir / "quality.json"
        _write_json(quality_report_path, quality)
        run_manifest = {
            "pipeline_schema_version": PIPELINE_SCHEMA_VERSION,
            "parser_contract_version": parser_contract_version,
            "source_id": source_id,
            "series_id": source_metadata.get("series_id"),
            "edition_id": source_metadata.get("edition_id"),
            "parser": source_metadata.get("parser"),
            "raw_snapshot_relpath": raw_manifest["snapshot_relpath"],
            "raw_artifact_sha256": raw_manifest["sha256"],
            "quality_profile_sha256": profile_hash,
            "normalized_sha256": normalized_hash,
            "record_count": record_count,
            "quality_passed": True,
        }
        run_manifest_path = staging_dir / "run.json"
        _write_json(run_manifest_path, run_manifest)
        try:
            staging_dir.rename(processed_dir)
        except OSError:
            if not processed_dir.exists():
                raise
            return _existing_result(
                processed_dir,
                raw_snapshot=raw_snapshot,
                raw_manifest=raw_manifest,
                source_id=source_id,
                profile_hash=profile_hash,
                parser_contract_version=parser_contract_version,
            )
        return PipelineResult(
            raw_snapshot=raw_snapshot,
            processed_dir=processed_dir,
            normalized_path=processed_dir / normalized_path.name,
            artifact_manifest_path=processed_dir / artifact_manifest_path.name,
            quality_report_path=processed_dir / quality_report_path.name,
            run_manifest_path=processed_dir / run_manifest_path.name,
            reused=False,
        )
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
