"""Immutable raw snapshots for already acquired official artifacts."""

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

from .errors import IntegrityError, SchemaError, SnapshotConflictError
from .provenance import build_manifest, detect_file_format, sha256_file


SNAPSHOT_SCHEMA_VERSION = 2
SAFE_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class RawSnapshot:
    """Paths and reuse status for one immutable raw snapshot."""

    snapshot_dir: Path
    artifact_path: Path
    manifest_path: Path
    reused: bool


def _retrieval_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError("retrieved_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retrieved_at must include a timezone offset")
    return parsed


def _required_metadata(metadata: Mapping[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("Source metadata field %s must be a non-empty string" % key)
    return value.strip()


def _manifest_for_snapshot(
    artifact: Path,
    *,
    source_id: str,
    source_metadata: Mapping[str, object],
    retrieved_at: str,
    snapshot_relpath: str,
    published_at: Optional[str],
    revision: Optional[str],
    acquisition: Optional[Mapping[str, object]],
) -> Mapping[str, object]:
    manifest = build_manifest(
        artifact,
        source_id=source_id,
        landing_url=_required_metadata(source_metadata, "landing_url"),
        download_url=_required_metadata(source_metadata, "download_url"),
        retrieved_at=retrieved_at,
    )
    manifest.update(
        {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "snapshot_relpath": snapshot_relpath,
            "immutable_snapshot": True,
            "acquisition_mode": "local_artifact_promotion",
            "series_id": _required_metadata(source_metadata, "series_id"),
            "edition_id": source_id,
            "expected_format": _required_metadata(source_metadata, "expected_format").lower(),
            "publisher": _required_metadata(source_metadata, "publisher"),
            "dataset": _required_metadata(source_metadata, "dataset"),
            "source_table": _required_metadata(source_metadata, "source_table"),
            "source_period": _required_metadata(source_metadata, "period"),
            "parser": _required_metadata(source_metadata, "parser"),
            "license_url": _required_metadata(source_metadata, "license_url"),
            "source_notes": source_metadata.get("notes", []),
            "source_dimensions": source_metadata.get("dimensions", []),
            "source_definitions": source_metadata.get("definitions", []),
            "coverage_periods": source_metadata.get("coverage_periods", []),
            "stable_ids": source_metadata.get("stable_ids", {}),
            "verified_at": source_metadata.get("verified_at"),
            "verification_level": source_metadata.get("verification_level"),
            "expected_sha256": source_metadata.get("expected_sha256"),
        }
    )
    if acquisition is not None:
        manifest["acquisition"] = dict(acquisition)
        manifest["acquisition_mode"] = str(acquisition.get("mode", "http_download"))
    if published_at is not None:
        manifest["published_at"] = published_at
    if revision is not None:
        manifest["revision"] = revision
    return manifest


def _existing_snapshot(
    snapshot_dir: Path,
    *,
    artifact_name: str,
    expected_manifest: Mapping[str, object],
) -> RawSnapshot:
    artifact_path = snapshot_dir / artifact_name
    manifest_path = snapshot_dir / "manifest.json"
    try:
        actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SnapshotConflictError(
            "Snapshot location contains a different artifact or invalid manifest: %s"
            % snapshot_dir
        ) from error
    if not artifact_path.is_file() or actual_manifest != expected_manifest:
        raise SnapshotConflictError(
            "Snapshot location contains a different artifact: %s" % snapshot_dir
        )
    if sha256_file(artifact_path) != expected_manifest["sha256"]:
        raise SnapshotConflictError(
            "Snapshot location contains a different artifact: %s" % snapshot_dir
        )
    return RawSnapshot(
        snapshot_dir=snapshot_dir,
        artifact_path=artifact_path,
        manifest_path=manifest_path,
        reused=True,
    )


def snapshot_artifact(
    source_path: Path,
    *,
    raw_root: Path,
    source_id: str,
    source_metadata: Mapping[str, object],
    retrieved_at: str,
    published_at: Optional[str] = None,
    revision: Optional[str] = None,
    acquisition: Optional[Mapping[str, object]] = None,
) -> RawSnapshot:
    """Promote a local official file into an immutable, idempotent raw snapshot."""

    if not SAFE_SOURCE_ID.fullmatch(source_id):
        raise ValueError("source_id contains unsafe path characters")
    retrieved = _retrieval_datetime(retrieved_at)
    artifact = Path(source_path)
    if not artifact.is_file():
        raise FileNotFoundError("Official artifact does not exist: %s" % artifact)
    if artifact.name == "manifest.json":
        raise ValueError("Official artifact filename cannot be manifest.json")

    expected_format = _required_metadata(source_metadata, "expected_format").lower()
    actual_format = detect_file_format(artifact)
    if actual_format != expected_format:
        raise IntegrityError(
            "Source %s expected %s but detected %s"
            % (source_id, expected_format, actual_format)
        )

    expected_hash = source_metadata.get("expected_sha256")
    actual_hash = sha256_file(artifact)
    if expected_hash is not None and actual_hash != expected_hash:
        raise IntegrityError(
            "Source %s SHA-256 does not match pinned edition: expected %s, observed %s"
            % (source_id, expected_hash, actual_hash)
        )

    series_id = _required_metadata(source_metadata, "series_id")
    if not SAFE_SOURCE_ID.fullmatch(series_id):
        raise ValueError("series_id contains unsafe path characters")
    edition_id = _required_metadata(source_metadata, "edition_id")
    if edition_id != source_id:
        raise SchemaError("Source metadata edition_id does not match %s" % source_id)

    directory_name = "%s_%s" % (
        retrieved.strftime("%Y%m%d_%H%M%S"),
        source_id.lower(),
    )
    source_root = Path(raw_root) / series_id / source_id
    snapshot_dir = source_root / directory_name
    snapshot_relpath = (
        Path(series_id) / source_id / directory_name / artifact.name
    ).as_posix()
    effective_published_at = (
        published_at if published_at is not None else source_metadata.get("published_at")
    )
    effective_revision = (
        revision if revision is not None else source_metadata.get("revision")
    )
    expected_manifest = _manifest_for_snapshot(
        artifact,
        source_id=source_id,
        source_metadata=source_metadata,
        retrieved_at=retrieved_at,
        snapshot_relpath=snapshot_relpath,
        published_at=(
            str(effective_published_at) if effective_published_at is not None else None
        ),
        revision=str(effective_revision) if effective_revision is not None else None,
        acquisition=acquisition,
    )

    if snapshot_dir.exists():
        return _existing_snapshot(
            snapshot_dir,
            artifact_name=artifact.name,
            expected_manifest=expected_manifest,
        )

    source_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=str(source_root)))
    try:
        staged_artifact = staging_dir / artifact.name
        shutil.copyfile(artifact, staged_artifact)
        if sha256_file(staged_artifact) != expected_manifest["sha256"]:
            raise IntegrityError("Artifact changed while creating the raw snapshot")
        (staging_dir / "manifest.json").write_text(
            json.dumps(expected_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        try:
            staging_dir.rename(snapshot_dir)
        except OSError:
            if not snapshot_dir.exists():
                raise
            return _existing_snapshot(
                snapshot_dir,
                artifact_name=artifact.name,
                expected_manifest=expected_manifest,
            )
        return RawSnapshot(
            snapshot_dir=snapshot_dir,
            artifact_path=snapshot_dir / artifact.name,
            manifest_path=snapshot_dir / "manifest.json",
            reused=False,
        )
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
