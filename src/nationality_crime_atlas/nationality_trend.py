"""Build nationality-specific clearance reference-ratio time series."""

import csv
import json
import os
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .indicators import (
    _catalog_paths,
    _catalog_source_artifacts,
    _contract_timestamp,
    _load_mapping_lookup,
    _load_nationality_rows,
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
    _verify_processed_input,
)
from .provenance import sha256_file


NATIONALITY_TREND_SCHEMA_VERSION = 1
LATEST_SCHEMA_VERSION = 1
CALCULATION_STATUSES = ("calculated", "refused")
METRICS = ("cleared_cases", "cleared_persons")
METRIC_LABELS = {"cleared_cases": "検挙件数", "cleared_persons": "検挙人員"}
FOREIGN_METRIC_FIELDS = {
    "cleared_cases": "criminal_code_cleared_cases",
    "cleared_persons": "criminal_code_cleared_persons",
}
INTERPRETATION_POLICY = (
    "observed_time_series_without_intrinsic_group_inference"
)


@dataclass(frozen=True)
class NationalityTrendContract:
    """Reviewed inputs and display rules for one time-series product."""

    trend_id: str
    label_ja: str
    label_en: str
    years: Tuple[int, ...]
    metrics: Tuple[str, ...]
    foreign_numerator_sources: Mapping[int, str]
    all_person_numerator_sources: Mapping[int, str]
    foreign_population_sources: Mapping[int, str]
    japanese_population_sources: Mapping[int, str]
    foreign_population_label_aliases: Mapping[str, str]
    expected_foreign_country_row_count: int
    expected_foreign_region_total_row_count: int
    foreign_total_outside_region_labels: Tuple[str, ...]
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
class NationalityTrendRecord:
    """One entity, metric, and year cell, including explicit refusals."""

    nationality_trend_schema_version: int
    trend_id: str
    label_ja: str
    label_en: str
    metric: str
    metric_label_ja: str
    display_multiplier: float
    display_unit_label_ja: str
    display_unit_label_en: str
    interpretation_policy: str
    ui_caveat: str
    entity_id: str
    published_label: str
    display_label: str
    source_order: int
    is_japanese_reference: bool
    year: int
    denominator_reference_date: str
    numerator_source_ids: Tuple[str, ...]
    denominator_source_id: str
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
    mismatch_flags: Tuple[str, ...]
    small_number_warning_flags: Tuple[str, ...]
    display_included: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NationalityTrendReport:
    """Locations and counts for one immutable trend run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    status_counts: Mapping[str, int]


CSV_FIELDS = tuple(NationalityTrendRecord.__dataclass_fields__)


def _string_tuple(value: object, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    return tuple(_require_string(item, label) for item in value)


def _year_tuple(value: object) -> Tuple[int, ...]:
    if not isinstance(value, list):
        raise SchemaError("years must be an array")
    years = tuple(_require_int(item, "year") for item in value)
    if len(years) < 2 or tuple(sorted(set(years))) != years:
        raise SchemaError("years must contain at least two unique ascending years")
    return years


def _year_source_map(
    value: object,
    *,
    years: Sequence[int],
    label: str,
) -> Mapping[int, str]:
    raw = _require_mapping(value, label)
    result = {
        int(year): _require_string(source_id, "%s[%s]" % (label, year))
        for year, source_id in raw.items()
    }
    if set(result) != set(years):
        raise SchemaError("%s must exactly cover trend years" % label)
    return dict(sorted(result.items()))


def _string_mapping(value: object, label: str) -> Mapping[str, str]:
    raw = _require_mapping(value, label)
    return {
        _require_string(source, "%s source label" % label): _require_string(
            target, "%s target label" % label
        )
        for source, target in raw.items()
    }


def load_nationality_trend_contract(
    path: Path,
) -> Tuple[NationalityTrendContract, Mapping[str, str]]:
    """Load and validate a nationality trend contract."""

    data = _read_json_object(path, "nationality trend contract")
    if data.get("schema_version") != 1:
        raise SchemaError("Unsupported nationality trend contract schema_version")
    raw_pins = _require_mapping(data.get("processed_input_pins"), "processed_input_pins")
    pins = {
        _require_string(source_id, "processed input source_id"): _require_sha256(
            digest, "processed_input_pins[%s]" % source_id
        )
        for source_id, digest in raw_pins.items()
    }
    item = _require_mapping(data.get("trend"), "trend")
    years = _year_tuple(item.get("years"))
    metrics = _string_tuple(item.get("metrics"), "metrics")
    if metrics != METRICS:
        raise SchemaError("metrics must be cleared_cases then cleared_persons")
    foreign_sources = _year_source_map(
        item.get("foreign_numerator_sources"),
        years=years,
        label="foreign_numerator_sources",
    )
    all_person_sources = _year_source_map(
        item.get("all_person_numerator_sources"),
        years=years,
        label="all_person_numerator_sources",
    )
    foreign_population_sources = _year_source_map(
        item.get("foreign_population_sources"),
        years=years,
        label="foreign_population_sources",
    )
    japanese_population_sources = _year_source_map(
        item.get("japanese_population_sources"),
        years=years,
        label="japanese_population_sources",
    )
    expected_sources = set(foreign_sources.values()) | set(all_person_sources.values())
    expected_sources |= set(foreign_population_sources.values())
    expected_sources |= set(japanese_population_sources.values())
    if set(pins) != expected_sources:
        raise SchemaError("processed_input_pins must exactly match trend sources")
    display_multiplier = _require_float(
        item.get("display_multiplier"), "display_multiplier"
    )
    if display_multiplier <= 0:
        raise SchemaError("display_multiplier must be positive")
    if item.get("default_display_behavior") != "include_all_with_warnings":
        raise SchemaError("Trend rows must remain included with warnings")
    if item.get("interpretation_policy") != INTERPRETATION_POLICY:
        raise SchemaError("Unsupported nationality trend interpretation_policy")
    return (
        NationalityTrendContract(
            trend_id=_require_string(item.get("trend_id"), "trend_id"),
            label_ja=_require_string(item.get("label_ja"), "label_ja"),
            label_en=_require_string(item.get("label_en"), "label_en"),
            years=years,
            metrics=metrics,
            foreign_numerator_sources=foreign_sources,
            all_person_numerator_sources=all_person_sources,
            foreign_population_sources=foreign_population_sources,
            japanese_population_sources=japanese_population_sources,
            foreign_population_label_aliases=_string_mapping(
                item.get("foreign_population_label_aliases", {}),
                "foreign_population_label_aliases",
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
            default_display_behavior="include_all_with_warnings",
            interpretation_policy=INTERPRETATION_POLICY,
            ui_caveat=_require_string(item.get("ui_caveat"), "ui_caveat"),
        ),
        dict(sorted(pins.items())),
    )


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


def _warning_flags(
    contract: NationalityTrendContract,
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


def _load_foreign_population_by_label(
    path: Path,
    *,
    source_id: str,
) -> Tuple[Mapping[str, int], str]:
    """Load the historical total-by-nationality table without inventing codes."""

    population = {}
    period_end = None
    for row in _load_rows(path, source_id=source_id, label="foreign population"):
        row_period_end = _require_string(row.get("period_end"), "period_end")
        if period_end is None:
            period_end = row_period_end
        elif period_end != row_period_end:
            raise SchemaError("Foreign population source contains multiple periods")
        if row.get("row_kind") != "country_or_area":
            continue
        label = _require_string(row.get("nationality"), "population nationality")
        if label in population:
            raise SchemaError("Duplicate foreign population label: %s" % label)
        population[label] = _require_nonnegative_int(
            row.get("population"), "foreign population"
        )
    if period_end is None or not population:
        raise SchemaError("Foreign population source has no nationality rows")
    return population, period_end


def _resolved_label_denominator(
    canonical_labels: Sequence[str],
    population: Mapping[str, int],
    aliases: Mapping[str, str],
) -> Tuple[Optional[int], Optional[str]]:
    total = 0
    for canonical_label in canonical_labels:
        population_label = aliases.get(canonical_label, canonical_label)
        if population_label not in population:
            return None, "missing_denominator_component"
        total += population[population_label]
    if total <= 0:
        return None, "denominator_non_positive"
    return total, None


def _record(
    contract: NationalityTrendContract,
    *,
    metric: str,
    entity_id: str,
    published_label: str,
    display_label: str,
    source_order: int,
    is_japanese_reference: bool,
    year: int,
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
    mismatch_flags: Sequence[str],
) -> NationalityTrendRecord:
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
    return NationalityTrendRecord(
        nationality_trend_schema_version=NATIONALITY_TREND_SCHEMA_VERSION,
        trend_id=contract.trend_id,
        label_ja=contract.label_ja,
        label_en=contract.label_en,
        metric=metric,
        metric_label_ja=METRIC_LABELS[metric],
        display_multiplier=contract.display_multiplier,
        display_unit_label_ja=contract.display_unit_label_ja,
        display_unit_label_en=contract.display_unit_label_en,
        interpretation_policy=contract.interpretation_policy,
        ui_caveat=contract.ui_caveat,
        entity_id=entity_id,
        published_label=published_label,
        display_label=display_label,
        source_order=source_order,
        is_japanese_reference=is_japanese_reference,
        year=year,
        denominator_reference_date=denominator_reference_date,
        numerator_source_ids=tuple(sorted(set(numerator_source_ids))),
        denominator_source_id=denominator_source_id,
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
        mismatch_flags=tuple(sorted(set(mismatch_flags))),
        small_number_warning_flags=_warning_flags(
            contract, numerator_value, denominator_value
        ),
        display_included=True,
    )


def _foreign_total_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    year: int,
    contract: NationalityTrendContract,
) -> Sequence[Mapping[str, object]]:
    region_rows = [
        row
        for row in rows
        if row.get("year") == year and row.get("row_kind") == "region_total"
    ]
    if len(region_rows) != contract.expected_foreign_region_total_row_count:
        raise SchemaError("expected foreign region-total row count differs")
    outside_rows = [
        row
        for row in rows
        if row.get("year") == year
        and row.get("row_kind") == "country"
        and row.get("region") is None
        and row.get("nationality") in contract.foreign_total_outside_region_labels
    ]
    if {row.get("nationality") for row in outside_rows} != set(
        contract.foreign_total_outside_region_labels
    ):
        raise SchemaError("foreign total outside-region labels differ")
    return [*region_rows, *outside_rows]


def _foreign_mismatches() -> List[str]:
    return [
        "all_foreign_vs_resident_population_mismatch",
        "annual_flow_vs_point_in_time_stock",
        "clearance_records_not_unique_risk_population",
        "denominator_reference_dates_differ_across_rows",
    ]


def _foreign_record(
    contract: NationalityTrendContract,
    *,
    metric: str,
    year: int,
    source_id: str,
    denominator_source_id: str,
    denominator_reference_date: str,
    row: Mapping[str, object],
    population: Mapping[str, int],
    mapping_lookup,
    duplicate_labels: Mapping[str, int],
) -> NationalityTrendRecord:
    mapping = _mapping_for_nationality(mapping_lookup, row)
    refusal_reason = None
    denominator = None
    if not mapping.canonical_ids:
        refusal_reason = "no_canonical_denominator_components"
    else:
        denominator, refusal_reason = _resolved_label_denominator(
            mapping.canonical_labels,
            population,
            contract.foreign_population_label_aliases,
        )
    mismatch_flags = _foreign_mismatches()
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
    source_order = _require_nonnegative_int(row.get("source_row"), "source_row")
    return _record(
        contract,
        metric=metric,
        entity_id=(
            mapping.canonical_ids[0]
            if len(mapping.canonical_ids) == 1
            else "npa-nationality:row-%d" % source_order
        ),
        published_label=label,
        display_label=display_label,
        source_order=source_order,
        is_japanese_reference=False,
        year=year,
        denominator_reference_date=denominator_reference_date,
        numerator_source_ids=[source_id],
        denominator_source_id=denominator_source_id,
        numerator_value=_require_nonnegative_int(
            row.get(FOREIGN_METRIC_FIELDS[metric]), FOREIGN_METRIC_FIELDS[metric]
        ),
        denominator_value=denominator,
        refusal_reason=refusal_reason,
        crosswalk_status=mapping.match_status,
        targets_complete=mapping.targets_complete,
        canonical_component_ids=mapping.canonical_ids,
        canonical_component_labels=mapping.canonical_labels,
        derivation_method="published_direct",
        derivation_formula="%s.%s" % (source_id, FOREIGN_METRIC_FIELDS[metric]),
        mismatch_flags=mismatch_flags,
    )


def _aggregated_record(
    contract: NationalityTrendContract,
    *,
    metric: str,
    year: int,
    source_id: str,
    denominator_source_id: str,
    denominator_reference_date: str,
    rows: Sequence[Mapping[str, object]],
    population: Mapping[str, int],
    mapping_lookup,
) -> NationalityTrendRecord:
    mappings = [_mapping_for_nationality(mapping_lookup, row) for row in rows]
    canonical_sets = {mapping.canonical_ids for mapping in mappings}
    canonical_ids: Tuple[str, ...] = ()
    canonical_labels: Tuple[str, ...] = ()
    if len(canonical_sets) == 1:
        canonical_ids = mappings[0].canonical_ids
        canonical_labels = mappings[0].canonical_labels
    refusal_reason = None
    if not canonical_ids:
        denominator = None
        refusal_reason = "aggregated_subcategory_crosswalk_not_exact"
    else:
        denominator, refusal_reason = _resolved_label_denominator(
            canonical_labels,
            population,
            contract.foreign_population_label_aliases,
        )
    mismatch_flags = _foreign_mismatches() + [
        "published_subcategories_aggregated_to_nationality"
    ]
    if len(canonical_ids) != 1 or any(
        mapping.match_status != "matched" or not mapping.targets_complete
        for mapping in mappings
    ):
        mismatch_flags.append("nationality_grouping_mismatch")
    source_order = min(
        _require_nonnegative_int(row.get("source_row"), "source_row") for row in rows
    )
    return _record(
        contract,
        metric=metric,
        entity_id=(
            canonical_ids[0]
            if len(canonical_ids) == 1
            else "npa-nationality:aggregated-%d" % source_order
        ),
        published_label=contract.aggregated_nationality_label,
        display_label=contract.aggregated_nationality_label,
        source_order=source_order,
        is_japanese_reference=False,
        year=year,
        denominator_reference_date=denominator_reference_date,
        numerator_source_ids=[source_id],
        denominator_source_id=denominator_source_id,
        numerator_value=sum(
            _require_nonnegative_int(
                row.get(FOREIGN_METRIC_FIELDS[metric]), FOREIGN_METRIC_FIELDS[metric]
            )
            for row in rows
        ),
        denominator_value=denominator,
        refusal_reason=refusal_reason,
        crosswalk_status="matched" if len(canonical_ids) == 1 else "ambiguous",
        targets_complete=all(mapping.targets_complete for mapping in mappings),
        canonical_component_ids=canonical_ids,
        canonical_component_labels=canonical_labels,
        derivation_method="sum_published_subcategories",
        derivation_formula="sum(%s.%s by published subcategory)"
        % (source_id, FOREIGN_METRIC_FIELDS[metric]),
        mismatch_flags=mismatch_flags,
    )


def _year_records(
    contract: NationalityTrendContract,
    *,
    year: int,
    catalog_paths: Mapping[str, Path],
    mapping_lookup,
) -> List[NationalityTrendRecord]:
    foreign_source_id = contract.foreign_numerator_sources[year]
    all_person_source_id = contract.all_person_numerator_sources[year]
    foreign_population_source_id = contract.foreign_population_sources[year]
    japanese_population_source_id = contract.japanese_population_sources[year]
    foreign_rows = _load_nationality_rows(
        catalog_paths[foreign_source_id], source_id=foreign_source_id
    )
    if any(row.get("population_scope") != "all_foreign" for row in foreign_rows):
        raise SchemaError("foreign numerator population_scope differs")
    country_rows = [
        row
        for row in foreign_rows
        if row.get("year") == year
        and row.get("row_kind") == "country"
        and row.get("subcategory") is None
    ]
    if len(country_rows) != contract.expected_foreign_country_row_count:
        raise SchemaError("expected foreign country row count differs")
    aggregate_rows = [
        row
        for row in foreign_rows
        if row.get("year") == year
        and row.get("row_kind") == "subcategory"
        and row.get("nationality") == contract.aggregated_nationality_label
    ]
    if len(aggregate_rows) != contract.expected_aggregated_subcategory_row_count:
        raise SchemaError("expected aggregated subcategory row count differs")
    total_rows = _foreign_total_rows(foreign_rows, year=year, contract=contract)

    all_person_rows = _load_rows(
        catalog_paths[all_person_source_id],
        source_id=all_person_source_id,
        label="all-person numerator",
    )
    all_person_row = _one_row(
        all_person_rows,
        label="national all-person numerator",
        predicate=lambda row: (
            row.get("year") == year
            and row.get("geography_type") == "national"
            and row.get("geography") == "日本"
            and row.get("population_scope") == "all_persons"
            and row.get("offense_scope")
            == "criminal_code_excluding_traffic_negligence"
        ),
    )
    japanese_population_rows = _load_rows(
        catalog_paths[japanese_population_source_id],
        source_id=japanese_population_source_id,
        label="Japanese population",
    )
    reference_date = "%d-10-01" % year
    japanese_population_row = _one_row(
        japanese_population_rows,
        label="national Japanese population",
        predicate=lambda row: (
            row.get("year") == year
            and row.get("reference_date") == reference_date
            and row.get("population_scope") == "japanese_population"
            and row.get("geography_type") == "national"
            and row.get("geography") == "日本"
        ),
    )
    japanese_population = _require_positive_int(
        japanese_population_row.get("population"), "Japanese population"
    )
    population, foreign_period_end = _load_foreign_population_by_label(
        catalog_paths[foreign_population_source_id],
        source_id=foreign_population_source_id,
    )
    if date.fromisoformat(foreign_period_end).year != year:
        raise SchemaError("foreign denominator year differs from trend year")

    label_counts = Counter(
        _require_string(row.get("nationality"), "nationality") for row in country_rows
    )
    records = []
    for metric in contract.metrics:
        foreign_metric = FOREIGN_METRIC_FIELDS[metric]
        foreign_total = sum(
            _require_nonnegative_int(row.get(foreign_metric), foreign_metric)
            for row in total_rows
        )
        all_person_total = _require_nonnegative_int(
            all_person_row.get(metric), metric
        )
        japanese_numerator = all_person_total - foreign_total
        if japanese_numerator < 0:
            raise SchemaError(
                "Foreign clearances exceed all-person clearances for %d %s"
                % (year, metric)
            )
        records.append(
            _record(
                contract,
                metric=metric,
                entity_id="jp-nationality:japanese",
                published_label="日本",
                display_label="日本（残差による参考値）",
                source_order=0,
                is_japanese_reference=True,
                year=year,
                denominator_reference_date=reference_date,
                numerator_source_ids=[foreign_source_id, all_person_source_id],
                denominator_source_id=japanese_population_source_id,
                numerator_value=japanese_numerator,
                denominator_value=japanese_population,
                refusal_reason=None,
                crosswalk_status=None,
                targets_complete=True,
                canonical_component_ids=["jp-nationality:japanese"],
                canonical_component_labels=["日本"],
                derivation_method="residual_subtraction",
                derivation_formula="%s.%s - %s.%s"
                % (all_person_source_id, metric, foreign_source_id, foreign_metric),
                mismatch_flags=[
                    "all_persons_minus_all_foreign_scope_assumption",
                    "annual_flow_vs_point_in_time_stock",
                    "clearance_records_not_unique_risk_population",
                    "denominator_reference_dates_differ_across_rows",
                    "japanese_numerator_derived_by_residual_subtraction",
                    "japanese_population_rounded_to_nearest_1000",
                ],
            )
        )
        records.extend(
            _foreign_record(
                contract,
                metric=metric,
                year=year,
                source_id=foreign_source_id,
                denominator_source_id=foreign_population_source_id,
                denominator_reference_date=foreign_period_end,
                row=row,
                population=population,
                mapping_lookup=mapping_lookup,
                duplicate_labels=label_counts,
            )
            for row in country_rows
        )
        records.append(
            _aggregated_record(
                contract,
                metric=metric,
                year=year,
                source_id=foreign_source_id,
                denominator_source_id=foreign_population_source_id,
                denominator_reference_date=foreign_period_end,
                rows=aggregate_rows,
                population=population,
                mapping_lookup=mapping_lookup,
            )
        )
    return records


def _validate_series_grid(
    records: Sequence[NationalityTrendRecord],
    contract: NationalityTrendContract,
) -> None:
    signatures_by_year: Dict[int, set] = {}
    for year in contract.years:
        rows = [
            row for row in records if row.year == year and row.metric == contract.metrics[0]
        ]
        signatures_by_year[year] = {
            (
                row.entity_id,
                row.published_label,
                row.display_label,
                row.source_order,
                row.is_japanese_reference,
            )
            for row in rows
        }
        if len(signatures_by_year[year]) != len(rows):
            raise SchemaError("Duplicate nationality trend entity in %d" % year)
    if len({frozenset(value) for value in signatures_by_year.values()}) != 1:
        raise SchemaError("Nationality trend entity set differs across years")
    expected = {
        (year, metric, entity_id)
        for year in contract.years
        for metric in contract.metrics
        for entity_id, _, _, _, _ in signatures_by_year[contract.years[0]]
    }
    observed = {(row.year, row.metric, row.entity_id) for row in records}
    if observed != expected or len(observed) != len(records):
        raise SchemaError("Nationality trend year/metric/entity grid is incomplete")


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_atomic_json(path: Path, value: object) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".%s." % path.name, suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    finally:
        temporary_path = Path(temporary_name)
        if temporary_path.exists():
            temporary_path.unlink()


def generate_nationality_trend_report(
    *,
    catalog_path: Path,
    processed_root: Path,
    mapping_latest_path: Path,
    contract_path: Path,
    output_root: Path,
    generated_at: str,
) -> NationalityTrendReport:
    """Generate an immutable nationality-by-year trend table."""

    contract, pins = load_nationality_trend_contract(contract_path)
    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _contract_timestamp(generated_at) + "_nationality_trend"
    )
    if destination.exists():
        raise IntegrityError(
            "Timestamped nationality trend output already exists and was not overwritten: %s"
            % destination
        )
    catalog_rows = _read_catalog(catalog_path)
    catalog_paths = _catalog_paths(catalog_rows, processed_root=processed_root)
    normalized_hashes = {}
    for source_id, pinned_hash in pins.items():
        if source_id not in catalog_paths:
            raise SchemaError("Missing trend source in catalog: %s" % source_id)
        normalized_hashes[source_id] = _verify_processed_input(
            catalog_paths[source_id], source_id, pinned_hash
        )
    source_artifacts = _catalog_source_artifacts(
        catalog_rows, pins, normalized_hashes
    )
    mapping_lookup, mapping_summary, mapping_run_dir = _load_mapping_lookup(
        mapping_latest_path
    )
    records = []
    for year in contract.years:
        records.extend(
            _year_records(
                contract,
                year=year,
                catalog_paths=catalog_paths,
                mapping_lookup=mapping_lookup,
            )
        )
    _validate_series_grid(records, contract)
    records.sort(
        key=lambda row: (row.metric, row.source_order, row.display_label, row.year)
    )
    status_counter = Counter(row.calculation_status for row in records)
    status_counts = {
        status: status_counter.get(status, 0) for status in CALCULATION_STATUSES
    }
    warning_counts = Counter(
        warning for row in records for warning in row.small_number_warning_flags
    )
    mismatch_counts = Counter(
        mismatch for row in records for mismatch in row.mismatch_flags
    )
    refusal_counts = Counter(
        row.refusal_reason for row in records if row.refusal_reason is not None
    )

    staging = Path(tempfile.mkdtemp(prefix=".nationality-trend-", dir=destination_root))
    try:
        jsonl_path = staging / "nationality_trend_records.jsonl"
        csv_path = staging / "nationality_trend_records.csv"
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
        _write_json(
            summary_path,
            {
                "nationality_trend_schema_version": NATIONALITY_TREND_SCHEMA_VERSION,
                "generated_at": generated_at,
                "catalog_sha256": sha256_file(Path(catalog_path)),
                "contract_sha256": sha256_file(Path(contract_path)),
                "mapping_latest_sha256": sha256_file(Path(mapping_latest_path)),
                "mapping_run_relpath": mapping_run_dir.name,
                "mapping_record_count": mapping_summary.get("mapping_record_count"),
                "processed_input_pins": dict(sorted(pins.items())),
                "source_artifacts": source_artifacts,
                "years": list(contract.years),
                "metrics": list(contract.metrics),
                "entity_count": len(
                    {row.entity_id for row in records if row.metric == contract.metrics[0]}
                ),
                "record_count": len(records),
                "status_counts": status_counts,
                "refusal_reason_counts": dict(sorted(refusal_counts.items())),
                "mismatch_flag_counts": dict(sorted(mismatch_counts.items())),
                "small_number_warning_counts": dict(sorted(warning_counts.items())),
                "display_included_count": sum(row.display_included for row in records),
            },
        )
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "nationality_trend_records.jsonl"
    final_csv = destination / "nationality_trend_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    _write_atomic_json(
        latest_path,
        {
            "nationality_trend_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "nationality_trend_records_sha256": sha256_file(final_jsonl),
            "nationality_trend_records_csv_sha256": sha256_file(final_csv),
        },
    )
    return NationalityTrendReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        status_counts=status_counts,
    )
