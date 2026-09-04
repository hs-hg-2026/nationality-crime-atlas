"""Generate provenance-first all-resident regional context outputs."""

import csv
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .provenance import sha256_file


ALL_RESIDENT_CONTEXT_SCHEMA_VERSION = 1
CONTRACT_SCHEMA_VERSION = 2
LATEST_SCHEMA_VERSION = 1
MEASURE_KIND = "public_data_derived_reference_ratio"
CANONICAL_FORMULA = "numerator_value / denominator_value"
DISPLAY_FORMULA = "quotient * display_multiplier"
STATISTICAL_COMPATIBILITY = "not_established"
CALCULATION_STATUSES = ("calculated", "refused")
DISPLAY_SCALE_STATUSES = ("provisional", "approved")
NUMERATOR_METRICS = ("recognized_cases", "cleared_cases", "cleared_persons")
DENOMINATOR_METRICS = ("total_population",)
REQUIRED_COMPARABILITY_FLAGS = frozenset(
    {
        "annual_flow_vs_point_in_time_population",
        "numerator_residency_scope_not_established",
    }
)
CSV_FIELDS = [
    "all_resident_context_schema_version",
    "context_id",
    "label_ja",
    "label_en",
    "measure_kind",
    "canonical_formula",
    "display_formula",
    "statistical_compatibility",
    "geography_label",
    "geography_id",
    "geography_type",
    "year",
    "reference_date",
    "numerator_source_id",
    "denominator_source_id",
    "numerator_metric",
    "denominator_metric",
    "numerator_value",
    "denominator_value",
    "quotient",
    "display_multiplier",
    "display_scale_status",
    "display_unit_label_ja",
    "display_unit_label_en",
    "display_value",
    "crosswalk_policy",
    "crosswalk_status",
    "targets_complete",
    "calculation_status",
    "refusal_reason",
    "mismatch_flags",
    "canonical_component_ids",
    "canonical_component_labels",
    "numerator_context",
    "denominator_context",
    "ui_caveat",
]

GEOGRAPHY_TYPE_ORDER = {
    "national": 0,
    "prefecture": 1,
    "police_region": 2,
    "police_subregion": 3,
    "prefecture_collection": 4,
}


@dataclass(frozen=True)
class MappingReference:
    """One reviewed mapping row keyed by source label and context."""

    match_status: str
    canonical_ids: Tuple[str, ...]
    canonical_labels: Tuple[str, ...]
    targets_complete: bool


@dataclass(frozen=True)
class AllResidentContextContract:
    """One metric definition for the all-resident regional context product."""

    context_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    numerator_source_id: str
    numerator_metric: str
    numerator_year: int
    numerator_period_type: str
    numerator_population_scope: str
    numerator_residency_scope: str
    numerator_offense_scope: str
    denominator_source_id: str
    denominator_metric: str
    denominator_reference_date: str
    denominator_period_type: str
    denominator_population_scope: str
    display_multiplier: float
    display_scale_status: str
    display_unit_label_ja: str
    display_unit_label_en: str
    crosswalk_policy: str
    expected_published_row_count: int
    expected_calculated_row_count: int
    base_mismatch_flags: Tuple[str, ...]
    ui_caveat: str


@dataclass(frozen=True)
class UnsupportedRequest:
    """One explicit unsupported numerator request boundary."""

    request_id: str
    label_ja: str
    label_en: str
    refusal_reason: str
    geography_label: str
    geography_id: str
    geography_type: str
    ui_caveat: str
    mismatch_flags: Tuple[str, ...]
    numerator_context: Mapping[str, object]


@dataclass(frozen=True)
class AllResidentContextRecord:
    """One calculated or refused all-resident context record."""

    all_resident_context_schema_version: int
    context_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    display_formula: str
    statistical_compatibility: str
    geography_label: str
    geography_id: str
    geography_type: str
    year: int
    reference_date: str
    numerator_source_id: Optional[str]
    denominator_source_id: Optional[str]
    numerator_metric: str
    denominator_metric: str
    numerator_value: Optional[int]
    denominator_value: Optional[int]
    quotient: Optional[float]
    display_multiplier: float
    display_scale_status: str
    display_unit_label_ja: str
    display_unit_label_en: str
    display_value: Optional[float]
    crosswalk_policy: str
    crosswalk_status: Optional[str]
    targets_complete: bool
    calculation_status: str
    refusal_reason: Optional[str]
    mismatch_flags: Tuple[str, ...]
    canonical_component_ids: Tuple[str, ...]
    canonical_component_labels: Tuple[str, ...]
    numerator_context: Mapping[str, object]
    denominator_context: Mapping[str, object]
    ui_caveat: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AllResidentContextReport:
    """Paths and counts for one immutable context run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    status_counts: Mapping[str, int]


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid %s JSON: %s" % (label, path)) from error
    if not isinstance(value, dict):
        raise SchemaError("%s JSON must contain an object: %s" % (label, path))
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SchemaError("%s must be an object" % label)
    return value


def _require_list(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("%s must be a non-empty string" % label)
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError("%s must be an integer" % label)
    return value


def _require_positive_int(value: object, label: str) -> int:
    result = _require_int(value, label)
    if result <= 0:
        raise SchemaError("%s must be positive" % label)
    return result


def _require_nonnegative_int(value: object, label: str) -> int:
    result = _require_int(value, label)
    if result < 0:
        raise SchemaError("%s must be non-negative" % label)
    return result


def _require_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError("%s must be numeric" % label)
    return float(value)


def _require_sha256(value: object, label: str) -> str:
    result = _require_string(value, label)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise SchemaError("%s must be a lowercase SHA-256 digest" % label)
    return result


def _require_iso_date(value: object, label: str) -> str:
    result = _require_string(value, label)
    try:
        date.fromisoformat(result)
    except ValueError as error:
        raise SchemaError("%s must be an ISO-8601 date" % label) from error
    return result


def _sorted_unique_strings(value: object, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    return tuple(sorted({_require_string(item, label) for item in value}))


def _load_processed_input_pins(data: Mapping[str, object]) -> Mapping[str, str]:
    raw_pins = _require_mapping(data.get("processed_input_pins"), "processed_input_pins")
    return {
        _require_string(source_id, "processed_input_pins source_id"): _require_sha256(
            digest, "processed_input_pins[%s]" % source_id
        )
        for source_id, digest in raw_pins.items()
    }


def load_all_resident_context_contracts(
    path: Path,
) -> Tuple[Tuple[AllResidentContextContract, ...], Tuple[UnsupportedRequest, ...], Mapping[str, str]]:
    """Load contracts, unsupported requests, and processed input pins."""

    data = _read_json_object(path, "all-resident context contract")
    if data.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise SchemaError("Unsupported all-resident context schema_version")
    processed_input_pins = _load_processed_input_pins(data)
    defaults = _require_mapping(data.get("defaults"), "defaults")
    contracts = []
    seen_ids = set()
    for index, item in enumerate(_require_list(data.get("contracts"), "contracts"), start=1):
        contract = dict(defaults)
        contract.update(_require_mapping(item, "contracts[%d]" % index))
        context_id = _require_string(contract.get("context_id"), "context_id")
        if context_id in seen_ids:
            raise SchemaError("Duplicate context_id: %s" % context_id)
        seen_ids.add(context_id)
        measure_kind = _require_string(contract.get("measure_kind"), "measure_kind")
        if measure_kind != MEASURE_KIND:
            raise SchemaError("Unsupported measure_kind: %s" % measure_kind)
        canonical_formula = _require_string(contract.get("canonical_formula"), "canonical_formula")
        if canonical_formula != CANONICAL_FORMULA:
            raise SchemaError("canonical_formula must be exactly %r" % CANONICAL_FORMULA)
        numerator_metric = _require_string(contract.get("numerator_metric"), "numerator_metric")
        if numerator_metric not in NUMERATOR_METRICS:
            raise SchemaError("Unsupported numerator_metric: %s" % numerator_metric)
        denominator_metric = _require_string(contract.get("denominator_metric"), "denominator_metric")
        if denominator_metric not in DENOMINATOR_METRICS:
            raise SchemaError("Unsupported denominator_metric: %s" % denominator_metric)
        numerator_period_type = _require_string(
            contract.get("numerator_period_type"), "numerator_period_type"
        )
        if numerator_period_type != "annual_flow":
            raise SchemaError("numerator_period_type must be annual_flow")
        numerator_residency_scope = _require_string(
            contract.get("numerator_residency_scope"), "numerator_residency_scope"
        )
        if numerator_residency_scope != "not_established":
            raise SchemaError("numerator_residency_scope must be not_established")
        denominator_period_type = _require_string(
            contract.get("denominator_period_type"), "denominator_period_type"
        )
        if denominator_period_type != "point_in_time_stock":
            raise SchemaError("denominator_period_type must be point_in_time_stock")
        display_scale_status = _require_string(
            contract.get("display_scale_status"), "display_scale_status"
        )
        if display_scale_status not in DISPLAY_SCALE_STATUSES:
            raise SchemaError("Unsupported display_scale_status: %s" % display_scale_status)
        base_mismatch_flags = _sorted_unique_strings(
            contract.get("base_mismatch_flags", []), "base_mismatch_flags"
        )
        missing_comparability_flags = sorted(
            REQUIRED_COMPARABILITY_FLAGS - set(base_mismatch_flags)
        )
        if missing_comparability_flags:
            raise SchemaError(
                "required base_mismatch_flags missing for %s: %s"
                % (context_id, ", ".join(missing_comparability_flags))
            )
        contracts.append(
            AllResidentContextContract(
                context_id=context_id,
                label_ja=_require_string(contract.get("label_ja"), "label_ja"),
                label_en=_require_string(contract.get("label_en"), "label_en"),
                measure_kind=measure_kind,
                canonical_formula=canonical_formula,
                numerator_source_id=_require_string(
                    contract.get("numerator_source_id"), "numerator_source_id"
                ),
                numerator_metric=numerator_metric,
                numerator_year=_require_int(contract.get("numerator_year"), "numerator_year"),
                numerator_period_type=numerator_period_type,
                numerator_population_scope=_require_string(
                    contract.get("numerator_population_scope"),
                    "numerator_population_scope",
                ),
                numerator_residency_scope=numerator_residency_scope,
                numerator_offense_scope=_require_string(
                    contract.get("numerator_offense_scope"),
                    "numerator_offense_scope",
                ),
                denominator_source_id=_require_string(
                    contract.get("denominator_source_id"), "denominator_source_id"
                ),
                denominator_metric=denominator_metric,
                denominator_reference_date=_require_iso_date(
                    contract.get("denominator_reference_date"),
                    "denominator_reference_date",
                ),
                denominator_period_type=denominator_period_type,
                denominator_population_scope=_require_string(
                    contract.get("denominator_population_scope"),
                    "denominator_population_scope",
                ),
                display_multiplier=_require_float(
                    contract.get("display_multiplier"), "display_multiplier"
                ),
                display_scale_status=display_scale_status,
                display_unit_label_ja=_require_string(
                    contract.get("display_unit_label_ja"), "display_unit_label_ja"
                ),
                display_unit_label_en=_require_string(
                    contract.get("display_unit_label_en"), "display_unit_label_en"
                ),
                crosswalk_policy=_require_string(
                    contract.get("crosswalk_policy"), "crosswalk_policy"
                ),
                expected_published_row_count=_require_positive_int(
                    contract.get("expected_published_row_count"),
                    "expected_published_row_count",
                ),
                expected_calculated_row_count=_require_positive_int(
                    contract.get("expected_calculated_row_count"),
                    "expected_calculated_row_count",
                ),
                base_mismatch_flags=base_mismatch_flags,
                ui_caveat=_require_string(contract.get("ui_caveat"), "ui_caveat"),
            )
        )
    unsupported_requests = []
    seen_request_ids = set()
    for index, item in enumerate(
        _require_list(data.get("unsupported_requests"), "unsupported_requests"),
        start=1,
    ):
        request = _require_mapping(item, "unsupported_requests[%d]" % index)
        request_id = _require_string(request.get("request_id"), "request_id")
        if request_id in seen_request_ids:
            raise SchemaError("Duplicate request_id: %s" % request_id)
        seen_request_ids.add(request_id)
        unsupported_requests.append(
            UnsupportedRequest(
                request_id=request_id,
                label_ja=_require_string(request.get("label_ja"), "label_ja"),
                label_en=_require_string(request.get("label_en"), "label_en"),
                refusal_reason=_require_string(
                    request.get("refusal_reason"), "refusal_reason"
                ),
                geography_label=_require_string(
                    request.get("geography_label"), "geography_label"
                ),
                geography_id=_require_string(request.get("geography_id"), "geography_id"),
                geography_type=_require_string(
                    request.get("geography_type"), "geography_type"
                ),
                ui_caveat=_require_string(request.get("ui_caveat"), "ui_caveat"),
                mismatch_flags=_sorted_unique_strings(
                    request.get("mismatch_flags", []), "mismatch_flags"
                ),
                numerator_context=_require_mapping(
                    request.get("numerator_context"), "numerator_context"
                ),
            )
        )
    return tuple(contracts), tuple(unsupported_requests), processed_input_pins


def _contract_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise SchemaError("generated_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone offset")
    return parsed.strftime("%Y%m%d_%H%M%S")


def _read_catalog(path: Path) -> List[Mapping[str, object]]:
    rows = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise SchemaError("Catalog row must be an object at line %d" % line_number)
                if row.get("processing_status") != "validated":
                    raise SchemaError(
                        "All-resident context generation requires validated catalog inputs"
                    )
                rows.append(row)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid artifact catalog: %s" % path) from error
    if not rows:
        raise SchemaError("Artifact catalog is empty")
    return rows


def _safe_processed_path(processed_root: Path, value: object) -> Path:
    relative = Path(_require_string(value, "processed_relpath"))
    if relative.is_absolute() or ".." in relative.parts:
        raise SchemaError("Unsafe processed_relpath: %s" % relative)
    path = Path(processed_root) / relative / "normalized.jsonl"
    if not path.is_file():
        raise SchemaError("Normalized input is missing: %s" % path)
    return path


def _verify_processed_input(path: Path, source_id: str, pinned_sha256: str) -> str:
    run = _read_json_object(Path(path).parent / "run.json", "processed run")
    if run.get("source_id") != source_id:
        raise SchemaError("Processed run source_id differs for %s" % source_id)
    if run.get("quality_passed") is not True:
        raise SchemaError("Processed run did not pass quality for %s" % source_id)
    expected = _require_string(run.get("normalized_sha256"), "normalized_sha256")
    observed = sha256_file(path)
    if observed != expected:
        raise IntegrityError(
            "Processed normalized input hash differs from run.json for %s" % source_id
        )
    if observed != pinned_sha256:
        raise IntegrityError(
            "Processed normalized input hash differs from contract pin for %s" % source_id
        )
    return observed


def _resolve_catalog_inputs(
    catalog_rows: Iterable[Mapping[str, object]],
    *,
    processed_root: Path,
    required_source_ids: Iterable[str],
    processed_input_pins: Mapping[str, str],
) -> Tuple[
    Dict[str, Path],
    Dict[str, Mapping[str, object]],
    Dict[str, str],
]:
    rows_by_source: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for row in catalog_rows:
        source_id = _require_string(row.get("source_id"), "catalog source_id")
        rows_by_source[source_id].append(row)

    paths = {}
    selected_rows = {}
    normalized_hashes = {}
    for source_id in sorted(set(required_source_ids)):
        candidates = rows_by_source.get(source_id, [])
        if not candidates:
            raise SchemaError("Missing required source in artifact catalog: %s" % source_id)
        pinned_sha256 = processed_input_pins[source_id]
        matches = []
        for row in candidates:
            path = _safe_processed_path(processed_root, row.get("processed_relpath"))
            run = _read_json_object(path.parent / "run.json", "processed run")
            if run.get("source_id") != source_id:
                raise SchemaError("Processed run source_id differs for %s" % source_id)
            if run.get("quality_passed") is not True:
                raise SchemaError("Processed run did not pass quality for %s" % source_id)
            declared_sha256 = _require_sha256(
                run.get("normalized_sha256"), "normalized_sha256"
            )
            if declared_sha256 != pinned_sha256:
                continue
            observed_sha256 = _verify_processed_input(path, source_id, pinned_sha256)
            matches.append((row, path, observed_sha256))
        if not matches:
            raise IntegrityError(
                "No catalog artifact matches contract pin for %s" % source_id
            )
        if len(matches) > 1:
            raise IntegrityError(
                "Multiple catalog artifacts match contract pin for %s" % source_id
            )
        selected_row, selected_path, observed_sha256 = matches[0]
        selected_rows[source_id] = selected_row
        paths[source_id] = selected_path
        normalized_hashes[source_id] = observed_sha256
    return paths, selected_rows, normalized_hashes


def _catalog_source_artifacts(
    catalog_rows: Mapping[str, Mapping[str, object]],
    required_source_ids: Iterable[str],
    normalized_hashes: Mapping[str, str],
) -> Mapping[str, Mapping[str, object]]:
    fields = (
        "series_id",
        "dataset",
        "publisher",
        "source_table",
        "source_period",
        "sha256",
        "landing_url",
        "download_url",
        "raw_relpath",
        "processed_relpath",
        "retrieved_at",
        "revision",
        "verification_level",
    )
    artifacts = {}
    for source_id in sorted(set(required_source_ids)):
        try:
            row = catalog_rows[source_id]
        except KeyError as error:
            raise SchemaError(
                "Missing required source in artifact catalog: %s" % source_id
            ) from error
        artifact = {}
        for field in fields:
            value = row.get(field)
            if value is None:
                raise SchemaError(
                    "Catalog provenance field %s is missing for %s" % (field, source_id)
                )
            artifact[field] = value
        artifact["normalized_sha256"] = normalized_hashes[source_id]
        artifacts[source_id] = artifact
    return artifacts


def _json_key(value: Mapping[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _mapping_key(
    *,
    source_id: str,
    source_entity_kind: str,
    source_label: str,
    source_context: Mapping[str, object],
) -> Tuple[str, str, str, str, str]:
    return (source_id, "geography", source_entity_kind, source_label, _json_key(source_context))


def _load_mapping_lookup(
    mapping_latest_path: Path,
) -> Tuple[Dict[Tuple[str, str, str, str, str], MappingReference], Mapping[str, object], Path]:
    latest = _read_json_object(mapping_latest_path, "mapping latest")
    if latest.get("mapping_schema_version") != 1:
        raise SchemaError("Unsupported mapping latest schema_version")
    mapping_root = Path(mapping_latest_path).parent
    run_relpath = Path(_require_string(latest.get("run_relpath"), "run_relpath"))
    if run_relpath.is_absolute() or ".." in run_relpath.parts:
        raise SchemaError("Unsafe mapping run_relpath: %s" % run_relpath)
    run_dir = mapping_root / run_relpath
    summary_path = run_dir / "summary.json"
    jsonl_path = run_dir / "dimension_mappings.jsonl"
    if not summary_path.is_file() or not jsonl_path.is_file():
        raise SchemaError("Mapping run is incomplete: %s" % run_dir)
    if latest.get("summary_sha256") != sha256_file(summary_path):
        raise IntegrityError("Mapping summary hash differs from latest.json")
    if latest.get("dimension_mappings_sha256") != sha256_file(jsonl_path):
        raise IntegrityError("Mapping JSONL hash differs from latest.json")
    summary = _read_json_object(summary_path, "mapping summary")
    lookup = {}
    with jsonl_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("Mapping row must be an object at line %d" % line_number)
            if row.get("dimension") != "geography":
                continue
            key = _mapping_key(
                source_id=_require_string(row.get("source_id"), "mapping source_id"),
                source_entity_kind=_require_string(
                    row.get("source_entity_kind"), "mapping source_entity_kind"
                ),
                source_label=_require_string(row.get("source_label"), "mapping source_label"),
                source_context=_require_mapping(
                    row.get("source_context", {}), "mapping source_context"
                ),
            )
            if key in lookup:
                raise SchemaError("Duplicate mapping row for %r" % (key,))
            lookup[key] = MappingReference(
                match_status=_require_string(row.get("match_status"), "match_status"),
                canonical_ids=tuple(row.get("canonical_ids", [])),
                canonical_labels=tuple(row.get("canonical_labels", [])),
                targets_complete=bool(row.get("targets_complete")),
            )
    return lookup, summary, run_dir


def _mapping_for_geography(
    lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
    row: Mapping[str, object],
) -> MappingReference:
    source_context = {
        "geography_type": row.get("geography_type"),
        "parent_region": row.get("parent_region"),
        "geography_semantics": row.get("geography_semantics"),
    }
    key = _mapping_key(
        source_id=_require_string(row.get("source_id"), "source_id"),
        source_entity_kind=_require_string(row.get("geography_type"), "geography_type"),
        source_label=_require_string(row.get("geography"), "geography"),
        source_context=source_context,
    )
    try:
        return lookup[key]
    except KeyError as error:
        raise SchemaError("Missing geography mapping for %r" % (key,)) from error


def _load_overall_prefecture_rows(path: Path, *, source_id: str) -> List[Mapping[str, object]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError(
                    "Overall prefecture crime row must be an object: %s:%d"
                    % (path, line_number)
                )
            if row.get("source_id") != source_id:
                raise SchemaError("Overall crime source_id differs from catalog: %s" % path)
            rows.append(row)
    return rows


def _load_population_rows(
    path: Path,
    *,
    source_id: str,
    mapping_lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
) -> Tuple[Mapping[str, Mapping[str, object]], str]:
    rows_by_id = {}
    reference_date = None
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError(
                    "Prefecture population row must be an object: %s:%d" % (path, line_number)
                )
            if row.get("source_id") != source_id:
                raise SchemaError("Population source_id differs from catalog: %s" % path)
            observed_reference_date = _require_iso_date(
                row.get("reference_date"), "reference_date"
            )
            if reference_date is None:
                reference_date = observed_reference_date
            elif reference_date != observed_reference_date:
                raise SchemaError("Population source contains multiple reference_date values")
            mapping = _mapping_for_geography(mapping_lookup, row)
            if (
                mapping.match_status != "matched"
                or len(mapping.canonical_ids) != 1
                or not mapping.targets_complete
            ):
                raise SchemaError(
                    "Population denominator geography must be an exact reviewed mapping"
                )
            geography_id = mapping.canonical_ids[0]
            if geography_id in rows_by_id:
                raise SchemaError("Duplicate denominator geography: %s" % geography_id)
            rows_by_id[geography_id] = row
    if reference_date is None:
        raise SchemaError("Population input is empty: %s" % path)
    return rows_by_id, reference_date


def _refusal_geography_id(row: Mapping[str, object]) -> str:
    return "published-geography:%s:%s:%s" % (
        _require_string(row.get("source_id"), "source_id"),
        _require_string(row.get("geography_type"), "geography_type"),
        _require_string(row.get("geography"), "geography"),
    )


def _build_record(
    *,
    contract: AllResidentContextContract,
    geography_label: str,
    geography_id: str,
    geography_type: str,
    year: int,
    reference_date: str,
    numerator_source_id: Optional[str],
    denominator_source_id: Optional[str],
    numerator_value: Optional[int],
    denominator_value: Optional[int],
    crosswalk_status: Optional[str],
    targets_complete: bool,
    refusal_reason: Optional[str],
    mismatch_flags: Sequence[str],
    canonical_component_ids: Sequence[str],
    canonical_component_labels: Sequence[str],
    numerator_context: Mapping[str, object],
    denominator_context: Mapping[str, object],
    ui_caveat: str,
) -> AllResidentContextRecord:
    if numerator_value is not None:
        _require_nonnegative_int(numerator_value, "numerator_value")
    if denominator_value is not None and denominator_value <= 0:
        raise SchemaError("denominator_value must be positive")
    quotient = None
    display_value = None
    status = "refused"
    if refusal_reason is None and numerator_value is not None and denominator_value is not None:
        quotient = numerator_value / denominator_value
        display_value = quotient * contract.display_multiplier
        status = "calculated"
    return AllResidentContextRecord(
        all_resident_context_schema_version=ALL_RESIDENT_CONTEXT_SCHEMA_VERSION,
        context_id=contract.context_id,
        label_ja=contract.label_ja,
        label_en=contract.label_en,
        measure_kind=contract.measure_kind,
        canonical_formula=contract.canonical_formula,
        display_formula=DISPLAY_FORMULA,
        statistical_compatibility=STATISTICAL_COMPATIBILITY,
        geography_label=geography_label,
        geography_id=geography_id,
        geography_type=geography_type,
        year=year,
        reference_date=reference_date,
        numerator_source_id=numerator_source_id,
        denominator_source_id=denominator_source_id,
        numerator_metric=contract.numerator_metric,
        denominator_metric=contract.denominator_metric,
        numerator_value=numerator_value,
        denominator_value=denominator_value,
        quotient=quotient,
        display_multiplier=contract.display_multiplier,
        display_scale_status=contract.display_scale_status,
        display_unit_label_ja=contract.display_unit_label_ja,
        display_unit_label_en=contract.display_unit_label_en,
        display_value=display_value,
        crosswalk_policy=contract.crosswalk_policy,
        crosswalk_status=crosswalk_status,
        targets_complete=targets_complete,
        calculation_status=status,
        refusal_reason=refusal_reason,
        mismatch_flags=tuple(sorted(set(mismatch_flags))),
        canonical_component_ids=tuple(canonical_component_ids),
        canonical_component_labels=tuple(canonical_component_labels),
        numerator_context=dict(numerator_context),
        denominator_context=dict(denominator_context),
        ui_caveat=ui_caveat,
    )


def _dynamic_mismatch_flags(
    row: Mapping[str, object],
    *,
    denial: bool,
) -> List[str]:
    flags = []
    geography_type = _require_string(row.get("geography_type"), "geography_type")
    if geography_type == "prefecture":
        flags.extend(
            [
                "police_reporting_area_unresolved",
                "police_reporting_area_vs_population_estimate_prefecture",
            ]
        )
    elif geography_type in {"police_region", "police_subregion"}:
        flags.extend(["police_reporting_area_unresolved", "no_equivalent_total_population_geography"])
        if denial:
            flags.append("non_prefecture_published_geography")
    return flags


def _selected_rows(
    rows: Sequence[Mapping[str, object]],
    contract: AllResidentContextContract,
) -> List[Mapping[str, object]]:
    selected = [
        row
        for row in rows
        if row.get("year") == contract.numerator_year
        and row.get("population_scope") == contract.numerator_population_scope
        and row.get("offense_scope") == contract.numerator_offense_scope
    ]
    if len(selected) != contract.expected_published_row_count:
        raise SchemaError(
            "expected_published_row_count differs for %s: expected %d, observed %d"
            % (
                contract.context_id,
                contract.expected_published_row_count,
                len(selected),
            )
        )
    return selected


def _build_context_records(
    contract: AllResidentContextContract,
    *,
    numerator_rows: Sequence[Mapping[str, object]],
    denominator_rows: Mapping[str, Mapping[str, object]],
    reference_date: str,
    mapping_lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
) -> List[AllResidentContextRecord]:
    if contract.numerator_year != date.fromisoformat(reference_date).year:
        raise SchemaError(
            "Same-year pairing failed for %s: %s vs %s"
            % (contract.context_id, contract.numerator_year, reference_date)
        )
    rows = _selected_rows(numerator_rows, contract)
    records = []
    calculated_count = 0
    seen_geographies = set()
    for row in rows:
        geography_label = _require_string(row.get("geography"), "geography")
        geography_type = _require_string(row.get("geography_type"), "geography_type")
        if (geography_type, geography_label) in seen_geographies:
            raise SchemaError("Duplicate numerator geography for %s" % contract.context_id)
        seen_geographies.add((geography_type, geography_label))
        mapping = _mapping_for_geography(mapping_lookup, row)
        base_flags = list(contract.base_mismatch_flags)
        if (
            geography_type in {"national", "prefecture"}
            and mapping.match_status == "matched"
            and len(mapping.canonical_ids) == 1
            and mapping.targets_complete
        ):
            geography_id = mapping.canonical_ids[0]
            denominator = denominator_rows.get(geography_id)
            refusal_reason = None
            denominator_value = None
            if denominator is None:
                refusal_reason = "missing_total_population_denominator"
            else:
                denominator_value = _require_positive_int(
                    denominator.get("population"), "population"
                )
            record = _build_record(
                contract=contract,
                geography_label=geography_label,
                geography_id=geography_id,
                geography_type=geography_type,
                year=contract.numerator_year,
                reference_date=reference_date,
                numerator_source_id=contract.numerator_source_id,
                denominator_source_id=contract.denominator_source_id,
                numerator_value=_require_nonnegative_int(
                    row.get(contract.numerator_metric), contract.numerator_metric
                ),
                denominator_value=denominator_value,
                crosswalk_status=mapping.match_status,
                targets_complete=mapping.targets_complete,
                refusal_reason=refusal_reason,
                mismatch_flags=base_flags + _dynamic_mismatch_flags(row, denial=False),
                canonical_component_ids=mapping.canonical_ids,
                canonical_component_labels=mapping.canonical_labels,
                numerator_context={
                    "population_scope": row.get("population_scope"),
                    "period_type": contract.numerator_period_type,
                    "residency_scope": contract.numerator_residency_scope,
                    "offense_scope": row.get("offense_scope"),
                    "geography_semantics": row.get("geography_semantics"),
                    "parent_region": row.get("parent_region"),
                },
                denominator_context={
                    "population_scope": contract.denominator_population_scope,
                    "period_type": contract.denominator_period_type,
                    "reference_date": reference_date,
                    "geography_semantics": (
                        "national_aggregate"
                        if geography_type == "national"
                        else "population_estimate_prefecture"
                    ),
                    "source_unit": denominator.get("source_unit") if denominator else None,
                    "rounding": denominator.get("rounding") if denominator else None,
                },
                ui_caveat=contract.ui_caveat,
            )
            if record.calculation_status == "calculated":
                calculated_count += 1
            records.append(record)
            continue
        records.append(
            _build_record(
                contract=contract,
                geography_label=geography_label,
                geography_id=_refusal_geography_id(row),
                geography_type=geography_type,
                year=contract.numerator_year,
                reference_date=reference_date,
                numerator_source_id=contract.numerator_source_id,
                denominator_source_id=contract.denominator_source_id,
                numerator_value=_require_nonnegative_int(
                    row.get(contract.numerator_metric), contract.numerator_metric
                ),
                denominator_value=None,
                crosswalk_status=mapping.match_status,
                targets_complete=mapping.targets_complete,
                refusal_reason="geography_not_exact_prefecture_or_national",
                mismatch_flags=base_flags + _dynamic_mismatch_flags(row, denial=True),
                canonical_component_ids=mapping.canonical_ids,
                canonical_component_labels=mapping.canonical_labels,
                numerator_context={
                    "population_scope": row.get("population_scope"),
                    "period_type": contract.numerator_period_type,
                    "residency_scope": contract.numerator_residency_scope,
                    "offense_scope": row.get("offense_scope"),
                    "geography_semantics": row.get("geography_semantics"),
                    "parent_region": row.get("parent_region"),
                },
                denominator_context={
                    "population_scope": contract.denominator_population_scope,
                    "period_type": contract.denominator_period_type,
                    "reference_date": reference_date,
                    "geography_semantics": None,
                    "source_unit": None,
                    "rounding": None,
                },
                ui_caveat=contract.ui_caveat,
            )
        )
    if calculated_count != contract.expected_calculated_row_count:
        raise SchemaError(
            "expected_calculated_row_count differs for %s: expected %d, observed %d"
            % (
                contract.context_id,
                contract.expected_calculated_row_count,
                calculated_count,
            )
        )
    return records


def _build_unsupported_request_records(
    contract: AllResidentContextContract,
    unsupported_requests: Sequence[UnsupportedRequest],
) -> List[AllResidentContextRecord]:
    records = []
    for request in unsupported_requests:
        records.append(
            _build_record(
                contract=contract,
                geography_label=request.geography_label,
                geography_id=request.geography_id,
                geography_type=request.geography_type,
                year=contract.numerator_year,
                reference_date=contract.denominator_reference_date,
                numerator_source_id=None,
                denominator_source_id=contract.denominator_source_id,
                numerator_value=None,
                denominator_value=None,
                crosswalk_status=None,
                targets_complete=False,
                refusal_reason=request.refusal_reason,
                mismatch_flags=request.mismatch_flags,
                canonical_component_ids=(),
                canonical_component_labels=(),
                numerator_context={
                    **request.numerator_context,
                    "requested_metric": contract.numerator_metric,
                    "requested_year": contract.numerator_year,
                },
                denominator_context={
                    "population_scope": contract.denominator_population_scope,
                    "period_type": contract.denominator_period_type,
                    "reference_date": contract.denominator_reference_date,
                },
                ui_caveat=request.ui_caveat,
            )
        )
    return records


def _csv_value(value: object) -> object:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


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


def _reconciliation(records: Sequence[AllResidentContextRecord]) -> Mapping[str, Mapping[str, int]]:
    by_context = defaultdict(dict)
    for record in records:
        if record.calculation_status != "calculated":
            continue
        bucket = by_context[record.context_id]
        if record.geography_type == "national":
            bucket["national_numerator_value"] = int(record.numerator_value or 0)
            bucket["national_denominator_value"] = int(record.denominator_value or 0)
        elif record.geography_type == "prefecture":
            bucket["prefecture_numerator_sum"] = bucket.get("prefecture_numerator_sum", 0) + int(
                record.numerator_value or 0
            )
            bucket["prefecture_denominator_sum"] = bucket.get(
                "prefecture_denominator_sum", 0
            ) + int(record.denominator_value or 0)
    result = {}
    for context_id, bucket in sorted(by_context.items()):
        result[context_id] = {
            "national_numerator_value": bucket.get("national_numerator_value", 0),
            "prefecture_numerator_sum": bucket.get("prefecture_numerator_sum", 0),
            "numerator_difference": bucket.get("national_numerator_value", 0)
            - bucket.get("prefecture_numerator_sum", 0),
            "national_denominator_value": bucket.get("national_denominator_value", 0),
            "prefecture_denominator_sum": bucket.get("prefecture_denominator_sum", 0),
            "denominator_difference": bucket.get("national_denominator_value", 0)
            - bucket.get("prefecture_denominator_sum", 0),
        }
    return result


def generate_all_resident_context_report(
    *,
    catalog_path: Path,
    processed_root: Path,
    mapping_latest_path: Path,
    contracts_path: Path,
    output_root: Path,
    generated_at: str,
) -> AllResidentContextReport:
    """Generate immutable all-resident regional context outputs."""

    contracts, unsupported_requests, processed_input_pins = load_all_resident_context_contracts(
        contracts_path
    )
    catalog_rows = _read_catalog(catalog_path)
    required_source_ids = {
        source_id
        for contract in contracts
        for source_id in (contract.numerator_source_id, contract.denominator_source_id)
    }
    missing_pins = sorted(required_source_ids - set(processed_input_pins))
    if missing_pins:
        raise SchemaError(
            "Missing processed_input_pins for required sources: %s"
            % ", ".join(missing_pins)
        )
    catalog_paths, selected_catalog_rows, normalized_hashes = _resolve_catalog_inputs(
        catalog_rows,
        processed_root=processed_root,
        required_source_ids=required_source_ids,
        processed_input_pins=processed_input_pins,
    )
    source_artifacts = _catalog_source_artifacts(
        selected_catalog_rows, required_source_ids, normalized_hashes
    )
    mapping_lookup, mapping_summary, mapping_run_dir = _load_mapping_lookup(mapping_latest_path)
    numerator_cache: Dict[str, List[Mapping[str, object]]] = {}
    denominator_cache: Dict[str, Tuple[Mapping[str, Mapping[str, object]], str]] = {}
    records: List[AllResidentContextRecord] = []
    for contract in contracts:
        numerator_path = catalog_paths[contract.numerator_source_id]
        denominator_path = catalog_paths[contract.denominator_source_id]
        if contract.numerator_source_id not in numerator_cache:
            numerator_cache[contract.numerator_source_id] = _load_overall_prefecture_rows(
                numerator_path, source_id=contract.numerator_source_id
            )
        if contract.denominator_source_id not in denominator_cache:
            denominator_cache[contract.denominator_source_id] = _load_population_rows(
                denominator_path,
                source_id=contract.denominator_source_id,
                mapping_lookup=mapping_lookup,
            )
        denominator_rows, observed_reference_date = denominator_cache[
            contract.denominator_source_id
        ]
        if observed_reference_date != contract.denominator_reference_date:
            raise SchemaError(
                "Configured denominator_reference_date differs from observed value for %s"
                % contract.denominator_source_id
            )
        records.extend(
            _build_context_records(
                contract,
                numerator_rows=numerator_cache[contract.numerator_source_id],
                denominator_rows=denominator_rows,
                reference_date=observed_reference_date,
                mapping_lookup=mapping_lookup,
            )
        )
        records.extend(_build_unsupported_request_records(contract, unsupported_requests))

    records.sort(
        key=lambda item: (
            item.context_id,
            item.year,
            GEOGRAPHY_TYPE_ORDER.get(item.geography_type, 99),
            item.geography_label,
        )
    )
    status_counts = Counter(item.calculation_status for item in records)
    refusal_reason_counts = Counter()
    mismatch_flag_counts = Counter()
    by_context = defaultdict(lambda: defaultdict(int))
    for item in records:
        by_context[item.context_id][item.calculation_status] += 1
        mismatch_flag_counts.update(item.mismatch_flags)
        if item.refusal_reason is not None:
            refusal_reason_counts[item.refusal_reason] += 1

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (_contract_timestamp(generated_at) + "_all_resident_context")
    if destination.exists():
        raise IntegrityError(
            "Timestamped all-resident context output already exists and was not overwritten: %s"
            % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".all-resident-context-", dir=destination_root))
    try:
        jsonl_path = staging / "regional_context_records.jsonl"
        csv_path = staging / "regional_context_records.csv"
        summary_path = staging / "summary.json"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for item in records:
                handle.write(
                    json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
                )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for item in records:
                writer.writerow({field: _csv_value(item.to_dict().get(field)) for field in CSV_FIELDS})
        summary = {
            "all_resident_context_schema_version": ALL_RESIDENT_CONTEXT_SCHEMA_VERSION,
            "generated_at": generated_at,
            "catalog_path": Path(catalog_path).as_posix(),
            "catalog_sha256": sha256_file(Path(catalog_path)),
            "contracts_path": Path(contracts_path).as_posix(),
            "contracts_sha256": sha256_file(Path(contracts_path)),
            "mapping_latest_path": Path(mapping_latest_path).as_posix(),
            "mapping_latest_sha256": sha256_file(Path(mapping_latest_path)),
            "mapping_run_relpath": mapping_run_dir.name,
            "mapping_record_count": mapping_summary.get("mapping_record_count"),
            "processed_input_pins": {
                source_id: processed_input_pins[source_id] for source_id in sorted(required_source_ids)
            },
            "source_artifacts": source_artifacts,
            "contract_count": len(contracts),
            "unsupported_request_count": len(unsupported_requests),
            "record_count": len(records),
            "status_counts": {
                status: status_counts.get(status, 0) for status in CALCULATION_STATUSES
            },
            "refusal_reason_counts": dict(sorted(refusal_reason_counts.items())),
            "mismatch_flag_counts": dict(sorted(mismatch_flag_counts.items())),
            "by_context": {
                context_id: {
                    status: counts.get(status, 0) for status in CALCULATION_STATUSES
                }
                for context_id, counts in sorted(by_context.items())
            },
            "reconciliation": _reconciliation(records),
        }
        _write_json(summary_path, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "regional_context_records.jsonl"
    final_csv = destination / "regional_context_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    _atomic_write_json(
        latest_path,
        {
            "all_resident_context_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "regional_context_records_sha256": sha256_file(final_jsonl),
            "regional_context_records_csv_sha256": sha256_file(final_csv),
        },
    )
    return AllResidentContextReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        status_counts={
            status: status_counts.get(status, 0) for status in CALCULATION_STATUSES
        },
    )
