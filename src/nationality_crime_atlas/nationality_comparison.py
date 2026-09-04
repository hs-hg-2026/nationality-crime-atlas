"""Build the nationwide nationality comparison, including a Japanese residual row."""

import csv
import json
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .indicators import (
    PopulationAggregate,
    _catalog_paths,
    _catalog_source_artifacts,
    _contract_timestamp,
    _load_mapping_lookup,
    _load_nationality_rows,
    _load_population_aggregates,
    _mapping_for_nationality,
    _read_catalog,
    _read_json_object,
    _require_float,
    _require_int,
    _require_mapping,
    _require_nonnegative_int,
    _require_positive_int,
    _require_sha256,
    _require_string,
    _resolved_denominator,
    _verify_processed_input,
    _write_json,
)
from .provenance import sha256_file


NATIONALITY_COMPARISON_SCHEMA_VERSION = 1
LATEST_SCHEMA_VERSION = 1
CALCULATION_STATUSES = ("calculated", "refused")
MEASURE_KIND = "public_data_derived_reference_ratio"
CANONICAL_FORMULA = "numerator_value / denominator_value"
DISPLAY_FORMULA = "quotient * display_multiplier"
STATISTICAL_COMPATIBILITY = "not_established"
DEFAULT_DISPLAY_BEHAVIOR = "include_all_with_warnings"
INTERPRETATION_POLICY = "observed_values_without_intrinsic_group_inference"


@dataclass(frozen=True)
class NationalityComparisonContract:
    """Versioned inputs and display rules for one nationwide comparison."""

    comparison_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    numerator_year: int
    foreign_numerator_source_id: str
    foreign_numerator_metric: str
    all_person_numerator_source_id: str
    all_person_numerator_metric: str
    foreign_population_source_id: str
    foreign_denominator_period_end: str
    japanese_population_source_id: str
    japanese_denominator_reference_date: str
    expected_foreign_country_row_count: int
    expected_foreign_region_total_row_count: int
    foreign_total_outside_region_labels: Tuple[str, ...]
    expected_foreign_total_numerator: int
    aggregated_nationality_label: str
    expected_aggregated_subcategory_row_count: int
    display_multiplier: float
    display_unit_label_ja: str
    display_unit_label_en: str
    small_number_denominator_threshold: int
    small_number_numerator_threshold: int
    default_display_behavior: str
    interpretation_policy: str
    ui_caveat: str


@dataclass(frozen=True)
class NationalityComparisonRecord:
    """One displayed nationality category or explicit no-value row."""

    nationality_comparison_schema_version: int
    comparison_id: str
    label_ja: str
    label_en: str
    measure_kind: str
    canonical_formula: str
    display_formula: str
    statistical_compatibility: str
    display_multiplier: float
    display_unit_label_ja: str
    display_unit_label_en: str
    default_display_behavior: str
    interpretation_policy: str
    ui_caveat: str
    entity_dimension: str
    entity_id: str
    published_label: str
    display_label: str
    source_order: int
    is_japanese_reference: bool
    year: int
    denominator_reference_date: str
    numerator_source_ids: Tuple[str, ...]
    denominator_source_id: str
    numerator_metric: str
    denominator_metric: str
    numerator_value: int
    denominator_value: Optional[int]
    quotient: Optional[float]
    display_value: Optional[float]
    calculation_status: str
    refusal_reason: Optional[str]
    crosswalk_status: Optional[str]
    targets_complete: bool
    canonical_component_ids: Tuple[str, ...]
    canonical_component_labels: Tuple[str, ...]
    derivation_method: str
    derivation_formula: str
    numerator_components: Tuple[Mapping[str, object], ...]
    mismatch_flags: Tuple[str, ...]
    small_number_warning_flags: Tuple[str, ...]
    display_included: bool
    numerator_context: Mapping[str, object]
    denominator_context: Mapping[str, object]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NationalityComparisonReport:
    """Locations and counts for one immutable comparison run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    status_counts: Mapping[str, int]


CSV_FIELDS = tuple(NationalityComparisonRecord.__dataclass_fields__)


def _iso_date(value: object, label: str) -> str:
    result = _require_string(value, label)
    try:
        parsed = date.fromisoformat(result)
    except ValueError as error:
        raise SchemaError("%s must be an ISO-8601 date" % label) from error
    if parsed.isoformat() != result:
        raise SchemaError("%s must use YYYY-MM-DD format" % label)
    return result


def _string_tuple(value: object, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    return tuple(_require_string(item, label) for item in value)


def load_nationality_comparison_contract(
    path: Path,
) -> Tuple[NationalityComparisonContract, Mapping[str, str]]:
    """Load and validate the single comparison contract and input pins."""

    data = _read_json_object(path, "nationality comparison contract")
    if data.get("schema_version") != 1:
        raise SchemaError("Unsupported nationality comparison contract schema_version")
    raw_pins = _require_mapping(data.get("processed_input_pins"), "processed_input_pins")
    pins = {
        _require_string(source_id, "processed input source_id"): _require_sha256(
            digest, "processed_input_pins[%s]" % source_id
        )
        for source_id, digest in raw_pins.items()
    }
    item = _require_mapping(data.get("comparison"), "comparison")
    measure_kind = _require_string(item.get("measure_kind"), "measure_kind")
    if measure_kind != MEASURE_KIND:
        raise SchemaError("Unsupported nationality comparison measure_kind")
    canonical_formula = _require_string(
        item.get("canonical_formula"), "canonical_formula"
    )
    if canonical_formula != CANONICAL_FORMULA:
        raise SchemaError("Unsupported nationality comparison canonical_formula")
    foreign_metric = _require_string(
        item.get("foreign_numerator_metric"), "foreign_numerator_metric"
    )
    if foreign_metric != "criminal_code_cleared_persons":
        raise SchemaError("foreign_numerator_metric must be criminal_code_cleared_persons")
    all_person_metric = _require_string(
        item.get("all_person_numerator_metric"), "all_person_numerator_metric"
    )
    if all_person_metric != "cleared_persons":
        raise SchemaError("all_person_numerator_metric must be cleared_persons")
    default_display_behavior = _require_string(
        item.get("default_display_behavior"), "default_display_behavior"
    )
    if default_display_behavior != DEFAULT_DISPLAY_BEHAVIOR:
        raise SchemaError("Comparison rows must remain included with warnings")
    interpretation_policy = _require_string(
        item.get("interpretation_policy"), "interpretation_policy"
    )
    if interpretation_policy != INTERPRETATION_POLICY:
        raise SchemaError("Unsupported interpretation_policy")
    display_multiplier = _require_float(
        item.get("display_multiplier"), "display_multiplier"
    )
    if display_multiplier <= 0:
        raise SchemaError("display_multiplier must be positive")
    contract = NationalityComparisonContract(
        comparison_id=_require_string(item.get("comparison_id"), "comparison_id"),
        label_ja=_require_string(item.get("label_ja"), "label_ja"),
        label_en=_require_string(item.get("label_en"), "label_en"),
        measure_kind=measure_kind,
        canonical_formula=canonical_formula,
        numerator_year=_require_int(item.get("numerator_year"), "numerator_year"),
        foreign_numerator_source_id=_require_string(
            item.get("foreign_numerator_source_id"), "foreign_numerator_source_id"
        ),
        foreign_numerator_metric=foreign_metric,
        all_person_numerator_source_id=_require_string(
            item.get("all_person_numerator_source_id"),
            "all_person_numerator_source_id",
        ),
        all_person_numerator_metric=all_person_metric,
        foreign_population_source_id=_require_string(
            item.get("foreign_population_source_id"),
            "foreign_population_source_id",
        ),
        foreign_denominator_period_end=_iso_date(
            item.get("foreign_denominator_period_end"),
            "foreign_denominator_period_end",
        ),
        japanese_population_source_id=_require_string(
            item.get("japanese_population_source_id"),
            "japanese_population_source_id",
        ),
        japanese_denominator_reference_date=_iso_date(
            item.get("japanese_denominator_reference_date"),
            "japanese_denominator_reference_date",
        ),
        expected_foreign_country_row_count=_require_positive_int(
            item.get("expected_foreign_country_row_count"),
            "expected_foreign_country_row_count",
        ),
        expected_foreign_region_total_row_count=_require_positive_int(
            item.get("expected_foreign_region_total_row_count"),
            "expected_foreign_region_total_row_count",
        ),
        foreign_total_outside_region_labels=_string_tuple(
            item.get("foreign_total_outside_region_labels"),
            "foreign_total_outside_region_labels",
        ),
        expected_foreign_total_numerator=_require_nonnegative_int(
            item.get("expected_foreign_total_numerator"),
            "expected_foreign_total_numerator",
        ),
        aggregated_nationality_label=_require_string(
            item.get("aggregated_nationality_label"),
            "aggregated_nationality_label",
        ),
        expected_aggregated_subcategory_row_count=_require_positive_int(
            item.get("expected_aggregated_subcategory_row_count"),
            "expected_aggregated_subcategory_row_count",
        ),
        display_multiplier=display_multiplier,
        display_unit_label_ja=_require_string(
            item.get("display_unit_label_ja"), "display_unit_label_ja"
        ),
        display_unit_label_en=_require_string(
            item.get("display_unit_label_en"), "display_unit_label_en"
        ),
        small_number_denominator_threshold=_require_positive_int(
            item.get("small_number_denominator_threshold"),
            "small_number_denominator_threshold",
        ),
        small_number_numerator_threshold=_require_positive_int(
            item.get("small_number_numerator_threshold"),
            "small_number_numerator_threshold",
        ),
        default_display_behavior=default_display_behavior,
        interpretation_policy=interpretation_policy,
        ui_caveat=_require_string(item.get("ui_caveat"), "ui_caveat"),
    )
    required_sources = {
        contract.foreign_numerator_source_id,
        contract.all_person_numerator_source_id,
        contract.foreign_population_source_id,
        contract.japanese_population_source_id,
    }
    if set(pins) != required_sources:
        raise SchemaError("processed_input_pins must exactly match comparison sources")
    return contract, pins


def _load_rows(path: Path, *, source_id: str, label: str) -> List[Mapping[str, object]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise SchemaError("%s row must be an object at line %d" % (label, line_number))
            if row.get("source_id") != source_id:
                raise SchemaError("%s source_id differs from catalog" % label)
            rows.append(row)
    if not rows:
        raise SchemaError("%s input is empty" % label)
    return rows


def _one_row(rows: Sequence[Mapping[str, object]], *, label: str, predicate):
    selected = [row for row in rows if predicate(row)]
    if len(selected) != 1:
        raise SchemaError("Expected exactly one %s row, observed %d" % (label, len(selected)))
    return selected[0]


def _foreign_total(
    rows: Sequence[Mapping[str, object]],
    contract: NationalityComparisonContract,
) -> Tuple[int, Tuple[Mapping[str, object], ...]]:
    region_rows = [
        row
        for row in rows
        if row.get("year") == contract.numerator_year
        and row.get("row_kind") == "region_total"
    ]
    if len(region_rows) != contract.expected_foreign_region_total_row_count:
        raise SchemaError("expected foreign region-total row count differs")
    outside_rows = [
        row
        for row in rows
        if row.get("year") == contract.numerator_year
        and row.get("row_kind") == "country"
        and row.get("region") is None
        and row.get("nationality") in contract.foreign_total_outside_region_labels
    ]
    if {row.get("nationality") for row in outside_rows} != set(
        contract.foreign_total_outside_region_labels
    ):
        raise SchemaError("foreign total outside-region labels differ")
    components = tuple(region_rows + outside_rows)
    total = sum(
        _require_nonnegative_int(
            row.get(contract.foreign_numerator_metric),
            contract.foreign_numerator_metric,
        )
        for row in components
    )
    if total != contract.expected_foreign_total_numerator:
        raise SchemaError(
            "foreign total numerator differs: expected %d, observed %d"
            % (contract.expected_foreign_total_numerator, total)
        )
    return total, components


def _warning_flags(
    contract: NationalityComparisonContract,
    numerator: int,
    denominator: Optional[int],
) -> Tuple[str, ...]:
    if denominator is None:
        return ()
    warnings = []
    if denominator < contract.small_number_denominator_threshold:
        warnings.append("small_denominator_base")
    if numerator < contract.small_number_numerator_threshold:
        warnings.append("sparse_numerator_count")
    return tuple(sorted(warnings))


def _record(
    contract: NationalityComparisonContract,
    *,
    entity_id: str,
    published_label: str,
    display_label: str,
    source_order: int,
    is_japanese_reference: bool,
    denominator_reference_date: str,
    numerator_source_ids: Sequence[str],
    denominator_source_id: str,
    numerator_value: int,
    denominator_value: Optional[int],
    refusal_reason: Optional[str],
    crosswalk_status: Optional[str],
    targets_complete: bool,
    canonical_component_ids: Sequence[str],
    canonical_component_labels: Sequence[str],
    derivation_method: str,
    derivation_formula: str,
    numerator_components: Sequence[Mapping[str, object]],
    mismatch_flags: Sequence[str],
    numerator_context: Mapping[str, object],
    denominator_context: Mapping[str, object],
) -> NationalityComparisonRecord:
    status = (
        "calculated"
        if refusal_reason is None and denominator_value is not None and denominator_value > 0
        else "refused"
    )
    if status == "calculated":
        quotient = numerator_value / denominator_value
        display_value = quotient * contract.display_multiplier
    else:
        quotient = None
        display_value = None
        denominator_value = None
    return NationalityComparisonRecord(
        nationality_comparison_schema_version=NATIONALITY_COMPARISON_SCHEMA_VERSION,
        comparison_id=contract.comparison_id,
        label_ja=contract.label_ja,
        label_en=contract.label_en,
        measure_kind=contract.measure_kind,
        canonical_formula=contract.canonical_formula,
        display_formula=DISPLAY_FORMULA,
        statistical_compatibility=STATISTICAL_COMPATIBILITY,
        display_multiplier=contract.display_multiplier,
        display_unit_label_ja=contract.display_unit_label_ja,
        display_unit_label_en=contract.display_unit_label_en,
        default_display_behavior=contract.default_display_behavior,
        interpretation_policy=contract.interpretation_policy,
        ui_caveat=contract.ui_caveat,
        entity_dimension="nationality",
        entity_id=entity_id,
        published_label=published_label,
        display_label=display_label,
        source_order=source_order,
        is_japanese_reference=is_japanese_reference,
        year=contract.numerator_year,
        denominator_reference_date=denominator_reference_date,
        numerator_source_ids=tuple(sorted(set(numerator_source_ids))),
        denominator_source_id=denominator_source_id,
        numerator_metric="criminal_code_cleared_persons",
        denominator_metric="corresponding_population",
        numerator_value=numerator_value,
        denominator_value=denominator_value,
        quotient=quotient,
        display_value=display_value,
        calculation_status=status,
        refusal_reason=refusal_reason,
        crosswalk_status=crosswalk_status,
        targets_complete=targets_complete,
        canonical_component_ids=tuple(canonical_component_ids),
        canonical_component_labels=tuple(canonical_component_labels),
        derivation_method=derivation_method,
        derivation_formula=derivation_formula,
        numerator_components=tuple(dict(component) for component in numerator_components),
        mismatch_flags=tuple(sorted(set(mismatch_flags))),
        small_number_warning_flags=_warning_flags(
            contract, numerator_value, denominator_value
        ),
        display_included=True,
        numerator_context=dict(numerator_context),
        denominator_context=dict(denominator_context),
    )


def _base_foreign_mismatches() -> List[str]:
    return [
        "all_foreign_vs_resident_population_mismatch",
        "annual_flow_vs_point_in_time_stock",
        "cleared_person_records_not_unique_risk_population",
        "denominator_reference_dates_differ_across_rows",
    ]


def _foreign_record(
    contract: NationalityComparisonContract,
    *,
    row: Mapping[str, object],
    population: Mapping[str, PopulationAggregate],
    mapping_lookup,
    duplicate_labels: Mapping[str, int],
) -> NationalityComparisonRecord:
    mapping = _mapping_for_nationality(mapping_lookup, row)
    mismatch_flags = _base_foreign_mismatches()
    refusal_reason = None
    denominator_value = None
    if not mapping.canonical_ids:
        refusal_reason = "no_canonical_denominator_components"
    else:
        denominator_value, refusal_reason = _resolved_denominator(
            mapping.canonical_ids, population
        )
    if mapping.match_status != "matched" or len(mapping.canonical_ids) != 1:
        mismatch_flags.append("nationality_grouping_mismatch")
    if not mapping.targets_complete:
        mismatch_flags.append("canonical_target_incomplete")
    label = _require_string(row.get("nationality"), "nationality")
    region = row.get("region")
    display_label = (
        "%s（%s）" % (label, region)
        if duplicate_labels.get(label, 0) > 1 and region
        else label
    )
    numerator = _require_nonnegative_int(
        row.get(contract.foreign_numerator_metric),
        contract.foreign_numerator_metric,
    )
    source_row = _require_nonnegative_int(row.get("source_row"), "source_row")
    return _record(
        contract,
        entity_id=(
            mapping.canonical_ids[0]
            if len(mapping.canonical_ids) == 1
            else "npa:S08:row-%d" % source_row
        ),
        published_label=label,
        display_label=display_label,
        source_order=source_row,
        is_japanese_reference=False,
        denominator_reference_date=contract.foreign_denominator_period_end,
        numerator_source_ids=[contract.foreign_numerator_source_id],
        denominator_source_id=contract.foreign_population_source_id,
        numerator_value=numerator,
        denominator_value=denominator_value,
        refusal_reason=refusal_reason,
        crosswalk_status=mapping.match_status,
        targets_complete=mapping.targets_complete,
        canonical_component_ids=mapping.canonical_ids,
        canonical_component_labels=mapping.canonical_labels,
        derivation_method="published_direct",
        derivation_formula="S08.criminal_code_cleared_persons",
        numerator_components=[
            {
                "source_id": contract.foreign_numerator_source_id,
                "source_row": source_row,
                "value": numerator,
            }
        ],
        mismatch_flags=mismatch_flags,
        numerator_context={
            "population_scope": row.get("population_scope"),
            "offense_scope": "criminal_code",
            "period_type": "calendar_year_flow",
            "region": region,
            "row_kind": row.get("row_kind"),
        },
        denominator_context={
            "population_scope": "resident_foreigners",
            "period_type": "year_end_stock",
            "reference_date": contract.foreign_denominator_period_end,
        },
    )


def _aggregated_record(
    contract: NationalityComparisonContract,
    *,
    rows: Sequence[Mapping[str, object]],
    population: Mapping[str, PopulationAggregate],
    mapping_lookup,
) -> NationalityComparisonRecord:
    mappings = [_mapping_for_nationality(mapping_lookup, row) for row in rows]
    canonical_sets = {mapping.canonical_ids for mapping in mappings}
    mismatch_flags = _base_foreign_mismatches() + [
        "published_subcategories_aggregated_to_nationality"
    ]
    refusal_reason = None
    canonical_ids: Tuple[str, ...] = ()
    canonical_labels: Tuple[str, ...] = ()
    if len(canonical_sets) == 1:
        canonical_ids = mappings[0].canonical_ids
        canonical_labels = mappings[0].canonical_labels
    if not canonical_ids:
        refusal_reason = "aggregated_subcategory_crosswalk_not_exact"
        denominator_value = None
    else:
        denominator_value, refusal_reason = _resolved_denominator(
            canonical_ids, population
        )
    if len(canonical_ids) != 1 or any(
        mapping.match_status != "matched" or not mapping.targets_complete
        for mapping in mappings
    ):
        mismatch_flags.append("nationality_grouping_mismatch")
    components = []
    numerator = 0
    for row in rows:
        value = _require_nonnegative_int(
            row.get(contract.foreign_numerator_metric),
            contract.foreign_numerator_metric,
        )
        numerator += value
        components.append(
            {
                "source_id": contract.foreign_numerator_source_id,
                "source_row": row.get("source_row"),
                "subcategory": row.get("subcategory"),
                "value": value,
            }
        )
    return _record(
        contract,
        entity_id=(
            canonical_ids[0]
            if len(canonical_ids) == 1
            else "npa:S08:aggregated-%s" % contract.aggregated_nationality_label
        ),
        published_label=contract.aggregated_nationality_label,
        display_label=contract.aggregated_nationality_label,
        source_order=min(_require_nonnegative_int(row.get("source_row"), "source_row") for row in rows),
        is_japanese_reference=False,
        denominator_reference_date=contract.foreign_denominator_period_end,
        numerator_source_ids=[contract.foreign_numerator_source_id],
        denominator_source_id=contract.foreign_population_source_id,
        numerator_value=numerator,
        denominator_value=denominator_value,
        refusal_reason=refusal_reason,
        crosswalk_status=("matched" if len(canonical_ids) == 1 else "ambiguous"),
        targets_complete=all(mapping.targets_complete for mapping in mappings),
        canonical_component_ids=canonical_ids,
        canonical_component_labels=canonical_labels,
        derivation_method="sum_published_subcategories",
        derivation_formula="sum(S08.criminal_code_cleared_persons by published subcategory)",
        numerator_components=components,
        mismatch_flags=mismatch_flags,
        numerator_context={
            "population_scope": "all_foreign",
            "offense_scope": "criminal_code",
            "period_type": "calendar_year_flow",
            "row_kind": "aggregated_subcategories",
        },
        denominator_context={
            "population_scope": "resident_foreigners",
            "period_type": "year_end_stock",
            "reference_date": contract.foreign_denominator_period_end,
        },
    )


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def generate_nationality_comparison_report(
    *,
    catalog_path: Path,
    processed_root: Path,
    mapping_latest_path: Path,
    contract_path: Path,
    output_root: Path,
    generated_at: str,
) -> NationalityComparisonReport:
    """Generate an immutable full comparison table from validated inputs."""

    contract, pins = load_nationality_comparison_contract(contract_path)
    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _contract_timestamp(generated_at) + "_nationality_comparison"
    )
    if destination.exists():
        raise IntegrityError(
            "Timestamped nationality comparison output already exists and was not overwritten: %s"
            % destination
        )

    catalog_rows = _read_catalog(catalog_path)
    catalog_paths = _catalog_paths(catalog_rows, processed_root=processed_root)
    normalized_hashes = {}
    for source_id, pinned_hash in sorted(pins.items()):
        try:
            source_path = catalog_paths[source_id]
        except KeyError as error:
            raise SchemaError("Missing comparison source in catalog: %s" % source_id) from error
        normalized_hashes[source_id] = _verify_processed_input(
            source_path, source_id, pinned_hash
        )
    source_artifacts = _catalog_source_artifacts(
        catalog_rows, pins, normalized_hashes
    )
    mapping_lookup, mapping_summary, mapping_run_dir = _load_mapping_lookup(
        mapping_latest_path
    )

    foreign_rows = _load_nationality_rows(
        catalog_paths[contract.foreign_numerator_source_id],
        source_id=contract.foreign_numerator_source_id,
    )
    country_rows = [
        row
        for row in foreign_rows
        if row.get("year") == contract.numerator_year
        and row.get("row_kind") == "country"
        and row.get("subcategory") is None
    ]
    if len(country_rows) != contract.expected_foreign_country_row_count:
        raise SchemaError("expected foreign country row count differs")
    aggregate_rows = [
        row
        for row in foreign_rows
        if row.get("year") == contract.numerator_year
        and row.get("row_kind") == "subcategory"
        and row.get("nationality") == contract.aggregated_nationality_label
    ]
    if len(aggregate_rows) != contract.expected_aggregated_subcategory_row_count:
        raise SchemaError("expected aggregated subcategory row count differs")
    if any(row.get("population_scope") != "all_foreign" for row in foreign_rows):
        raise SchemaError("foreign numerator population_scope differs")
    foreign_total, foreign_total_rows = _foreign_total(foreign_rows, contract)

    all_person_rows = _load_rows(
        catalog_paths[contract.all_person_numerator_source_id],
        source_id=contract.all_person_numerator_source_id,
        label="all-person numerator",
    )
    all_person_row = _one_row(
        all_person_rows,
        label="national all-person numerator",
        predicate=lambda row: (
            row.get("year") == contract.numerator_year
            and row.get("geography_type") == "national"
            and row.get("geography") == "日本"
            and row.get("population_scope") == "all_persons"
            and row.get("offense_scope")
            == "criminal_code_excluding_traffic_negligence"
        ),
    )
    all_person_total = _require_nonnegative_int(
        all_person_row.get(contract.all_person_numerator_metric),
        contract.all_person_numerator_metric,
    )
    japanese_numerator = all_person_total - foreign_total
    if japanese_numerator < 0:
        raise SchemaError("Derived Japanese numerator is negative")

    japanese_population_rows = _load_rows(
        catalog_paths[contract.japanese_population_source_id],
        source_id=contract.japanese_population_source_id,
        label="Japanese population",
    )
    japanese_population_row = _one_row(
        japanese_population_rows,
        label="national Japanese population",
        predicate=lambda row: (
            row.get("year") == contract.numerator_year
            and row.get("reference_date")
            == contract.japanese_denominator_reference_date
            and row.get("population_scope") == "japanese_population"
            and row.get("geography_type") == "national"
            and row.get("geography") == "日本"
        ),
    )
    japanese_population = _require_positive_int(
        japanese_population_row.get("population"), "Japanese population"
    )

    nationality_population, _, observed_period_end = _load_population_aggregates(
        catalog_paths[contract.foreign_population_source_id],
        source_id=contract.foreign_population_source_id,
    )
    if observed_period_end != contract.foreign_denominator_period_end:
        raise SchemaError("foreign denominator period differs from contract")

    records = [
        _record(
            contract,
            entity_id="jp-nationality:japanese",
            published_label="日本",
            display_label="日本（残差による参考値）",
            source_order=0,
            is_japanese_reference=True,
            denominator_reference_date=contract.japanese_denominator_reference_date,
            numerator_source_ids=[
                contract.foreign_numerator_source_id,
                contract.all_person_numerator_source_id,
            ],
            denominator_source_id=contract.japanese_population_source_id,
            numerator_value=japanese_numerator,
            denominator_value=japanese_population,
            refusal_reason=None,
            crosswalk_status=None,
            targets_complete=True,
            canonical_component_ids=["jp-nationality:japanese"],
            canonical_component_labels=["日本"],
            derivation_method="residual_subtraction",
            derivation_formula="S15.all_person_cleared_persons - S08.all_foreign_criminal_code_cleared_persons",
            numerator_components=[
                {
                    "source_id": contract.all_person_numerator_source_id,
                    "role": "minuend",
                    "value": all_person_total,
                },
                {
                    "source_id": contract.foreign_numerator_source_id,
                    "role": "subtrahend",
                    "value": foreign_total,
                    "component_source_rows": [row.get("source_row") for row in foreign_total_rows],
                },
            ],
            mismatch_flags=[
                "all_persons_minus_all_foreign_scope_assumption",
                "annual_flow_vs_point_in_time_stock",
                "cleared_person_records_not_unique_risk_population",
                "denominator_reference_dates_differ_across_rows",
                "japanese_numerator_derived_by_residual_subtraction",
                "japanese_population_rounded_to_nearest_1000",
            ],
            numerator_context={
                "population_scope": "derived_japanese_residual",
                "offense_scope": "criminal_code_excluding_traffic_negligence",
                "period_type": "calendar_year_flow",
            },
            denominator_context={
                "population_scope": "japanese_population",
                "period_type": "point_in_time_stock",
                "reference_date": contract.japanese_denominator_reference_date,
                "rounding": japanese_population_row.get("rounding"),
            },
        )
    ]
    label_counts = Counter(
        _require_string(row.get("nationality"), "nationality")
        for row in country_rows
    )
    records.extend(
        _foreign_record(
            contract,
            row=row,
            population=nationality_population,
            mapping_lookup=mapping_lookup,
            duplicate_labels=label_counts,
        )
        for row in country_rows
    )
    records.append(
        _aggregated_record(
            contract,
            rows=aggregate_rows,
            population=nationality_population,
            mapping_lookup=mapping_lookup,
        )
    )
    records.sort(key=lambda record: (record.source_order, record.display_label))
    status_counter = Counter(record.calculation_status for record in records)
    status_counts = {
        status: status_counter.get(status, 0) for status in CALCULATION_STATUSES
    }
    mismatch_counts = Counter(
        flag for record in records for flag in record.mismatch_flags
    )
    warning_counts = Counter(
        flag for record in records for flag in record.small_number_warning_flags
    )
    refusal_counts = Counter(
        record.refusal_reason
        for record in records
        if record.refusal_reason is not None
    )

    staging = Path(
        tempfile.mkdtemp(prefix=".nationality-comparison-", dir=destination_root)
    )
    try:
        jsonl_path = staging / "nationality_comparison_records.jsonl"
        csv_path = staging / "nationality_comparison_records.csv"
        summary_path = staging / "summary.json"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(
                    json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for record in records:
                row = record.to_dict()
                writer.writerow(
                    {field: _csv_value(row.get(field)) for field in CSV_FIELDS}
                )
        summary = {
            "nationality_comparison_schema_version": NATIONALITY_COMPARISON_SCHEMA_VERSION,
            "generated_at": generated_at,
            "catalog_path": Path(catalog_path).as_posix(),
            "catalog_sha256": sha256_file(Path(catalog_path)),
            "contract_path": Path(contract_path).as_posix(),
            "contract_sha256": sha256_file(Path(contract_path)),
            "mapping_latest_path": Path(mapping_latest_path).as_posix(),
            "mapping_latest_sha256": sha256_file(Path(mapping_latest_path)),
            "mapping_run_relpath": mapping_run_dir.name,
            "mapping_record_count": mapping_summary.get("mapping_record_count"),
            "processed_input_pins": dict(sorted(pins.items())),
            "source_artifacts": source_artifacts,
            "record_count": len(records),
            "status_counts": status_counts,
            "refusal_reason_counts": dict(sorted(refusal_counts.items())),
            "mismatch_flag_counts": dict(sorted(mismatch_counts.items())),
            "small_number_warning_counts": dict(sorted(warning_counts.items())),
            "display_included_count": sum(record.display_included for record in records),
            "japanese_numerator_reconciliation": {
                "all_person_criminal_code_cleared_persons": all_person_total,
                "all_foreign_criminal_code_cleared_persons": foreign_total,
                "derived_japanese_criminal_code_cleared_persons": japanese_numerator,
            },
        }
        _write_json(summary_path, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "nationality_comparison_records.jsonl"
    final_csv = destination / "nationality_comparison_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    latest_temp = destination_root / ".latest.json.tmp"
    _write_json(
        latest_temp,
        {
            "nationality_comparison_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "nationality_comparison_records_sha256": sha256_file(final_jsonl),
            "nationality_comparison_records_csv_sha256": sha256_file(final_csv),
        },
    )
    latest_temp.replace(latest_path)
    return NationalityComparisonReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        status_counts=status_counts,
    )
