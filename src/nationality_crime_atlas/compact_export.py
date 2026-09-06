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


COMPACT_EXPORT_SCHEMA_VERSION = 8
LATEST_SCHEMA_VERSION = 8
CALCULATION_STATUSES = ("calculated", "refused")
SAME_YEAR_GAP_CONTEXT_ID = "all_resident_same_year_recognition_clearance_gap"
RECOGNIZED_CONTEXT_ID = "all_resident_recognized_cases"
CLEARED_CASES_CONTEXT_ID = "all_resident_cleared_cases"
CLEARANCE_SHARE_TREND_ID = "national_criminal_code_clearance_foreign_share"
CLEARANCE_SHARE_INTERPRETATION_POLICY = "share_of_clearances_not_population_risk"
CLEARANCE_SHARE_LABEL_JA = (
    "全国の刑法犯検挙（日本人等を含む）に占める外国人区分の割合"
)
CLEARANCE_SHARE_UI_CAVEAT = (
    "分母は日本人等を含む全国の刑法犯検挙総数、分子は警察庁の"
    "「外国人」「来日外国人」区分、または両者の算術差分である。"
    "検挙全体に占める構成比であり、人口当たりの犯罪率、犯罪の発生率、"
    "個人のriskを示さない。「来日外国人」は定着居住者、在日米軍関係者、"
    "在留資格不明者を除く区分で、短期滞在者だけを指さない。差分にも"
    "定着居住者以外が含まれるため、普段から住む外国人だけを表す値ではない。"
)
CLEARANCE_POPULATION_TREND_ID = "national_clearance_population_reference_ratio"
CLEARANCE_POPULATION_INTERPRETATION_POLICY = (
    "public_data_reference_ratio_not_probability"
)
CLEARANCE_POPULATION_LABEL_JA = "人口1,000人当たりの刑法犯検挙参考比率"
CLEARANCE_POPULATION_UI_CAVEAT = (
    "1年間の刑法犯検挙件数または検挙人員を、10月1日の日本人人口または"
    "12月31日の在留外国人数で単純に割った公表統計由来の参考比率である。犯罪統計の分子から"
    "居住者だけを識別できず、特に「外国人全体」と在留外国人人口の対象範囲は一致しない。"
    "犯罪を行う確率や公的な犯罪率を示さない。"
)
CLEARANCE_POPULATION_GROUP_CONTRACTS = {
    "japanese_etc_residual": {
        "label_ja": "日本人等（全国総数−外国人全体の残差）",
        "numerator_source_ids": ("S15", "S08"),
        "population_scope": "japanese_population",
        "derivation_method": (
            "arithmetic_residual_all_person_minus_all_foreign_division"
        ),
        "required_flags": (
            "annual_clearance_flow_vs_point_in_time_population_stock",
            "japanese_numerator_is_arithmetic_residual",
            "japanese_population_rounded_to_nearest_1000",
            "numerator_residency_scope_not_established",
            "october_1_population_reference_date",
            "public_data_reference_ratio_not_official_crime_rate",
        ),
    },
    "all_foreign": {
        "label_ja": "外国人全体（分母は在留外国人数）",
        "numerator_source_ids": ("S08",),
        "population_scope": "resident_foreigner_population",
        "derivation_method": "direct_published_count_division",
        "required_flags": (
            "all_foreign_numerator_vs_resident_foreigner_denominator",
            "annual_clearance_flow_vs_point_in_time_population_stock",
            "december_31_population_reference_date",
            "numerator_residency_scope_not_established",
            "public_data_reference_ratio_not_official_crime_rate",
        ),
    },
}
_JAPANESE_POPULATION_SOURCES = {
    **{year: "S18" for year in range(2015, 2021)},
    2021: "S17_2021",
    2022: "S17_2022",
    2023: "S17_2023",
    2024: "S17",
}
_FOREIGN_POPULATION_COORDINATES = {
    2016: ("S19_2016", "16-12-01-1", 7, 3),
    2017: ("S19_2017", "17-12-01-1", 7, 3),
    2018: ("S19_2018", "18-12-01-1", 7, 3),
    2019: ("S19_2019", "19-12-01-1", 7, 2),
    2020: ("S19_2020", "20-12-01-1", 7, 2),
    2021: ("S19_2021", "21-12-01-1", 7, 2),
    2022: ("S19_2022", "22-12-01m", 5, 6),
    2023: ("S19_2023", "23-12-01m", 5, 5),
    2024: ("S19_2024", "24-12-01m", 5, 5),
}
CLEARANCE_SHARE_SCOPE_CONTRACTS = {
    "all_foreign": {
        "label_ja": "外国人全体",
        "numerator_source_id": "S08",
        "numerator_source_ids": ("S08",),
        "derivation_method": "direct_published_counts_division",
        "required_flags": (
            "all_foreign_scope_not_resident_foreigner_population",
            "denominator_includes_japanese_and_others",
            "share_of_clearance_counts_not_population_rate",
        ),
    },
    "visiting_foreign": {
        "label_ja": "来日外国人",
        "numerator_source_id": "S09",
        "numerator_source_ids": ("S09",),
        "derivation_method": "direct_published_counts_division",
        "required_flags": (
            "denominator_includes_japanese_and_others",
            "share_of_clearance_counts_not_population_rate",
            "visiting_foreign_includes_nonresidents",
        ),
    },
    "all_foreign_minus_visiting_foreign": {
        "label_ja": "外国人全体−来日外国人（差分）",
        "numerator_source_id": "S08",
        "numerator_source_ids": ("S08", "S09"),
        "derivation_method": (
            "arithmetic_residual_all_foreign_minus_visiting_foreign"
        ),
        "required_flags": (
            "arithmetic_residual_not_directly_published",
            "denominator_includes_japanese_and_others",
            "residual_includes_settled_residents_us_forces_and_unknown_status",
            "residual_not_equivalent_to_usual_residents",
            "share_of_clearance_counts_not_population_rate",
        ),
    },
}

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
_CLEARANCE_SHARE_DEFINITION_FIELDS = (
    "national_clearance_share_schema_version",
    "trend_id",
    "label_ja",
    "label_en",
    "interpretation_policy",
    "ui_caveat",
    "display_multiplier",
    "display_unit_label_ja",
)
_CLEARANCE_POPULATION_DEFINITION_FIELDS = (
    "clearance_population_trend_schema_version",
    "trend_id",
    "label_ja",
    "label_en",
    "interpretation_policy",
    "ui_caveat",
    "display_multiplier",
    "display_unit_label_ja",
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


def _clearance_share_semantic_error(detail: str) -> None:
    raise SchemaError("clearance share semantic contract: %s" % detail)


def _validate_clearance_share_components(
    row: Mapping[str, object],
    expected: Sequence[Tuple[object, ...]],
) -> None:
    components = row.get("source_components")
    if not isinstance(components, (list, tuple)) or any(
        not isinstance(component, dict) for component in components
    ):
        _clearance_share_semantic_error("source_components must be an object array")
    actual = [
        (
            component.get("source_id"),
            component.get("role"),
            component.get("metric"),
            component.get("value"),
            component.get("source_table"),
            component.get("source_sheet"),
            component.get("source_row"),
            component.get("source_column"),
        )
        for component in components
    ]
    if actual != list(expected):
        _clearance_share_semantic_error("source_components do not match scope inputs")


def _validate_clearance_share_bundle(bundle: _DatasetBundle) -> None:
    years = bundle.summary.get("years")
    year_count = bundle.summary.get("year_count")
    if (
        not isinstance(years, list)
        or not years
        or any(isinstance(year, bool) or not isinstance(year, int) for year in years)
        or years != sorted(set(years))
    ):
        raise SchemaError("clearance share years must be ascending unique integers")
    if year_count != len(years):
        raise SchemaError("clearance share summary year_count differs")

    seen = set()
    expected_scopes = set(CLEARANCE_SHARE_SCOPE_CONTRACTS)
    expected_metrics = {"cleared_cases", "cleared_persons"}
    for index, row in enumerate(bundle.records, start=1):
        year = row.get("year")
        scope = row.get("foreign_scope")
        metric = row.get("metric")
        key = (year, scope, metric)
        if key in seen:
            raise SchemaError("Duplicate clearance share row: %r" % (key,))
        seen.add(key)
        if year not in years or scope not in expected_scopes or metric not in expected_metrics:
            raise SchemaError("Unsupported clearance share dimensions at row %d" % index)
        scope_contract = CLEARANCE_SHARE_SCOPE_CONTRACTS[scope]
        if (
            row.get("trend_id") != CLEARANCE_SHARE_TREND_ID
            or row.get("label_ja") != CLEARANCE_SHARE_LABEL_JA
            or row.get("interpretation_policy")
            != CLEARANCE_SHARE_INTERPRETATION_POLICY
            or row.get("ui_caveat") != CLEARANCE_SHARE_UI_CAVEAT
            or row.get("foreign_scope_label_ja") != scope_contract["label_ja"]
            or row.get("numerator_source_id")
            != scope_contract["numerator_source_id"]
            or row.get("denominator_source_id") != "S15"
            or row.get("derivation_method")
            != scope_contract["derivation_method"]
            or row.get("metric_label_ja")
            != ("検挙件数" if metric == "cleared_cases" else "検挙人員")
        ):
            _clearance_share_semantic_error(
                "scope, source, label, or interpretation binding differs at row %d"
                % index
            )
        numerator_source_ids = row.get("numerator_source_ids")
        if (
            not isinstance(numerator_source_ids, (list, tuple))
            or not numerator_source_ids
            or any(
                not isinstance(source_id, str) or not source_id
                for source_id in numerator_source_ids
            )
        ):
            raise SchemaError(
                "Invalid clearance share numerator_source_ids at row %d" % index
            )
        if tuple(numerator_source_ids) != scope_contract["numerator_source_ids"]:
            _clearance_share_semantic_error(
                "numerator source binding differs at row %d" % index
            )
        mismatch_flags = row.get("mismatch_flags")
        if (
            not isinstance(mismatch_flags, (list, tuple))
            or any(not isinstance(flag, str) for flag in mismatch_flags)
            or not set(scope_contract["required_flags"]).issubset(mismatch_flags)
        ):
            _clearance_share_semantic_error(
                "required mismatch flags are absent at row %d" % index
            )
        numerator = row.get("numerator_value")
        denominator = row.get("denominator_value")
        quotient = row.get("quotient")
        display_multiplier = row.get("display_multiplier")
        display_value = row.get("display_value")
        if (
            isinstance(numerator, bool)
            or not isinstance(numerator, int)
            or numerator < 0
            or isinstance(denominator, bool)
            or not isinstance(denominator, int)
            or denominator <= 0
            or numerator > denominator
        ):
            raise SchemaError("Invalid clearance share component counts at row %d" % index)
        expected_quotient = numerator / denominator
        if (
            isinstance(quotient, bool)
            or not isinstance(quotient, (int, float))
            or not math.isclose(quotient, expected_quotient, rel_tol=1e-12, abs_tol=1e-12)
            or display_multiplier != 100
            or isinstance(display_value, bool)
            or not isinstance(display_value, (int, float))
            or not math.isclose(
                display_value,
                expected_quotient * display_multiplier,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise SchemaError("Clearance share arithmetic differs at row %d" % index)
        expected_formula = (
            "(S08.%s - S09.%s) / S15.%s" % (metric, metric, metric)
            if scope == "all_foreign_minus_visiting_foreign"
            else "%s.%s / S15.%s"
            % (scope_contract["numerator_source_id"], metric, metric)
        )
        if row.get("derivation_formula") != expected_formula:
            _clearance_share_semantic_error(
                "derivation formula differs at row %d" % index
            )
    expected = {
        (year, scope, metric)
        for year in years
        for scope in expected_scopes
        for metric in expected_metrics
    }
    if seen != expected:
        raise SchemaError("Clearance share year/scope/metric grid is incomplete")

    indexed = {
        (row["year"], row["metric"], row["foreign_scope"]): row
        for row in bundle.records
    }
    for year in years:
        for metric in expected_metrics:
            all_foreign = indexed[(year, metric, "all_foreign")]
            visiting_foreign = indexed[(year, metric, "visiting_foreign")]
            residual = indexed[
                (year, metric, "all_foreign_minus_visiting_foreign")
            ]
            rows = (all_foreign, visiting_foreign, residual)
            if len({row.get("denominator_value") for row in rows}) != 1 or len(
                {row.get("denominator_source_id") for row in rows}
            ) != 1:
                raise SchemaError(
                    "Clearance share denominators differ for %d %s" % (year, metric)
                )
            expected_residual = (
                all_foreign["numerator_value"] - visiting_foreign["numerator_value"]
            )
            if expected_residual < 0 or residual.get("numerator_value") != expected_residual:
                raise SchemaError(
                    "Clearance share residual differs for %d %s" % (year, metric)
                )
            expected_sources = [
                all_foreign.get("numerator_source_id"),
                visiting_foreign.get("numerator_source_id"),
            ]
            if residual.get("numerator_source_ids") != expected_sources:
                raise SchemaError(
                    "Clearance share residual sources differ for %d %s" % (year, metric)
                )
            if residual.get("derivation_method") != (
                "arithmetic_residual_all_foreign_minus_visiting_foreign"
            ):
                raise SchemaError(
                    "Clearance share residual method differs for %d %s" % (year, metric)
                )
            _validate_clearance_share_components(
                all_foreign,
                (
                    (
                        "S08",
                        "numerator",
                        metric,
                        all_foreign["numerator_value"],
                        "130",
                        "01",
                        year - 2007,
                        7 if metric == "cleared_cases" else 8,
                    ),
                    (
                        "S15",
                        "denominator",
                        metric,
                        all_foreign["denominator_value"],
                        "3",
                        "刑法犯総数",
                        year - 2006,
                        5 if metric == "cleared_cases" else 6,
                    ),
                ),
            )
            _validate_clearance_share_components(
                visiting_foreign,
                (
                    (
                        "S09",
                        "numerator",
                        metric,
                        visiting_foreign["numerator_value"],
                        "131",
                        "01",
                        year - 2007,
                        6 if metric == "cleared_cases" else 7,
                    ),
                    (
                        "S15",
                        "denominator",
                        metric,
                        visiting_foreign["denominator_value"],
                        "3",
                        "刑法犯総数",
                        year - 2006,
                        5 if metric == "cleared_cases" else 6,
                    ),
                ),
            )
            _validate_clearance_share_components(
                residual,
                (
                    (
                        "S08",
                        "numerator_minuend",
                        metric,
                        all_foreign["numerator_value"],
                        "130",
                        "01",
                        year - 2007,
                        7 if metric == "cleared_cases" else 8,
                    ),
                    (
                        "S09",
                        "numerator_subtrahend",
                        metric,
                        visiting_foreign["numerator_value"],
                        "131",
                        "01",
                        year - 2007,
                        6 if metric == "cleared_cases" else 7,
                    ),
                    (
                        "S15",
                        "denominator",
                        metric,
                        residual["denominator_value"],
                        "3",
                        "刑法犯総数",
                        year - 2006,
                        5 if metric == "cleared_cases" else 6,
                    ),
                ),
            )


def _clearance_population_semantic_error(detail: str) -> None:
    raise SchemaError("clearance population semantic contract: %s" % detail)


def _clearance_population_component_signature(
    component: Mapping[str, object],
) -> Tuple[object, ...]:
    return (
        component.get("source_id"),
        component.get("role"),
        component.get("metric"),
        component.get("value"),
        component.get("source_table"),
        component.get("source_sheet"),
        component.get("source_row"),
        component.get("source_column"),
        component.get("published_value"),
        component.get("published_unit"),
    )


def _validate_clearance_population_components(
    row: Mapping[str, object],
    expected: Sequence[Tuple[object, ...]],
) -> None:
    components = row.get("source_components")
    if not isinstance(components, (list, tuple)) or any(
        not isinstance(component, dict) for component in components
    ):
        _clearance_population_semantic_error(
            "source_components must be an object array"
        )
    actual = [
        _clearance_population_component_signature(component)
        for component in components
    ]
    if actual != list(expected):
        _clearance_population_semantic_error(
            "source_components do not match population inputs"
        )


def _japanese_population_coordinate(year: int) -> Tuple[object, ...]:
    source_id = _JAPANESE_POPULATION_SOURCES.get(year)
    if source_id is None:
        _clearance_population_semantic_error(
            "unsupported Japanese population year %d" % year
        )
    if source_id == "S18":
        return source_id, "5", "日本人人口 (2015年～2020年)", 11, year - 2010
    return source_id, "2", "第2表", 12, 9


def _validate_clearance_population_bundle(bundle: _DatasetBundle) -> None:
    years = bundle.summary.get("years")
    year_count = bundle.summary.get("year_count")
    if (
        not isinstance(years, list)
        or not years
        or any(isinstance(year, bool) or not isinstance(year, int) for year in years)
        or years != sorted(set(years))
    ):
        raise SchemaError(
            "clearance population years must be ascending unique integers"
        )
    if year_count != len(years):
        raise SchemaError("clearance population summary year_count differs")
    if bundle.summary.get("trend_id") != CLEARANCE_POPULATION_TREND_ID:
        _clearance_population_semantic_error("summary trend_id differs")

    expected_groups = set(CLEARANCE_POPULATION_GROUP_CONTRACTS)
    expected_metrics = {"cleared_cases", "cleared_persons"}
    seen = set()
    for index, row in enumerate(bundle.records, start=1):
        year = row.get("year")
        group = row.get("population_group")
        metric = row.get("metric")
        key = (year, group, metric)
        if key in seen:
            raise SchemaError("Duplicate clearance population row: %r" % (key,))
        seen.add(key)
        if year not in years or group not in expected_groups or metric not in expected_metrics:
            raise SchemaError(
                "Unsupported clearance population dimensions at row %d" % index
            )

        contract = CLEARANCE_POPULATION_GROUP_CONTRACTS[group]
        if (
            row.get("trend_id") != CLEARANCE_POPULATION_TREND_ID
            or row.get("label_ja") != CLEARANCE_POPULATION_LABEL_JA
            or row.get("interpretation_policy")
            != CLEARANCE_POPULATION_INTERPRETATION_POLICY
            or row.get("ui_caveat") != CLEARANCE_POPULATION_UI_CAVEAT
            or row.get("population_group_label_ja") != contract["label_ja"]
            or row.get("population_scope") != contract["population_scope"]
            or row.get("metric_label_ja")
            != ("検挙件数" if metric == "cleared_cases" else "検挙人員")
            or row.get("display_multiplier") != 1000
            or row.get("display_unit_label_ja") != "人口1,000人当たり"
        ):
            _clearance_population_semantic_error(
                "group, label, or interpretation binding differs at row %d" % index
            )

        numerator_source_ids = row.get("numerator_source_ids")
        if (
            not isinstance(numerator_source_ids, (list, tuple))
            or tuple(numerator_source_ids) != contract["numerator_source_ids"]
        ):
            _clearance_population_semantic_error(
                "numerator source binding differs at row %d" % index
            )
        mismatch_flags = row.get("mismatch_flags")
        if (
            not isinstance(mismatch_flags, (list, tuple))
            or any(not isinstance(flag, str) for flag in mismatch_flags)
            or not set(contract["required_flags"]).issubset(mismatch_flags)
        ):
            _clearance_population_semantic_error(
                "required mismatch flags are absent at row %d" % index
            )

        numerator = row.get("numerator_value")
        if isinstance(numerator, bool) or not isinstance(numerator, int) or numerator < 0:
            raise SchemaError(
                "Invalid clearance population numerator at row %d" % index
            )
        clearance_component = (
            "S08",
            "numerator",
            metric,
            numerator,
            "130",
            "01",
            year - 2007,
            7 if metric == "cleared_cases" else 8,
            None,
            None,
        )

        if group == "japanese_etc_residual":
            denominator = row.get("denominator_value")
            components = row.get("source_components")
            if (
                row.get("calculation_status") != "calculated"
                or row.get("refusal_reason") is not None
                or isinstance(denominator, bool)
                or not isinstance(denominator, int)
                or denominator <= 0
                or not isinstance(components, (list, tuple))
                or len(components) != 3
                or not all(isinstance(component, dict) for component in components)
            ):
                _clearance_population_semantic_error(
                    "Japanese residual calculation status differs at row %d" % index
                )
            all_person_value = components[0].get("value")
            all_foreign_value = components[1].get("value")
            if (
                isinstance(all_person_value, bool)
                or not isinstance(all_person_value, int)
                or isinstance(all_foreign_value, bool)
                or not isinstance(all_foreign_value, int)
                or all_person_value - all_foreign_value != numerator
            ):
                _clearance_population_semantic_error(
                    "Japanese numerator residual differs at row %d" % index
                )
            source_id, table, sheet, source_row, source_column = (
                _japanese_population_coordinate(year)
            )
            if (
                row.get("denominator_source_id") != source_id
                or row.get("population_reference_date") != "%d-10-01" % year
                or row.get("denominator_rounding") != "nearest_1000_persons"
                or row.get("derivation_method") != contract["derivation_method"]
                or row.get("derivation_formula")
                != "(S15.%s - S08.%s) / %s.population * 1000"
                % (metric, metric, source_id)
            ):
                _clearance_population_semantic_error(
                    "Japanese source, date, or formula differs at row %d" % index
                )
            _validate_clearance_population_components(
                row,
                (
                    (
                        "S15",
                        "numerator_minuend",
                        metric,
                        all_person_value,
                        "3",
                        "刑法犯総数",
                        year - 2006,
                        5 if metric == "cleared_cases" else 6,
                        None,
                        None,
                    ),
                    (
                        "S08",
                        "numerator_subtrahend",
                        metric,
                        all_foreign_value,
                        "130",
                        "01",
                        year - 2007,
                        7 if metric == "cleared_cases" else 8,
                        None,
                        None,
                    ),
                    (
                        source_id,
                        "denominator",
                        "population",
                        denominator,
                        table,
                        sheet,
                        source_row,
                        source_column,
                        denominator // 1000,
                        "1000_persons",
                    ),
                ),
            )
        else:
            expected_foreign = _FOREIGN_POPULATION_COORDINATES.get(year)
            if expected_foreign is None:
                if (
                    row.get("calculation_status") != "refused"
                    or row.get("refusal_reason")
                    != "resident_foreigner_population_source_not_registered_for_year"
                    or row.get("denominator_value") is not None
                    or row.get("quotient") is not None
                    or row.get("display_value") is not None
                    or row.get("denominator_source_id") is not None
                    or row.get("population_reference_date") is not None
                    or row.get("denominator_rounding") is not None
                    or row.get("derivation_method")
                    != "direct_published_count_division_refused"
                    or row.get("derivation_formula") is not None
                    or "population_denominator_unavailable" not in mismatch_flags
                ):
                    _clearance_population_semantic_error(
                        "foreign refusal semantics differ at row %d" % index
                    )
                _validate_clearance_population_components(row, (clearance_component,))
                continue
            source_id, sheet, source_row, source_column = expected_foreign
            denominator = row.get("denominator_value")
            if (
                row.get("calculation_status") != "calculated"
                or row.get("refusal_reason") is not None
                or isinstance(denominator, bool)
                or not isinstance(denominator, int)
                or denominator <= 0
                or row.get("denominator_source_id") != source_id
                or row.get("population_reference_date") != "%d-12-31" % year
                or row.get("denominator_rounding") != "as_published_persons"
                or row.get("derivation_method") != contract["derivation_method"]
                or row.get("derivation_formula")
                != "S08.%s / %s.population * 1000" % (metric, source_id)
            ):
                _clearance_population_semantic_error(
                    "foreign source, date, or formula differs at row %d" % index
                )
            _validate_clearance_population_components(
                row,
                (
                    clearance_component,
                    (
                        source_id,
                        "denominator",
                        "population",
                        denominator,
                        "1",
                        sheet,
                        source_row,
                        source_column,
                        denominator,
                        "persons",
                    ),
                ),
            )

        denominator = row.get("denominator_value")
        quotient = row.get("quotient")
        display_value = row.get("display_value")
        expected_quotient = numerator / denominator
        if (
            isinstance(quotient, bool)
            or not isinstance(quotient, (int, float))
            or not math.isclose(
                quotient, expected_quotient, rel_tol=1e-12, abs_tol=1e-12
            )
            or isinstance(display_value, bool)
            or not isinstance(display_value, (int, float))
            or not math.isclose(
                display_value,
                expected_quotient * 1000,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise SchemaError(
                "Clearance population arithmetic differs at row %d" % index
            )

    expected = {
        (year, group, metric)
        for year in years
        for group in expected_groups
        for metric in expected_metrics
    }
    if seen != expected:
        raise SchemaError("Clearance population year/group/metric grid is incomplete")


def _validate_clearance_population_share_consistency(
    population_bundle: _DatasetBundle,
    share_bundle: _DatasetBundle,
) -> None:
    share_rows = {
        (row.get("year"), row.get("metric")): row
        for row in share_bundle.records
        if row.get("foreign_scope") == "all_foreign"
    }
    for row in population_bundle.records:
        if row.get("population_group") != "all_foreign":
            continue
        share = share_rows.get((row.get("year"), row.get("metric")))
        if share is None:
            continue
        if (
            row.get("numerator_value") != share.get("numerator_value")
            or row.get("numerator_source_ids") != share.get("numerator_source_ids")
        ):
            _clearance_population_semantic_error(
                "all-foreign numerator differs from clearance-share input"
            )


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
                if field == "normalized_sha256" and value is None:
                    continue
                if field in {"sha256", "normalized_sha256"}:
                    artifact[field] = _require_sha256(
                        value, "source_artifacts[%s].%s" % (source_id, field)
                    )
                else:
                    artifact[field] = _require_string(
                        value, "source_artifacts[%s].%s" % (source_id, field)
                    )
            existing = sources.get(source_id)
            if existing is not None:
                conflicts = {
                    field
                    for field in set(existing) & set(artifact)
                    if existing[field] != artifact[field]
                }
                if conflicts:
                    raise SchemaError(
                        "Conflicting public source metadata for %s" % source_id
                    )
                merged = dict(existing)
                merged.update(artifact)
                sources[source_id] = merged
            else:
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
        "clearance_share_view": "national_criminal_code_clearance_foreign_share",
        "clearance_population_view": CLEARANCE_POPULATION_TREND_ID,
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
    clearance_share_latest_path: Path,
    clearance_population_latest_path: Path,
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
    clearance_share_bundle = _load_dataset_bundle(
        name="clearance_share_trend",
        latest_path=clearance_share_latest_path,
        schema_key="national_clearance_share_schema_version",
        expected_schema_version=2,
        records_filename="clearance_share_records.jsonl",
        records_hash_key="clearance_share_records_sha256",
        summary_record_count_key="record_count",
    )
    clearance_population_bundle = _load_dataset_bundle(
        name="clearance_population_trend",
        latest_path=clearance_population_latest_path,
        schema_key="clearance_population_trend_schema_version",
        expected_schema_version=1,
        records_filename="clearance_population_records.jsonl",
        records_hash_key="clearance_population_records_sha256",
        summary_record_count_key="record_count",
    )
    _validate_offense_composition_bundle(offense_bundle)
    _validate_clearance_share_bundle(clearance_share_bundle)
    _validate_clearance_population_bundle(clearance_population_bundle)
    _validate_clearance_population_share_consistency(
        clearance_population_bundle,
        clearance_share_bundle,
    )
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
    clearance_share_definitions = _collect_definitions(
        clearance_share_bundle.records,
        id_field="trend_id",
        definition_fields=_CLEARANCE_SHARE_DEFINITION_FIELDS,
        label="clearance share trend",
    )
    clearance_population_definitions = _collect_definitions(
        clearance_population_bundle.records,
        id_field="trend_id",
        definition_fields=_CLEARANCE_POPULATION_DEFINITION_FIELDS,
        label="clearance population trend",
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
    compact_clearance_share_rows = _compact_rows(
        clearance_share_bundle.records,
        id_field="trend_id",
        definition_fields=_CLEARANCE_SHARE_DEFINITION_FIELDS,
    )
    compact_clearance_population_rows = _compact_rows(
        clearance_population_bundle.records,
        id_field="trend_id",
        definition_fields=_CLEARANCE_POPULATION_DEFINITION_FIELDS,
    )
    public_sources = _public_sources(
        (
            indicator_bundle,
            all_resident_bundle,
            comparison_bundle,
            offense_bundle,
            clearance_share_bundle,
            clearance_population_bundle,
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
    _validate_record_source_links(
        clearance_share_bundle.records,
        public_sources,
        label="clearance_share_trend",
        array_fields=("numerator_source_ids",),
    )
    _validate_record_source_links(
        clearance_population_bundle.records,
        public_sources,
        label="clearance_population_trend",
        scalar_fields=("denominator_source_id",),
        array_fields=("numerator_source_ids",),
    )
    record_counts = {
        "nationality_indicators": len(compact_indicator_rows),
        "all_resident_context": len(compact_context_rows),
        "nationality_comparison": len(compact_comparison_rows),
        "offense_composition": len(compact_offense_rows),
        "clearance_share_trends": len(compact_clearance_share_rows),
        "clearance_population_trends": len(compact_clearance_population_rows),
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
        "clearance_share_trend": {
            "latest_path": clearance_share_bundle.latest_path.name,
            "latest_sha256": clearance_share_bundle.latest_sha256,
            "latest_manifest": dict(clearance_share_bundle.latest_manifest),
            "summary_path": "%s/summary.json" % clearance_share_bundle.run_dir.name,
            "summary_sha256": clearance_share_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (
                clearance_share_bundle.run_dir.name,
                clearance_share_bundle.records_path.name,
            ),
            "records_sha256": clearance_share_bundle.records_sha256,
            "record_count": len(clearance_share_bundle.records),
            "status_counts": _status_counts(clearance_share_bundle.records),
        },
        "clearance_population_trend": {
            "latest_path": clearance_population_bundle.latest_path.name,
            "latest_sha256": clearance_population_bundle.latest_sha256,
            "latest_manifest": dict(clearance_population_bundle.latest_manifest),
            "summary_path": "%s/summary.json"
            % clearance_population_bundle.run_dir.name,
            "summary_sha256": clearance_population_bundle.summary_sha256,
            "records_path": "%s/%s"
            % (
                clearance_population_bundle.run_dir.name,
                clearance_population_bundle.records_path.name,
            ),
            "records_sha256": clearance_population_bundle.records_sha256,
            "record_count": len(clearance_population_bundle.records),
            "status_counts": _status_counts(clearance_population_bundle.records),
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
            "clearance_share_ids": clearance_share_definitions,
            "clearance_population_ids": clearance_population_definitions,
        },
        "records": {
            "nationality_indicators": compact_indicator_rows,
            "all_resident_context": compact_context_rows,
            "nationality_comparison": compact_comparison_rows,
            "offense_composition": compact_offense_rows,
            "clearance_share_trends": compact_clearance_share_rows,
            "clearance_population_trends": compact_clearance_population_rows,
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
                    "clearance_share_ids": len(clearance_share_definitions),
                    "clearance_population_ids": len(
                        clearance_population_definitions
                    ),
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
