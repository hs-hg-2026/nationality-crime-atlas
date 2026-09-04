"""Build a compact dashboard export from immutable indicator products."""

import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .provenance import sha256_file


COMPACT_EXPORT_SCHEMA_VERSION = 5
LATEST_SCHEMA_VERSION = 5
CALCULATION_STATUSES = ("calculated", "refused")
SAME_YEAR_GAP_CONTEXT_ID = "all_resident_same_year_recognition_clearance_gap"
RECOGNIZED_CONTEXT_ID = "all_resident_recognized_cases"
CLEARED_CASES_CONTEXT_ID = "all_resident_cleared_cases"

_INDICATOR_DEFINITION_FIELDS = (
    "indicator_run_schema_version",
    "indicator_id",
    "label_ja",
    "label_en",
    "measure_kind",
    "canonical_formula",
    "display_formula",
    "statistical_compatibility",
    "entity_dimension",
    "display_multiplier",
    "display_scale_status",
    "display_unit_label_ja",
    "display_unit_label_en",
    "crosswalk_policy",
    "ui_caveat",
    "small_number_warning_policy_version",
    "small_number_warning_policy_status",
    "default_ranking_behavior",
)
_ALL_RESIDENT_DEFINITION_FIELDS = (
    "all_resident_context_schema_version",
    "context_id",
    "label_ja",
    "label_en",
    "measure_kind",
    "canonical_formula",
    "display_formula",
    "statistical_compatibility",
    "display_multiplier",
    "display_scale_status",
    "display_unit_label_ja",
    "display_unit_label_en",
    "crosswalk_policy",
)
_NATIONALITY_COMPARISON_DEFINITION_FIELDS = (
    "nationality_comparison_schema_version",
    "comparison_id",
    "label_ja",
    "label_en",
    "measure_kind",
    "canonical_formula",
    "display_formula",
    "statistical_compatibility",
    "display_multiplier",
    "display_unit_label_ja",
    "display_unit_label_en",
    "default_display_behavior",
    "interpretation_policy",
    "ui_caveat",
    "entity_dimension",
)
_OFFENSE_COMPOSITION_DEFINITION_FIELDS = (
    "offense_composition_schema_version",
    "composition_id",
    "label_ja",
    "label_en",
    "interpretation_policy",
    "ui_caveat",
)
_OFFENSE_CATEGORY_DEFINITION_FIELDS = (
    "offense_id",
    "offense_label",
    "category_display_order",
    "category_color",
    "official_severity_role",
)
_SAFE_RELATIVE_PATH_KEYS = ("run_relpath",)
_PUBLIC_SOURCE_FIELDS = (
    "series_id",
    "dataset",
    "publisher",
    "source_table",
    "source_period",
    "sha256",
    "landing_url",
    "download_url",
    "retrieved_at",
    "revision",
    "verification_level",
    "normalized_sha256",
)


@dataclass(frozen=True)
class CompactExportReport:
    """Paths and counts for one compact export bundle."""

    output_dir: Path
    export_path: Path
    summary_path: Path
    latest_path: Path
    record_counts: Mapping[str, int]


@dataclass(frozen=True)
class _DatasetBundle:
    name: str
    latest_path: Path
    latest_manifest: Mapping[str, object]
    latest_sha256: str
    run_dir: Path
    summary_path: Path
    summary: Mapping[str, object]
    summary_sha256: str
    records_path: Path
    records_sha256: str
    records: Sequence[Mapping[str, object]]


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise SchemaError("Unable to read %s: %s" % (label, path)) from error


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_snapshot(
    path: Path, label: str
) -> Tuple[Mapping[str, object], str]:
    raw = _read_bytes(path, label)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid %s JSON: %s" % (label, path)) from error
    if not isinstance(value, dict):
        raise SchemaError("%s JSON must contain an object: %s" % (label, path))
    return value, _sha256_bytes(raw)


def _read_jsonl_snapshot(
    path: Path, label: str
) -> Tuple[List[Mapping[str, object]], str]:
    raw = _read_bytes(path, label)
    rows = []
    try:
        text = raw.decode("utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError(
                    "%s row must be an object: %s:%d" % (label, path, line_number)
                )
            rows.append(row)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid %s JSONL: %s" % (label, path)) from error
    return rows, _sha256_bytes(raw)


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("%s must be a non-empty string" % label)
    return value


def _require_sha256(value: object, label: str) -> str:
    result = _require_string(value, label)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise SchemaError("%s must be a lowercase SHA-256 digest" % label)
    return result


def _require_safe_relpath(value: object, label: str) -> Path:
    relative = Path(_require_string(value, label))
    if relative.is_absolute() or ".." in relative.parts:
        raise SchemaError("Unsafe %s: %s" % (label, relative))
    return relative


def _contract_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise SchemaError("generated_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone offset")
    return parsed.strftime("%Y%m%d_%H%M%S")


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    """Durably publish JSON through a unique same-directory temporary file."""

    destination = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".%s." % destination.name,
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _status_counts(rows: Iterable[Mapping[str, object]]) -> Mapping[str, int]:
    counter = Counter()
    for row in rows:
        status = row.get("calculation_status")
        if status not in CALCULATION_STATUSES:
            raise SchemaError("Unsupported calculation_status: %r" % status)
        counter[status] += 1
    return {status: counter.get(status, 0) for status in CALCULATION_STATUSES}


def _validate_source_summary(
    *,
    name: str,
    summary: Mapping[str, object],
    schema_key: str,
    expected_schema_version: int,
    record_count_key: str,
    rows: Sequence[Mapping[str, object]],
) -> None:
    if summary.get(schema_key) != expected_schema_version:
        raise SchemaError("Unsupported %s schema_version in summary.json" % name)
    expected_count = summary.get(record_count_key)
    if isinstance(expected_count, bool) or not isinstance(expected_count, int):
        raise SchemaError("%s summary record_count must be an integer" % name)
    if expected_count != len(rows):
        raise SchemaError("%s summary record_count differs from records" % name)
    expected_status_counts = summary.get("status_counts")
    if not isinstance(expected_status_counts, dict):
        raise SchemaError("%s summary status_counts must be an object" % name)
    observed_status_counts = _status_counts(rows)
    normalized_expected = {
        status: expected_status_counts.get(status, 0) for status in CALCULATION_STATUSES
    }
    if normalized_expected != observed_status_counts or any(
        key not in CALCULATION_STATUSES for key in expected_status_counts
    ):
        raise SchemaError("%s summary status_counts differ from records" % name)


def _validate_source_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    name: str,
    schema_key: str,
    expected_schema_version: int,
) -> None:
    if not rows:
        raise SchemaError("%s records are empty" % name)
    seen = set()
    for index, row in enumerate(rows, start=1):
        if row.get(schema_key) != expected_schema_version:
            raise SchemaError("Unsupported %s record schema at row %d" % (name, index))
        canonical = json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if canonical in seen:
            raise SchemaError("Duplicate %s record at row %d" % (name, index))
        seen.add(canonical)


def _load_dataset_bundle(
    *,
    name: str,
    latest_path: Path,
    schema_key: str,
    expected_schema_version: int,
    records_filename: str,
    records_hash_key: str,
    summary_record_count_key: str,
) -> _DatasetBundle:
    latest, latest_sha256 = _read_json_snapshot(latest_path, "%s latest" % name)
    if latest.get(schema_key) != expected_schema_version:
        raise SchemaError("Unsupported %s schema_version in latest.json" % name)
    run_relpath = _require_safe_relpath(latest.get("run_relpath"), "run_relpath")
    run_dir = Path(latest_path).parent / run_relpath
    summary_path = run_dir / "summary.json"
    records_path = run_dir / records_filename
    if not summary_path.is_file() or not records_path.is_file():
        raise SchemaError("%s run is incomplete: %s" % (name, run_dir))
    expected_summary_sha256 = _require_sha256(
        latest.get("summary_sha256"), "summary_sha256"
    )
    summary, summary_sha256 = _read_json_snapshot(summary_path, "%s summary" % name)
    if summary_sha256 != expected_summary_sha256:
        raise IntegrityError("%s summary hash differs from latest.json" % name)
    expected_records_sha256 = _require_sha256(
        latest.get(records_hash_key), records_hash_key
    )
    records, records_sha256 = _read_jsonl_snapshot(records_path, "%s records" % name)
    if records_sha256 != expected_records_sha256:
        raise IntegrityError("%s record hash differs from latest.json" % name)
    _validate_source_rows(
        records,
        name=name,
        schema_key=schema_key,
        expected_schema_version=expected_schema_version,
    )
    _validate_source_summary(
        name=name,
        summary=summary,
        schema_key=schema_key,
        expected_schema_version=expected_schema_version,
        record_count_key=summary_record_count_key,
        rows=records,
    )
    for key in _SAFE_RELATIVE_PATH_KEYS:
        if key in latest:
            _require_safe_relpath(latest.get(key), key)
    return _DatasetBundle(
        name=name,
        latest_path=Path(latest_path),
        latest_manifest=latest,
        latest_sha256=latest_sha256,
        run_dir=run_dir,
        summary_path=summary_path,
        summary=summary,
        summary_sha256=summary_sha256,
        records_path=records_path,
        records_sha256=records_sha256,
        records=records,
    )


def _collect_definitions(
    rows: Sequence[Mapping[str, object]],
    *,
    id_field: str,
    definition_fields: Sequence[str],
    label: str,
) -> Mapping[str, Mapping[str, object]]:
    definitions: Dict[str, Dict[str, object]] = {}
    for row in rows:
        row_id = _require_string(row.get(id_field), id_field)
        definition = {
            field: row.get(field) for field in definition_fields if field != id_field
        }
        existing = definitions.get(row_id)
        if existing is None:
            definitions[row_id] = definition
            continue
        if existing != definition:
            raise SchemaError("Conflicting %s definition for %s" % (label, row_id))
    return dict(sorted(definitions.items()))


def _compact_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    id_field: str,
    definition_fields: Sequence[str],
) -> List[Mapping[str, object]]:
    removable_fields = set(definition_fields) - {id_field}
    compacted = []
    for row in rows:
        compacted.append(
            {
                key: value
                for key, value in row.items()
                if key not in removable_fields
            }
        )
    return compacted


def _same_year_gap_pair_key(row: Mapping[str, object]) -> Tuple[str, str, str, int]:
    year = row.get("year")
    if isinstance(year, bool) or not isinstance(year, int):
        raise SchemaError("same-year gap row year must be an integer")
    return (
        _require_string(row.get("geography_id"), "geography_id"),
        _require_string(row.get("geography_type"), "geography_type"),
        _require_string(row.get("geography_label"), "geography_label"),
        year,
    )


def _same_year_gap_index(
    rows: Sequence[Mapping[str, object]], context_id: str
) -> Mapping[Tuple[str, str, str, int], Mapping[str, object]]:
    indexed: Dict[Tuple[str, str, str, int], Mapping[str, object]] = {}
    for row in rows:
        if row.get("context_id") != context_id:
            continue
        key = _same_year_gap_pair_key(row)
        if key in indexed:
            raise SchemaError("Duplicate same-year gap input row: %r" % (key,))
        indexed[key] = row
    if not indexed:
        raise SchemaError("Missing same-year gap input context: %s" % context_id)
    return indexed


def _optional_case_count(value: object, label: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaError("%s must be a non-negative integer or null" % label)
    return value


def derive_same_year_recognition_clearance_gap(
    rows: Sequence[Mapping[str, object]],
) -> Tuple[Mapping[str, object], List[Mapping[str, object]]]:
    """Derive a signed same-year flow difference without calling it unresolved."""

    recognized_by_key = _same_year_gap_index(rows, RECOGNIZED_CONTEXT_ID)
    cleared_by_key = _same_year_gap_index(rows, CLEARED_CASES_CONTEXT_ID)
    if set(recognized_by_key) != set(cleared_by_key):
        missing_cleared = sorted(set(recognized_by_key) - set(cleared_by_key))
        missing_recognized = sorted(set(cleared_by_key) - set(recognized_by_key))
        raise SchemaError(
            "Same-year recognized/cleared geography sets differ: "
            "missing_cleared=%r missing_recognized=%r"
            % (missing_cleared, missing_recognized)
        )

    caveat = (
        "当年の検挙件数には前年以前に認知した事件の検挙が含まれ得るため、"
        "認知件数との差分・割合は同一事件cohortの未解決件数／未解決率ではない。"
        "値はclampせず、負値も含めて同年flowの機械的差分として表示する。"
    )
    definition = {
        "all_resident_context_schema_version": 1,
        "label_ja": "都道府県等別 刑法犯認知件数−検挙件数の同年差分",
        "label_en": "Same-year recognized minus cleared criminal-code cases by published geography",
        "measure_kind": "public_data_derived_same_year_flow_difference",
        "canonical_formula": "(recognized_cases - cleared_cases) / recognized_cases",
        "display_formula": "quotient * display_multiplier",
        "statistical_compatibility": "not_established",
        "display_multiplier": 100.0,
        "display_scale_status": "provisional",
        "display_unit_label_ja": "%",
        "display_unit_label_en": "%",
        "crosswalk_policy": "same_source_same_published_geography",
        "display_kind": "same_year_recognition_clearance_gap",
        "interpretation_policy": "same_year_flow_difference_not_cohort_unresolved",
        "ui_caveat": caveat,
    }
    base_flags = {
        "case_count_not_person_count",
        "clearance_can_include_prior_year_recognitions",
        "criminal_code_scope_only",
        "not_unresolved_case_cohort",
        "same_year_flow_difference",
    }
    preserved_flags = {
        "non_prefecture_published_geography",
        "numerator_not_published",
        "numerator_residency_scope_not_established",
        "police_reporting_area_unresolved",
        "primary_baseline_is_all_residents",
    }
    derived_rows: List[Mapping[str, object]] = []
    for key, recognized_row in recognized_by_key.items():
        cleared_row = cleared_by_key[key]
        recognized_source_id = recognized_row.get("numerator_source_id")
        cleared_source_id = cleared_row.get("numerator_source_id")
        if recognized_source_id != cleared_source_id:
            raise SchemaError("Same-year gap inputs use different sources for %r" % (key,))

        recognized_value = _optional_case_count(
            recognized_row.get("numerator_value"), "recognized_cases_value"
        )
        cleared_value = _optional_case_count(
            cleared_row.get("numerator_value"), "cleared_cases_value"
        )
        gap_value = None
        quotient = None
        display_value = None
        refusal_reason = None
        calculation_status = "calculated"
        if recognized_value is None or cleared_value is None:
            calculation_status = "refused"
            recognized_reason = recognized_row.get("refusal_reason")
            cleared_reason = cleared_row.get("refusal_reason")
            refusal_reason = (
                recognized_reason
                if recognized_reason == cleared_reason and recognized_reason is not None
                else "paired_source_value_unavailable"
            )
        else:
            gap_value = recognized_value - cleared_value
            if recognized_value == 0:
                calculation_status = "refused"
                refusal_reason = "zero_recognized_cases"
            else:
                quotient = gap_value / recognized_value
                display_value = quotient * 100.0

        mismatch_flags = set(base_flags)
        for source_row in (recognized_row, cleared_row):
            raw_flags = source_row.get("mismatch_flags", [])
            if not isinstance(raw_flags, (list, tuple)):
                raise SchemaError("same-year gap mismatch_flags must be an array")
            mismatch_flags.update(flag for flag in raw_flags if flag in preserved_flags)

        geography_id, geography_type, geography_label, year = key
        derived_rows.append(
            {
                "all_resident_context_schema_version": 1,
                "context_id": SAME_YEAR_GAP_CONTEXT_ID,
                **definition,
                "geography_label": geography_label,
                "geography_id": geography_id,
                "geography_type": geography_type,
                "year": year,
                "reference_date": "%04d-12-31" % year,
                "numerator_source_id": recognized_source_id,
                "denominator_source_id": recognized_source_id,
                "numerator_metric": "recognized_minus_cleared_cases_same_year",
                "denominator_metric": "recognized_cases",
                "numerator_value": gap_value,
                "denominator_value": recognized_value,
                "recognized_cases_value": recognized_value,
                "cleared_cases_value": cleared_value,
                "quotient": quotient,
                "display_value": display_value,
                "crosswalk_status": "paired_same_source_geography",
                "targets_complete": bool(
                    recognized_row.get("targets_complete")
                    and cleared_row.get("targets_complete")
                ),
                "calculation_status": calculation_status,
                "refusal_reason": refusal_reason,
                "mismatch_flags": sorted(mismatch_flags),
                "canonical_component_ids": list(
                    recognized_row.get("canonical_component_ids", [])
                ),
                "canonical_component_labels": list(
                    recognized_row.get("canonical_component_labels", [])
                ),
                "numerator_context": {
                    "recognized_metric": "recognized_cases",
                    "cleared_metric": "cleared_cases",
                    "period_type": "annual_flow",
                    "year": year,
                    "cohort_linkage": "not_available",
                    "clearance_time_scope": "can_include_prior_year_recognitions",
                },
                "denominator_context": {
                    "metric": "recognized_cases",
                    "period_type": "annual_flow",
                    "year": year,
                },
            }
        )
    return definition, derived_rows


def _compact_offense_rows(
    rows: Sequence[Mapping[str, object]],
) -> List[Mapping[str, object]]:
    removable_fields = set(
        _OFFENSE_COMPOSITION_DEFINITION_FIELDS
        + _OFFENSE_CATEGORY_DEFINITION_FIELDS
    ) - {"composition_id", "offense_id"}
    return [
        {key: value for key, value in row.items() if key not in removable_fields}
        for row in rows
    ]


def _validate_offense_composition_bundle(bundle: _DatasetBundle) -> None:
    threshold = bundle.summary.get("small_number_total_threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold <= 0:
        raise SchemaError(
            "offense composition small_number_total_threshold must be positive"
        )
    raw_definitions = bundle.summary.get("category_definitions")
    if not isinstance(raw_definitions, list) or not raw_definitions:
        raise SchemaError(
            "offense_composition summary category_definitions must be an array"
        )
    expected_categories = {}
    for raw_definition in raw_definitions:
        if not isinstance(raw_definition, dict):
            raise SchemaError("offense category definition must be an object")
        offense_id = _require_string(
            raw_definition.get("offense_id"), "offense_id"
        )
        if offense_id in expected_categories:
            raise SchemaError("Duplicate offense category definition: %s" % offense_id)
        expected_categories[offense_id] = {
            "offense_label": _require_string(
                raw_definition.get("label_ja"), "category label_ja"
            ),
            "category_display_order": raw_definition.get("display_order"),
            "category_color": _require_string(
                raw_definition.get("color"), "category color"
            ),
            "official_severity_role": _require_string(
                raw_definition.get("official_severity_role"),
                "official_severity_role",
            ),
        }
    observed_categories = _collect_definitions(
        bundle.records,
        id_field="offense_id",
        definition_fields=_OFFENSE_CATEGORY_DEFINITION_FIELDS,
        label="offense category",
    )
    if observed_categories != dict(sorted(expected_categories.items())):
        raise SchemaError(
            "offense category definitions differ between summary and records"
        )

    by_entity: Dict[str, List[Mapping[str, object]]] = {}
    for row in bundle.records:
        entity_id = _require_string(row.get("entity_id"), "entity_id")
        by_entity.setdefault(entity_id, []).append(row)
    summary_entity_count = bundle.summary.get("entity_count")
    if (
        isinstance(summary_entity_count, bool)
        or not isinstance(summary_entity_count, int)
        or summary_entity_count != len(by_entity)
    ):
        raise SchemaError("offense composition summary entity_count differs")
    category_ids = set(expected_categories)
    for entity_id, entity_rows in by_entity.items():
        if {row.get("offense_id") for row in entity_rows} != category_ids:
            raise SchemaError(
                "offense categories are incomplete for entity %s" % entity_id
            )
        for metric in ("cleared_cases", "cleared_persons"):
            total_field = "criminal_code_%s_total" % metric
            share_field = "%s_share" % metric
            status_field = "%s_share_status" % metric
            totals = {row.get(total_field) for row in entity_rows}
            if len(totals) != 1:
                raise SchemaError(
                    "offense composition totals conflict for entity %s" % entity_id
                )
            total = next(iter(totals))
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                raise SchemaError("offense composition total must be non-negative")
            values = [row.get(metric) for row in entity_rows]
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values
            ):
                raise SchemaError("offense composition values must be non-negative")
            if sum(values) != total:
                raise SchemaError(
                    "offense composition values do not sum to total for %s"
                    % entity_id
                )
            shares = [row.get(share_field) for row in entity_rows]
            statuses = {row.get(status_field) for row in entity_rows}
            if total == 0:
                if statuses != {"refused_zero_total"} or any(
                    share is not None for share in shares
                ):
                    raise SchemaError(
                        "zero-total offense shares must be explicitly refused"
                    )
            elif statuses != {"calculated"} or any(
                isinstance(share, bool) or not isinstance(share, (int, float))
                for share in shares
            ):
                raise SchemaError("nonzero offense shares must be calculated")
            elif not math.isclose(sum(shares), 1.0, rel_tol=1e-9, abs_tol=1e-9):
                raise SchemaError(
                    "offense composition shares do not sum to one for %s"
                    % entity_id
                )

    clustering = bundle.summary.get("clustering")
    if not isinstance(clustering, dict):
        raise SchemaError("offense composition clustering must be an object")
    entity_ids = set(by_entity)
    for metric in ("cleared_cases", "cleared_persons"):
        definition = clustering.get(metric)
        if not isinstance(definition, dict):
            raise SchemaError("offense composition clustering metric is missing")
        order = definition.get("order")
        if not isinstance(order, list) or len(order) != len(set(order)):
            raise SchemaError("offense composition cluster order is invalid")
        if set(order) != entity_ids:
            raise SchemaError("offense composition cluster order is incomplete")


def _public_sources(
    bundles: Sequence[_DatasetBundle],
) -> Mapping[str, Mapping[str, object]]:
    sources: Dict[str, Dict[str, object]] = {}
    for bundle in bundles:
        raw_artifacts = bundle.summary.get("source_artifacts")
        if not isinstance(raw_artifacts, dict) or not raw_artifacts:
            raise SchemaError("%s summary source_artifacts must be a non-empty object" % bundle.name)
        for raw_source_id, raw_artifact in raw_artifacts.items():
            source_id = _require_string(raw_source_id, "source_id")
            if not isinstance(raw_artifact, dict):
                raise SchemaError("source_artifacts[%s] must be an object" % source_id)
            artifact = {}
            for field in _PUBLIC_SOURCE_FIELDS:
                value = raw_artifact.get(field)
                if field in {"sha256", "normalized_sha256"}:
                    artifact[field] = _require_sha256(
                        value, "source_artifacts[%s].%s" % (source_id, field)
                    )
                else:
                    artifact[field] = _require_string(
                        value, "source_artifacts[%s].%s" % (source_id, field)
                    )
            existing = sources.get(source_id)
            if existing is not None and existing != artifact:
                raise SchemaError("Conflicting public source metadata for %s" % source_id)
            sources[source_id] = artifact
    return dict(sorted(sources.items()))


def _validate_record_source_links(
    rows: Sequence[Mapping[str, object]],
    sources: Mapping[str, Mapping[str, object]],
    *,
    label: str,
    scalar_fields: Sequence[str] = ("numerator_source_id", "denominator_source_id"),
    array_fields: Sequence[str] = (),
) -> None:
    for index, row in enumerate(rows, start=1):
        for field in scalar_fields:
            source_id = row.get(field)
            if source_id is not None:
                source_id = _require_string(source_id, "%s.%s" % (label, field))
            if source_id is not None and source_id not in sources:
                raise SchemaError(
                    "%s row %d references missing public source %s"
                    % (label, index, source_id)
                )
        for field in array_fields:
            source_ids = row.get(field)
            if not isinstance(source_ids, (list, tuple)) or not source_ids:
                raise SchemaError("%s.%s must be a non-empty array" % (label, field))
            for raw_source_id in source_ids:
                source_id = _require_string(
                    raw_source_id, "%s.%s" % (label, field)
                )
                if source_id not in sources:
                    raise SchemaError(
                        "%s row %d references missing public source %s"
                        % (label, index, source_id)
                    )


def _publication_policy() -> Mapping[str, object]:
    return {
        "primary_view": "all_resident_context",
        "secondary_view": "nationality_comparison",
        "supplementary_view": "nationality_indicators",
        "composition_view": "offense_composition",
        "same_year_gap_view": SAME_YEAR_GAP_CONTEXT_ID,
        "same_year_gap_is_unresolved_cohort": False,
        "derived_value_label_ja": "公表統計由来の参考比率",
        "derived_value_label_en": "public-data-derived reference ratio",
        "count_and_reference_ratio_toggle_required": True,
        "official_crime_rate_claim_allowed": False,
    }


def generate_compact_export(
    *,
    indicator_latest_path: Path,
    all_resident_latest_path: Path,
    nationality_comparison_latest_path: Path,
    offense_composition_latest_path: Path,
    output_root: Path,
    generated_at: str,
) -> CompactExportReport:
    """Build one immutable compact export bundle for the dashboard layer."""

    indicator_bundle = _load_dataset_bundle(
        name="nationality_indicators",
        latest_path=indicator_latest_path,
        schema_key="indicator_run_schema_version",
        expected_schema_version=2,
        records_filename="indicator_records.jsonl",
        records_hash_key="indicator_records_sha256",
        summary_record_count_key="indicator_record_count",
    )
    all_resident_bundle = _load_dataset_bundle(
        name="all_resident_context",
        latest_path=all_resident_latest_path,
        schema_key="all_resident_context_schema_version",
        expected_schema_version=1,
        records_filename="regional_context_records.jsonl",
        records_hash_key="regional_context_records_sha256",
        summary_record_count_key="record_count",
    )
    comparison_bundle = _load_dataset_bundle(
        name="nationality_comparison",
        latest_path=nationality_comparison_latest_path,
        schema_key="nationality_comparison_schema_version",
        expected_schema_version=1,
        records_filename="nationality_comparison_records.jsonl",
        records_hash_key="nationality_comparison_records_sha256",
        summary_record_count_key="record_count",
    )
    offense_bundle = _load_dataset_bundle(
        name="offense_composition",
        latest_path=offense_composition_latest_path,
        schema_key="offense_composition_schema_version",
        expected_schema_version=1,
        records_filename="offense_composition_records.jsonl",
        records_hash_key="offense_composition_records_sha256",
        summary_record_count_key="record_count",
    )
    _validate_offense_composition_bundle(offense_bundle)
    gap_definition, gap_records = derive_same_year_recognition_clearance_gap(
        all_resident_bundle.records
    )
    all_context_records = [*all_resident_bundle.records, *gap_records]

    indicator_definitions = _collect_definitions(
        indicator_bundle.records,
        id_field="indicator_id",
        definition_fields=_INDICATOR_DEFINITION_FIELDS,
        label="indicator",
    )
    context_definitions = dict(_collect_definitions(
        all_resident_bundle.records,
        id_field="context_id",
        definition_fields=_ALL_RESIDENT_DEFINITION_FIELDS,
        label="context",
    ))
    context_definitions[SAME_YEAR_GAP_CONTEXT_ID] = gap_definition
    context_definitions = dict(sorted(context_definitions.items()))
    comparison_definitions = _collect_definitions(
        comparison_bundle.records,
        id_field="comparison_id",
        definition_fields=_NATIONALITY_COMPARISON_DEFINITION_FIELDS,
        label="nationality comparison",
    )
    offense_composition_definitions = _collect_definitions(
        offense_bundle.records,
        id_field="composition_id",
        definition_fields=_OFFENSE_COMPOSITION_DEFINITION_FIELDS,
        label="offense composition",
    )
    raw_offense_category_definitions = _collect_definitions(
        offense_bundle.records,
        id_field="offense_id",
        definition_fields=_OFFENSE_CATEGORY_DEFINITION_FIELDS,
        label="offense category",
    )
    offense_category_definitions = {
        offense_id: {
            "label_ja": definition["offense_label"],
            "display_order": definition["category_display_order"],
            "color": definition["category_color"],
            "official_severity_role": definition["official_severity_role"],
        }
        for offense_id, definition in raw_offense_category_definitions.items()
    }
    category_order = [
        offense_id
        for offense_id, _ in sorted(
            offense_category_definitions.items(),
            key=lambda item: item[1]["display_order"],
        )
    ]
    offense_composition_definitions = {
        composition_id: dict(
            definition,
            category_ids=category_order,
            clustering=offense_bundle.summary["clustering"],
            small_number_total_threshold=offense_bundle.summary[
                "small_number_total_threshold"
            ],
        )
        for composition_id, definition in offense_composition_definitions.items()
    }
    compact_indicator_rows = _compact_rows(
        indicator_bundle.records,
        id_field="indicator_id",
        definition_fields=_INDICATOR_DEFINITION_FIELDS,
    )
    compact_context_rows = _compact_rows(
        all_resident_bundle.records,
        id_field="context_id",
        definition_fields=_ALL_RESIDENT_DEFINITION_FIELDS,
    )
    compact_context_rows.extend(
        {
            key: value
            for key, value in row.items()
            if key not in gap_definition
        }
        for row in gap_records
    )
    compact_comparison_rows = _compact_rows(
        comparison_bundle.records,
        id_field="comparison_id",
        definition_fields=_NATIONALITY_COMPARISON_DEFINITION_FIELDS,
    )
    compact_offense_rows = _compact_offense_rows(offense_bundle.records)
    public_sources = _public_sources(
        (
            indicator_bundle,
            all_resident_bundle,
            comparison_bundle,
            offense_bundle,
        )
    )
    _validate_record_source_links(
        indicator_bundle.records,
        public_sources,
        label="nationality_indicators",
    )
    _validate_record_source_links(
        all_context_records,
        public_sources,
        label="all_resident_context",
    )
    _validate_record_source_links(
        comparison_bundle.records,
        public_sources,
        label="nationality_comparison",
        scalar_fields=("denominator_source_id",),
        array_fields=("numerator_source_ids",),
    )
    _validate_record_source_links(
        offense_bundle.records,
        public_sources,
        label="offense_composition",
        scalar_fields=(),
        array_fields=("numerator_source_ids",),
    )
    record_counts = {
        "nationality_indicators": len(compact_indicator_rows),
        "all_resident_context": len(compact_context_rows),
        "nationality_comparison": len(compact_comparison_rows),
        "offense_composition": len(compact_offense_rows),
    }
    source_runs = {
        "nationality_indicators": {
            "latest_path": indicator_bundle.latest_path.name,
            "latest_sha256": indicator_bundle.latest_sha256,
            "latest_manifest": dict(indicator_bundle.latest_manifest),
            "summary_path": "%s/summary.json" % indicator_bundle.run_dir.name,
            "summary_sha256": indicator_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (indicator_bundle.run_dir.name, indicator_bundle.records_path.name),
            "records_sha256": indicator_bundle.records_sha256,
            "record_count": len(indicator_bundle.records),
            "status_counts": _status_counts(indicator_bundle.records),
        },
        "all_resident_context": {
            "latest_path": all_resident_bundle.latest_path.name,
            "latest_sha256": all_resident_bundle.latest_sha256,
            "latest_manifest": dict(all_resident_bundle.latest_manifest),
            "summary_path": "%s/summary.json" % all_resident_bundle.run_dir.name,
            "summary_sha256": all_resident_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (all_resident_bundle.run_dir.name, all_resident_bundle.records_path.name),
            "records_sha256": all_resident_bundle.records_sha256,
            "record_count": len(all_resident_bundle.records),
            "status_counts": _status_counts(all_resident_bundle.records),
        },
        "nationality_comparison": {
            "latest_path": comparison_bundle.latest_path.name,
            "latest_sha256": comparison_bundle.latest_sha256,
            "latest_manifest": dict(comparison_bundle.latest_manifest),
            "summary_path": "%s/summary.json" % comparison_bundle.run_dir.name,
            "summary_sha256": comparison_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (comparison_bundle.run_dir.name, comparison_bundle.records_path.name),
            "records_sha256": comparison_bundle.records_sha256,
            "record_count": len(comparison_bundle.records),
            "status_counts": _status_counts(comparison_bundle.records),
        },
        "offense_composition": {
            "latest_path": offense_bundle.latest_path.name,
            "latest_sha256": offense_bundle.latest_sha256,
            "latest_manifest": dict(offense_bundle.latest_manifest),
            "summary_path": "%s/summary.json" % offense_bundle.run_dir.name,
            "summary_sha256": offense_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (offense_bundle.run_dir.name, offense_bundle.records_path.name),
            "records_sha256": offense_bundle.records_sha256,
            "record_count": len(offense_bundle.records),
            "status_counts": _status_counts(offense_bundle.records),
        },
    }
    payload = {
        "compact_export_schema_version": COMPACT_EXPORT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "publication_policy": _publication_policy(),
        "sources": public_sources,
        "source_runs": source_runs,
        "definitions": {
            "indicator_ids": indicator_definitions,
            "context_ids": context_definitions,
            "nationality_comparison_ids": comparison_definitions,
            "offense_composition_ids": offense_composition_definitions,
            "offense_category_ids": offense_category_definitions,
        },
        "records": {
            "nationality_indicators": compact_indicator_rows,
            "all_resident_context": compact_context_rows,
            "nationality_comparison": compact_comparison_rows,
            "offense_composition": compact_offense_rows,
        },
    }

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (_contract_timestamp(generated_at) + "_compact_export")
    if destination.exists():
        raise IntegrityError(
            "Timestamped compact export already exists and was not overwritten: %s" % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".compact-export-", dir=destination_root))
    try:
        export_path = staging / "dashboard_export.json"
        summary_path = staging / "summary.json"
        _write_json(export_path, payload)
        _write_json(
            summary_path,
            {
                "compact_export_schema_version": COMPACT_EXPORT_SCHEMA_VERSION,
                "generated_at": generated_at,
                "record_counts": record_counts,
                "source_runs": source_runs,
                "definition_counts": {
                    "indicator_ids": len(indicator_definitions),
                    "context_ids": len(context_definitions),
                    "nationality_comparison_ids": len(comparison_definitions),
                    "offense_composition_ids": len(
                        offense_composition_definitions
                    ),
                    "offense_category_ids": len(offense_category_definitions),
                },
                "source_count": len(public_sources),
                "dashboard_export_sha256": sha256_file(export_path),
            },
        )
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_export = destination / "dashboard_export.json"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    _atomic_write_json(
        latest_path,
        {
            "compact_export_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "dashboard_export_sha256": sha256_file(final_export),
        },
    )
    return CompactExportReport(
        output_dir=destination,
        export_path=final_export,
        summary_path=final_summary,
        latest_path=latest_path,
        record_counts=record_counts,
    )
