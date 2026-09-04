"""Streaming quality gates for normalized source JSONL datasets."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Set

from .errors import SchemaError
from .provenance import sha256_file


QUALITY_REPORT_SCHEMA_VERSION = 1
MAX_REPORTED_ERRORS = 100

RECORD_SPECS = {
    "population": {
        "fields": {
            "period_end",
            "nationality_code",
            "nationality",
            "residence_status_code",
            "residence_status",
            "sex_code",
            "sex",
            "age_group_code",
            "age_group",
            "age",
            "prefecture_code",
            "prefecture",
            "value",
            "suppressed",
            "source_id",
            "source_sheet",
            "source_row",
        },
        "key_fields": (
            "period_end",
            "nationality_code",
            "nationality",
            "residence_status_code",
            "residence_status",
            "sex_code",
            "sex",
            "age_group_code",
            "age_group",
            "age",
            "prefecture_code",
            "prefecture",
            "source_id",
        ),
        "metric_fields": ("value",),
        "period_field": "period_end",
    },
    "nationality_crime": {
        "fields": {
            "year",
            "population_scope",
            "region",
            "nationality",
            "subcategory",
            "row_kind",
            "cleared_cases",
            "cleared_persons",
            "criminal_code_cleared_cases",
            "criminal_code_cleared_persons",
            "source_id",
            "source_table",
            "source_sheet",
            "source_row",
        },
        "key_fields": (
            "year",
            "population_scope",
            "region",
            "nationality",
            "subcategory",
            "row_kind",
            "source_id",
            "source_table",
        ),
        "metric_fields": (
            "cleared_cases",
            "cleared_persons",
            "criminal_code_cleared_cases",
            "criminal_code_cleared_persons",
        ),
        "period_field": "year",
    },
    "prefecture_crime": {
        "fields": {
            "year",
            "population_scope",
            "offense_scope",
            "geography",
            "geography_type",
            "parent_region",
            "geography_semantics",
            "cleared_cases",
            "cleared_persons",
            "source_id",
            "source_table",
            "source_sheet",
            "source_row",
        },
        "key_fields": (
            "year",
            "population_scope",
            "offense_scope",
            "geography",
            "geography_type",
            "parent_region",
            "geography_semantics",
            "source_id",
            "source_table",
        ),
        "metric_fields": ("cleared_cases", "cleared_persons"),
        "period_field": "year",
    },
    "overall_prefecture_crime": {
        "fields": {
            "year",
            "population_scope",
            "offense_scope",
            "geography",
            "geography_type",
            "parent_region",
            "geography_semantics",
            "recognized_cases",
            "cleared_cases",
            "cleared_persons",
            "source_id",
            "source_table",
            "source_sheet",
            "source_row",
        },
        "key_fields": (
            "year",
            "population_scope",
            "offense_scope",
            "geography",
            "geography_type",
            "parent_region",
            "geography_semantics",
            "source_id",
            "source_table",
        ),
        "metric_fields": ("recognized_cases", "cleared_cases", "cleared_persons"),
        "period_field": "year",
    },
    "prefecture_population": {
        "fields": {
            "year",
            "reference_date",
            "population_scope",
            "geography",
            "geography_type",
            "parent_region",
            "geography_semantics",
            "population",
            "source_value",
            "source_unit",
            "rounding",
            "source_id",
            "source_table",
            "source_sheet",
            "source_row",
        },
        "key_fields": (
            "year",
            "reference_date",
            "population_scope",
            "geography",
            "geography_type",
            "geography_semantics",
            "source_id",
            "source_table",
        ),
        "metric_fields": ("population", "source_value"),
        "period_field": "year",
    },
}


class _ErrorCollector:
    def __init__(self) -> None:
        self.count = 0
        self.messages = []

    def add(self, message: str) -> None:
        self.count += 1
        if len(self.messages) < MAX_REPORTED_ERRORS:
            self.messages.append(message)


def _validate_profile(profile: Mapping[str, object], label: str) -> None:
    record_type = profile.get("record_type")
    if record_type not in RECORD_SPECS:
        raise SchemaError("Quality profile %s has an invalid record_type" % label)
    expected_count = profile.get("expected_record_count")
    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count < 0
    ):
        raise SchemaError(
            "Quality profile %s expected_record_count must be a non-negative integer"
            % label
        )
    fields = RECORD_SPECS[record_type]["fields"]
    for section in ("allowed_values", "expected_distinct_counts", "expected_sums"):
        values = profile.get(section, {})
        if not isinstance(values, dict):
            raise SchemaError("Quality profile %s %s must be an object" % (label, section))
        unknown = sorted(set(values) - fields)
        if unknown:
            raise SchemaError(
                "Quality profile %s %s references unknown fields: %s"
                % (label, section, ", ".join(unknown))
            )
    anchors = profile.get("anchors", [])
    if not isinstance(anchors, list):
        raise SchemaError("Quality profile %s anchors must be an array" % label)


def load_quality_profiles(path: Path) -> Dict[str, Dict[str, object]]:
    """Load versioned source profiles and reject invalid profile structure."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise SchemaError("Quality profile registry schema_version must be 1")
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise SchemaError("Quality profile registry must contain a profiles object")
    for source_id, profile in profiles.items():
        if not isinstance(profile, dict):
            raise SchemaError("Quality profile %s must be an object" % source_id)
        _validate_profile(profile, source_id)
    return profiles


def _duplicate_fingerprint(record: Mapping[str, object], fields: Sequence[str]) -> bytes:
    encoded = json.dumps(
        [record[field] for field in fields],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=16).digest()


def _sorted_values(values: Set[object]):
    return sorted(values, key=lambda value: (str(type(value)), str(value)))


def validate_jsonl(
    path: Path,
    *,
    source_id: str,
    profile: Mapping[str, object],
    artifact_manifest: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    """Validate normalized JSONL in one pass and return an auditable report."""

    _validate_profile(profile, source_id)
    normalized_path = Path(path)
    record_type = str(profile["record_type"])
    spec = RECORD_SPECS[record_type]
    expected_fields = spec["fields"]
    key_fields = spec["key_fields"]
    metric_fields = spec["metric_fields"]
    period_field = str(spec["period_field"])
    errors = _ErrorCollector()

    if artifact_manifest is not None:
        if artifact_manifest.get("source_id") != source_id:
            errors.add("artifact manifest source_id does not match %s" % source_id)
    expected_artifact_hash = profile.get("expected_artifact_sha256")
    actual_artifact_hash = (
        artifact_manifest.get("sha256") if artifact_manifest is not None else None
    )
    if expected_artifact_hash is not None and actual_artifact_hash != expected_artifact_hash:
        errors.add(
            "artifact SHA-256 does not match profile: expected %s, observed %s"
            % (expected_artifact_hash, actual_artifact_hash)
        )

    allowed_values = profile.get("allowed_values", {})
    distinct_expectations = profile.get("expected_distinct_counts", {})
    sum_expectations = profile.get("expected_sums", {})
    observed_allowed: Dict[str, Set[object]] = {
        field: set() for field in allowed_values
    }
    observed_distinct: Dict[str, Set[object]] = {
        field: set() for field in distinct_expectations
    }
    sums = {field: 0 for field in sum_expectations}
    periods: Set[object] = set()
    fingerprints: Set[bytes] = set()
    duplicate_count = 0
    record_count = 0
    anchors = profile.get("anchors", [])
    anchor_matches = [0 for _ in anchors]

    with normalized_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                errors.add("line %d is blank" % line_number)
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                errors.add("line %d is invalid JSON: %s" % (line_number, error.msg))
                continue
            if not isinstance(record, dict):
                errors.add("line %d must contain a JSON object" % line_number)
                continue
            record_count += 1
            observed_fields = set(record)
            if observed_fields != expected_fields:
                missing = sorted(expected_fields - observed_fields)
                extra = sorted(observed_fields - expected_fields)
                errors.add(
                    "line %d schema fields differ: missing=%s extra=%s"
                    % (line_number, missing, extra)
                )

            if record.get("source_id") != source_id:
                errors.add("line %d source_id does not match %s" % (line_number, source_id))
            if all(field in record for field in key_fields):
                fingerprint = _duplicate_fingerprint(record, key_fields)
                if fingerprint in fingerprints:
                    duplicate_count += 1
                    errors.add("line %d has duplicate dimensions" % line_number)
                else:
                    fingerprints.add(fingerprint)

            if period_field in record:
                periods.add(record[period_field])
            for field, allowed in allowed_values.items():
                if field not in record:
                    continue
                value = record[field]
                observed_allowed[field].add(value)
                if value not in allowed:
                    errors.add(
                        "line %d field %s has unknown allowed value %r"
                        % (line_number, field, value)
                    )
            for field in distinct_expectations:
                if field in record:
                    observed_distinct[field].add(record[field])

            for field in metric_fields:
                if field not in record:
                    continue
                value = record[field]
                if record_type == "population" and value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    errors.add(
                        "line %d field %s must be a non-negative integer"
                        % (line_number, field)
                    )
            for field in sums:
                value = record.get(field)
                if isinstance(value, int) and not isinstance(value, bool):
                    sums[field] += value

            if record_type == "population":
                suppressed = record.get("suppressed")
                value = record.get("value")
                if not isinstance(suppressed, bool):
                    errors.add("line %d suppressed must be boolean" % line_number)
                elif suppressed and value is not None:
                    errors.add(
                        "line %d suppressed record must have a null value" % line_number
                    )
                elif not suppressed and value is None:
                    errors.add(
                        "line %d unsuppressed record must have an integer value"
                        % line_number
                    )

            for anchor_index, anchor in enumerate(anchors):
                where = anchor.get("where", {})
                if not all(key in record and record[key] == value for key, value in where.items()):
                    continue
                anchor_matches[anchor_index] += 1
                for field, expected in anchor.get("expect", {}).items():
                    if record.get(field) != expected:
                        errors.add(
                            "line %d anchor expected %s=%r but observed %r"
                            % (line_number, field, expected, record.get(field))
                        )

    expected_count = int(profile["expected_record_count"])
    if record_count != expected_count:
        errors.add(
            "expected record_count %d but observed %d" % (expected_count, record_count)
        )
    if artifact_manifest is not None:
        manifest_count = artifact_manifest.get("record_count")
        if manifest_count != record_count:
            errors.add(
                "manifest record_count %r does not match observed %d"
                % (manifest_count, record_count)
            )

    expected_periods = profile.get(
        "expected_periods" if record_type == "population" else "expected_years"
    )
    if expected_periods is not None and set(expected_periods) != periods:
        errors.add(
            "expected %s %r but observed %r"
            % (
                "periods" if record_type == "population" else "years",
                _sorted_values(set(expected_periods)),
                _sorted_values(periods),
            )
        )
    for field, expected in distinct_expectations.items():
        observed = len(observed_distinct[field])
        if observed != expected:
            errors.add(
                "field %s expected %d distinct values but observed %d"
                % (field, expected, observed)
            )
    for field, expected in sum_expectations.items():
        if sums[field] != expected:
            errors.add(
                "field %s expected sum %r but observed %r"
                % (field, expected, sums[field])
            )
    for index, anchor in enumerate(anchors):
        expected_matches = anchor.get("expected_matches", 1)
        if anchor_matches[index] != expected_matches:
            errors.add(
                "anchor %d expected %d matches but observed %d"
                % (index + 1, expected_matches, anchor_matches[index])
            )

    observed_periods = _sorted_values(periods)
    report = {
        "quality_report_schema_version": QUALITY_REPORT_SCHEMA_VERSION,
        "source_id": source_id,
        "record_type": record_type,
        "input_filename": normalized_path.name,
        "input_sha256": sha256_file(normalized_path),
        "artifact_sha256": actual_artifact_hash,
        "record_count": record_count,
        "duplicate_count": duplicate_count,
        "observed_periods" if record_type == "population" else "observed_years": observed_periods,
        "observed_values": {
            field: _sorted_values(values) for field, values in observed_allowed.items()
        },
        "distinct_counts": {
            field: len(values) for field, values in observed_distinct.items()
        },
        "sums": sums,
        "anchors_checked": len(anchors),
        "anchor_matches": anchor_matches,
        "error_count": errors.count,
        "errors_truncated": errors.count > len(errors.messages),
        "errors": errors.messages,
        "passed": errors.count == 0,
    }
    return report
