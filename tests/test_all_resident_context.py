import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import nationality_crime_atlas.all_resident_context as context_module
from nationality_crime_atlas.all_resident_context import (
    generate_all_resident_context_report,
    load_all_resident_context_contracts,
)
from nationality_crime_atlas.all_resident_context_cli import main as context_main
from nationality_crime_atlas.errors import IntegrityError, SchemaError
from nationality_crime_atlas.provenance import sha256_file


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return sha256_file(path)


def _mapping_row(
    *,
    source_id: str,
    source_entity_kind: str,
    source_label: str,
    source_context,
    match_status: str,
    canonical_ids,
    canonical_labels,
    targets_complete: bool,
):
    return {
        "mapping_schema_version": 1,
        "dimension": "geography",
        "source_id": source_id,
        "source_entity_kind": source_entity_kind,
        "source_label": source_label,
        "source_code": None,
        "source_context": source_context,
        "match_status": match_status,
        "match_method": "fixture",
        "canonical_ids": list(canonical_ids),
        "canonical_labels": list(canonical_labels),
        "targets_complete": targets_complete,
        "reason": "fixture",
        "mapping_scope": "Label/category crosswalk only; it does not establish statistical compatibility between numerator and denominator.",
    }


def _fixture(tmp_path: Path):
    processed_root = tmp_path / "processed"
    mapping_root = processed_root / "_mappings"
    output_root = tmp_path / "output"
    generated_at = "2026-09-01T15:00:00+09:00"

    s15_relpath = "npa-all-persons-prefecture-crime/S15/run-fixture"
    s16_relpath = "npa-total-population-prefecture/S16/run-fixture"
    s15_path = processed_root / s15_relpath / "normalized.jsonl"
    s16_path = processed_root / s16_relpath / "normalized.jsonl"
    s15_rows = [
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "日本",
            "geography_type": "national",
            "parent_region": None,
            "geography_semantics": "national_aggregate",
            "recognized_cases": 500,
            "cleared_cases": 250,
            "cleared_persons": 200,
        },
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "北海道",
            "geography_type": "prefecture",
            "parent_region": "北海道",
            "geography_semantics": "police_reporting_area_unresolved",
            "recognized_cases": 200,
            "cleared_cases": 100,
            "cleared_persons": 80,
        },
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "青森県",
            "geography_type": "prefecture",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
            "recognized_cases": 300,
            "cleared_cases": 150,
            "cleared_persons": 120,
        },
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "東北",
            "geography_type": "police_region",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
            "recognized_cases": 999,
            "cleared_cases": 500,
            "cleared_persons": 400,
        },
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "札幌",
            "geography_type": "police_subregion",
            "parent_region": "北海道",
            "geography_semantics": "police_reporting_area_unresolved",
            "recognized_cases": 111,
            "cleared_cases": 55,
            "cleared_persons": 44,
        },
    ]
    s16_rows = [
        {
            "source_id": "S16",
            "year": 2024,
            "reference_date": "2024-10-01",
            "population_scope": "total_population",
            "geography": "日本",
            "geography_type": "national",
            "parent_region": None,
            "geography_semantics": "national_aggregate",
            "population": 3000,
            "source_value": 3,
            "source_unit": "1000_persons",
            "rounding": "nearest_1000_persons",
        },
        {
            "source_id": "S16",
            "year": 2024,
            "reference_date": "2024-10-01",
            "population_scope": "total_population",
            "geography": "北海道",
            "geography_type": "prefecture",
            "parent_region": None,
            "geography_semantics": "population_estimate_prefecture",
            "population": 1000,
            "source_value": 1,
            "source_unit": "1000_persons",
            "rounding": "nearest_1000_persons",
        },
        {
            "source_id": "S16",
            "year": 2024,
            "reference_date": "2024-10-01",
            "population_scope": "total_population",
            "geography": "青森県",
            "geography_type": "prefecture",
            "parent_region": None,
            "geography_semantics": "population_estimate_prefecture",
            "population": 2001,
            "source_value": 2,
            "source_unit": "1000_persons",
            "rounding": "nearest_1000_persons",
        },
    ]
    s15_hash = _write_jsonl(s15_path, s15_rows)
    s16_hash = _write_jsonl(s16_path, s16_rows)
    _write_json(
        s15_path.parent / "run.json",
        {"source_id": "S15", "normalized_sha256": s15_hash, "quality_passed": True},
    )
    _write_json(
        s16_path.parent / "run.json",
        {"source_id": "S16", "normalized_sha256": s16_hash, "quality_passed": True},
    )

    catalog_path = processed_root / "_catalog" / "artifacts.jsonl"
    _write_jsonl(
        catalog_path,
        [
            {
                "source_id": "S15",
                "series_id": "npa-all-persons-prefecture-crime",
                "dataset": "fixture",
                "publisher": "fixture",
                "source_table": "3",
                "source_period": "2024",
                "sha256": "artifact-s15",
                "landing_url": "https://example.test/s15",
                "download_url": "https://example.test/s15.xlsx",
                "raw_relpath": "raw/s15.xlsx",
                "processed_relpath": s15_relpath,
                "retrieved_at": "2026-09-01T13:20:01+09:00",
                "revision": "fixture",
                "verification_level": "binary_and_primary",
                "processing_status": "validated",
            },
            {
                "source_id": "S16",
                "series_id": "npa-total-population-prefecture",
                "dataset": "fixture",
                "publisher": "fixture",
                "source_table": "144",
                "source_period": "2024-10-01",
                "sha256": "artifact-s16",
                "landing_url": "https://example.test/s16",
                "download_url": "https://example.test/s16.xlsx",
                "raw_relpath": "raw/s16.xlsx",
                "processed_relpath": s16_relpath,
                "retrieved_at": "2026-09-01T13:20:12+09:00",
                "revision": "fixture",
                "verification_level": "binary_and_primary",
                "processing_status": "validated",
            },
        ],
    )

    mapping_run = mapping_root / "20260901_150000_dimension_mapping"
    mapping_jsonl = mapping_run / "dimension_mappings.jsonl"
    mapping_rows = [
        _mapping_row(
            source_id="S15",
            source_entity_kind="national",
            source_label="日本",
            source_context={
                "geography_type": "national",
                "parent_region": None,
                "geography_semantics": "national_aggregate",
            },
            match_status="matched",
            canonical_ids=["jp:all"],
            canonical_labels=["日本全国"],
            targets_complete=True,
        ),
        _mapping_row(
            source_id="S15",
            source_entity_kind="prefecture",
            source_label="北海道",
            source_context={
                "geography_type": "prefecture",
                "parent_region": "北海道",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="matched",
            canonical_ids=["jp-prefecture:01"],
            canonical_labels=["北海道"],
            targets_complete=True,
        ),
        _mapping_row(
            source_id="S15",
            source_entity_kind="prefecture",
            source_label="青森県",
            source_context={
                "geography_type": "prefecture",
                "parent_region": "東北",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="matched",
            canonical_ids=["jp-prefecture:02"],
            canonical_labels=["青森県"],
            targets_complete=True,
        ),
        _mapping_row(
            source_id="S15",
            source_entity_kind="police_region",
            source_label="東北",
            source_context={
                "geography_type": "police_region",
                "parent_region": "東北",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="ambiguous",
            canonical_ids=[],
            canonical_labels=[],
            targets_complete=False,
        ),
        _mapping_row(
            source_id="S15",
            source_entity_kind="police_subregion",
            source_label="札幌",
            source_context={
                "geography_type": "police_subregion",
                "parent_region": "北海道",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="ambiguous",
            canonical_ids=[],
            canonical_labels=[],
            targets_complete=False,
        ),
        _mapping_row(
            source_id="S16",
            source_entity_kind="national",
            source_label="日本",
            source_context={
                "geography_type": "national",
                "parent_region": None,
                "geography_semantics": "national_aggregate",
            },
            match_status="matched",
            canonical_ids=["jp:all"],
            canonical_labels=["日本全国"],
            targets_complete=True,
        ),
        _mapping_row(
            source_id="S16",
            source_entity_kind="prefecture",
            source_label="北海道",
            source_context={
                "geography_type": "prefecture",
                "parent_region": None,
                "geography_semantics": "population_estimate_prefecture",
            },
            match_status="matched",
            canonical_ids=["jp-prefecture:01"],
            canonical_labels=["北海道"],
            targets_complete=True,
        ),
        _mapping_row(
            source_id="S16",
            source_entity_kind="prefecture",
            source_label="青森県",
            source_context={
                "geography_type": "prefecture",
                "parent_region": None,
                "geography_semantics": "population_estimate_prefecture",
            },
            match_status="matched",
            canonical_ids=["jp-prefecture:02"],
            canonical_labels=["青森県"],
            targets_complete=True,
        ),
    ]
    mapping_hash = _write_jsonl(mapping_jsonl, mapping_rows)
    mapping_summary = mapping_run / "summary.json"
    _write_json(mapping_summary, {"mapping_record_count": len(mapping_rows)})
    _write_json(
        mapping_root / "latest.json",
        {
            "mapping_schema_version": 1,
            "run_relpath": mapping_run.name,
            "summary_sha256": sha256_file(mapping_summary),
            "dimension_mappings_sha256": mapping_hash,
        },
    )

    contracts_path = tmp_path / "contracts.json"
    _write_json(
        contracts_path,
        {
            "schema_version": 2,
            "processed_input_pins": {"S15": s15_hash, "S16": s16_hash},
            "defaults": {
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "numerator_source_id": "S15",
                "numerator_year": 2024,
                "numerator_period_type": "annual_flow",
                "numerator_population_scope": "all_persons",
                "numerator_residency_scope": "not_established",
                "numerator_offense_scope": "criminal_code_excluding_traffic_negligence",
                "denominator_source_id": "S16",
                "denominator_metric": "total_population",
                "denominator_reference_date": "2024-10-01",
                "denominator_period_type": "point_in_time_stock",
                "denominator_population_scope": "total_population",
                "display_multiplier": 100000,
                "display_scale_status": "provisional",
                "display_unit_label_ja": "人口10万人当たり",
                "display_unit_label_en": "per 100,000 residents",
                "crosswalk_policy": "exact",
                "expected_published_row_count": 5,
                "expected_calculated_row_count": 3,
            },
            "contracts": [
                {
                    "context_id": "recognized",
                    "label_ja": "認知件数",
                    "label_en": "recognized",
                    "numerator_metric": "recognized_cases",
                    "base_mismatch_flags": [
                        "annual_flow_vs_point_in_time_population",
                        "case_count_not_person_count",
                        "numerator_residency_scope_not_established",
                        "total_population_rounded_to_nearest_1000",
                    ],
                    "ui_caveat": "fixture",
                },
                {
                    "context_id": "cleared_cases",
                    "label_ja": "検挙件数",
                    "label_en": "cleared cases",
                    "numerator_metric": "cleared_cases",
                    "base_mismatch_flags": [
                        "annual_flow_vs_point_in_time_population",
                        "case_count_not_person_count",
                        "numerator_residency_scope_not_established",
                        "total_population_rounded_to_nearest_1000",
                    ],
                    "ui_caveat": "fixture",
                },
                {
                    "context_id": "cleared_persons",
                    "label_ja": "検挙人員",
                    "label_en": "cleared persons",
                    "numerator_metric": "cleared_persons",
                    "base_mismatch_flags": [
                        "annual_flow_vs_point_in_time_population",
                        "cleared_person_records_not_unique_risk_population",
                        "numerator_residency_scope_not_established",
                        "total_population_rounded_to_nearest_1000",
                    ],
                    "ui_caveat": "fixture",
                },
            ],
            "unsupported_requests": [
                {
                    "request_id": "japanese_prefecture",
                    "label_ja": "日本国籍都道府県別",
                    "label_en": "japanese prefecture",
                    "refusal_reason": "japanese_prefecture_numerator_unpublished",
                    "geography_label": "都道府県別",
                    "geography_id": "request:japanese",
                    "geography_type": "prefecture_collection",
                    "ui_caveat": "fixture",
                    "mismatch_flags": ["numerator_not_published"],
                    "numerator_context": {
                        "requested_geography_grain": "prefecture",
                        "requested_population_scope": "japanese_nationals",
                    },
                },
                {
                    "request_id": "nationality_prefecture",
                    "label_ja": "個別国籍都道府県別",
                    "label_en": "nationality prefecture",
                    "refusal_reason": "individual_nationality_prefecture_numerator_unpublished",
                    "geography_label": "都道府県別",
                    "geography_id": "request:nationality",
                    "geography_type": "prefecture_collection",
                    "ui_caveat": "fixture",
                    "mismatch_flags": ["numerator_not_published"],
                    "numerator_context": {
                        "requested_geography_grain": "prefecture",
                        "requested_population_scope": "individual_nationality",
                    },
                },
            ],
        },
    )

    return {
        "catalog_path": catalog_path,
        "processed_root": processed_root,
        "mapping_latest_path": mapping_root / "latest.json",
        "contracts_path": contracts_path,
        "output_root": output_root,
        "generated_at": generated_at,
    }


PREFECTURE_NAMES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]


def _spread_total(total, fixed_values):
    remaining_names = [name for name in PREFECTURE_NAMES if name not in fixed_values]
    remaining_total = total - sum(fixed_values.values())
    base, extra = divmod(remaining_total, len(remaining_names))
    values = dict(fixed_values)
    values.update(
        {
            name: base + (1 if index < extra else 0)
            for index, name in enumerate(remaining_names)
        }
    )
    return values


def _production_geometry_fixture(tmp_path: Path):
    """Expand the small fixture to the reviewed 2024 production row geometry."""

    paths = _fixture(tmp_path)
    s15_relpath = "npa-all-persons-prefecture-crime/S15/run-fixture"
    s16_relpath = "npa-total-population-prefecture/S16/run-fixture"
    s15_path = paths["processed_root"] / s15_relpath / "normalized.jsonl"
    s16_path = paths["processed_root"] / s16_relpath / "normalized.jsonl"

    recognized = _spread_total(
        737679, {"東京都": 94752, "埼玉県": 51667}
    )
    cleared_cases = _spread_total(
        287273, {"東京都": 33961, "埼玉県": 16691}
    )
    cleared_persons = _spread_total(
        191826, {"東京都": 23731, "埼玉県": 10054}
    )
    population = _spread_total(
        123803, {"東京都": 14178, "埼玉県": 7332}
    )

    s15_rows = [
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "日本",
            "geography_type": "national",
            "parent_region": None,
            "geography_semantics": "national_aggregate",
            "recognized_cases": 737679,
            "cleared_cases": 287273,
            "cleared_persons": 191826,
        }
    ]
    s16_rows = [
        {
            "source_id": "S16",
            "year": 2024,
            "reference_date": "2024-10-01",
            "population_scope": "total_population",
            "geography": "日本",
            "geography_type": "national",
            "parent_region": None,
            "geography_semantics": "national_aggregate",
            "population": 123802000,
            "source_value": 123802,
            "source_unit": "1000_persons",
            "rounding": "nearest_1000_persons",
        }
    ]
    geography_ids = {"日本": "jp:all"}
    for index, name in enumerate(PREFECTURE_NAMES, start=1):
        geography_ids[name] = "jp-prefecture:%02d" % index
        s15_rows.append(
            {
                "source_id": "S15",
                "year": 2024,
                "population_scope": "all_persons",
                "offense_scope": "criminal_code_excluding_traffic_negligence",
                "geography": name,
                "geography_type": "prefecture",
                "parent_region": "fixture-region",
                "geography_semantics": "police_reporting_area_unresolved",
                "recognized_cases": recognized[name],
                "cleared_cases": cleared_cases[name],
                "cleared_persons": cleared_persons[name],
            }
        )
        s16_rows.append(
            {
                "source_id": "S16",
                "year": 2024,
                "reference_date": "2024-10-01",
                "population_scope": "total_population",
                "geography": name,
                "geography_type": "prefecture",
                "parent_region": None,
                "geography_semantics": "population_estimate_prefecture",
                "population": population[name] * 1000,
                "source_value": population[name],
                "source_unit": "1000_persons",
                "rounding": "nearest_1000_persons",
            }
        )
    for index in range(1, 8):
        s15_rows.append(
            {
                "source_id": "S15",
                "year": 2024,
                "population_scope": "all_persons",
                "offense_scope": "criminal_code_excluding_traffic_negligence",
                "geography": "Police Region %d" % index,
                "geography_type": "police_region",
                "parent_region": "Police Region %d" % index,
                "geography_semantics": "police_reporting_area_unresolved",
                "recognized_cases": 1,
                "cleared_cases": 1,
                "cleared_persons": 1,
            }
        )
    for index in range(1, 6):
        s15_rows.append(
            {
                "source_id": "S15",
                "year": 2024,
                "population_scope": "all_persons",
                "offense_scope": "criminal_code_excluding_traffic_negligence",
                "geography": "Police Subregion %d" % index,
                "geography_type": "police_subregion",
                "parent_region": "北海道",
                "geography_semantics": "police_reporting_area_unresolved",
                "recognized_cases": 1,
                "cleared_cases": 1,
                "cleared_persons": 1,
            }
        )

    s15_hash = _write_jsonl(s15_path, s15_rows)
    s16_hash = _write_jsonl(s16_path, s16_rows)
    _write_json(
        s15_path.parent / "run.json",
        {"source_id": "S15", "normalized_sha256": s15_hash, "quality_passed": True},
    )
    _write_json(
        s16_path.parent / "run.json",
        {"source_id": "S16", "normalized_sha256": s16_hash, "quality_passed": True},
    )

    contracts = json.loads(paths["contracts_path"].read_text(encoding="utf-8"))
    contracts["processed_input_pins"] = {"S15": s15_hash, "S16": s16_hash}
    contracts["defaults"]["expected_published_row_count"] = 60
    contracts["defaults"]["expected_calculated_row_count"] = 48
    _write_json(paths["contracts_path"], contracts)

    mapping_rows = []
    for row in s15_rows + s16_rows:
        geography_type = row["geography_type"]
        matched = geography_type in {"national", "prefecture"}
        mapping_rows.append(
            _mapping_row(
                source_id=row["source_id"],
                source_entity_kind=geography_type,
                source_label=row["geography"],
                source_context={
                    "geography_type": geography_type,
                    "parent_region": row["parent_region"],
                    "geography_semantics": row["geography_semantics"],
                },
                match_status="matched" if matched else "ambiguous",
                canonical_ids=[geography_ids[row["geography"]]] if matched else [],
                canonical_labels=[row["geography"]] if matched else [],
                targets_complete=matched,
            )
        )
    mapping_latest = json.loads(paths["mapping_latest_path"].read_text(encoding="utf-8"))
    mapping_run = paths["mapping_latest_path"].parent / mapping_latest["run_relpath"]
    mapping_jsonl = mapping_run / "dimension_mappings.jsonl"
    mapping_hash = _write_jsonl(mapping_jsonl, mapping_rows)
    mapping_summary = mapping_run / "summary.json"
    _write_json(mapping_summary, {"mapping_record_count": len(mapping_rows)})
    _write_json(
        paths["mapping_latest_path"],
        {
            "mapping_schema_version": 1,
            "run_relpath": mapping_run.name,
            "summary_sha256": sha256_file(mapping_summary),
            "dimension_mappings_sha256": mapping_hash,
        },
    )
    return paths


def test_contract_loader_accepts_all_resident_context_schema(tmp_path):
    paths = _fixture(tmp_path)

    contracts, unsupported_requests, pins = load_all_resident_context_contracts(
        paths["contracts_path"]
    )

    assert [contract.context_id for contract in contracts] == [
        "recognized",
        "cleared_cases",
        "cleared_persons",
    ]
    assert [request.request_id for request in unsupported_requests] == [
        "japanese_prefecture",
        "nationality_prefecture",
    ]
    assert set(pins) == {"S15", "S16"}


def test_generate_all_resident_context_report_builds_calculated_and_refused_rows(tmp_path):
    paths = _fixture(tmp_path)

    result = generate_all_resident_context_report(**paths)

    records = [
        json.loads(line)
        for line in result.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.record_count == 21
    assert result.status_counts == {"calculated": 9, "refused": 12}
    hokkaido = next(
        row
        for row in records
        if row["context_id"] == "recognized" and row["geography_label"] == "北海道"
    )
    assert hokkaido["calculation_status"] == "calculated"
    assert hokkaido["geography_id"] == "jp-prefecture:01"
    assert hokkaido["denominator_value"] == 1000
    assert hokkaido["display_value"] == 20000.0
    assert "police_reporting_area_vs_population_estimate_prefecture" in hokkaido["mismatch_flags"]
    assert "annual_flow_vs_point_in_time_population" in hokkaido["mismatch_flags"]
    assert "numerator_residency_scope_not_established" in hokkaido["mismatch_flags"]
    assert hokkaido["numerator_context"]["period_type"] == "annual_flow"
    assert hokkaido["numerator_context"]["residency_scope"] == "not_established"
    assert hokkaido["denominator_context"]["period_type"] == "point_in_time_stock"
    tohoku = next(
        row for row in records if row["context_id"] == "recognized" and row["geography_label"] == "東北"
    )
    assert tohoku["calculation_status"] == "refused"
    assert tohoku["refusal_reason"] == "geography_not_exact_prefecture_or_national"
    unsupported = next(
        row
        for row in records
        if row["context_id"] == "recognized"
        and row["refusal_reason"] == "japanese_prefecture_numerator_unpublished"
    )
    assert unsupported["numerator_source_id"] is None
    assert summary["reconciliation"]["recognized"]["numerator_difference"] == 0
    assert summary["reconciliation"]["recognized"]["denominator_difference"] == -1
    assert summary["refusal_reason_counts"][
        "individual_nationality_prefecture_numerator_unpublished"
    ] == 3


def test_context_cli_writes_latest_pointer(tmp_path):
    paths = _fixture(tmp_path)

    result = context_main(
        [
            "--catalog",
            str(paths["catalog_path"]),
            "--processed-root",
            str(paths["processed_root"]),
            "--mapping-latest",
            str(paths["mapping_latest_path"]),
            "--contracts",
            str(paths["contracts_path"]),
            "--output-root",
            str(paths["output_root"]),
            "--generated-at",
            paths["generated_at"],
        ]
    )

    latest = json.loads((paths["output_root"] / "latest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert latest["run_relpath"] == "20260901_150000_all_resident_context"
    run_dir = paths["output_root"] / latest["run_relpath"]
    assert latest["summary_sha256"] == sha256_file(run_dir / "summary.json")
    assert latest["regional_context_records_sha256"] == sha256_file(
        run_dir / "regional_context_records.jsonl"
    )
    assert latest["regional_context_records_csv_sha256"] == sha256_file(
        run_dir / "regional_context_records.csv"
    )


def test_pin_mismatch_raises_integrity_error(tmp_path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["contracts_path"].read_text(encoding="utf-8"))
    payload["processed_input_pins"]["S15"] = "0" * 64
    _write_json(paths["contracts_path"], payload)

    with pytest.raises(IntegrityError, match="contract pin"):
        generate_all_resident_context_report(**paths)


def test_catalog_selects_the_single_revision_matching_the_contract_pin(tmp_path):
    paths = _fixture(tmp_path)
    catalog_rows = [
        json.loads(line)
        for line in paths["catalog_path"].read_text(encoding="utf-8").splitlines()
    ]
    current = next(row for row in catalog_rows if row["source_id"] == "S15")
    current_path = (
        paths["processed_root"] / current["processed_relpath"] / "normalized.jsonl"
    )
    previous_rows = [
        json.loads(line) for line in current_path.read_text(encoding="utf-8").splitlines()
    ]
    previous_rows[0]["recognized_cases"] += 1
    previous_relpath = "npa-all-persons-prefecture-crime/S15/run-previous"
    previous_path = paths["processed_root"] / previous_relpath / "normalized.jsonl"
    previous_hash = _write_jsonl(previous_path, previous_rows)
    _write_json(
        previous_path.parent / "run.json",
        {
            "source_id": "S15",
            "normalized_sha256": previous_hash,
            "quality_passed": True,
        },
    )
    previous_catalog_row = dict(current)
    previous_catalog_row.update(
        {
            "processed_relpath": previous_relpath,
            "raw_relpath": "raw/s15-previous.xlsx",
            "retrieved_at": "2026-08-31T13:20:01+09:00",
            "revision": "previous",
        }
    )
    _write_jsonl(paths["catalog_path"], [previous_catalog_row] + catalog_rows)

    result = generate_all_resident_context_report(**paths)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert summary["source_artifacts"]["S15"]["processed_relpath"] == current[
        "processed_relpath"
    ]


def test_catalog_rejects_multiple_revisions_matching_the_same_contract_pin(tmp_path):
    paths = _fixture(tmp_path)
    catalog_rows = [
        json.loads(line)
        for line in paths["catalog_path"].read_text(encoding="utf-8").splitlines()
    ]
    current = next(row for row in catalog_rows if row["source_id"] == "S15")
    current_path = (
        paths["processed_root"] / current["processed_relpath"] / "normalized.jsonl"
    )
    duplicate_relpath = "npa-all-persons-prefecture-crime/S15/run-duplicate"
    duplicate_path = paths["processed_root"] / duplicate_relpath / "normalized.jsonl"
    duplicate_hash = _write_jsonl(
        duplicate_path,
        [
            json.loads(line)
            for line in current_path.read_text(encoding="utf-8").splitlines()
        ],
    )
    _write_json(
        duplicate_path.parent / "run.json",
        {
            "source_id": "S15",
            "normalized_sha256": duplicate_hash,
            "quality_passed": True,
        },
    )
    duplicate_catalog_row = dict(current)
    duplicate_catalog_row.update(
        {
            "processed_relpath": duplicate_relpath,
            "raw_relpath": "raw/s15-duplicate.xlsx",
            "retrieved_at": "2026-09-01T13:21:01+09:00",
            "revision": "duplicate",
        }
    )
    _write_jsonl(paths["catalog_path"], catalog_rows + [duplicate_catalog_row])

    with pytest.raises(
        IntegrityError, match="Multiple catalog artifacts match contract pin for S15"
    ):
        generate_all_resident_context_report(**paths)


def test_contract_loader_rejects_missing_required_comparability_flags(tmp_path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["contracts_path"].read_text(encoding="utf-8"))
    for contract in payload["contracts"]:
        contract["base_mismatch_flags"] = [
            flag
            for flag in contract["base_mismatch_flags"]
            if flag != "annual_flow_vs_point_in_time_population"
        ]
    _write_json(paths["contracts_path"], payload)

    with pytest.raises(SchemaError, match="required base_mismatch_flags"):
        load_all_resident_context_contracts(paths["contracts_path"])


def test_concurrent_runs_publish_a_hash_closed_latest_pointer(tmp_path, monkeypatch):
    paths = _fixture(tmp_path)
    original_replace = Path.replace
    latest_barrier = threading.Barrier(2)

    def synchronized_replace(path, target):
        if Path(target).name == "latest.json":
            latest_barrier.wait(timeout=5)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", synchronized_replace)

    def generate(generated_at):
        arguments = dict(paths)
        arguments["generated_at"] = generated_at
        return context_module.generate_all_resident_context_report(**arguments)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = list(
            executor.map(
                generate,
                ["2026-09-01T15:01:00+09:00", "2026-09-01T15:02:00+09:00"],
            )
        )

    assert len(reports) == 2
    latest = json.loads((paths["output_root"] / "latest.json").read_text(encoding="utf-8"))
    run_dir = paths["output_root"] / latest["run_relpath"]
    assert latest["summary_sha256"] == sha256_file(run_dir / "summary.json")
    assert latest["regional_context_records_sha256"] == sha256_file(
        run_dir / "regional_context_records.jsonl"
    )


def test_reviewed_2024_row_geometry_and_anchor_values_are_regression_locked(tmp_path):
    paths = _production_geometry_fixture(tmp_path)

    result = generate_all_resident_context_report(**paths)
    records = [
        json.loads(line)
        for line in result.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert result.record_count == 186
    assert result.status_counts == {"calculated": 144, "refused": 42}
    assert summary["refusal_reason_counts"] == {
        "geography_not_exact_prefecture_or_national": 36,
        "individual_nationality_prefecture_numerator_unpublished": 3,
        "japanese_prefecture_numerator_unpublished": 3,
    }
    for context_id in (
        "recognized",
        "cleared_cases",
        "cleared_persons",
    ):
        assert summary["by_context"][context_id] == {"calculated": 48, "refused": 14}
        assert summary["reconciliation"][context_id]["numerator_difference"] == 0
        assert summary["reconciliation"][context_id]["denominator_difference"] == -1000

    tokyo = next(
        row
        for row in records
        if row["context_id"] == "recognized" and row["geography_label"] == "東京都"
    )
    saitama = next(
        row
        for row in records
        if row["context_id"] == "recognized" and row["geography_label"] == "埼玉県"
    )
    assert tokyo["numerator_value"] == 94752
    assert tokyo["denominator_value"] == 14178000
    assert tokyo["display_value"] == pytest.approx(668.303005)
    assert saitama["numerator_value"] == 51667
    assert saitama["denominator_value"] == 7332000
    assert saitama["display_value"] == pytest.approx(704.678123)
    assert tokyo["numerator_value"] > saitama["numerator_value"]
    assert tokyo["display_value"] < saitama["display_value"]
