"""Canonical label mapping with explicit matched, ambiguous, and unmatched states."""

import csv
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .errors import MappingConflictError, SchemaError
from .provenance import sha256_file


MAPPING_SCHEMA_VERSION = 1
MATCH_STATUSES = ("matched", "ambiguous", "unmatched")
CSV_FIELDS = [
    "mapping_schema_version",
    "dimension",
    "source_id",
    "source_entity_kind",
    "source_label",
    "source_code",
    "source_context",
    "match_status",
    "match_method",
    "canonical_ids",
    "canonical_labels",
    "targets_complete",
    "reason",
    "mapping_scope",
]


@dataclass(frozen=True)
class CanonicalReference:
    """Canonical ISA nationality and prefecture code-label indexes."""

    nationality_by_code: Mapping[str, str]
    nationality_codes_by_label: Mapping[str, Tuple[str, ...]]
    prefecture_by_code: Mapping[str, str]
    prefecture_codes_by_label: Mapping[str, Tuple[str, ...]]


@dataclass(frozen=True)
class DimensionMapping:
    """One source dimension label and its explicit canonical mapping state."""

    mapping_schema_version: int
    dimension: str
    source_id: str
    source_entity_kind: str
    source_label: str
    source_code: Optional[str]
    source_context: Mapping[str, object]
    match_status: str
    match_method: str
    canonical_ids: Tuple[str, ...]
    canonical_labels: Tuple[str, ...]
    targets_complete: bool
    reason: str
    mapping_scope: str

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-ready representation without losing source context."""

        return asdict(self)


@dataclass(frozen=True)
class DimensionMappingReport:
    """Paths and counts for one immutable mapping audit run."""

    output_dir: Path
    jsonl_path: Path
    csv_path: Path
    summary_path: Path
    latest_path: Path
    record_count: int
    status_counts: Mapping[str, int]


def _read_json_object(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid JSON object: %s" % path) from error
    if not isinstance(value, dict):
        raise SchemaError("JSON document must contain an object: %s" % path)
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SchemaError("%s must be an object" % label)
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("%s must be a non-empty string" % label)
    return value


def load_dimension_mapping_config(path: Path) -> Mapping[str, object]:
    """Load and validate the authored crosswalk rules."""

    config = _read_json_object(path)
    if config.get("schema_version") != MAPPING_SCHEMA_VERSION:
        raise SchemaError("Unsupported dimension mapping schema_version")
    _require_nonempty_string(config.get("mapping_scope"), "mapping_scope")
    nationality = _require_mapping(config.get("nationality"), "nationality")
    geography = _require_mapping(config.get("geography"), "geography")
    for field in ("aliases", "composites", "unmatched", "region_code_prefixes"):
        _require_mapping(nationality.get(field), "nationality.%s" % field)
    for field in ("national", "non_equivalent_types"):
        _require_mapping(geography.get(field), "geography.%s" % field)
    return config


def _add_code_label(
    by_code: Dict[str, str],
    *,
    code: object,
    label: object,
    dimension: str,
) -> None:
    code_value = _require_nonempty_string(code, "%s code" % dimension)
    label_value = _require_nonempty_string(label, "%s label" % dimension)
    existing = by_code.get(code_value)
    if existing is not None and existing != label_value:
        raise SchemaError(
            "%s code %s changed label from %r to %r"
            % (dimension, code_value, existing, label_value)
        )
    by_code[code_value] = label_value


def _invert_labels(by_code: Mapping[str, str]) -> Mapping[str, Tuple[str, ...]]:
    values: Dict[str, List[str]] = defaultdict(list)
    for code, label in by_code.items():
        values[label].append(code)
    return {label: tuple(sorted(codes)) for label, codes in values.items()}


def build_canonical_reference(
    population_records: Iterable[Mapping[str, object]],
) -> CanonicalReference:
    """Build a union reference and reject code-label drift across editions."""

    nationality_by_code: Dict[str, str] = {}
    prefecture_by_code: Dict[str, str] = {}
    record_count = 0
    for record in population_records:
        record_count += 1
        _add_code_label(
            nationality_by_code,
            code=record.get("nationality_code"),
            label=record.get("nationality"),
            dimension="nationality",
        )
        _add_code_label(
            prefecture_by_code,
            code=record.get("prefecture_code"),
            label=record.get("prefecture"),
            dimension="prefecture",
        )
    if record_count == 0:
        raise SchemaError("No population reference records were provided")
    return CanonicalReference(
        nationality_by_code=dict(sorted(nationality_by_code.items())),
        nationality_codes_by_label=_invert_labels(nationality_by_code),
        prefecture_by_code=dict(sorted(prefecture_by_code.items())),
        prefecture_codes_by_label=_invert_labels(prefecture_by_code),
    )


def _nationality_id(code: str) -> str:
    return "isa-nationality:%s" % code


def _prefecture_id(code: str) -> str:
    return "jp-prefecture:%s" % code


def _mapping(
    *,
    dimension: str,
    source_id: object,
    source_entity_kind: object,
    source_label: object,
    source_code: Optional[object],
    source_context: Mapping[str, object],
    match_status: str,
    match_method: str,
    canonical_ids: Sequence[str],
    canonical_labels: Sequence[str],
    targets_complete: bool,
    reason: str,
    config: Mapping[str, object],
) -> DimensionMapping:
    if match_status not in MATCH_STATUSES:
        raise SchemaError("Invalid match status: %s" % match_status)
    return DimensionMapping(
        mapping_schema_version=MAPPING_SCHEMA_VERSION,
        dimension=dimension,
        source_id=_require_nonempty_string(source_id, "source_id"),
        source_entity_kind=_require_nonempty_string(
            source_entity_kind, "source_entity_kind"
        ),
        source_label=_require_nonempty_string(source_label, "source_label"),
        source_code=str(source_code) if source_code is not None else None,
        source_context=dict(source_context),
        match_status=match_status,
        match_method=match_method,
        canonical_ids=tuple(canonical_ids),
        canonical_labels=tuple(canonical_labels),
        targets_complete=targets_complete,
        reason=reason,
        mapping_scope=str(config["mapping_scope"]),
    )


def _resolve_nationality_labels(
    labels: object,
    reference: CanonicalReference,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if not isinstance(labels, list) or not labels:
        raise SchemaError("target_labels must be a non-empty array")
    pairs: List[Tuple[str, str]] = []
    for label in labels:
        label_value = _require_nonempty_string(label, "target label")
        codes = reference.nationality_codes_by_label.get(label_value, ())
        if not codes:
            raise SchemaError("Target nationality label is absent: %s" % label_value)
        pairs.extend((_nationality_id(code), label_value) for code in codes)
    unique = sorted(set(pairs))
    return tuple(item[0] for item in unique), tuple(item[1] for item in unique)


def _reviewed_rule(
    rules: Mapping[str, object],
    *,
    source_label: str,
    source_id: str,
    rule_kind: str,
) -> Optional[Mapping[str, object]]:
    """Return a source-scoped rule or stop until a new edition is reviewed."""

    if source_label not in rules:
        return None
    rule = _require_mapping(rules[source_label], "%s rule" % rule_kind)
    source_ids = rule.get("source_ids")
    if not isinstance(source_ids, list) or not source_ids:
        raise SchemaError("%s rule source_ids must be a non-empty array" % rule_kind)
    reviewed_ids = tuple(
        _require_nonempty_string(value, "%s source_id" % rule_kind)
        for value in source_ids
    )
    if source_id not in reviewed_ids:
        raise SchemaError(
            "%s rule for %s is not reviewed for source_id %s"
            % (rule_kind, source_label, source_id)
        )
    return rule


def map_nationality_dimension(
    record: Mapping[str, object],
    *,
    reference: CanonicalReference,
    config: Mapping[str, object],
) -> DimensionMapping:
    """Map one population or NPA nationality/category record without fuzzy matching."""

    source_id = record.get("source_id")
    code = record.get("nationality_code")
    if code is not None:
        code_value = str(code)
        label = record.get("nationality")
        expected = reference.nationality_by_code.get(code_value)
        if expected != label:
            raise SchemaError("Population nationality code-label pair is not canonical")
        return _mapping(
            dimension="nationality_or_region",
            source_id=source_id,
            source_entity_kind="population_nationality",
            source_label=label,
            source_code=code_value,
            source_context={},
            match_status="matched",
            match_method="source_code",
            canonical_ids=(_nationality_id(code_value),),
            canonical_labels=(str(label),),
            targets_complete=True,
            reason="The ISA source code and label define the canonical category.",
            config=config,
        )

    nationality_config = _require_mapping(config.get("nationality"), "nationality")
    source_id_value = _require_nonempty_string(source_id, "source_id")
    row_kind = _require_nonempty_string(record.get("row_kind"), "row_kind")
    region = record.get("region")
    nationality = record.get("nationality")
    source_label = region if row_kind == "region_total" else nationality
    context = {
        "region": region,
        "row_kind": row_kind,
        "subcategory": record.get("subcategory"),
    }
    if row_kind == "region_total":
        region_rules = _require_mapping(
            nationality_config.get("region_code_prefixes"),
            "nationality.region_code_prefixes",
        )
        region_rule = _reviewed_rule(
            region_rules,
            source_label=str(source_label),
            source_id=source_id_value,
            rule_kind="region",
        )
        if region_rule is None:
            return _mapping(
                dimension="nationality_or_region",
                source_id=source_id,
                source_entity_kind=row_kind,
                source_label=source_label,
                source_code=None,
                source_context=context,
                match_status="unmatched",
                match_method="no_region_rule",
                canonical_ids=(),
                canonical_labels=(),
                targets_complete=False,
                reason="No explicit crosswalk rule exists for this source region.",
                config=config,
            )
        prefixes = region_rule.get("prefixes")
        if not isinstance(prefixes, list) or not prefixes:
            raise SchemaError("region rule prefixes must be a non-empty array")
        codes = sorted(
            code_value
            for code_value in reference.nationality_by_code
            if any(code_value.startswith(str(prefix)) for prefix in prefixes)
        )
        return _mapping(
            dimension="nationality_or_region",
            source_id=source_id,
            source_entity_kind=row_kind,
            source_label=source_label,
            source_code=None,
            source_context=context,
            match_status="ambiguous",
            match_method="source_region_aggregate",
            canonical_ids=tuple(_nationality_id(item) for item in codes),
            canonical_labels=tuple(reference.nationality_by_code[item] for item in codes),
            targets_complete=False,
            reason=(
                "The source region spans multiple ISA categories; category-system "
                "compatibility is not asserted."
            ),
            config=config,
        )

    label_value = _require_nonempty_string(source_label, "nationality source label")
    composites = _require_mapping(
        nationality_config.get("composites"), "nationality.composites"
    )
    aliases = _require_mapping(
        nationality_config.get("aliases"), "nationality.aliases"
    )
    unmatched = _require_mapping(
        nationality_config.get("unmatched"), "nationality.unmatched"
    )
    composite_rule = _reviewed_rule(
        composites,
        source_label=label_value,
        source_id=source_id_value,
        rule_kind="composite",
    )
    alias_rule = _reviewed_rule(
        aliases,
        source_label=label_value,
        source_id=source_id_value,
        rule_kind="alias",
    )
    unmatched_rule = _reviewed_rule(
        unmatched,
        source_label=label_value,
        source_id=source_id_value,
        rule_kind="unmatched",
    )
    if composite_rule is not None:
        rule = composite_rule
        ids, labels = _resolve_nationality_labels(rule.get("target_labels"), reference)
        return _mapping(
            dimension="nationality_or_region",
            source_id=source_id,
            source_entity_kind=row_kind,
            source_label=label_value,
            source_code=None,
            source_context=context,
            match_status="ambiguous",
            match_method="explicit_composite",
            canonical_ids=ids,
            canonical_labels=labels,
            targets_complete=bool(rule.get("targets_complete")),
            reason=_require_nonempty_string(rule.get("reason"), "composite reason"),
            config=config,
        )
    if alias_rule is not None:
        rule = alias_rule
        ids, labels = _resolve_nationality_labels(rule.get("target_labels"), reference)
        return _mapping(
            dimension="nationality_or_region",
            source_id=source_id,
            source_entity_kind=row_kind,
            source_label=label_value,
            source_code=None,
            source_context=context,
            match_status="matched" if len(ids) == 1 else "ambiguous",
            match_method="explicit_alias",
            canonical_ids=ids,
            canonical_labels=labels,
            targets_complete=True,
            reason=_require_nonempty_string(rule.get("reason"), "alias reason"),
            config=config,
        )
    if unmatched_rule is not None:
        rule = unmatched_rule
        return _mapping(
            dimension="nationality_or_region",
            source_id=source_id,
            source_entity_kind=row_kind,
            source_label=label_value,
            source_code=None,
            source_context=context,
            match_status="unmatched",
            match_method="explicit_unmatched",
            canonical_ids=(),
            canonical_labels=(),
            targets_complete=False,
            reason=_require_nonempty_string(rule.get("reason"), "unmatched reason"),
            config=config,
        )
    codes = reference.nationality_codes_by_label.get(label_value, ())
    status = "matched" if len(codes) == 1 else "ambiguous" if codes else "unmatched"
    return _mapping(
        dimension="nationality_or_region",
        source_id=source_id,
        source_entity_kind=row_kind,
        source_label=label_value,
        source_code=None,
        source_context=context,
        match_status=status,
        match_method="exact_label" if codes else "no_exact_target",
        canonical_ids=tuple(_nationality_id(item) for item in codes),
        canonical_labels=tuple(reference.nationality_by_code[item] for item in codes),
        targets_complete=bool(codes),
        reason=(
            "Exactly one ISA category has the same source label."
            if len(codes) == 1
            else "No single exact ISA category target exists."
        ),
        config=config,
    )


def map_geography_dimension(
    record: Mapping[str, object],
    *,
    reference: CanonicalReference,
    config: Mapping[str, object],
) -> DimensionMapping:
    """Map one population or NPA geography while retaining police-area semantics."""

    source_id = record.get("source_id")
    code = record.get("prefecture_code")
    if code is not None:
        code_value = str(code)
        label = record.get("prefecture")
        expected = reference.prefecture_by_code.get(code_value)
        if expected != label:
            raise SchemaError("Population prefecture code-label pair is not canonical")
        return _mapping(
            dimension="geography",
            source_id=source_id,
            source_entity_kind="population_prefecture",
            source_label=label,
            source_code=code_value,
            source_context={},
            match_status="matched",
            match_method="source_code",
            canonical_ids=(_prefecture_id(code_value),),
            canonical_labels=(str(label),),
            targets_complete=True,
            reason="The ISA source code and label define the canonical category.",
            config=config,
        )

    geography_config = _require_mapping(config.get("geography"), "geography")
    geography_type = _require_nonempty_string(
        record.get("geography_type"), "geography_type"
    )
    source_label = _require_nonempty_string(record.get("geography"), "geography")
    context = {
        "geography_type": geography_type,
        "parent_region": record.get("parent_region"),
        "geography_semantics": record.get("geography_semantics"),
    }
    if geography_type == "national":
        national = _require_mapping(geography_config.get("national"), "geography.national")
        rule = national.get(source_label)
        if not isinstance(rule, dict):
            raise SchemaError("No national geography rule for %s" % source_label)
        return _mapping(
            dimension="geography",
            source_id=source_id,
            source_entity_kind=geography_type,
            source_label=source_label,
            source_code=None,
            source_context=context,
            match_status="matched",
            match_method="explicit_national_aggregate",
            canonical_ids=(
                _require_nonempty_string(rule.get("canonical_id"), "canonical_id"),
            ),
            canonical_labels=(
                _require_nonempty_string(rule.get("canonical_label"), "canonical_label"),
            ),
            targets_complete=True,
            reason=_require_nonempty_string(rule.get("reason"), "national reason"),
            config=config,
        )
    non_equivalent = _require_mapping(
        geography_config.get("non_equivalent_types"),
        "geography.non_equivalent_types",
    )
    if geography_type in non_equivalent:
        return _mapping(
            dimension="geography",
            source_id=source_id,
            source_entity_kind=geography_type,
            source_label=source_label,
            source_code=None,
            source_context=context,
            match_status="ambiguous",
            match_method="non_equivalent_geography",
            canonical_ids=(),
            canonical_labels=(),
            targets_complete=False,
            reason=_require_nonempty_string(
                non_equivalent[geography_type], "non-equivalent reason"
            ),
            config=config,
        )
    codes = reference.prefecture_codes_by_label.get(source_label, ())
    status = "matched" if len(codes) == 1 else "ambiguous" if codes else "unmatched"
    return _mapping(
        dimension="geography",
        source_id=source_id,
        source_entity_kind=geography_type,
        source_label=source_label,
        source_code=None,
        source_context=context,
        match_status=status,
        match_method="exact_label" if codes else "no_exact_target",
        canonical_ids=tuple(_prefecture_id(item) for item in codes),
        canonical_labels=tuple(reference.prefecture_by_code[item] for item in codes),
        targets_complete=bool(codes),
        reason=(
            "Exactly one ISA prefecture category has the same label."
            if len(codes) == 1
            else "No single exact ISA prefecture category target exists."
        ),
        config=config,
    )


def _read_catalog(path: Path) -> List[Mapping[str, object]]:
    rows: List[Mapping[str, object]] = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise SchemaError("Catalog row must be an object at line %d" % line_number)
                if value.get("processing_status") != "validated":
                    raise SchemaError("Dimension mapping requires validated catalog inputs")
                rows.append(value)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SchemaError("Invalid artifact catalog: %s" % path) from error
    if not rows:
        raise SchemaError("Artifact catalog is empty")
    return rows


def _safe_processed_path(processed_root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise SchemaError("processed_relpath must be a string")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise SchemaError("Unsafe processed_relpath: %s" % relative)
    path = Path(processed_root) / relative / "normalized.jsonl"
    if not path.is_file():
        raise SchemaError("Normalized input is missing: %s" % path)
    return path


def _record_key(record: Mapping[str, object], fields: Sequence[str]) -> str:
    return json.dumps(
        {field: record.get(field) for field in fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _collect_dimensions(
    catalog: Sequence[Mapping[str, object]],
    *,
    processed_root: Path,
) -> Tuple[
    List[Mapping[str, object]],
    List[Mapping[str, object]],
    List[Mapping[str, object]],
    int,
]:
    population: Dict[str, Mapping[str, object]] = {}
    nationality: Dict[str, Mapping[str, object]] = {}
    geography: Dict[str, Mapping[str, object]] = {}
    input_count = 0
    for catalog_row in catalog:
        source_id = _require_nonempty_string(catalog_row.get("source_id"), "source_id")
        normalized_path = _safe_processed_path(
            processed_root, catalog_row.get("processed_relpath")
        )
        try:
            with normalized_path.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise SchemaError(
                            "Normalized row must be an object: %s:%d"
                            % (normalized_path, line_number)
                        )
                    if row.get("source_id") != source_id:
                        raise SchemaError("Normalized source_id differs from catalog")
                    input_count += 1
                    if "nationality_code" in row and "prefecture_code" in row:
                        nat_key = _record_key(
                            row, ("source_id", "nationality_code", "nationality")
                        )
                        pref_key = _record_key(
                            row, ("source_id", "prefecture_code", "prefecture")
                        )
                        population["nationality:" + nat_key] = {
                            "source_id": source_id,
                            "nationality_code": row.get("nationality_code"),
                            "nationality": row.get("nationality"),
                            "prefecture_code": row.get("prefecture_code"),
                            "prefecture": row.get("prefecture"),
                        }
                        population["prefecture:" + pref_key] = dict(row)
                    elif "row_kind" in row:
                        key = _record_key(
                            row,
                            (
                                "source_id",
                                "row_kind",
                                "region",
                                "nationality",
                                "subcategory",
                            ),
                        )
                        nationality[key] = dict(row)
                    elif "geography_type" in row:
                        key = _record_key(
                            row,
                            (
                                "source_id",
                                "geography",
                                "geography_type",
                                "parent_region",
                                "geography_semantics",
                            ),
                        )
                        geography[key] = dict(row)
                    else:
                        raise SchemaError(
                            "Unsupported normalized dimension schema: %s:%d"
                            % (normalized_path, line_number)
                        )
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise SchemaError("Invalid normalized JSONL: %s" % normalized_path) from error
    return (
        list(population.values()),
        list(nationality.values()),
        list(geography.values()),
        input_count,
    )


def _mapping_sort_key(item: DimensionMapping) -> Tuple[str, ...]:
    return (
        item.source_id,
        item.dimension,
        item.source_entity_kind,
        item.source_label,
        json.dumps(item.source_context, ensure_ascii=False, sort_keys=True),
    )


def _generated_timestamp(value: str) -> str:
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


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def generate_dimension_mapping_report(
    *,
    catalog_path: Path,
    processed_root: Path,
    config_path: Path,
    output_root: Path,
    generated_at: str,
) -> DimensionMappingReport:
    """Generate an immutable cross-source mapping audit from validated normalized data."""

    config = load_dimension_mapping_config(config_path)
    catalog = _read_catalog(catalog_path)
    population, nationality, geography, input_count = _collect_dimensions(
        catalog, processed_root=processed_root
    )
    reference = build_canonical_reference(population)
    mappings: List[DimensionMapping] = []
    seen_population_nationalities = set()
    seen_population_prefectures = set()
    for row in population:
        nat_key = (str(row.get("source_id")), str(row.get("nationality_code")))
        if nat_key not in seen_population_nationalities:
            mappings.append(
                map_nationality_dimension(row, reference=reference, config=config)
            )
            seen_population_nationalities.add(nat_key)
        pref_key = (str(row.get("source_id")), str(row.get("prefecture_code")))
        if pref_key not in seen_population_prefectures:
            mappings.append(map_geography_dimension(row, reference=reference, config=config))
            seen_population_prefectures.add(pref_key)
    mappings.extend(
        map_nationality_dimension(row, reference=reference, config=config)
        for row in nationality
    )
    mappings.extend(
        map_geography_dimension(row, reference=reference, config=config)
        for row in geography
    )
    mappings.sort(key=_mapping_sort_key)

    status_counts = Counter(item.match_status for item in mappings)
    status_payload = {status: status_counts.get(status, 0) for status in MATCH_STATUSES}
    by_source: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in mappings:
        by_source[item.source_id][item.match_status] += 1
    source_payload = {
        source_id: {
            status: counts.get(status, 0) for status in MATCH_STATUSES
        }
        for source_id, counts in sorted(by_source.items())
    }

    destination_root = Path(output_root)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / (
        _generated_timestamp(generated_at) + "_dimension_mapping"
    )
    if destination.exists():
        raise MappingConflictError(
            "Timestamped mapping output already exists and was not overwritten: %s"
            % destination
        )
    staging = Path(tempfile.mkdtemp(prefix=".dimension-mapping-", dir=destination_root))
    try:
        jsonl_path = staging / "dimension_mappings.jsonl"
        csv_path = staging / "dimension_mappings.csv"
        summary_path = staging / "summary.json"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for item in mappings:
                handle.write(
                    json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
                )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for item in mappings:
                writer.writerow(
                    {key: _csv_value(value) for key, value in item.to_dict().items()}
                )
        summary = {
            "mapping_schema_version": MAPPING_SCHEMA_VERSION,
            "generated_at": generated_at,
            "mapping_scope": config["mapping_scope"],
            "config_path": Path(config_path).as_posix(),
            "config_sha256": sha256_file(Path(config_path)),
            "catalog_path": Path(catalog_path).as_posix(),
            "catalog_sha256": sha256_file(Path(catalog_path)),
            "source_ids": sorted(str(row.get("source_id")) for row in catalog),
            "input_record_count": input_count,
            "mapping_record_count": len(mappings),
            "status_counts": status_payload,
            "by_source": source_payload,
            "canonical_reference_counts": {
                "nationality_or_region": len(reference.nationality_by_code),
                "geography": len(reference.prefecture_by_code),
            },
        }
        _write_json(summary_path, summary)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    final_jsonl = destination / "dimension_mappings.jsonl"
    final_csv = destination / "dimension_mappings.csv"
    final_summary = destination / "summary.json"
    latest_path = destination_root / "latest.json"
    latest_temp = destination_root / ".latest.json.tmp"
    _write_json(
        latest_temp,
        {
            "mapping_schema_version": MAPPING_SCHEMA_VERSION,
            "generated_at": generated_at,
            "run_relpath": destination.name,
            "summary_sha256": sha256_file(final_summary),
            "dimension_mappings_sha256": sha256_file(final_jsonl),
        },
    )
    latest_temp.replace(latest_path)
    return DimensionMappingReport(
        output_dir=destination,
        jsonl_path=final_jsonl,
        csv_path=final_csv,
        summary_path=final_summary,
        latest_path=latest_path,
        record_count=len(mappings),
        status_counts=status_payload,
    )
