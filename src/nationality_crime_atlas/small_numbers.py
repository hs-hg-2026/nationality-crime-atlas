"""Reproducible small-number sensitivity audits for indicator outputs."""

import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .errors import IntegrityError, SchemaError
from .provenance import sha256_file


SENSITIVITY_SCHEMA_VERSION = 1
INDICATOR_RUN_SCHEMA_VERSION = 2
POLICY_STATUS = "sensitivity_only"
COMPARISON_OPERATOR = "strictly_less_than"
CALCULATION_STATUSES = ("calculated", "refused")
THRESHOLD_KINDS = ("denominator", "numerator")
CSV_FIELDS = [
    "small_number_sensitivity_schema_version",
    "threshold_kind",
    "threshold",
    "comparison_operator",
    "observation_id",
    "observed_value",
    "entity_dimension",
    "published_label",
    "geography_id",
    "geography_label",
    "years",
    "numerator_source_ids",
    "numerator_metrics",
    "denominator_source_ids",
    "canonical_component_ids",
    "canonical_component_labels",
    "observation_context",
    "affected_indicator_record_count",
    "indicator_ids",
    "crosswalk_policies",
]


@dataclass(frozen=True)
class SmallNumberSensitivityRecord:
    """One unique observation affected by one candidate threshold."""

    small_number_sensitivity_schema_version: int
    threshold_kind: str
    threshold: int
    comparison_operator: str
    observation_id: str
    observed_value: int
    entity_dimension: str
    published_label: Optional[str]
    geography_id: str
    geography_label: str
    years: Tuple[int, ...]
    numerator_source_ids: Tuple[str, ...]
    numerator_metrics: Tuple[str, ...]
    denominator_source_ids: Tuple[str, ...]
    canonical_component_ids: Tuple[str, ...]
    canonical_component_labels: Tuple[str, ...]
    observation_context: Mapping[str, object]
    affected_indicator_record_count: int
    indicator_ids: Tuple[str, ...]
    crosswalk_policies: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SmallNumberSensitivityReport:
    """Paths and counts for one immutable sensitivity audit."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid %s JSON: %s" % (label, path)) from error
    if not isinstance(value, dict):
        raise SchemaError("%s JSON must contain an object: %s" % (label, path))
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("%s must be a non-empty string" % label)
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError("%s must be an integer" % label)
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SchemaError("%s must be an object" % label)
    return value


def _require_string_sequence(value: object, label: str) -> Tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError("%s must be an array" % label)
    return tuple(_require_string(item, label) for item in value)


def _load_thresholds(value: object, label: str) -> Tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise SchemaError("%s must be a non-empty array" % label)
    thresholds = tuple(_require_int(item, label) for item in value)
    if any(item <= 0 for item in thresholds):
        raise SchemaError("%s must contain only positive values" % label)
    if any(left >= right for left, right in zip(thresholds, thresholds[1:])):
        raise SchemaError("%s must be strictly increasing" % label)
    return thresholds


def load_small_number_config(path: Path) -> Mapping[str, object]:
    """Load candidate thresholds without treating them as publication policy."""

    data = _read_json_object(path, "small-number sensitivity config")
    if data.get("schema_version") != SENSITIVITY_SCHEMA_VERSION:
        raise SchemaError("Unsupported small-number sensitivity schema_version")
    if data.get("policy_status") != POLICY_STATUS:
        raise SchemaError("policy_status must be %s" % POLICY_STATUS)
    if data.get("comparison_operator") != COMPARISON_OPERATOR:
        raise SchemaError("comparison_operator must be %s" % COMPARISON_OPERATOR)
    return {
        "schema_version": SENSITIVITY_SCHEMA_VERSION,
        "policy_status": POLICY_STATUS,
        "comparison_operator": COMPARISON_OPERATOR,
        "denominator_thresholds": _load_thresholds(
            data.get("denominator_thresholds"), "denominator_thresholds"
        ),
        "numerator_thresholds": _load_thresholds(
            data.get("numerator_thresholds"), "numerator_thresholds"
        ),
    }


def _safe_run_dir(latest_path: Path, latest: Mapping[str, object]) -> Path:
    relative = Path(_require_string(latest.get("run_relpath"), "run_relpath"))
    if relative.is_absolute() or ".." in relative.parts:
        raise SchemaError("Unsafe indicator run_relpath: %s" % relative)
    run_dir = Path(latest_path).parent / relative
    if not run_dir.is_dir():
        raise SchemaError("Indicator run directory is missing: %s" % run_dir)
    return run_dir


def _verify_hash(path: Path, expected: object, label: str) -> str:
    expected_hash = _require_string(expected, label)
    if not path.is_file():
        raise SchemaError("Required indicator artifact is missing: %s" % path)
    observed = sha256_file(path)
    if observed != expected_hash:
        raise IntegrityError("%s hash differs from indicator latest.json" % label)
    return observed


def _load_indicator_records(
    records_path: Path,
    summary: Mapping[str, object],
) -> Tuple[List[Mapping[str, object]], Mapping[str, int]]:
    rows = []
    counts = Counter()
    try:
        with Path(records_path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise SchemaError(
                        "Indicator record must be an object at line %d" % line_number
                    )
                if row.get("indicator_run_schema_version") != INDICATOR_RUN_SCHEMA_VERSION:
                    raise SchemaError("Unsupported indicator record schema version")
                status = _require_string(
                    row.get("calculation_status"), "calculation_status"
                )
                if status not in CALCULATION_STATUSES:
                    raise SchemaError("Unsupported calculation_status: %s" % status)
                counts[status] += 1
                rows.append(row)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid indicator records: %s" % records_path) from error

    expected_count = _require_int(
        summary.get("indicator_record_count"), "indicator_record_count"
    )
    if len(rows) != expected_count:
        raise IntegrityError("Indicator record count differs from summary.json")
    expected_status = _require_mapping(summary.get("status_counts"), "status_counts")
    for status in CALCULATION_STATUSES:
        if counts[status] != _require_int(expected_status.get(status), status):
            raise IntegrityError("Indicator status counts differ from summary.json")
    return rows, {status: counts[status] for status in CALCULATION_STATUSES}


def _json_key(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _observation_id(kind: str, key: Tuple[object, ...]) -> str:
    payload = _json_key([kind, *key]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validated_calculated_row(row: Mapping[str, object]) -> Mapping[str, object]:
    numerator_value = _require_int(row.get("numerator_value"), "numerator_value")
    denominator_value = _require_int(
        row.get("denominator_value"), "denominator_value"
    )
    if numerator_value < 0:
        raise SchemaError("numerator_value must be non-negative")
    if denominator_value <= 0:
        raise SchemaError("denominator_value must be positive")
    published_label = row.get("published_label")
    if published_label is not None:
        _require_string(published_label, "published_label")
    _require_string(row.get("indicator_id"), "indicator_id")
    _require_string(row.get("crosswalk_policy"), "crosswalk_policy")
    _require_string(row.get("entity_dimension"), "entity_dimension")
    _require_string(row.get("geography_id"), "geography_id")
    _require_string(row.get("geography_label"), "geography_label")
    _require_int(row.get("year"), "year")
    _require_string(row.get("numerator_source_id"), "numerator_source_id")
    _require_string(row.get("numerator_metric"), "numerator_metric")
    _require_mapping(row.get("numerator_context"), "numerator_context")
    _require_string(row.get("denominator_source_id"), "denominator_source_id")
    _require_string_sequence(
        row.get("canonical_component_ids"), "canonical_component_ids"
    )
    _require_string_sequence(
        row.get("canonical_component_labels"), "canonical_component_labels"
    )
    return row


def _new_group(
    *,
    kind: str,
    key: Tuple[object, ...],
    row: Mapping[str, object],
    observed_value: int,
    observation_context: Mapping[str, object],
    canonical_component_ids: Sequence[str],
    canonical_component_labels: Sequence[str],
) -> Dict[str, object]:
    return {
        "kind": kind,
        "key": key,
        "observation_id": _observation_id(kind, key),
        "observed_value": observed_value,
        "entity_dimension": row["entity_dimension"],
        "published_label": row.get("published_label"),
        "geography_id": row["geography_id"],
        "geography_label": row["geography_label"],
        "observation_context": dict(observation_context),
        "canonical_component_ids": set(canonical_component_ids),
        "canonical_component_labels": set(canonical_component_labels),
        "years": set(),
        "numerator_source_ids": set(),
        "numerator_metrics": set(),
        "denominator_source_ids": set(),
        "indicator_ids": set(),
        "crosswalk_policies": set(),
        "affected_indicator_record_count": 0,
    }


def _add_row_to_group(group: Dict[str, object], row: Mapping[str, object]) -> None:
    group["years"].add(row["year"])
    group["numerator_source_ids"].add(row["numerator_source_id"])
    group["numerator_metrics"].add(row["numerator_metric"])
    group["denominator_source_ids"].add(row["denominator_source_id"])
    group["indicator_ids"].add(row["indicator_id"])
    group["crosswalk_policies"].add(row["crosswalk_policy"])
    group["affected_indicator_record_count"] += 1


def _group_calculated_records(
    rows: Sequence[Mapping[str, object]],
) -> Mapping[str, Mapping[Tuple[object, ...], Dict[str, object]]]:
    groups: Dict[str, Dict[Tuple[object, ...], Dict[str, object]]] = {
        kind: {} for kind in THRESHOLD_KINDS
    }
    for raw_row in rows:
        if raw_row.get("calculation_status") != "calculated":
            continue
        row = _validated_calculated_row(raw_row)
        canonical_ids = _require_string_sequence(
            row.get("canonical_component_ids"), "canonical_component_ids"
        )
        canonical_labels = _require_string_sequence(
            row.get("canonical_component_labels"), "canonical_component_labels"
        )
        denominator_key = (
            row["denominator_source_id"],
            row["entity_dimension"],
            row["geography_id"],
            row.get("published_label"),
            canonical_ids,
            row["denominator_value"],
        )
        denominator_group = groups["denominator"].setdefault(
            denominator_key,
            _new_group(
                kind="denominator",
                key=denominator_key,
                row=row,
                observed_value=row["denominator_value"],
                observation_context={},
                canonical_component_ids=canonical_ids,
                canonical_component_labels=canonical_labels,
            ),
        )
        _add_row_to_group(denominator_group, row)

        numerator_context = _require_mapping(
            row.get("numerator_context"), "numerator_context"
        )
        numerator_key = (
            row["numerator_source_id"],
            row["numerator_metric"],
            row["year"],
            row["entity_dimension"],
            row["geography_id"],
            row.get("published_label"),
            _json_key(numerator_context),
            row["numerator_value"],
        )
        numerator_group = groups["numerator"].setdefault(
            numerator_key,
            _new_group(
                kind="numerator",
                key=numerator_key,
                row=row,
                observed_value=row["numerator_value"],
                observation_context=numerator_context,
                canonical_component_ids=(),
                canonical_component_labels=(),
            ),
        )
        _add_row_to_group(numerator_group, row)
    return groups


def _sensitivity_record(
    group: Mapping[str, object], threshold: int
) -> SmallNumberSensitivityRecord:
    return SmallNumberSensitivityRecord(
        small_number_sensitivity_schema_version=SENSITIVITY_SCHEMA_VERSION,
        threshold_kind=group["kind"],
        threshold=threshold,
        comparison_operator=COMPARISON_OPERATOR,
        observation_id=group["observation_id"],
        observed_value=group["observed_value"],
        entity_dimension=group["entity_dimension"],
        published_label=group["published_label"],
        geography_id=group["geography_id"],
        geography_label=group["geography_label"],
        years=tuple(sorted(group["years"])),
        numerator_source_ids=tuple(sorted(group["numerator_source_ids"])),
        numerator_metrics=tuple(sorted(group["numerator_metrics"])),
        denominator_source_ids=tuple(sorted(group["denominator_source_ids"])),
        canonical_component_ids=tuple(sorted(group["canonical_component_ids"])),
        canonical_component_labels=tuple(
            sorted(group["canonical_component_labels"])
        ),
        observation_context=group["observation_context"],
        affected_indicator_record_count=group[
            "affected_indicator_record_count"
        ],
        indicator_ids=tuple(sorted(group["indicator_ids"])),
        crosswalk_policies=tuple(sorted(group["crosswalk_policies"])),
    )


def _build_sensitivity_records(
    groups: Mapping[str, Mapping[Tuple[object, ...], Mapping[str, object]]],
    config: Mapping[str, object],
) -> Tuple[List[SmallNumberSensitivityRecord], Mapping[str, object]]:
    records = []
    summaries = {}
    for kind in THRESHOLD_KINDS:
        thresholds = config["%s_thresholds" % kind]
        kind_summaries = []
        ordered_groups = sorted(
            groups[kind].values(),
            key=lambda item: (
                item["observed_value"],
                item["geography_id"],
                item["published_label"] or "",
                item["observation_id"],
            ),
        )
        for threshold in thresholds:
            affected = [
                group
                for group in ordered_groups
                if group["observed_value"] < threshold
            ]
            kind_summaries.append(
                {
                    "threshold": threshold,
                    "affected_indicator_record_count": sum(
                        group["affected_indicator_record_count"]
                        for group in affected
                    ),
                    "unique_observation_count": len(affected),
                }
            )
            records.extend(
                _sensitivity_record(group, threshold) for group in affected
            )
        summaries[kind] = kind_summaries
    records.sort(
        key=lambda item: (
            item.threshold_kind,
            item.threshold,
            item.observed_value,
            item.observation_id,
        )
    )
    return records, summaries


def _generated_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise SchemaError("generated_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("generated_at must include a timezone")
    return parsed.strftime("%Y%m%d_%H%M%S")


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


def generate_small_number_sensitivity_report(
    *,
    indicator_latest_path: Path,
    config_path: Path,
    output_root: Path,
    generated_at: str,
) -> SmallNumberSensitivityReport:
    """Generate an immutable sensitivity matrix from a pinned indicator run."""

    config = load_small_number_config(config_path)
    latest = _read_json_object(indicator_latest_path, "indicator latest")
    if latest.get("indicator_run_schema_version") != INDICATOR_RUN_SCHEMA_VERSION:
        raise SchemaError("Unsupported indicator latest schema version")
    run_dir = _safe_run_dir(indicator_latest_path, latest)
    records_path = run_dir / "indicator_records.jsonl"
    csv_path = run_dir / "indicator_records.csv"
    summary_path = run_dir / "summary.json"
    records_hash = _verify_hash(
        records_path,
        latest.get("indicator_records_sha256"),
        "indicator_records_sha256",
    )
    csv_hash = _verify_hash(
        csv_path,
        latest.get("indicator_records_csv_sha256"),
        "indicator_records_csv_sha256",
    )
    summary_hash = _verify_hash(
        summary_path, latest.get("summary_sha256"), "summary_sha256"
    )
    indicator_summary = _read_json_object(summary_path, "indicator summary")
    if (
        indicator_summary.get("indicator_run_schema_version")
        != INDICATOR_RUN_SCHEMA_VERSION
    ):
        raise SchemaError("Unsupported indicator summary schema version")
    indicator_rows, status_counts = _load_indicator_records(
        records_path, indicator_summary
    )
    groups = _group_calculated_records(indicator_rows)
    sensitivity_records, threshold_summaries = _build_sensitivity_records(
        groups, config
    )

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _generated_timestamp(generated_at) + "_small_number_sensitivity"
    )
    if destination.exists():
        raise IntegrityError(
            "Timestamped sensitivity output already exists and was not overwritten: %s"
            % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".small-number-", dir=destination_root))
    try:
        output_jsonl = staging / "sensitivity_records.jsonl"
        output_csv = staging / "sensitivity_records.csv"
        output_summary = staging / "summary.json"
        output_input_manifest = staging / "indicator_input_manifest.json"
        _write_json(output_input_manifest, latest)
        with output_jsonl.open("w", encoding="utf-8") as handle:
            for record in sensitivity_records:
                handle.write(
                    json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for record in sensitivity_records:
                values = record.to_dict()
                writer.writerow(
                    {field: _csv_value(values[field]) for field in CSV_FIELDS}
                )
        summary = {
            "small_number_sensitivity_schema_version": SENSITIVITY_SCHEMA_VERSION,
            "analysis_kind": "small_number_threshold_sensitivity",
            "policy_status": POLICY_STATUS,
            "comparison_operator": COMPARISON_OPERATOR,
            "generated_at": generated_at,
            "config_path": Path(config_path).as_posix(),
            "config_sha256": sha256_file(Path(config_path)),
            "indicator_latest_path": Path(indicator_latest_path).as_posix(),
            "indicator_latest_sha256": sha256_file(Path(indicator_latest_path)),
            "indicator_input_manifest_relpath": output_input_manifest.name,
            "indicator_input_manifest_sha256": sha256_file(output_input_manifest),
            "indicator_run_relpath": run_dir.name,
            "indicator_summary_sha256": summary_hash,
            "indicator_records_sha256": records_hash,
            "indicator_records_csv_sha256": csv_hash,
            "indicator_record_count": len(indicator_rows),
            "calculated_indicator_record_count": status_counts["calculated"],
            "refused_indicator_record_count": status_counts["refused"],
            "threshold_summaries": threshold_summaries,
            "sensitivity_record_count": len(sensitivity_records),
            "deduplication_rules": {
                "denominator": (
                    "Same published denominator identity is counted once across "
                    "indicator policy and metric views."
                ),
                "numerator": (
                    "Same source/metric/year/entity/context observation is counted "
                    "once across crosswalk policy views."
                ),
            },
        }
        _write_json(output_summary, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "sensitivity_records.jsonl"
    final_csv = destination / "sensitivity_records.csv"
    final_summary = destination / "summary.json"
    final_input_manifest = destination / "indicator_input_manifest.json"
    latest_path = destination_root / "latest.json"
    latest_temp = destination_root / ".latest.json.tmp"
    _write_json(
        latest_temp,
        {
            "small_number_sensitivity_schema_version": SENSITIVITY_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "indicator_input_manifest_sha256": sha256_file(final_input_manifest),
            "sensitivity_records_sha256": sha256_file(final_jsonl),
            "sensitivity_records_csv_sha256": sha256_file(final_csv),
        },
    )
    latest_temp.replace(latest_path)
    return SmallNumberSensitivityReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(sensitivity_records),
    )
