"""Indicator contracts and provenance-first reference-ratio generation."""

import csv
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .provenance import sha256_file


INDICATOR_CONTRACT_SCHEMA_VERSION = 2
INDICATOR_RUN_SCHEMA_VERSION = 2
MEASURE_KIND = "public_data_derived_reference_ratio"
CANONICAL_FORMULA = "numerator_value / denominator_value"
DISPLAY_FORMULA = "quotient * display_multiplier"
STATISTICAL_COMPATIBILITY = "not_established"
CROSSWALK_POLICIES = ("exact", "as_published_mismatch")
NUMERATOR_METRICS = ("cleared_cases", "cleared_persons")
DENOMINATOR_METRICS = ("resident_population",)
GEOGRAPHY_GRAINS = ("national", "prefecture")
NUMERATOR_ROW_KINDS = ("country", "prefecture")
NUMERATOR_POPULATION_SCOPES = ("all_foreign", "visiting_foreign")
NUMERATOR_PERIOD_TYPES = ("calendar_year_flow",)
DENOMINATOR_POPULATION_SCOPES = ("resident_foreigners",)
DENOMINATOR_PERIOD_TYPES = ("year_end_stock",)
DISPLAY_SCALE_STATUSES = ("provisional", "approved")
CALCULATION_STATUSES = ("calculated", "refused")
SMALL_NUMBER_WARNING_POLICY_STATUSES = ("approved_project_heuristic",)
DEFAULT_RANKING_BEHAVIORS = ("exclude_flagged", "include_all")
CSV_FIELDS = [
    "indicator_run_schema_version",
    "indicator_id",
    "label_ja",
    "label_en",
    "measure_kind",
    "canonical_formula",
    "display_formula",
    "statistical_compatibility",
    "entity_dimension",
    "published_label",
    "geography_label",
    "geography_id",
    "geography_type",
    "year",
    "period_end",
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
    "small_number_warning_policy_version",
    "small_number_warning_policy_status",
    "small_number_warning_flags",
    "default_ranking_behavior",
    "default_ranking_excluded",
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


@dataclass(frozen=True)
class IndicatorContract:
    """One machine-readable contract for a publishable reference ratio."""

    indicator_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    numerator_source_id: str
    numerator_metric: str
    numerator_year: int
    numerator_row_kind: str
    numerator_offense_scope: Optional[str]
    numerator_population_scope: str
    numerator_period_type: str
    numerator_geography_semantics: str
    denominator_source_id: str
    denominator_metric: str
    denominator_period_end: str
    denominator_population_scope: str
    denominator_period_type: str
    denominator_geography_semantics: str
    geography_grain: str
    crosswalk_policy: str
    expected_numerator_row_count: int
    display_multiplier: float
    display_scale_status: str
    display_unit_label_ja: str
    display_unit_label_en: str
    small_number_warning_policy_version: int
    small_number_warning_policy_status: str
    small_number_warning_denominator_threshold: int
    small_number_warning_numerator_threshold: int
    default_ranking_behavior: str
    base_mismatch_flags: Tuple[str, ...]
    ui_caveat: str


@dataclass(frozen=True)
class IndicatorRecord:
    """One calculated or explicitly refused project-derived reference ratio row."""

    indicator_run_schema_version: int
    indicator_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    display_formula: str
    statistical_compatibility: str
    entity_dimension: str
    published_label: Optional[str]
    geography_label: str
    geography_id: str
    geography_type: str
    year: int
    period_end: str
    numerator_source_id: str
    denominator_source_id: str
    numerator_metric: str
    denominator_metric: str
    numerator_value: int
    denominator_value: Optional[int]
    quotient: Optional[float]
    display_multiplier: float
    display_scale_status: str
    display_unit_label_ja: str
    display_unit_label_en: str
    display_value: Optional[float]
    small_number_warning_policy_version: int
    small_number_warning_policy_status: str
    small_number_warning_flags: Tuple[str, ...]
    default_ranking_behavior: str
    default_ranking_excluded: bool
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
class IndicatorReport:
    """Filesystem locations and summary counts for one immutable indicator run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    status_counts: Mapping[str, int]


@dataclass(frozen=True)
class MappingReference:
    """One validated mapping row keyed by source label and context."""

    dimension: str
    source_id: str
    source_entity_kind: str
    source_label: str
    source_context: Mapping[str, object]
    match_status: str
    canonical_ids: Tuple[str, ...]
    canonical_labels: Tuple[str, ...]
    targets_complete: bool


@dataclass
class PopulationAggregate:
    """Aggregated resident population with completeness tracking."""

    label: str
    value: int = 0
    complete: bool = True


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


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("%s must be a non-empty string" % label)
    return value


def _require_sha256(value: object, label: str) -> str:
    result = _require_string(value, label)
    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise SchemaError("%s must be a lowercase SHA-256 digest" % label)
    return result


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


def _require_iso_date(value: object, label: str) -> str:
    result = _require_string(value, label)
    try:
        parsed = date.fromisoformat(result)
    except ValueError as error:
        raise SchemaError("%s must be an ISO-8601 date" % label) from error
    if parsed.isoformat() != result:
        raise SchemaError("%s must use YYYY-MM-DD format" % label)
    return result


def _sorted_unique_strings(value: object, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    items = []
    for item in value:
        items.append(_require_string(item, label))
    return tuple(sorted(set(items)))


def load_indicator_contracts(path: Path) -> Tuple[IndicatorContract, ...]:
    """Load machine-readable indicator contracts and reject ambiguous definitions."""

    data = _read_json_object(path, "indicator contract")
    if data.get("schema_version") != INDICATOR_CONTRACT_SCHEMA_VERSION:
        raise SchemaError("Unsupported indicator contract schema_version")
    items = data.get("contracts")
    if not isinstance(items, list) or not items:
        raise SchemaError("indicator contracts must contain a non-empty contracts array")
    defaults = _require_mapping(data.get("defaults", {}), "indicator defaults")
    contracts = []
    seen_ids = set()
    for index, item in enumerate(items, start=1):
        contract = dict(defaults)
        contract.update(_require_mapping(item, "contract[%d]" % index))
        indicator_id = _require_string(contract.get("indicator_id"), "indicator_id")
        if indicator_id in seen_ids:
            raise SchemaError("Duplicate indicator_id: %s" % indicator_id)
        seen_ids.add(indicator_id)
        measure_kind = _require_string(contract.get("measure_kind"), "measure_kind")
        if measure_kind != MEASURE_KIND:
            raise SchemaError("measure_kind is unsupported: %s" % measure_kind)
        canonical_formula = _require_string(
            contract.get("canonical_formula"), "canonical_formula"
        )
        if canonical_formula != CANONICAL_FORMULA:
            raise SchemaError(
                "canonical_formula must be exactly %r" % CANONICAL_FORMULA
            )
        numerator_metric = _require_string(
            contract.get("numerator_metric"), "numerator_metric"
        )
        if numerator_metric not in NUMERATOR_METRICS:
            raise SchemaError("numerator_metric is unsupported: %s" % numerator_metric)
        denominator_metric = _require_string(
            contract.get("denominator_metric"), "denominator_metric"
        )
        if denominator_metric not in DENOMINATOR_METRICS:
            raise SchemaError("denominator_metric is unsupported: %s" % denominator_metric)
        geography_grain = _require_string(
            contract.get("geography_grain"), "geography_grain"
        )
        if geography_grain not in GEOGRAPHY_GRAINS:
            raise SchemaError("geography_grain is unsupported: %s" % geography_grain)
        numerator_row_kind = _require_string(
            contract.get("numerator_row_kind"), "numerator_row_kind"
        )
        if numerator_row_kind not in NUMERATOR_ROW_KINDS:
            raise SchemaError(
                "numerator_row_kind is unsupported: %s" % numerator_row_kind
            )
        if (geography_grain, numerator_row_kind) not in (
            ("national", "country"),
            ("prefecture", "prefecture"),
        ):
            raise SchemaError(
                "geography_grain and numerator_row_kind are incompatible"
            )
        crosswalk_policy = _require_string(
            contract.get("crosswalk_policy"), "crosswalk_policy"
        )
        if crosswalk_policy not in CROSSWALK_POLICIES:
            raise SchemaError("crosswalk_policy is unsupported: %s" % crosswalk_policy)
        display_multiplier = _require_float(
            contract.get("display_multiplier"), "display_multiplier"
        )
        if display_multiplier <= 0:
            raise SchemaError("display_multiplier must be positive")
        display_scale_status = _require_string(
            contract.get("display_scale_status"), "display_scale_status"
        )
        if display_scale_status not in DISPLAY_SCALE_STATUSES:
            raise SchemaError(
                "display_scale_status is unsupported: %s" % display_scale_status
            )
        small_number_warning_policy_version = _require_positive_int(
            contract.get("small_number_warning_policy_version"),
            "small_number_warning_policy_version",
        )
        small_number_warning_policy_status = _require_string(
            contract.get("small_number_warning_policy_status"),
            "small_number_warning_policy_status",
        )
        if (
            small_number_warning_policy_status
            not in SMALL_NUMBER_WARNING_POLICY_STATUSES
        ):
            raise SchemaError(
                "small_number_warning_policy_status is unsupported: %s"
                % small_number_warning_policy_status
            )
        small_number_warning_denominator_threshold = _require_positive_int(
            contract.get("small_number_warning_denominator_threshold"),
            "small_number_warning_denominator_threshold",
        )
        small_number_warning_numerator_threshold = _require_positive_int(
            contract.get("small_number_warning_numerator_threshold"),
            "small_number_warning_numerator_threshold",
        )
        default_ranking_behavior = _require_string(
            contract.get("default_ranking_behavior"),
            "default_ranking_behavior",
        )
        if default_ranking_behavior not in DEFAULT_RANKING_BEHAVIORS:
            raise SchemaError(
                "default_ranking_behavior is unsupported: %s"
                % default_ranking_behavior
            )
        numerator_population_scope = _require_string(
            contract.get("numerator_population_scope"),
            "numerator_population_scope",
        )
        if numerator_population_scope not in NUMERATOR_POPULATION_SCOPES:
            raise SchemaError(
                "numerator_population_scope is unsupported: %s"
                % numerator_population_scope
            )
        numerator_period_type = _require_string(
            contract.get("numerator_period_type"), "numerator_period_type"
        )
        if numerator_period_type not in NUMERATOR_PERIOD_TYPES:
            raise SchemaError(
                "numerator_period_type is unsupported: %s" % numerator_period_type
            )
        denominator_population_scope = _require_string(
            contract.get("denominator_population_scope"),
            "denominator_population_scope",
        )
        if denominator_population_scope not in DENOMINATOR_POPULATION_SCOPES:
            raise SchemaError(
                "denominator_population_scope is unsupported: %s"
                % denominator_population_scope
            )
        denominator_period_type = _require_string(
            contract.get("denominator_period_type"), "denominator_period_type"
        )
        if denominator_period_type not in DENOMINATOR_PERIOD_TYPES:
            raise SchemaError(
                "denominator_period_type is unsupported: %s"
                % denominator_period_type
            )
        contracts.append(
            IndicatorContract(
                indicator_id=indicator_id,
                label_ja=_require_string(contract.get("label_ja"), "label_ja"),
                label_en=_require_string(contract.get("label_en"), "label_en"),
                measure_kind=measure_kind,
                canonical_formula=canonical_formula,
                numerator_source_id=_require_string(
                    contract.get("numerator_source_id"), "numerator_source_id"
                ),
                numerator_metric=numerator_metric,
                numerator_year=_require_int(
                    contract.get("numerator_year"), "numerator_year"
                ),
                numerator_row_kind=numerator_row_kind,
                numerator_offense_scope=(
                    _require_string(
                        contract.get("numerator_offense_scope"),
                        "numerator_offense_scope",
                    )
                    if contract.get("numerator_offense_scope") is not None
                    else None
                ),
                numerator_population_scope=numerator_population_scope,
                numerator_period_type=numerator_period_type,
                numerator_geography_semantics=_require_string(
                    contract.get("numerator_geography_semantics"),
                    "numerator_geography_semantics",
                ),
                denominator_source_id=_require_string(
                    contract.get("denominator_source_id"), "denominator_source_id"
                ),
                denominator_metric=denominator_metric,
                denominator_period_end=_require_iso_date(
                    contract.get("denominator_period_end"), "denominator_period_end"
                ),
                denominator_population_scope=denominator_population_scope,
                denominator_period_type=denominator_period_type,
                denominator_geography_semantics=_require_string(
                    contract.get("denominator_geography_semantics"),
                    "denominator_geography_semantics",
                ),
                geography_grain=geography_grain,
                crosswalk_policy=crosswalk_policy,
                expected_numerator_row_count=_require_positive_int(
                    contract.get("expected_numerator_row_count"),
                    "expected_numerator_row_count",
                ),
                display_multiplier=display_multiplier,
                display_scale_status=display_scale_status,
                display_unit_label_ja=_require_string(
                    contract.get("display_unit_label_ja"), "display_unit_label_ja"
                ),
                display_unit_label_en=_require_string(
                    contract.get("display_unit_label_en"), "display_unit_label_en"
                ),
                small_number_warning_policy_version=(
                    small_number_warning_policy_version
                ),
                small_number_warning_policy_status=(
                    small_number_warning_policy_status
                ),
                small_number_warning_denominator_threshold=(
                    small_number_warning_denominator_threshold
                ),
                small_number_warning_numerator_threshold=(
                    small_number_warning_numerator_threshold
                ),
                default_ranking_behavior=default_ranking_behavior,
                base_mismatch_flags=_sorted_unique_strings(
                    contract.get("base_mismatch_flags", []), "base_mismatch_flags"
                ),
                ui_caveat=_require_string(contract.get("ui_caveat"), "ui_caveat"),
            )
        )
    return tuple(contracts)


def _load_processed_input_pins(path: Path) -> Mapping[str, str]:
    data = _read_json_object(path, "indicator contract")
    raw_pins = _require_mapping(
        data.get("processed_input_pins"), "processed_input_pins"
    )
    pins = {}
    for source_id, digest in raw_pins.items():
        validated_source_id = _require_string(
            source_id, "processed_input_pins source_id"
        )
        pins[validated_source_id] = _require_sha256(
            digest, "processed_input_pins[%s]" % validated_source_id
        )
    return pins


def _small_number_warning_policy_summary(
    contracts: Sequence[IndicatorContract],
) -> Mapping[str, object]:
    if not contracts:
        raise SchemaError("At least one indicator contract is required")
    policies = {
        (
            contract.small_number_warning_policy_version,
            contract.small_number_warning_policy_status,
            contract.small_number_warning_denominator_threshold,
            contract.small_number_warning_numerator_threshold,
            contract.default_ranking_behavior,
        )
        for contract in contracts
    }
    if len(policies) != 1:
        raise SchemaError(
            "small-number warning policy must match across all contracts"
        )
    (
        policy_version,
        policy_status,
        denominator_threshold,
        numerator_threshold,
        default_ranking_behavior,
    ) = next(iter(policies))
    return {
        "policy_version": policy_version,
        "policy_status": policy_status,
        "denominator_threshold": denominator_threshold,
        "numerator_threshold": numerator_threshold,
        "default_ranking_behavior": default_ranking_behavior,
    }


def _read_catalog(path: Path) -> List[Mapping[str, object]]:
    rows = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise SchemaError("Catalog row must be an object at line %d" % line_number)
                if row.get("processing_status") != "validated":
                    raise SchemaError("Indicator generation requires validated catalog inputs")
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
    run_path = Path(path).parent / "run.json"
    run = _read_json_object(run_path, "processed run")
    if run.get("source_id") != source_id:
        raise SchemaError("Processed run source_id differs for %s" % source_id)
    if run.get("quality_passed") is not True:
        raise SchemaError("Processed run did not pass quality for %s" % source_id)
    expected = _require_string(
        run.get("normalized_sha256"), "processed run normalized_sha256"
    )
    observed = sha256_file(path)
    if observed != expected:
        raise IntegrityError(
            "Processed normalized input hash differs from run.json for %s"
            % source_id
        )
    if observed != pinned_sha256:
        raise IntegrityError(
            "Processed normalized input hash differs from contract pin for %s"
            % source_id
        )
    return observed


def _json_key(source_context: Mapping[str, object]) -> str:
    return json.dumps(source_context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _mapping_key(
    *,
    source_id: str,
    dimension: str,
    source_entity_kind: str,
    source_label: str,
    source_context: Mapping[str, object],
) -> Tuple[str, str, str, str, str]:
    return (
        source_id,
        dimension,
        source_entity_kind,
        source_label,
        _json_key(source_context),
    )


def _load_mapping_lookup(mapping_latest_path: Path) -> Tuple[Dict[Tuple[str, str, str, str, str], MappingReference], Mapping[str, object], Path]:
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
    lookup: Dict[Tuple[str, str, str, str, str], MappingReference] = {}
    with jsonl_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("Mapping row must be an object at line %d" % line_number)
            key = _mapping_key(
                source_id=_require_string(row.get("source_id"), "mapping source_id"),
                dimension=_require_string(row.get("dimension"), "mapping dimension"),
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
                dimension=key[1],
                source_id=key[0],
                source_entity_kind=key[2],
                source_label=key[3],
                source_context=json.loads(key[4]),
                match_status=_require_string(row.get("match_status"), "match_status"),
                canonical_ids=tuple(row.get("canonical_ids", [])),
                canonical_labels=tuple(row.get("canonical_labels", [])),
                targets_complete=bool(row.get("targets_complete")),
            )
    return lookup, summary, run_dir


def _load_population_aggregates(
    path: Path,
    *,
    source_id: str,
) -> Tuple[Mapping[str, PopulationAggregate], Mapping[str, PopulationAggregate], str]:
    by_nationality: Dict[str, PopulationAggregate] = {}
    by_prefecture: Dict[str, PopulationAggregate] = {}
    period_end = None
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("Population row must be an object: %s:%d" % (path, line_number))
            if row.get("source_id") != source_id:
                raise SchemaError("Population source_id differs from catalog: %s" % path)
            row_period_end = _require_string(row.get("period_end"), "period_end")
            if period_end is None:
                period_end = row_period_end
            elif period_end != row_period_end:
                raise SchemaError("Population source contains multiple period_end values")
            value = row.get("value")
            suppressed = bool(row.get("suppressed"))
            nationality_code = _require_string(
                row.get("nationality_code"), "population nationality_code"
            )
            nationality_label = _require_string(
                row.get("nationality"), "population nationality"
            )
            prefecture_code = _require_string(
                row.get("prefecture_code"), "population prefecture_code"
            )
            prefecture_label = _require_string(
                row.get("prefecture"), "population prefecture"
            )
            nationality_id = "isa-nationality:%s" % nationality_code
            prefecture_id = "jp-prefecture:%s" % prefecture_code
            nationality = by_nationality.setdefault(
                nationality_id, PopulationAggregate(label=nationality_label)
            )
            prefecture = by_prefecture.setdefault(
                prefecture_id, PopulationAggregate(label=prefecture_label)
            )
            if value is None or suppressed:
                nationality.complete = False
                prefecture.complete = False
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise SchemaError("Population value must be an integer or null")
            if value < 0:
                raise SchemaError("Population value must be non-negative")
            nationality.value += value
            prefecture.value += value
    if period_end is None:
        raise SchemaError("Population input is empty: %s" % path)
    return by_nationality, by_prefecture, period_end


def _load_nationality_rows(path: Path, *, source_id: str) -> List[Mapping[str, object]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("Nationality row must be an object: %s:%d" % (path, line_number))
            if row.get("source_id") != source_id:
                raise SchemaError("Nationality source_id differs from catalog: %s" % path)
            rows.append(row)
    return rows


def _load_prefecture_rows(path: Path, *, source_id: str) -> List[Mapping[str, object]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("Prefecture row must be an object: %s:%d" % (path, line_number))
            if row.get("source_id") != source_id:
                raise SchemaError("Prefecture source_id differs from catalog: %s" % path)
            rows.append(row)
    return rows


def _contract_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise SchemaError("generated_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone offset")
    return parsed.strftime("%Y%m%d_%H%M%S")


def _catalog_paths(
    catalog_rows: Iterable[Mapping[str, object]],
    *,
    processed_root: Path,
) -> Dict[str, Path]:
    paths = {}
    for row in catalog_rows:
        source_id = _require_string(row.get("source_id"), "catalog source_id")
        if source_id in paths:
            raise SchemaError("Duplicate catalog source_id: %s" % source_id)
        paths[source_id] = _safe_processed_path(processed_root, row.get("processed_relpath"))
    return paths


def _catalog_source_artifacts(
    catalog_rows: Iterable[Mapping[str, object]],
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
    by_source = {
        _require_string(row.get("source_id"), "catalog source_id"): row
        for row in catalog_rows
    }
    artifacts = {}
    for source_id in sorted(set(required_source_ids)):
        try:
            row = by_source[source_id]
        except KeyError as error:
            raise SchemaError(
                "Missing required source in artifact catalog: %s" % source_id
            ) from error
        artifact = {}
        for field in fields:
            value = row.get(field)
            if value is None:
                raise SchemaError(
                    "Catalog provenance field %s is missing for %s"
                    % (field, source_id)
                )
            artifact[field] = value
        artifact["normalized_sha256"] = normalized_hashes[source_id]
        artifacts[source_id] = artifact
    return artifacts


def _mapping_for_nationality(
    lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
    row: Mapping[str, object],
) -> MappingReference:
    source_context = {
        "region": row.get("region"),
        "row_kind": row.get("row_kind"),
        "subcategory": row.get("subcategory"),
    }
    key = _mapping_key(
        source_id=_require_string(row.get("source_id"), "source_id"),
        dimension="nationality_or_region",
        source_entity_kind=_require_string(row.get("row_kind"), "row_kind"),
        source_label=_require_string(row.get("nationality"), "nationality"),
        source_context=source_context,
    )
    try:
        return lookup[key]
    except KeyError as error:
        raise SchemaError("Missing nationality mapping for %r" % (key,)) from error


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
        dimension="geography",
        source_entity_kind=_require_string(row.get("geography_type"), "geography_type"),
        source_label=_require_string(row.get("geography"), "geography"),
        source_context=source_context,
    )
    try:
        return lookup[key]
    except KeyError as error:
        raise SchemaError("Missing geography mapping for %r" % (key,)) from error


def _year_from_period_end(period_end: str) -> int:
    return date.fromisoformat(period_end).year


def _build_record(
    *,
    contract: IndicatorContract,
    entity_dimension: str,
    published_label: Optional[str],
    geography_label: str,
    geography_id: str,
    geography_type: str,
    numerator_value: int,
    denominator_value: Optional[int],
    year: int,
    period_end: str,
    crosswalk_status: Optional[str],
    targets_complete: bool,
    mismatch_flags: Sequence[str],
    canonical_component_ids: Sequence[str],
    canonical_component_labels: Sequence[str],
    numerator_context: Mapping[str, object],
    denominator_context: Mapping[str, object],
    refusal_reason: Optional[str] = None,
) -> IndicatorRecord:
    if denominator_value is not None and denominator_value > 0:
        quotient = numerator_value / denominator_value
        display_value = quotient * contract.display_multiplier
        status = "calculated"
    else:
        quotient = None
        display_value = None
        status = "refused"
    if refusal_reason is not None:
        quotient = None
        display_value = None
        status = "refused"
    mismatch = tuple(sorted(set(mismatch_flags)))
    small_number_warning_flags = []
    if status == "calculated":
        if denominator_value < contract.small_number_warning_denominator_threshold:
            small_number_warning_flags.append("small_denominator_base")
        if numerator_value < contract.small_number_warning_numerator_threshold:
            small_number_warning_flags.append("sparse_numerator_count")
    default_ranking_excluded = (
        status == "calculated"
        and bool(small_number_warning_flags)
        and contract.default_ranking_behavior == "exclude_flagged"
    )
    return IndicatorRecord(
        indicator_run_schema_version=INDICATOR_RUN_SCHEMA_VERSION,
        indicator_id=contract.indicator_id,
        label_ja=contract.label_ja,
        label_en=contract.label_en,
        measure_kind=contract.measure_kind,
        canonical_formula=contract.canonical_formula,
        display_formula=DISPLAY_FORMULA,
        statistical_compatibility=STATISTICAL_COMPATIBILITY,
        entity_dimension=entity_dimension,
        published_label=published_label,
        geography_label=geography_label,
        geography_id=geography_id,
        geography_type=geography_type,
        year=year,
        period_end=period_end,
        numerator_source_id=contract.numerator_source_id,
        denominator_source_id=contract.denominator_source_id,
        numerator_metric=contract.numerator_metric,
        denominator_metric=contract.denominator_metric,
        numerator_value=numerator_value,
        denominator_value=denominator_value if status == "calculated" else None,
        quotient=quotient,
        display_multiplier=contract.display_multiplier,
        display_scale_status=contract.display_scale_status,
        display_unit_label_ja=contract.display_unit_label_ja,
        display_unit_label_en=contract.display_unit_label_en,
        display_value=display_value,
        small_number_warning_policy_version=(
            contract.small_number_warning_policy_version
        ),
        small_number_warning_policy_status=(
            contract.small_number_warning_policy_status
        ),
        small_number_warning_flags=tuple(sorted(small_number_warning_flags)),
        default_ranking_behavior=contract.default_ranking_behavior,
        default_ranking_excluded=default_ranking_excluded,
        crosswalk_policy=contract.crosswalk_policy,
        crosswalk_status=crosswalk_status,
        targets_complete=targets_complete,
        calculation_status=status,
        refusal_reason=refusal_reason,
        mismatch_flags=mismatch,
        canonical_component_ids=tuple(canonical_component_ids),
        canonical_component_labels=tuple(canonical_component_labels),
        numerator_context=dict(numerator_context),
        denominator_context=dict(denominator_context),
        ui_caveat=contract.ui_caveat,
    )


def _resolved_denominator(
    components: Sequence[str],
    population: Mapping[str, PopulationAggregate],
) -> Tuple[Optional[int], Optional[str]]:
    total = 0
    for component in components:
        aggregate = population.get(component)
        if aggregate is None:
            return None, "missing_denominator_component"
        if not aggregate.complete:
            return None, "suppressed_denominator_component"
        total += aggregate.value
    if total <= 0:
        return None, "denominator_non_positive"
    return total, None


def _build_nationality_indicator_records(
    contract: IndicatorContract,
    *,
    rows: Sequence[Mapping[str, object]],
    population: Mapping[str, PopulationAggregate],
    mapping_lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
    denominator_period_end: str,
) -> List[IndicatorRecord]:
    if _year_from_period_end(denominator_period_end) != contract.numerator_year:
        raise SchemaError(
            "Same-year pairing failed for %s: %s vs %s"
            % (
                contract.indicator_id,
                contract.numerator_year,
                denominator_period_end,
            )
        )
    selected_rows = [
        row
        for row in rows
        if row.get("year") == contract.numerator_year
        and row.get("row_kind") == contract.numerator_row_kind
        and row.get("subcategory") is None
    ]
    selected_keys = [
        (
            row.get("year"),
            row.get("region"),
            row.get("nationality"),
            row.get("row_kind"),
            row.get("subcategory"),
        )
        for row in selected_rows
    ]
    if len(set(selected_keys)) != len(selected_keys):
        raise SchemaError("Duplicate numerator cell for %s" % contract.indicator_id)
    if len(selected_rows) != contract.expected_numerator_row_count:
        raise SchemaError(
            "expected_numerator_row_count differs for %s: expected %d, observed %d"
            % (
                contract.indicator_id,
                contract.expected_numerator_row_count,
                len(selected_rows),
            )
        )
    records = []
    seen_cells = set()
    for row in selected_rows:
        if row.get("population_scope") != contract.numerator_population_scope:
            raise SchemaError(
                "numerator population_scope differs for %s"
                % contract.indicator_id
            )
        cell_key = (
            row.get("year"),
            row.get("region"),
            row.get("nationality"),
            row.get("row_kind"),
            row.get("subcategory"),
        )
        if cell_key in seen_cells:
            raise SchemaError(
                "Duplicate numerator cell for %s: %r"
                % (contract.indicator_id, cell_key)
            )
        seen_cells.add(cell_key)
        mapping = _mapping_for_nationality(mapping_lookup, row)
        mismatch_flags = list(contract.base_mismatch_flags)
        refusal_reason = None
        if contract.crosswalk_policy == "exact":
            if (
                mapping.match_status != "matched"
                or len(mapping.canonical_ids) != 1
                or not mapping.targets_complete
            ):
                refusal_reason = "crosswalk_not_exact"
        else:
            if not mapping.canonical_ids:
                refusal_reason = "no_canonical_denominator_components"
            elif mapping.match_status == "ambiguous":
                mismatch_flags.append("nationality_grouping_mismatch")
        if mapping.match_status == "ambiguous" and not mapping.targets_complete:
            mismatch_flags.append("canonical_target_incomplete")
        denominator_value = None
        denominator_reason = None
        if refusal_reason is None:
            denominator_value, denominator_reason = _resolved_denominator(
                mapping.canonical_ids, population
            )
            if denominator_reason is not None:
                refusal_reason = denominator_reason
        records.append(
            _build_record(
                contract=contract,
                entity_dimension="nationality",
                published_label=_require_string(row.get("nationality"), "nationality"),
                geography_label="日本全国",
                geography_id="jp:all",
                geography_type="national",
                numerator_value=_require_nonnegative_int(
                    row.get(contract.numerator_metric), contract.numerator_metric
                ),
                denominator_value=denominator_value,
                year=contract.numerator_year,
                period_end=denominator_period_end,
                crosswalk_status=mapping.match_status,
                targets_complete=mapping.targets_complete,
                mismatch_flags=mismatch_flags,
                canonical_component_ids=mapping.canonical_ids,
                canonical_component_labels=mapping.canonical_labels,
                numerator_context={
                    "population_scope": row.get("population_scope"),
                    "period_type": contract.numerator_period_type,
                    "geography_semantics": contract.numerator_geography_semantics,
                    "region": row.get("region"),
                    "row_kind": row.get("row_kind"),
                },
                denominator_context={
                    "period_end": denominator_period_end,
                    "period_type": contract.denominator_period_type,
                    "population_scope": contract.denominator_population_scope,
                    "geography_grain": "national",
                    "geography_semantics": contract.denominator_geography_semantics,
                },
                refusal_reason=refusal_reason,
            )
        )
    return records


def _build_prefecture_indicator_records(
    contract: IndicatorContract,
    *,
    rows: Sequence[Mapping[str, object]],
    population: Mapping[str, PopulationAggregate],
    mapping_lookup: Mapping[Tuple[str, str, str, str, str], MappingReference],
    denominator_period_end: str,
) -> List[IndicatorRecord]:
    if _year_from_period_end(denominator_period_end) != contract.numerator_year:
        raise SchemaError(
            "Same-year pairing failed for %s: %s vs %s"
            % (
                contract.indicator_id,
                contract.numerator_year,
                denominator_period_end,
            )
        )
    selected_rows = [
        row
        for row in rows
        if row.get("year") == contract.numerator_year
        and row.get("geography_type") == contract.numerator_row_kind
        and (
            contract.numerator_offense_scope is None
            or row.get("offense_scope") == contract.numerator_offense_scope
        )
    ]
    selected_keys = [
        (
            row.get("year"),
            row.get("offense_scope"),
            row.get("geography_type"),
            row.get("geography"),
        )
        for row in selected_rows
    ]
    if len(set(selected_keys)) != len(selected_keys):
        raise SchemaError("Duplicate numerator cell for %s" % contract.indicator_id)
    if len(selected_rows) != contract.expected_numerator_row_count:
        raise SchemaError(
            "expected_numerator_row_count differs for %s: expected %d, observed %d"
            % (
                contract.indicator_id,
                contract.expected_numerator_row_count,
                len(selected_rows),
            )
        )
    records = []
    seen_cells = set()
    for row in selected_rows:
        if row.get("population_scope") != contract.numerator_population_scope:
            raise SchemaError(
                "numerator population_scope differs for %s"
                % contract.indicator_id
            )
        if (
            row.get("geography_semantics")
            != contract.numerator_geography_semantics
        ):
            raise SchemaError(
                "numerator geography_semantics differs for %s"
                % contract.indicator_id
            )
        cell_key = (
            row.get("year"),
            row.get("offense_scope"),
            row.get("geography_type"),
            row.get("geography"),
        )
        if cell_key in seen_cells:
            raise SchemaError(
                "Duplicate numerator cell for %s: %r"
                % (contract.indicator_id, cell_key)
            )
        seen_cells.add(cell_key)
        mapping = _mapping_for_geography(mapping_lookup, row)
        mismatch_flags = list(contract.base_mismatch_flags)
        refusal_reason = None
        if (
            mapping.match_status != "matched"
            or len(mapping.canonical_ids) != 1
            or not mapping.targets_complete
        ):
            refusal_reason = "geography_not_exact_prefecture"
        denominator_value = None
        denominator_reason = None
        if refusal_reason is None:
            denominator_value, denominator_reason = _resolved_denominator(
                mapping.canonical_ids, population
            )
            if denominator_reason is not None:
                refusal_reason = denominator_reason
        records.append(
            _build_record(
                contract=contract,
                entity_dimension="geography",
                published_label=_require_string(row.get("geography"), "geography"),
                geography_label=_require_string(row.get("geography"), "geography"),
                geography_id=mapping.canonical_ids[0] if mapping.canonical_ids else "unknown",
                geography_type=_require_string(row.get("geography_type"), "geography_type"),
                numerator_value=_require_nonnegative_int(
                    row.get(contract.numerator_metric), contract.numerator_metric
                ),
                denominator_value=denominator_value,
                year=contract.numerator_year,
                period_end=denominator_period_end,
                crosswalk_status=mapping.match_status,
                targets_complete=mapping.targets_complete,
                mismatch_flags=mismatch_flags,
                canonical_component_ids=mapping.canonical_ids,
                canonical_component_labels=mapping.canonical_labels,
                numerator_context={
                    "population_scope": row.get("population_scope"),
                    "period_type": contract.numerator_period_type,
                    "offense_scope": row.get("offense_scope"),
                    "geography_semantics": row.get("geography_semantics"),
                    "parent_region": row.get("parent_region"),
                },
                denominator_context={
                    "period_end": denominator_period_end,
                    "period_type": contract.denominator_period_type,
                    "population_scope": contract.denominator_population_scope,
                    "geography_grain": "prefecture",
                    "geography_semantics": contract.denominator_geography_semantics,
                },
                refusal_reason=refusal_reason,
            )
        )
    return records


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def generate_indicator_report(
    *,
    catalog_path: Path,
    processed_root: Path,
    mapping_latest_path: Path,
    contracts_path: Path,
    output_root: Path,
    generated_at: str,
) -> IndicatorReport:
    """Generate immutable reference-ratio outputs from validated processed data."""

    contracts = load_indicator_contracts(contracts_path)
    warning_policy = _small_number_warning_policy_summary(contracts)
    catalog_rows = _read_catalog(catalog_path)
    catalog_paths = _catalog_paths(catalog_rows, processed_root=processed_root)
    required_source_ids = {
        source_id
        for contract in contracts
        for source_id in (
            contract.numerator_source_id,
            contract.denominator_source_id,
        )
    }
    processed_input_pins = _load_processed_input_pins(contracts_path)
    missing_pins = sorted(required_source_ids - set(processed_input_pins))
    if missing_pins:
        raise SchemaError(
            "Missing processed_input_pins for required sources: %s"
            % ", ".join(missing_pins)
        )
    normalized_hashes = {}
    for source_id in sorted(required_source_ids):
        try:
            processed_path = catalog_paths[source_id]
        except KeyError as error:
            raise SchemaError(
                "Missing required source in artifact catalog: %s" % source_id
            ) from error
        normalized_hashes[source_id] = _verify_processed_input(
            processed_path,
            source_id,
            processed_input_pins[source_id],
        )
    source_artifacts = _catalog_source_artifacts(
        catalog_rows,
        required_source_ids,
        normalized_hashes,
    )
    mapping_lookup, mapping_summary, mapping_run_dir = _load_mapping_lookup(
        mapping_latest_path
    )

    population_cache: Dict[str, Tuple[Mapping[str, PopulationAggregate], Mapping[str, PopulationAggregate], str]] = {}
    nationality_cache: Dict[str, List[Mapping[str, object]]] = {}
    prefecture_cache: Dict[str, List[Mapping[str, object]]] = {}

    records: List[IndicatorRecord] = []
    for contract in contracts:
        try:
            denominator_path = catalog_paths[contract.denominator_source_id]
        except KeyError as error:
            raise SchemaError(
                "Missing denominator source in catalog: %s"
                % contract.denominator_source_id
            ) from error
        try:
            numerator_path = catalog_paths[contract.numerator_source_id]
        except KeyError as error:
            raise SchemaError(
                "Missing numerator source in catalog: %s"
                % contract.numerator_source_id
            ) from error

        if contract.denominator_source_id not in population_cache:
            population_cache[contract.denominator_source_id] = _load_population_aggregates(
                denominator_path,
                source_id=contract.denominator_source_id,
            )
        nationality_population, prefecture_population, observed_period_end = population_cache[
            contract.denominator_source_id
        ]
        if observed_period_end != contract.denominator_period_end:
            raise SchemaError(
                "Configured denominator_period_end differs from observed value for %s"
                % contract.denominator_source_id
            )

        if contract.geography_grain == "national":
            if contract.numerator_source_id not in nationality_cache:
                nationality_cache[contract.numerator_source_id] = _load_nationality_rows(
                    numerator_path,
                    source_id=contract.numerator_source_id,
                )
            records.extend(
                _build_nationality_indicator_records(
                    contract,
                    rows=nationality_cache[contract.numerator_source_id],
                    population=nationality_population,
                    mapping_lookup=mapping_lookup,
                    denominator_period_end=observed_period_end,
                )
            )
        else:
            if contract.numerator_source_id not in prefecture_cache:
                prefecture_cache[contract.numerator_source_id] = _load_prefecture_rows(
                    numerator_path,
                    source_id=contract.numerator_source_id,
                )
            records.extend(
                _build_prefecture_indicator_records(
                    contract,
                    rows=prefecture_cache[contract.numerator_source_id],
                    population=prefecture_population,
                    mapping_lookup=mapping_lookup,
                    denominator_period_end=observed_period_end,
                )
            )

    records.sort(
        key=lambda item: (
            item.indicator_id,
            item.year,
            item.geography_label,
            item.published_label or "",
        )
    )
    status_counts = Counter(item.calculation_status for item in records)
    status_payload = {
        status: status_counts.get(status, 0) for status in CALCULATION_STATUSES
    }
    by_indicator: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    mismatch_flag_counts = Counter()
    refusal_reason_counts = Counter()
    small_number_warning_counts = Counter()
    for item in records:
        by_indicator[item.indicator_id][item.calculation_status] += 1
        mismatch_flag_counts.update(item.mismatch_flags)
        if item.refusal_reason is not None:
            refusal_reason_counts[item.refusal_reason] += 1
        small_number_warning_counts.update(item.small_number_warning_flags)
        if item.small_number_warning_flags:
            small_number_warning_counts["either_warning"] += 1
        if item.default_ranking_excluded:
            small_number_warning_counts["default_ranking_excluded"] += 1

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (_contract_timestamp(generated_at) + "_indicators")
    if destination.exists():
        raise IntegrityError(
            "Timestamped indicator output already exists and was not overwritten: %s"
            % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".indicator-run-", dir=destination_root))
    try:
        jsonl_path = staging / "indicator_records.jsonl"
        csv_path = staging / "indicator_records.csv"
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
                writer.writerow(
                    {
                        field: _csv_value(item.to_dict().get(field))
                        for field in CSV_FIELDS
                    }
                )
        summary = {
            "indicator_run_schema_version": INDICATOR_RUN_SCHEMA_VERSION,
            "generated_at": generated_at,
            "catalog_path": Path(catalog_path).as_posix(),
            "catalog_sha256": sha256_file(Path(catalog_path)),
            "contracts_path": Path(contracts_path).as_posix(),
            "contracts_sha256": sha256_file(Path(contracts_path)),
            "processed_input_pins": {
                source_id: processed_input_pins[source_id]
                for source_id in sorted(required_source_ids)
            },
            "mapping_latest_path": Path(mapping_latest_path).as_posix(),
            "mapping_latest_sha256": sha256_file(Path(mapping_latest_path)),
            "mapping_run_relpath": mapping_run_dir.name,
            "mapping_record_count": mapping_summary.get("mapping_record_count"),
            "contract_count": len(contracts),
            "indicator_record_count": len(records),
            "status_counts": status_payload,
            "mismatch_flag_counts": dict(sorted(mismatch_flag_counts.items())),
            "refusal_reason_counts": dict(sorted(refusal_reason_counts.items())),
            "small_number_warning_policy": warning_policy,
            "small_number_warning_counts": {
                key: small_number_warning_counts.get(key, 0)
                for key in (
                    "small_denominator_base",
                    "sparse_numerator_count",
                    "either_warning",
                    "default_ranking_excluded",
                )
            },
            "source_artifacts": source_artifacts,
            "by_indicator": {
                indicator_id: {
                    status: counts.get(status, 0) for status in CALCULATION_STATUSES
                }
                for indicator_id, counts in sorted(by_indicator.items())
            },
        }
        _write_json(summary_path, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "indicator_records.jsonl"
    final_csv = destination / "indicator_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    latest_temp = destination_root / ".latest.json.tmp"
    _write_json(
        latest_temp,
        {
            "indicator_run_schema_version": INDICATOR_RUN_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "indicator_records_sha256": sha256_file(final_jsonl),
            "indicator_records_csv_sha256": sha256_file(final_csv),
        },
    )
    latest_temp.replace(latest_path)
    return IndicatorReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        status_counts=status_payload,
    )
