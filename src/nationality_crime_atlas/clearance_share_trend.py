"""Build annual foreign-scope shares of nationwide criminal-code clearances."""

import csv
import json
import os
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .models import NationalClearanceAnnualRecord
from .npa_all_residents import parse_npa_all_person_annual_clearances
from .npa_nationality import parse_npa_nationality_annual_clearances
from .provenance import sha256_file


CLEARANCE_SHARE_TREND_SCHEMA_VERSION = 2
CONTRACT_SCHEMA_VERSION = 1
LATEST_SCHEMA_VERSION = 2
SUPPORTED_METRICS = ("cleared_cases", "cleared_persons")
SUPPORTED_FOREIGN_SCOPES = ("all_foreign", "visiting_foreign")
DERIVED_FOREIGN_SCOPE = "all_foreign_minus_visiting_foreign"
DERIVED_FOREIGN_SCOPE_LABEL_JA = "外国人全体−来日外国人（差分）"
INTERPRETATION_POLICY = "share_of_clearances_not_population_risk"


@dataclass(frozen=True)
class ForeignSourceDefinition:
    """One reviewed NPA foreign-scope numerator series."""

    source_id: str
    source_table: str
    foreign_scope: str
    label_ja: str


@dataclass(frozen=True)
class ClearanceShareTrendContract:
    """Reviewed sources and display semantics for the annual share product."""

    trend_id: str
    label_ja: str
    label_en: str
    years: Tuple[int, ...]
    all_person_source_id: str
    foreign_sources: Tuple[ForeignSourceDefinition, ...]
    metrics: Tuple[str, ...]
    display_multiplier: int
    display_unit_label_ja: str
    interpretation_policy: str
    ui_caveat: str


@dataclass(frozen=True)
class ClearanceShareTrendRecord:
    """One annual numerator share with both component counts retained."""

    national_clearance_share_schema_version: int
    trend_id: str
    label_ja: str
    label_en: str
    interpretation_policy: str
    ui_caveat: str
    year: int
    foreign_scope: str
    foreign_scope_label_ja: str
    metric: str
    metric_label_ja: str
    numerator_value: int
    denominator_value: int
    quotient: float
    display_multiplier: int
    display_unit_label_ja: str
    display_value: float
    calculation_status: str
    refusal_reason: Optional[str]
    numerator_source_id: str
    numerator_source_ids: Tuple[str, ...]
    denominator_source_id: str
    derivation_method: str
    derivation_formula: str
    source_components: Tuple[Mapping[str, object], ...]
    mismatch_flags: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ClearanceShareTrendReport:
    """Locations and counts for one immutable annual share run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    year_count: int


@dataclass(frozen=True)
class _SourceInput:
    source_id: str
    catalog_row: Mapping[str, object]
    raw_path: Path
    raw_sha256: str


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


def _require_sha256(value: object, label: str) -> str:
    result = _require_string(value, label)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise SchemaError("%s must be a lowercase SHA-256 digest" % label)
    return result


def _load_contract(
    path: Path,
) -> Tuple[ClearanceShareTrendContract, Mapping[str, str]]:
    data = _read_json_object(path, "clearance share trend contract")
    if data.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise SchemaError("Unsupported clearance share trend contract schema_version")
    raw_pins = _require_mapping(data.get("artifact_pins"), "artifact_pins")
    pins = {
        _require_string(source_id, "artifact pin source_id"): _require_sha256(
            digest, "artifact_pins[%s]" % source_id
        )
        for source_id, digest in raw_pins.items()
    }
    item = _require_mapping(data.get("trend"), "trend")
    years = tuple(_require_int(year, "years") for year in _require_list(item.get("years"), "years"))
    if not years or tuple(sorted(set(years))) != years:
        raise SchemaError("years must be a non-empty ascending unique array")
    all_person_source_id = _require_string(
        item.get("all_person_source_id"), "all_person_source_id"
    )
    foreign_sources = []
    for raw_source in _require_list(item.get("foreign_sources"), "foreign_sources"):
        source = _require_mapping(raw_source, "foreign source")
        definition = ForeignSourceDefinition(
            source_id=_require_string(source.get("source_id"), "foreign source_id"),
            source_table=_require_string(
                source.get("source_table"), "foreign source_table"
            ),
            foreign_scope=_require_string(
                source.get("foreign_scope"), "foreign_scope"
            ),
            label_ja=_require_string(source.get("label_ja"), "foreign label_ja"),
        )
        foreign_sources.append(definition)
    if tuple(source.foreign_scope for source in foreign_sources) != SUPPORTED_FOREIGN_SCOPES:
        raise SchemaError("foreign_sources must contain all_foreign then visiting_foreign")
    expected_tables = {"all_foreign": "130", "visiting_foreign": "131"}
    if any(
        source.source_table != expected_tables[source.foreign_scope]
        for source in foreign_sources
    ):
        raise SchemaError("foreign source_table does not match its reviewed scope")
    metrics = tuple(
        _require_string(metric, "metrics")
        for metric in _require_list(item.get("metrics"), "metrics")
    )
    if metrics != SUPPORTED_METRICS:
        raise SchemaError("metrics must contain cleared_cases then cleared_persons")
    interpretation_policy = _require_string(
        item.get("interpretation_policy"), "interpretation_policy"
    )
    if interpretation_policy != INTERPRETATION_POLICY:
        raise SchemaError("Unsupported interpretation_policy")
    display_multiplier = _require_int(
        item.get("display_multiplier"), "display_multiplier"
    )
    if display_multiplier != 100:
        raise SchemaError("display_multiplier must be 100 for percent")
    required_sources = {all_person_source_id} | {
        source.source_id for source in foreign_sources
    }
    if set(pins) != required_sources:
        raise SchemaError("artifact_pins must exactly match trend sources")
    return (
        ClearanceShareTrendContract(
            trend_id=_require_string(item.get("trend_id"), "trend_id"),
            label_ja=_require_string(item.get("label_ja"), "label_ja"),
            label_en=_require_string(item.get("label_en"), "label_en"),
            years=years,
            all_person_source_id=all_person_source_id,
            foreign_sources=tuple(foreign_sources),
            metrics=metrics,
            display_multiplier=display_multiplier,
            display_unit_label_ja=_require_string(
                item.get("display_unit_label_ja"), "display_unit_label_ja"
            ),
            interpretation_policy=interpretation_policy,
            ui_caveat=_require_string(item.get("ui_caveat"), "ui_caveat"),
        ),
        pins,
    )


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
    raw_root: Path,
) -> _SourceInput:
    source_rows = [row for row in catalog_rows if row.get("source_id") == source_id]
    matching = [row for row in source_rows if row.get("sha256") == artifact_pin]
    if len(matching) != 1:
        raise IntegrityError(
            "Catalog artifact pin selected %d rows for %s"
            % (len(matching), source_id)
        )
    row = matching[0]
    if row.get("processing_status") != "validated":
        raise SchemaError("Clearance share trend requires validated source %s" % source_id)
    raw_path = _safe_join(raw_root, row.get("raw_relpath"), "raw_relpath")
    if not raw_path.is_file():
        raise SchemaError("Raw clearance input is missing: %s" % raw_path)
    observed_hash = sha256_file(raw_path)
    if observed_hash != artifact_pin:
        raise IntegrityError("Raw artifact differs from artifact pin for %s" % source_id)
    return _SourceInput(
        source_id=source_id,
        catalog_row=row,
        raw_path=raw_path,
        raw_sha256=observed_hash,
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
    return artifact


def _by_year(
    records: Sequence[NationalClearanceAnnualRecord],
    *,
    expected_years: Sequence[int],
    source_id: str,
) -> Mapping[int, NationalClearanceAnnualRecord]:
    indexed = {record.year: record for record in records}
    if len(indexed) != len(records):
        raise SchemaError("Duplicate annual clearance row for %s" % source_id)
    if tuple(sorted(indexed)) != tuple(expected_years):
        raise SchemaError(
            "Annual years differ for %s: expected %r observed %r"
            % (source_id, tuple(expected_years), tuple(sorted(indexed)))
        )
    return indexed


def _component(record: NationalClearanceAnnualRecord, metric: str) -> Mapping[str, object]:
    return {
        "source_id": record.source_id,
        "source_table": record.source_table,
        "source_sheet": record.source_sheet,
        "source_row": record.source_row,
        "source_column": (
            record.source_cases_column
            if metric == "cleared_cases"
            else record.source_persons_column
        ),
        "metric": metric,
        "value": getattr(record, metric),
    }


def _records(
    contract: ClearanceShareTrendContract,
    *,
    all_person: Mapping[int, NationalClearanceAnnualRecord],
    foreign: Mapping[str, Mapping[int, NationalClearanceAnnualRecord]],
) -> List[ClearanceShareTrendRecord]:
    result = []
    metric_labels = {"cleared_cases": "検挙件数", "cleared_persons": "検挙人員"}
    common_flags = (
        "denominator_includes_japanese_and_others",
        "share_of_clearance_counts_not_population_rate",
    )
    for year in contract.years:
        denominator_record = all_person[year]
        for source in contract.foreign_sources:
            numerator_record = foreign[source.foreign_scope][year]
            for metric in contract.metrics:
                numerator = getattr(numerator_record, metric)
                denominator = getattr(denominator_record, metric)
                if denominator <= 0:
                    raise SchemaError(
                        "All-person denominator must be positive for %d %s"
                        % (year, metric)
                    )
                if numerator > denominator:
                    raise SchemaError(
                        "Foreign numerator exceeds all-person denominator for %d %s %s"
                        % (year, source.foreign_scope, metric)
                    )
                quotient = numerator / denominator
                flags = list(common_flags)
                if source.foreign_scope == "visiting_foreign":
                    flags.append("visiting_foreign_includes_nonresidents")
                else:
                    flags.append("all_foreign_scope_not_resident_foreigner_population")
                result.append(
                    ClearanceShareTrendRecord(
                        national_clearance_share_schema_version=CLEARANCE_SHARE_TREND_SCHEMA_VERSION,
                        trend_id=contract.trend_id,
                        label_ja=contract.label_ja,
                        label_en=contract.label_en,
                        interpretation_policy=contract.interpretation_policy,
                        ui_caveat=contract.ui_caveat,
                        year=year,
                        foreign_scope=source.foreign_scope,
                        foreign_scope_label_ja=source.label_ja,
                        metric=metric,
                        metric_label_ja=metric_labels[metric],
                        numerator_value=numerator,
                        denominator_value=denominator,
                        quotient=quotient,
                        display_multiplier=contract.display_multiplier,
                        display_unit_label_ja=contract.display_unit_label_ja,
                        display_value=quotient * contract.display_multiplier,
                        calculation_status="calculated",
                        refusal_reason=None,
                        numerator_source_id=numerator_record.source_id,
                        numerator_source_ids=(numerator_record.source_id,),
                        denominator_source_id=denominator_record.source_id,
                        derivation_method="direct_published_counts_division",
                        derivation_formula=(
                            "%s.%s / %s.%s"
                            % (
                                numerator_record.source_id,
                                metric,
                                denominator_record.source_id,
                                metric,
                            )
                        ),
                        source_components=(
                            dict(_component(numerator_record, metric), role="numerator"),
                            dict(
                                _component(denominator_record, metric),
                                role="denominator",
                            ),
                        ),
                        mismatch_flags=tuple(sorted(flags)),
                    )
                )

        all_foreign_record = foreign["all_foreign"][year]
        visiting_foreign_record = foreign["visiting_foreign"][year]
        for metric in contract.metrics:
            all_foreign_value = getattr(all_foreign_record, metric)
            visiting_foreign_value = getattr(visiting_foreign_record, metric)
            if visiting_foreign_value > all_foreign_value:
                raise SchemaError(
                    "Visiting-foreign clearances exceed all-foreign clearances "
                    "for %d %s" % (year, metric)
                )
            numerator = all_foreign_value - visiting_foreign_value
            denominator = getattr(denominator_record, metric)
            quotient = numerator / denominator
            result.append(
                ClearanceShareTrendRecord(
                    national_clearance_share_schema_version=CLEARANCE_SHARE_TREND_SCHEMA_VERSION,
                    trend_id=contract.trend_id,
                    label_ja=contract.label_ja,
                    label_en=contract.label_en,
                    interpretation_policy=contract.interpretation_policy,
                    ui_caveat=contract.ui_caveat,
                    year=year,
                    foreign_scope=DERIVED_FOREIGN_SCOPE,
                    foreign_scope_label_ja=DERIVED_FOREIGN_SCOPE_LABEL_JA,
                    metric=metric,
                    metric_label_ja=metric_labels[metric],
                    numerator_value=numerator,
                    denominator_value=denominator,
                    quotient=quotient,
                    display_multiplier=contract.display_multiplier,
                    display_unit_label_ja=contract.display_unit_label_ja,
                    display_value=quotient * contract.display_multiplier,
                    calculation_status="calculated",
                    refusal_reason=None,
                    numerator_source_id=all_foreign_record.source_id,
                    numerator_source_ids=(
                        all_foreign_record.source_id,
                        visiting_foreign_record.source_id,
                    ),
                    denominator_source_id=denominator_record.source_id,
                    derivation_method=(
                        "arithmetic_residual_all_foreign_minus_visiting_foreign"
                    ),
                    derivation_formula=(
                        "(%s.%s - %s.%s) / %s.%s"
                        % (
                            all_foreign_record.source_id,
                            metric,
                            visiting_foreign_record.source_id,
                            metric,
                            denominator_record.source_id,
                            metric,
                        )
                    ),
                    source_components=(
                        dict(
                            _component(all_foreign_record, metric),
                            role="numerator_minuend",
                        ),
                        dict(
                            _component(visiting_foreign_record, metric),
                            role="numerator_subtrahend",
                        ),
                        dict(
                            _component(denominator_record, metric),
                            role="denominator",
                        ),
                    ),
                    mismatch_flags=tuple(
                        sorted(
                            (*common_flags,
                             "arithmetic_residual_not_directly_published",
                             "residual_includes_settled_residents_us_forces_and_unknown_status",
                             "residual_not_equivalent_to_usual_residents")
                        )
                    ),
                )
            )
    return result


def _contract_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise SchemaError("generated_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone offset")
    return parsed.strftime("%Y%m%d_%H%M%S")


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
        prefix=".%s." % path.name,
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def generate_clearance_share_trend(
    *,
    catalog_path: Path,
    raw_root: Path,
    contract_path: Path,
    output_root: Path,
    generated_at: str,
) -> ClearanceShareTrendReport:
    """Generate one immutable annual clearance-share dataset."""

    contract, artifact_pins = _load_contract(contract_path)
    catalog_rows = _read_catalog(catalog_path)
    inputs = {
        source_id: _select_source_input(
            catalog_rows=catalog_rows,
            source_id=source_id,
            artifact_pin=artifact_pin,
            raw_root=raw_root,
        )
        for source_id, artifact_pin in artifact_pins.items()
    }
    all_person = _by_year(
        parse_npa_all_person_annual_clearances(
            inputs[contract.all_person_source_id].raw_path,
            source_id=contract.all_person_source_id,
        ),
        expected_years=contract.years,
        source_id=contract.all_person_source_id,
    )
    foreign = {}
    for source in contract.foreign_sources:
        foreign[source.foreign_scope] = _by_year(
            parse_npa_nationality_annual_clearances(
                inputs[source.source_id].raw_path,
                table_id=source.source_table,
                source_id=source.source_id,
            ),
            expected_years=contract.years,
            source_id=source.source_id,
        )
    records = _records(contract, all_person=all_person, foreign=foreign)

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _contract_timestamp(generated_at) + "_clearance_share_trend"
    )
    if destination.exists():
        raise IntegrityError(
            "Timestamped clearance share trend already exists and was not overwritten: %s"
            % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".clearance-share-", dir=destination_root))
    try:
        jsonl_path = staging / "clearance_share_records.jsonl"
        csv_path = staging / "clearance_share_records.csv"
        summary_path = staging / "summary.json"
        dictionaries = [record.to_dict() for record in records]
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in dictionaries:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = tuple(dictionaries[0])
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in dictionaries:
                writer.writerow({key: _csv_value(value) for key, value in row.items()})
        _write_json(
            summary_path,
            {
                "national_clearance_share_schema_version": CLEARANCE_SHARE_TREND_SCHEMA_VERSION,
                "generated_at": generated_at,
                "trend_id": contract.trend_id,
                "record_count": len(records),
                "year_count": len(contract.years),
                "years": list(contract.years),
                "scope_counts": dict(
                    sorted(Counter(record.foreign_scope for record in records).items())
                ),
                "metric_counts": dict(
                    sorted(Counter(record.metric for record in records).items())
                ),
                "status_counts": {"calculated": len(records), "refused": 0},
                "artifact_pins": dict(sorted(artifact_pins.items())),
                "source_artifacts": {
                    source_id: _source_artifact(source)
                    for source_id, source in sorted(inputs.items())
                },
                "clearance_share_records_sha256": sha256_file(jsonl_path),
                "clearance_share_records_csv_sha256": sha256_file(csv_path),
            },
        )
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "clearance_share_records.jsonl"
    final_csv = destination / "clearance_share_records.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    _atomic_write_json(
        latest_path,
        {
            "national_clearance_share_schema_version": LATEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "clearance_share_records_sha256": sha256_file(final_jsonl),
            "clearance_share_records_csv_sha256": sha256_file(final_csv),
        },
    )
    return ClearanceShareTrendReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(records),
        year_count=len(contract.years),
    )
