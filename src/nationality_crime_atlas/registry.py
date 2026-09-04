"""Validation and loading for the versioned source registry."""

import json
import re
from pathlib import Path
from typing import Dict, Mapping
from urllib.parse import urlsplit

from .errors import SchemaError


REGISTRY_SCHEMA_VERSION = 2
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

SERIES_REQUIRED_FIELDS = {
    "publisher",
    "dataset",
    "parser",
    "license_url",
    "dimensions",
    "definitions",
    "notes",
}

EDITION_REQUIRED_FIELDS = {
    "series_id",
    "source_table",
    "expected_format",
    "filename",
    "landing_url",
    "download_url",
    "period",
    "coverage_periods",
    "published_at",
    "revision",
    "stable_ids",
    "verified_at",
    "verification_level",
    "expected_sha256",
}


def _require_object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SchemaError("%s must be an object" % label)
    return value


def _require_fields(metadata: Mapping[str, object], required, label: str) -> None:
    missing = sorted(required - set(metadata))
    if missing:
        raise SchemaError("%s is missing fields: %s" % (label, ", ".join(missing)))


def _require_https(value: object, label: str) -> None:
    if not isinstance(value, str) or urlsplit(value).scheme.lower() != "https":
        raise SchemaError("%s must be an HTTPS URL" % label)


def _validate_series(series_id: str, metadata: Mapping[str, object]) -> None:
    if not SAFE_ID.fullmatch(series_id):
        raise SchemaError("Series ID contains unsafe path characters: %s" % series_id)
    _require_fields(metadata, SERIES_REQUIRED_FIELDS, "Series %s" % series_id)
    for field in ("publisher", "dataset", "parser"):
        if not isinstance(metadata.get(field), str) or not str(metadata[field]).strip():
            raise SchemaError(
                "Series %s field %s must be a non-empty string" % (series_id, field)
            )
    _require_https(metadata.get("license_url"), "Series %s license_url" % series_id)
    for field in ("dimensions", "definitions", "notes"):
        if not isinstance(metadata.get(field), list):
            raise SchemaError("Series %s field %s must be an array" % (series_id, field))


def _validate_edition(
    edition_id: str,
    metadata: Mapping[str, object],
    series: Mapping[str, Mapping[str, object]],
) -> None:
    if not SAFE_ID.fullmatch(edition_id):
        raise SchemaError("Edition ID contains unsafe path characters: %s" % edition_id)
    _require_fields(metadata, EDITION_REQUIRED_FIELDS, "Edition %s" % edition_id)
    series_id = metadata.get("series_id")
    if series_id not in series:
        raise SchemaError(
            "Edition %s references unknown series %r" % (edition_id, series_id)
        )
    expected_format = metadata.get("expected_format")
    if expected_format not in {"xls", "xlsx"}:
        raise SchemaError("Edition %s expected_format must be xls or xlsx" % edition_id)
    filename = metadata.get("filename")
    if (
        not isinstance(filename, str)
        or not filename.strip()
        or Path(filename).name != filename
        or filename in {".", "..", "manifest.json"}
    ):
        raise SchemaError("Edition %s filename is unsafe" % edition_id)
    _require_https(metadata.get("landing_url"), "Edition %s landing_url" % edition_id)
    _require_https(metadata.get("download_url"), "Edition %s download_url" % edition_id)
    if (
        not isinstance(metadata.get("coverage_periods"), list)
        or not metadata["coverage_periods"]
    ):
        raise SchemaError(
            "Edition %s coverage_periods must be a non-empty array" % edition_id
        )
    if not isinstance(metadata.get("stable_ids"), dict):
        raise SchemaError("Edition %s stable_ids must be an object" % edition_id)
    expected_hash = metadata.get("expected_sha256")
    if expected_hash is not None and (
        not isinstance(expected_hash, str) or not SHA256.fullmatch(expected_hash)
    ):
        raise SchemaError(
            "Edition %s expected_sha256 must be null or SHA-256" % edition_id
        )


def load_source_registry(path: Path) -> Dict[str, Dict[str, object]]:
    """Load registry v2 and return series metadata merged into each edition."""

    registry_path = Path(path)
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise SchemaError(
            "Source registry schema_version must be %d" % REGISTRY_SCHEMA_VERSION
        )
    series_raw = _require_object(data.get("series"), "Source registry series")
    editions_raw = _require_object(data.get("editions"), "Source registry editions")

    series: Dict[str, Mapping[str, object]] = {}
    for series_id, value in series_raw.items():
        metadata = _require_object(value, "Series %s metadata" % series_id)
        _validate_series(series_id, metadata)
        series[series_id] = metadata

    editions: Dict[str, Dict[str, object]] = {}
    for edition_id, value in editions_raw.items():
        metadata = _require_object(value, "Edition %s metadata" % edition_id)
        _validate_edition(edition_id, metadata, series)
        series_id = str(metadata["series_id"])
        merged = dict(series[series_id])
        merged.update(metadata)
        merged["series_id"] = series_id
        merged["edition_id"] = edition_id
        editions[edition_id] = merged
    return editions
