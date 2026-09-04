"""Generated inventory joining acquired artifacts to their official sources."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from .errors import IntegrityError
from .provenance import sha256_file


CATALOG_SCHEMA_VERSION = 1
CATALOG_FIELDS = [
    "artifact_catalog_schema_version",
    "series_id",
    "source_id",
    "publisher",
    "dataset",
    "source_table",
    "source_period",
    "coverage_periods",
    "landing_url",
    "download_url",
    "retrieved_at",
    "published_at",
    "revision",
    "verification_level",
    "local_filename",
    "raw_relpath",
    "sha256",
    "byte_size",
    "file_format",
    "acquisition_mode",
    "final_url",
    "http_status",
    "processing_status",
    "processed_relpath",
    "record_count",
    "quality_passed",
]


@dataclass(frozen=True)
class CatalogResult:
    """Paths and row count for the generated artifact inventory."""

    jsonl_path: Path
    csv_path: Path
    record_count: int


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise IntegrityError("Invalid provenance JSON: %s" % path) from error
    if not isinstance(value, dict):
        raise IntegrityError("Provenance JSON must contain an object: %s" % path)
    return value


def _safe_artifact_path(raw_root: Path, relative_value: object) -> Path:
    if not isinstance(relative_value, str):
        raise IntegrityError("Raw manifest snapshot_relpath must be a string")
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise IntegrityError("Raw manifest snapshot_relpath is unsafe: %s" % relative)
    return raw_root / relative


def _processed_state(
    processed_dir: Path,
    *,
    source_id: object,
    artifact_sha256: object,
) -> Dict[str, object]:
    state: Dict[str, object] = {
        "processing_status": "raw_only",
        "processed_relpath": None,
        "record_count": None,
        "quality_passed": False,
    }
    if not processed_dir.exists():
        return state
    try:
        run = _read_json(processed_dir / "run.json")
        quality = _read_json(processed_dir / "quality.json")
        artifact = _read_json(processed_dir / "artifact.manifest.json")
        normalized_path = processed_dir / "normalized.jsonl"
        normalized_hash = sha256_file(normalized_path)
        valid = (
            run.get("source_id") == source_id
            and run.get("raw_artifact_sha256") == artifact_sha256
            and run.get("normalized_sha256") == normalized_hash
            and run.get("quality_passed") is True
            and quality.get("passed") is True
            and quality.get("input_sha256") == normalized_hash
            and artifact.get("normalized_sha256") == normalized_hash
            and artifact.get("sha256") == artifact_sha256
            and quality.get("record_count") == artifact.get("record_count")
        )
    except (IntegrityError, FileNotFoundError):
        valid = False
        quality = {}
        artifact = {}
    state["processing_status"] = "validated" if valid else "processed_invalid"
    state["processed_relpath"] = processed_dir.as_posix()
    state["record_count"] = artifact.get("record_count")
    state["quality_passed"] = bool(valid)
    return state


def _catalog_record(
    manifest: Mapping[str, object],
    *,
    raw_root: Path,
    processed_root: Path,
) -> Dict[str, object]:
    artifact_path = _safe_artifact_path(raw_root, manifest.get("snapshot_relpath"))
    if not artifact_path.is_file():
        raise IntegrityError("Raw artifact is missing: %s" % artifact_path)
    observed_hash = sha256_file(artifact_path)
    if observed_hash != manifest.get("sha256"):
        raise IntegrityError("Raw artifact SHA-256 differs from manifest: %s" % artifact_path)

    snapshot_relative_dir = Path(str(manifest["snapshot_relpath"])).parent
    processed_dir = processed_root / snapshot_relative_dir
    acquisition = manifest.get("acquisition")
    acquisition_data = acquisition if isinstance(acquisition, dict) else {}
    record: Dict[str, object] = {
        "artifact_catalog_schema_version": CATALOG_SCHEMA_VERSION,
        "series_id": manifest.get("series_id"),
        "source_id": manifest.get("source_id"),
        "publisher": manifest.get("publisher"),
        "dataset": manifest.get("dataset"),
        "source_table": manifest.get("source_table"),
        "source_period": manifest.get("source_period"),
        "coverage_periods": manifest.get("coverage_periods", []),
        "landing_url": manifest.get("landing_url"),
        "download_url": manifest.get("download_url"),
        "retrieved_at": manifest.get("retrieved_at"),
        "published_at": manifest.get("published_at"),
        "revision": manifest.get("revision"),
        "verification_level": manifest.get("verification_level"),
        "local_filename": manifest.get("local_filename"),
        "raw_relpath": manifest.get("snapshot_relpath"),
        "sha256": manifest.get("sha256"),
        "byte_size": manifest.get("byte_size"),
        "file_format": manifest.get("file_format"),
        "acquisition_mode": manifest.get("acquisition_mode"),
        "final_url": acquisition_data.get("final_url"),
        "http_status": acquisition_data.get("http_status"),
    }
    record.update(
        _processed_state(
            processed_dir,
            source_id=manifest.get("source_id"),
            artifact_sha256=manifest.get("sha256"),
        )
    )
    if record["processed_relpath"] is not None:
        record["processed_relpath"] = snapshot_relative_dir.as_posix()
    return record


def _csv_value(value: object) -> object:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def rebuild_artifact_catalog(
    *,
    raw_root: Path,
    processed_root: Path,
    catalog_dir: Optional[Path] = None,
) -> CatalogResult:
    """Regenerate machine- and human-readable inventories from immutable manifests."""

    raw_path = Path(raw_root)
    processed_path = Path(processed_root)
    rows: List[Dict[str, object]] = []
    if raw_path.exists():
        for manifest_path in sorted(raw_path.rglob("manifest.json")):
            rows.append(
                _catalog_record(
                    _read_json(manifest_path),
                    raw_root=raw_path,
                    processed_root=processed_path,
                )
            )
    rows.sort(
        key=lambda row: (
            str(row.get("series_id")),
            str(row.get("source_id")),
            str(row.get("retrieved_at")),
        )
    )

    destination = Path(catalog_dir) if catalog_dir is not None else processed_path / "_catalog"
    destination.mkdir(parents=True, exist_ok=True)
    jsonl_path = destination / "artifacts.jsonl"
    csv_path = destination / "artifacts.csv"
    jsonl_temp = destination / ".artifacts.jsonl.tmp"
    csv_temp = destination / ".artifacts.csv.tmp"
    try:
        with jsonl_temp.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
        with csv_temp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=CATALOG_FIELDS, lineterminator="\n"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({field: _csv_value(row.get(field)) for field in CATALOG_FIELDS})
        jsonl_temp.replace(jsonl_path)
        csv_temp.replace(csv_path)
    finally:
        if jsonl_temp.exists():
            jsonl_temp.unlink()
        if csv_temp.exists():
            csv_temp.unlink()
    return CatalogResult(
        jsonl_path=jsonl_path,
        csv_path=csv_path,
        record_count=len(rows),
    )
