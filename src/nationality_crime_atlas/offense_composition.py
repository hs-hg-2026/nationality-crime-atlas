"""Build a provenance-first offense composition by nationality."""

import csv
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .models import AllPersonOffenseGroupRecord, NationalityOffenseGroupRecord
from .npa_offenses import (
    TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS,
    parse_npa_all_person_offense_groups,
    parse_npa_nationality_offense_groups,
)
from .provenance import sha256_file


OFFENSE_COMPOSITION_SCHEMA_VERSION = 1
CONTRACT_SCHEMA_VERSION = 1
LATEST_SCHEMA_VERSION = 1
CALCULATION_STATUSES = ("calculated", "refused")
SUPPORTED_METRICS = ("cleared_cases", "cleared_persons")
INTERPRETATION_POLICY = "patterns_without_intrinsic_group_inference"


@dataclass(frozen=True)
class CategoryDefinition:
    """One mutually exclusive official top-level criminal-code category."""

    offense_id: str
    label_ja: str
    color: str
    display_order: int
    official_severity_role: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OffenseCompositionContract:
    """Reviewed source and display contract for the composition product."""

    composition_id: str
    label_ja: str
    label_en: str
    year: int
    foreign_source_id: str
    foreign_source_table: str
    all_person_source_id: str
    all_person_source_table: str
    expected_foreign_country_row_count: int
    expected_foreign_region_total_row_count: int
    aggregated_nationality_label: str
    expected_aggregated_subcategory_row_count: int
    expected_foreign_entity_count: int
    expected_total_entity_count: int
    category_definitions: Tuple[CategoryDefinition, ...]
    metrics: Tuple[str, ...]
    small_number_total_threshold: int
    clustering_distance: str
    clustering_log_base: int
    clustering_linkage: str
    clustering_input: str
    interpretation_policy: str
    ui_caveat: str


@dataclass(frozen=True)
class OffenseCompositionRecord:
    """One entity/category row with both published clearance measures."""

    offense_composition_schema_version: int
    composition_id: str
    label_ja: str
    label_en: str
    interpretation_policy: str
    ui_caveat: str
    year: int
    entity_id: str
    published_label: str
    display_label: str
    source_order: int
    entity_kind: str
    is_japanese_reference: bool
    offense_id: str
    offense_label: str
    category_display_order: int
    category_color: str
    official_severity_role: str
    cleared_cases: int
    cleared_persons: int
    criminal_code_cleared_cases_total: int
    criminal_code_cleared_persons_total: int
    cleared_cases_share: Optional[float]
    cleared_persons_share: Optional[float]
    cleared_cases_share_status: str
    cleared_persons_share_status: str
    calculation_status: str
    refusal_reason: Optional[str]
    derivation_method: str
    derivation_formula: str
    numerator_source_ids: Tuple[str, ...]
    source_components: Tuple[Mapping[str, object], ...]
    mismatch_flags: Tuple[str, ...]
    small_number_warning_flags: Tuple[str, ...]
    display_included: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OffenseCompositionReport:
    """Locations and counts for one immutable composition run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    entity_count: int
    status_counts: Mapping[str, int]


@dataclass(frozen=True)
class _SourceInput:
    source_id: str
    catalog_row: Mapping[str, object]
    raw_path: Path
    normalized_path: Path
    raw_sha256: str
    normalized_sha256: str


CSV_FIELDS = tuple(OffenseCompositionRecord.__dataclass_fields__)


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid %s JSON: %s" % (label, path)) from error
    if not isinstance(value, dict):
        raise SchemaError("%s JSON must contain an object" % label)
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


def _require_sha256(value: object, label: str) -> str:
    result = _require_string(value, label)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise SchemaError("%s must be a lowercase SHA-256 digest" % label)
    return result


def _string_tuple(value: object, label: str) -> Tuple[str, ...]:
    return tuple(_require_string(item, label) for item in _require_list(value, label))


def _contract_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise SchemaError("generated_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone offset")
    return parsed.strftime("%Y%m%d_%H%M%S")


def _load_contract(
    path: Path,
) -> Tuple[OffenseCompositionContract, Mapping[str, str], Mapping[str, str]]:
    data = _read_json_object(path, "offense composition contract")
    if data.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise SchemaError("Unsupported offense composition contract schema_version")
    raw_artifact_pins = _require_mapping(data.get("artifact_pins"), "artifact_pins")
    raw_processed_pins = _require_mapping(
        data.get("processed_input_pins"), "processed_input_pins"
    )
    artifact_pins = {
        _require_string(source_id, "artifact pin source_id"): _require_sha256(
            digest, "artifact_pins[%s]" % source_id
        )
        for source_id, digest in raw_artifact_pins.items()
    }
    processed_pins = {
        _require_string(source_id, "processed pin source_id"): _require_sha256(
            digest, "processed_input_pins[%s]" % source_id
        )
        for source_id, digest in raw_processed_pins.items()
    }
    item = _require_mapping(data.get("composition"), "composition")
    foreign_source_id = _require_string(
        item.get("foreign_source_id"), "foreign_source_id"
    )
    all_person_source_id = _require_string(
        item.get("all_person_source_id"), "all_person_source_id"
    )
    required_sources = {foreign_source_id, all_person_source_id}
    if set(artifact_pins) != required_sources:
        raise SchemaError("artifact_pins must exactly match composition sources")
    if set(processed_pins) != required_sources:
        raise SchemaError("processed_input_pins must exactly match composition sources")

    category_ids = _string_tuple(item.get("category_ids"), "category_ids")
    if category_ids != TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS:
        raise SchemaError("category_ids must be the six official top-level groups")
    definitions = []
    for index, raw_definition in enumerate(
        _require_list(item.get("category_definitions"), "category_definitions"),
        start=1,
    ):
        definition = _require_mapping(
            raw_definition, "category_definitions[%d]" % index
        )
        color = _require_string(definition.get("color"), "category color")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise SchemaError("category color must be a six-digit hex color")
        definitions.append(
            CategoryDefinition(
                offense_id=_require_string(
                    definition.get("offense_id"), "category offense_id"
                ),
                label_ja=_require_string(
                    definition.get("label_ja"), "category label_ja"
                ),
                color=color.lower(),
                display_order=_require_positive_int(
                    definition.get("display_order"), "category display_order"
                ),
                official_severity_role=_require_string(
                    definition.get("official_severity_role"),
                    "official_severity_role",
                ),
            )
        )
    definitions.sort(key=lambda definition: definition.display_order)
    if tuple(definition.offense_id for definition in definitions) != category_ids:
        raise SchemaError("category_definitions differ from category_ids")
    if tuple(definition.display_order for definition in definitions) != tuple(
        range(1, len(definitions) + 1)
    ):
        raise SchemaError("category display_order must be contiguous from 1")
    for definition in definitions:
        expected_role = (
            "official_high_severity_category"
            if definition.offense_id == "heinous"
            else "not_a_project_severity_classification"
        )
        if definition.official_severity_role != expected_role:
            raise SchemaError(
                "official_severity_role conflicts with the official category scope"
            )

    metrics = _string_tuple(item.get("metrics"), "metrics")
    if set(metrics) != set(SUPPORTED_METRICS) or len(metrics) != len(
        SUPPORTED_METRICS
    ):
        raise SchemaError("metrics must contain cleared_cases and cleared_persons")
    clustering = _require_mapping(item.get("clustering"), "clustering")
    distance = _require_string(clustering.get("distance"), "clustering distance")
    log_base = _require_int(clustering.get("log_base"), "clustering log_base")
    linkage = _require_string(clustering.get("linkage"), "clustering linkage")
    clustering_input = _require_string(
        clustering.get("input"), "clustering input"
    )
    if (distance, log_base, linkage, clustering_input) != (
        "jensen_shannon",
        2,
        "average",
        "within_entity_composition_share",
    ):
        raise SchemaError("Unsupported clustering definition")
    interpretation_policy = _require_string(
        item.get("interpretation_policy"), "interpretation_policy"
    )
    if interpretation_policy != INTERPRETATION_POLICY:
        raise SchemaError("Unsupported interpretation_policy")

    contract = OffenseCompositionContract(
        composition_id=_require_string(item.get("composition_id"), "composition_id"),
        label_ja=_require_string(item.get("label_ja"), "label_ja"),
        label_en=_require_string(item.get("label_en"), "label_en"),
        year=_require_int(item.get("year"), "year"),
        foreign_source_id=foreign_source_id,
        foreign_source_table=_require_string(
            item.get("foreign_source_table"), "foreign_source_table"
        ),
        all_person_source_id=all_person_source_id,
        all_person_source_table=_require_string(
            item.get("all_person_source_table"), "all_person_source_table"
        ),
        expected_foreign_country_row_count=_require_positive_int(
            item.get("expected_foreign_country_row_count"),
            "expected_foreign_country_row_count",
        ),
        expected_foreign_region_total_row_count=_require_nonnegative_int(
            item.get("expected_foreign_region_total_row_count"),
            "expected_foreign_region_total_row_count",
        ),
        aggregated_nationality_label=_require_string(
            item.get("aggregated_nationality_label"),
            "aggregated_nationality_label",
        ),
        expected_aggregated_subcategory_row_count=_require_positive_int(
            item.get("expected_aggregated_subcategory_row_count"),
            "expected_aggregated_subcategory_row_count",
        ),
        expected_foreign_entity_count=_require_positive_int(
            item.get("expected_foreign_entity_count"),
            "expected_foreign_entity_count",
        ),
        expected_total_entity_count=_require_positive_int(
            item.get("expected_total_entity_count"),
            "expected_total_entity_count",
        ),
        category_definitions=tuple(definitions),
        metrics=metrics,
        small_number_total_threshold=_require_positive_int(
            item.get("small_number_total_threshold"),
            "small_number_total_threshold",
        ),
        clustering_distance=distance,
        clustering_log_base=log_base,
        clustering_linkage=linkage,
        clustering_input=clustering_input,
        interpretation_policy=interpretation_policy,
        ui_caveat=_require_string(item.get("ui_caveat"), "ui_caveat"),
    )
    if contract.foreign_source_table != "130":
        raise SchemaError("foreign_source_table must be 130")
    if contract.all_person_source_table != "3":
        raise SchemaError("all_person_source_table must be 3")
    if contract.expected_foreign_entity_count != (
        contract.expected_foreign_country_row_count + 1
    ):
        raise SchemaError("expected_foreign_entity_count must include one aggregate")
    if contract.expected_total_entity_count != (
        contract.expected_foreign_entity_count + 1
    ):
        raise SchemaError("expected_total_entity_count must include Japan")
    return contract, artifact_pins, processed_pins


def _read_catalog(path: Path) -> List[Mapping[str, object]]:
    rows = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise SchemaError(
                        "Catalog row must be an object at line %d" % line_number
                    )
                if row.get("processing_status") != "validated":
                    raise SchemaError(
                        "Offense composition requires validated catalog inputs"
                    )
                rows.append(row)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid artifact catalog: %s" % path) from error
    if not rows:
        raise SchemaError("Artifact catalog is empty")
    return rows


def _safe_join(root: Path, value: object, label: str) -> Path:
    relative = Path(_require_string(value, label))
    if relative.is_absolute() or ".." in relative.parts:
        raise SchemaError("Unsafe %s: %s" % (label, relative))
    return Path(root) / relative


def _select_source_input(
    *,
    catalog_rows: Sequence[Mapping[str, object]],
    source_id: str,
    artifact_pin: str,
    processed_pin: str,
    raw_root: Path,
    processed_root: Path,
) -> _SourceInput:
    source_rows = [row for row in catalog_rows if row.get("source_id") == source_id]
    if not source_rows:
        raise SchemaError("Missing offense composition source: %s" % source_id)
    matching = [row for row in source_rows if row.get("sha256") == artifact_pin]
    if len(matching) != 1:
        raise IntegrityError(
            "Catalog artifact pin selected %d rows for %s" % (len(matching), source_id)
        )
    row = matching[0]
    raw_path = _safe_join(raw_root, row.get("raw_relpath"), "raw_relpath")
    if not raw_path.is_file():
        raise SchemaError("Raw offense input is missing: %s" % raw_path)
    observed_raw_hash = sha256_file(raw_path)
    if observed_raw_hash != artifact_pin:
        raise IntegrityError("Raw artifact differs from artifact pin for %s" % source_id)

    processed_dir = _safe_join(
        processed_root, row.get("processed_relpath"), "processed_relpath"
    )
    normalized_path = processed_dir / "normalized.jsonl"
    run_path = processed_dir / "run.json"
    if not normalized_path.is_file():
        raise SchemaError("Normalized offense input is missing: %s" % normalized_path)
    run = _read_json_object(run_path, "processed run")
    if run.get("source_id") != source_id:
        raise SchemaError("Processed run source_id differs for %s" % source_id)
    if run.get("quality_passed") is not True:
        raise SchemaError("Processed run did not pass quality for %s" % source_id)
    if run.get("raw_artifact_sha256") != observed_raw_hash:
        raise IntegrityError(
            "Processed run raw hash differs from artifact pin for %s" % source_id
        )
    observed_normalized_hash = sha256_file(normalized_path)
    if run.get("normalized_sha256") != observed_normalized_hash:
        raise IntegrityError(
            "Processed normalized input hash differs from run.json for %s" % source_id
        )
    if observed_normalized_hash != processed_pin:
        raise IntegrityError(
            "Processed normalized input hash differs from contract pin for %s"
            % source_id
        )
    return _SourceInput(
        source_id=source_id,
        catalog_row=row,
        raw_path=raw_path,
        normalized_path=normalized_path,
        raw_sha256=observed_raw_hash,
        normalized_sha256=observed_normalized_hash,
    )


def _source_artifact(source: _SourceInput) -> Mapping[str, object]:
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
    artifact = {}
    for field in fields:
        value = source.catalog_row.get(field)
        if value is None:
            raise SchemaError(
                "Catalog provenance field %s is missing for %s"
                % (field, source.source_id)
            )
        artifact[field] = value
    artifact["normalized_sha256"] = source.normalized_sha256
    return artifact


def _entity_key(
    record: NationalityOffenseGroupRecord,
) -> Tuple[object, ...]:
    return (
        record.year,
        record.row_kind,
        record.region,
        record.nationality,
        record.subcategory,
    )


def _group_foreign_records(
    records: Iterable[NationalityOffenseGroupRecord],
) -> Mapping[Tuple[object, ...], Mapping[str, NationalityOffenseGroupRecord]]:
    grouped: Dict[
        Tuple[object, ...], Dict[str, NationalityOffenseGroupRecord]
    ] = {}
    for record in records:
        by_offense = grouped.setdefault(_entity_key(record), {})
        if record.offense_id in by_offense:
            raise SchemaError("Duplicate offense group for source entity")
        by_offense[record.offense_id] = record
    return grouped


def _one_group(
    groups: Iterable[Mapping[str, NationalityOffenseGroupRecord]], label: str
) -> Mapping[str, NationalityOffenseGroupRecord]:
    items = list(groups)
    if len(items) != 1:
        raise SchemaError("Expected exactly one %s; found %d" % (label, len(items)))
    return items[0]


def _metric_total(
    group: Mapping[str, NationalityOffenseGroupRecord], metric: str
) -> int:
    return getattr(group["criminal_code"], metric)


def _component(record: object, metric: str, value: int) -> Mapping[str, object]:
    return {
        "source_id": getattr(record, "source_id"),
        "source_table": getattr(record, "source_table"),
        "source_sheet": getattr(record, "source_sheet"),
        "source_row": getattr(record, "source_row"),
        "metric": metric,
        "value": value,
    }


def _warning_flags(
    *, cases_total: int, persons_total: int, threshold: int
) -> Tuple[str, ...]:
    flags = []
    if cases_total < threshold:
        flags.append("sparse_entity_total_cleared_cases")
    if persons_total < threshold:
        flags.append("sparse_entity_total_cleared_persons")
    return tuple(flags)


def _make_entity_records(
    contract: OffenseCompositionContract,
    *,
    entity_id: str,
    published_label: str,
    display_label: str,
    source_order: int,
    entity_kind: str,
    is_japanese_reference: bool,
    offense_values: Mapping[str, Mapping[str, int]],
    totals: Mapping[str, int],
    derivation_method: str,
    derivation_formula: str,
    numerator_source_ids: Sequence[str],
    components: Mapping[str, Sequence[Mapping[str, object]]],
    mismatch_flags: Sequence[str],
) -> List[OffenseCompositionRecord]:
    all_metrics_unavailable = all(
        totals[metric] == 0 for metric in SUPPORTED_METRICS
    )
    refusal_reason = (
        "zero_criminal_code_totals_prevent_all_composition_shares"
        if all_metrics_unavailable
        else None
    )
    status = "refused" if all_metrics_unavailable else "calculated"
    warning_flags = _warning_flags(
        cases_total=totals["cleared_cases"],
        persons_total=totals["cleared_persons"],
        threshold=contract.small_number_total_threshold,
    )
    records = []
    for definition in contract.category_definitions:
        values = offense_values[definition.offense_id]
        records.append(
            OffenseCompositionRecord(
                offense_composition_schema_version=OFFENSE_COMPOSITION_SCHEMA_VERSION,
                composition_id=contract.composition_id,
                label_ja=contract.label_ja,
                label_en=contract.label_en,
                interpretation_policy=contract.interpretation_policy,
                ui_caveat=contract.ui_caveat,
                year=contract.year,
                entity_id=entity_id,
                published_label=published_label,
                display_label=display_label,
                source_order=source_order,
                entity_kind=entity_kind,
                is_japanese_reference=is_japanese_reference,
                offense_id=definition.offense_id,
                offense_label=definition.label_ja,
                category_display_order=definition.display_order,
                category_color=definition.color,
                official_severity_role=definition.official_severity_role,
                cleared_cases=values["cleared_cases"],
                cleared_persons=values["cleared_persons"],
                criminal_code_cleared_cases_total=totals["cleared_cases"],
                criminal_code_cleared_persons_total=totals["cleared_persons"],
                cleared_cases_share=(
                    values["cleared_cases"] / totals["cleared_cases"]
                    if totals["cleared_cases"]
                    else None
                ),
                cleared_persons_share=(
                    values["cleared_persons"] / totals["cleared_persons"]
                    if totals["cleared_persons"]
                    else None
                ),
                cleared_cases_share_status=(
                    "calculated"
                    if totals["cleared_cases"]
                    else "refused_zero_total"
                ),
                cleared_persons_share_status=(
                    "calculated"
                    if totals["cleared_persons"]
                    else "refused_zero_total"
                ),
                calculation_status=status,
                refusal_reason=refusal_reason,
                derivation_method=derivation_method,
                derivation_formula=derivation_formula,
                numerator_source_ids=tuple(numerator_source_ids),
                source_components=tuple(components[definition.offense_id]),
                mismatch_flags=tuple(mismatch_flags),
                small_number_warning_flags=warning_flags,
                display_included=True,
            )
        )
    return records


def _direct_foreign_records(
    contract: OffenseCompositionContract,
    group: Mapping[str, NationalityOffenseGroupRecord],
    *,
    display_label: Optional[str] = None,
) -> List[OffenseCompositionRecord]:
    reference = group["criminal_code"]
    if reference.nationality is None:
        raise SchemaError("Foreign country row has no nationality label")
    values = {
        offense_id: {
            metric: getattr(group[offense_id], metric)
            for metric in SUPPORTED_METRICS
        }
        for offense_id in TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS
    }
    components = {
        offense_id: [
            _component(group[offense_id], metric, values[offense_id][metric])
            for metric in SUPPORTED_METRICS
        ]
        for offense_id in TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS
    }
    totals = {metric: _metric_total(group, metric) for metric in SUPPORTED_METRICS}
    return _make_entity_records(
        contract,
        entity_id="npa:%s:row-%d"
        % (contract.foreign_source_id, reference.source_row),
        published_label=reference.nationality,
        display_label=display_label or reference.nationality,
        source_order=reference.source_row,
        entity_kind="published_nationality",
        is_japanese_reference=False,
        offense_values=values,
        totals=totals,
        derivation_method="published_row",
        derivation_formula="S08 published nationality row by official offense group",
        numerator_source_ids=[contract.foreign_source_id],
        components=components,
        mismatch_flags=[],
    )


def _aggregate_foreign_records(
    contract: OffenseCompositionContract,
    groups: Sequence[Mapping[str, NationalityOffenseGroupRecord]],
) -> List[OffenseCompositionRecord]:
    values = {}
    components = {}
    for offense_id in TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS:
        values[offense_id] = {
            metric: sum(getattr(group[offense_id], metric) for group in groups)
            for metric in SUPPORTED_METRICS
        }
        components[offense_id] = [
            _component(
                group[offense_id], metric, getattr(group[offense_id], metric)
            )
            for group in groups
            for metric in SUPPORTED_METRICS
        ]
    totals = {
        metric: sum(_metric_total(group, metric) for group in groups)
        for metric in SUPPORTED_METRICS
    }
    source_order = min(group["criminal_code"].source_row for group in groups)
    return _make_entity_records(
        contract,
        entity_id="npa:%s:aggregate:%s"
        % (contract.foreign_source_id, contract.aggregated_nationality_label),
        published_label=contract.aggregated_nationality_label,
        display_label=contract.aggregated_nationality_label,
        source_order=source_order,
        entity_kind="aggregated_published_subcategories",
        is_japanese_reference=False,
        offense_values=values,
        totals=totals,
        derivation_method="sum_published_subcategories",
        derivation_formula="sum(S08 published subcategory rows by offense group)",
        numerator_source_ids=[contract.foreign_source_id],
        components=components,
        mismatch_flags=["published_nationality_is_sum_of_subcategories"],
    )


def _japanese_records(
    contract: OffenseCompositionContract,
    *,
    all_person: Mapping[str, AllPersonOffenseGroupRecord],
    all_foreign: Mapping[str, NationalityOffenseGroupRecord],
) -> List[OffenseCompositionRecord]:
    values = {}
    components = {}
    for offense_id in TOP_LEVEL_CRIMINAL_CODE_GROUP_IDS:
        values[offense_id] = {}
        components[offense_id] = []
        for metric in SUPPORTED_METRICS:
            minuend = getattr(all_person[offense_id], metric)
            subtrahend = getattr(all_foreign[offense_id], metric)
            residual = minuend - subtrahend
            if residual < 0:
                raise SchemaError(
                    "Derived Japanese %s is negative for %s"
                    % (metric, offense_id)
                )
            values[offense_id][metric] = residual
            components[offense_id].extend(
                [
                    dict(
                        _component(all_person[offense_id], metric, minuend),
                        role="minuend",
                    ),
                    dict(
                        _component(all_foreign[offense_id], metric, subtrahend),
                        role="subtrahend",
                    ),
                ]
            )
    totals = {}
    for metric in SUPPORTED_METRICS:
        total = getattr(all_person["criminal_code"], metric) - getattr(
            all_foreign["criminal_code"], metric
        )
        if total < 0:
            raise SchemaError("Derived Japanese criminal-code total is negative")
        if sum(values[offense_id][metric] for offense_id in values) != total:
            raise SchemaError("Japanese residual groups do not sum to residual total")
        totals[metric] = total
    return _make_entity_records(
        contract,
        entity_id="jp-nationality:japanese",
        published_label="日本",
        display_label="日本（残差による参考値）",
        source_order=0,
        entity_kind="derived_japanese_residual",
        is_japanese_reference=True,
        offense_values=values,
        totals=totals,
        derivation_method="residual_subtraction",
        derivation_formula="S15 all persons - S08 all foreign by offense group",
        numerator_source_ids=[
            contract.all_person_source_id,
            contract.foreign_source_id,
        ],
        components=components,
        mismatch_flags=[
            "all_persons_minus_all_foreign_scope_assumption",
            "japanese_values_derived_by_residual_subtraction",
        ],
    )


def jensen_shannon_distance(
    left: Sequence[float], right: Sequence[float]
) -> float:
    """Return the base-2 Jensen-Shannon distance between two distributions."""

    if not left or len(left) != len(right):
        raise ValueError("Jensen-Shannon inputs must have the same positive length")
    if any(value < 0 or not math.isfinite(value) for value in tuple(left) + tuple(right)):
        raise ValueError("Jensen-Shannon inputs must be finite and non-negative")
    left_total = sum(left)
    right_total = sum(right)
    if left_total <= 0 or right_total <= 0:
        raise ValueError("Jensen-Shannon inputs must have positive sums")
    left_probability = tuple(value / left_total for value in left)
    right_probability = tuple(value / right_total for value in right)
    midpoint = tuple(
        (left_value + right_value) / 2
        for left_value, right_value in zip(left_probability, right_probability)
    )

    def divergence(distribution: Sequence[float]) -> float:
        return sum(
            value * math.log2(value / middle)
            for value, middle in zip(distribution, midpoint)
            if value > 0
        )

    squared = (divergence(left_probability) + divergence(right_probability)) / 2
    return math.sqrt(max(0.0, squared))


def _cluster_order(
    entity_vectors: Sequence[Tuple[str, int, Sequence[float]]]
) -> Tuple[str, ...]:
    if len(entity_vectors) <= 1:
        return tuple(item[0] for item in entity_vectors)
    ids = [item[0] for item in entity_vectors]
    source_orders = [item[1] for item in entity_vectors]
    distances = {
        (left, right): jensen_shannon_distance(
            entity_vectors[left][2], entity_vectors[right][2]
        )
        for left in range(len(entity_vectors))
        for right in range(left + 1, len(entity_vectors))
    }

    def distance(left: int, right: int) -> float:
        return distances[(min(left, right), max(left, right))]

    clusters: List[List[int]] = [[index] for index in range(len(entity_vectors))]
    while len(clusters) > 1:
        candidates = []
        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                left = clusters[left_index]
                right = clusters[right_index]
                average = sum(
                    distance(left_item, right_item)
                    for left_item in left
                    for right_item in right
                ) / (len(left) * len(right))
                signature = tuple(
                    sorted(
                        (source_orders[item], ids[item])
                        for item in left + right
                    )
                )
                candidates.append((average, signature, left_index, right_index))
        _, _, left_index, right_index = min(candidates)
        left = clusters[left_index]
        right = clusters[right_index]
        orientations = (
            left + right,
            list(reversed(left)) + right,
            left + list(reversed(right)),
            list(reversed(left)) + list(reversed(right)),
            right + left,
            list(reversed(right)) + left,
            right + list(reversed(left)),
            list(reversed(right)) + list(reversed(left)),
        )
        merged = min(
            orientations,
            key=lambda order: (
                sum(distance(first, second) for first, second in zip(order, order[1:])),
                tuple((source_orders[item], ids[item]) for item in order),
            ),
        )
        clusters.pop(right_index)
        clusters.pop(left_index)
        clusters.append(merged)
    return tuple(ids[index] for index in clusters[0])


def _clustering_summary(
    contract: OffenseCompositionContract,
    records: Sequence[OffenseCompositionRecord],
) -> Mapping[str, Mapping[str, object]]:
    by_entity: Dict[str, List[OffenseCompositionRecord]] = {}
    for record in records:
        by_entity.setdefault(record.entity_id, []).append(record)
    result = {}
    for metric in contract.metrics:
        share_field = "%s_share" % metric
        total_field = "criminal_code_%s_total" % metric
        vectors = []
        excluded = []
        for entity_records in by_entity.values():
            ordered = sorted(
                entity_records, key=lambda record: record.category_display_order
            )
            if getattr(ordered[0], total_field) == 0:
                excluded.append((ordered[0].source_order, ordered[0].entity_id))
                continue
            vector = [getattr(record, share_field) for record in ordered]
            vectors.append((ordered[0].entity_id, ordered[0].source_order, vector))
        clustered = list(_cluster_order(vectors))
        clustered.extend(entity_id for _, entity_id in sorted(excluded))
        result[metric] = {
            "distance": contract.clustering_distance,
            "log_base": contract.clustering_log_base,
            "linkage": contract.clustering_linkage,
            "input": contract.clustering_input,
            "order": clustered,
            "not_clustered_zero_total_entity_ids": [
                entity_id for _, entity_id in sorted(excluded)
            ],
        }
    return result


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
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
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".%s." % path.name, suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def generate_offense_composition_report(
    *,
    catalog_path: Path,
    raw_root: Path,
    processed_root: Path,
    contract_path: Path,
    output_root: Path,
    generated_at: str,
) -> OffenseCompositionReport:
    """Generate one immutable nationality/offense composition product."""

    contract, artifact_pins, processed_pins = _load_contract(contract_path)
    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _contract_timestamp(generated_at) + "_offense_composition"
    )
    if destination.exists():
        raise IntegrityError(
            "Timestamped offense composition output already exists and was not overwritten: %s"
            % destination
        )

    catalog_rows = _read_catalog(catalog_path)
    inputs = {
        source_id: _select_source_input(
            catalog_rows=catalog_rows,
            source_id=source_id,
            artifact_pin=artifact_pins[source_id],
            processed_pin=processed_pins[source_id],
            raw_root=raw_root,
            processed_root=processed_root,
        )
        for source_id in sorted(artifact_pins)
    }
    foreign_input = inputs[contract.foreign_source_id]
    all_person_input = inputs[contract.all_person_source_id]
    foreign_parsed = parse_npa_nationality_offense_groups(
        foreign_input.raw_path,
        table_id=contract.foreign_source_table,
        source_id=contract.foreign_source_id,
    )
    all_person_parsed = parse_npa_all_person_offense_groups(
        all_person_input.raw_path,
        source_id=contract.all_person_source_id,
    )
    if sha256_file(foreign_input.raw_path) != foreign_input.raw_sha256:
        raise IntegrityError("Foreign artifact changed while being parsed")
    if sha256_file(all_person_input.raw_path) != all_person_input.raw_sha256:
        raise IntegrityError("All-person artifact changed while being parsed")
    if {record.year for record in foreign_parsed} != {contract.year}:
        raise SchemaError("Foreign offense year differs from contract")
    if {record.year for record in all_person_parsed} != {contract.year}:
        raise SchemaError("All-person offense year differs from contract")

    grouped = _group_foreign_records(foreign_parsed)
    country_groups = [
        group
        for key, group in grouped.items()
        if key[1] == "country" and key[4] is None
    ]
    region_groups = [group for key, group in grouped.items() if key[1] == "region_total"]
    aggregate_groups = [
        group
        for key, group in grouped.items()
        if key[1] == "subcategory"
        and key[3] == contract.aggregated_nationality_label
    ]
    other_subcategories = [
        key
        for key in grouped
        if key[1] == "subcategory"
        and key[3] != contract.aggregated_nationality_label
    ]
    if other_subcategories:
        raise SchemaError("Unexpected unhandled nationality subcategory rows")
    if len(country_groups) != contract.expected_foreign_country_row_count:
        raise SchemaError("expected foreign country row count differs")
    if len(region_groups) != contract.expected_foreign_region_total_row_count:
        raise SchemaError("expected foreign region total row count differs")
    if len(aggregate_groups) != contract.expected_aggregated_subcategory_row_count:
        raise SchemaError("expected aggregated subcategory row count differs")
    all_foreign = _one_group(
        (
            group
            for key, group in grouped.items()
            if key[1] == "annual_total"
        ),
        "all-foreign annual total",
    )
    all_person = {record.offense_id: record for record in all_person_parsed}

    records = _japanese_records(
        contract, all_person=all_person, all_foreign=all_foreign
    )
    country_label_counts = Counter(
        group["criminal_code"].nationality for group in country_groups
    )
    for group in country_groups:
        reference = group["criminal_code"]
        display_label = reference.nationality
        if country_label_counts[reference.nationality] > 1:
            display_label = "%s（%s）" % (
                reference.nationality,
                reference.region or "地域外",
            )
        records.extend(
            _direct_foreign_records(
                contract, group, display_label=display_label
            )
        )
    records.extend(_aggregate_foreign_records(contract, aggregate_groups))
    records.sort(
        key=lambda record: (
            record.source_order,
            record.display_label,
            record.category_display_order,
        )
    )
    entity_count = len({record.entity_id for record in records})
    if entity_count != contract.expected_total_entity_count:
        raise SchemaError("expected total entity count differs")
    foreign_entity_count = len(
        {record.entity_id for record in records if not record.is_japanese_reference}
    )
    if foreign_entity_count != contract.expected_foreign_entity_count:
        raise SchemaError("expected foreign entity count differs")
    status_counter = Counter(record.calculation_status for record in records)
    status_counts = {
        status: status_counter.get(status, 0) for status in CALCULATION_STATUSES
    }
    warning_counts = Counter(
        flag for record in records for flag in record.small_number_warning_flags
    )
    mismatch_counts = Counter(
        flag for record in records for flag in record.mismatch_flags
    )

    staging = Path(
        tempfile.mkdtemp(prefix=".offense-composition-", dir=destination_root)
    )
    try:
        jsonl_path = staging / "offense_composition_records.jsonl"
        csv_path = staging / "offense_composition_records.csv"
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
        japanese_rows = [record for record in records if record.is_japanese_reference]
        summary = {
            "offense_composition_schema_version": OFFENSE_COMPOSITION_SCHEMA_VERSION,
            "generated_at": generated_at,
            "composition_id": contract.composition_id,
            "label_ja": contract.label_ja,
            "label_en": contract.label_en,
            "interpretation_policy": contract.interpretation_policy,
            "ui_caveat": contract.ui_caveat,
            "catalog_path": Path(catalog_path).as_posix(),
            "catalog_sha256": sha256_file(Path(catalog_path)),
            "contract_path": Path(contract_path).as_posix(),
            "contract_sha256": sha256_file(Path(contract_path)),
            "artifact_pins": dict(sorted(artifact_pins.items())),
            "processed_input_pins": dict(sorted(processed_pins.items())),
            "source_artifacts": {
                source_id: _source_artifact(source)
                for source_id, source in sorted(inputs.items())
            },
            "record_count": len(records),
            "entity_count": entity_count,
            "status_counts": status_counts,
            "small_number_warning_counts": dict(sorted(warning_counts.items())),
            "mismatch_flag_counts": dict(sorted(mismatch_counts.items())),
            "display_included_count": sum(record.display_included for record in records),
            "small_number_total_threshold": contract.small_number_total_threshold,
            "category_definitions": [
                definition.to_dict() for definition in contract.category_definitions
            ],
            "clustering": _clustering_summary(contract, records),
            "excluded_source_rows": {
                "region_total_count": len(region_groups),
                "reason": "official regional totals are not nationality entities",
            },
            "japanese_reconciliation": {
                metric: {
                    "all_person_criminal_code_total": getattr(
                        all_person["criminal_code"], metric
                    ),
                    "all_foreign_criminal_code_total": getattr(
                        all_foreign["criminal_code"], metric
                    ),
                    "derived_japanese_criminal_code_total": getattr(
                        japanese_rows[0], "criminal_code_%s_total" % metric
                    ),
                }
                for metric in SUPPORTED_METRICS
            },
        }
        _write_json(summary_path, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "offense_composition_records.jsonl"
    final_csv = destination / "offense_composition_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    _atomic_write_json(
        latest_path,
        {
            "offense_composition_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "offense_composition_records_sha256": sha256_file(final_jsonl),
            "offense_composition_records_csv_sha256": sha256_file(final_csv),
        },
    )
    return OffenseCompositionReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        entity_count=entity_count,
        status_counts=status_counts,
    )
