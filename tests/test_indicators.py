import json
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import IntegrityError, SchemaError
from nationality_crime_atlas.indicator_cli import main as indicator_main
from nationality_crime_atlas.indicators import (
    generate_indicator_report,
    load_indicator_contracts,
)
from nationality_crime_atlas.provenance import sha256_file


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _mapping_row(
    *,
    dimension: str,
    source_id: str,
    source_entity_kind: str,
    source_label: str,
    source_context,
    match_status: str,
    match_method: str,
    canonical_ids,
    canonical_labels,
    targets_complete: bool,
    reason: str,
):
    return {
        "mapping_schema_version": 1,
        "dimension": dimension,
        "source_id": source_id,
        "source_entity_kind": source_entity_kind,
        "source_label": source_label,
        "source_code": None,
        "source_context": source_context,
        "match_status": match_status,
        "match_method": match_method,
        "canonical_ids": list(canonical_ids),
        "canonical_labels": list(canonical_labels),
        "targets_complete": targets_complete,
        "reason": reason,
        "mapping_scope": (
            "Label/category crosswalk only; it does not establish statistical "
            "compatibility between numerator and denominator."
        ),
    }


def _indicator_fixture(tmp_path: Path):
    processed_root = tmp_path / "processed"
    output_root = tmp_path / "output"
    mapping_root = processed_root / "_mappings"

    population_2024_rows = [
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_037",
            "nationality": "ベトナム",
            "prefecture_code": "01",
            "prefecture": "北海道",
            "value": 10,
            "suppressed": False,
        },
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_037",
            "nationality": "ベトナム",
            "prefecture_code": "13",
            "prefecture": "東京都",
            "value": 5,
            "suppressed": False,
        },
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_023",
            "nationality": "中国",
            "prefecture_code": "13",
            "prefecture": "東京都",
            "value": 20,
            "suppressed": False,
        },
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_022",
            "nationality": "台湾",
            "prefecture_code": "13",
            "prefecture": "東京都",
            "value": 3,
            "suppressed": False,
        },
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_011",
            "nationality": "韓国",
            "prefecture_code": "13",
            "prefecture": "東京都",
            "value": 8,
            "suppressed": False,
        },
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": "01_012",
            "nationality": "（朝鮮）",
            "prefecture_code": "13",
            "prefecture": "東京都",
            "value": 2,
            "suppressed": False,
        },
    ]
    population_2025_rows = [
        {
            "source_id": "S14",
            "period_end": "2025-12-31",
            "nationality_code": "01_037",
            "nationality": "ベトナム",
            "prefecture_code": "01",
            "prefecture": "北海道",
            "value": 40,
            "suppressed": False,
        },
        {
            "source_id": "S14",
            "period_end": "2025-12-31",
            "nationality_code": "01_023",
            "nationality": "中国",
            "prefecture_code": "01",
            "prefecture": "北海道",
            "value": 10,
            "suppressed": False,
        },
        {
            "source_id": "S14",
            "period_end": "2025-12-31",
            "nationality_code": "01_037",
            "nationality": "ベトナム",
            "prefecture_code": "02",
            "prefecture": "青森県",
            "value": 12,
            "suppressed": False,
        },
        {
            "source_id": "S14",
            "period_end": "2025-12-31",
            "nationality_code": "01_023",
            "nationality": "中国",
            "prefecture_code": "02",
            "prefecture": "青森県",
            "value": 3,
            "suppressed": False,
        },
    ]
    nationality_rows = [
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "ベトナム",
            "subcategory": None,
            "row_kind": "country",
            "cleared_cases": 6,
            "cleared_persons": 3,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "中国",
            "subcategory": None,
            "row_kind": "country",
            "cleared_cases": 8,
            "cleared_persons": 4,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "韓国・朝鮮",
            "subcategory": None,
            "row_kind": "country",
            "cleared_cases": 10,
            "cleared_persons": 5,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "その他",
            "subcategory": None,
            "row_kind": "country",
            "cleared_cases": 2,
            "cleared_persons": 1,
        },
    ]
    prefecture_rows = [
        {
            "source_id": "S02",
            "year": 2025,
            "population_scope": "visiting_foreign",
            "offense_scope": "criminal_and_special_law",
            "geography": "北海道",
            "geography_type": "prefecture",
            "parent_region": "北海道",
            "geography_semantics": "police_reporting_area_unresolved",
            "cleared_cases": 20,
            "cleared_persons": 10,
        },
        {
            "source_id": "S02",
            "year": 2025,
            "population_scope": "visiting_foreign",
            "offense_scope": "criminal_and_special_law",
            "geography": "青森県",
            "geography_type": "prefecture",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
            "cleared_cases": 6,
            "cleared_persons": 3,
        },
        {
            "source_id": "S02",
            "year": 2025,
            "population_scope": "visiting_foreign",
            "offense_scope": "criminal_and_special_law",
            "geography": "東北",
            "geography_type": "police_region",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
            "cleared_cases": 99,
            "cleared_persons": 50,
        },
    ]
    relpaths = {
        "S14_2024_12": "isa-resident-foreigner-population-t1/S14_2024_12/run",
        "S14": "isa-resident-foreigner-population-t1/S14/run",
        "S08": "npa-all-foreign-nationality-crime/S08/run",
        "S02": "npa-prefecture-visiting-foreign-crime/S02/run",
    }
    _write_jsonl(processed_root / relpaths["S14_2024_12"] / "normalized.jsonl", population_2024_rows)
    _write_jsonl(processed_root / relpaths["S14"] / "normalized.jsonl", population_2025_rows)
    _write_jsonl(processed_root / relpaths["S08"] / "normalized.jsonl", nationality_rows)
    _write_jsonl(processed_root / relpaths["S02"] / "normalized.jsonl", prefecture_rows)
    for source_id, relpath in relpaths.items():
        normalized_path = processed_root / relpath / "normalized.jsonl"
        _write_json(
            normalized_path.parent / "run.json",
            {
                "source_id": source_id,
                "quality_passed": True,
                "normalized_sha256": sha256_file(normalized_path),
                "record_count": len(normalized_path.read_text(encoding="utf-8").splitlines()),
            },
        )
    _write_jsonl(
        processed_root / "_catalog" / "artifacts.jsonl",
        [
            {
                "source_id": source_id,
                "series_id": "fixture-" + source_id.lower(),
                "processed_relpath": relpath,
                "processing_status": "validated",
                "dataset": "Fixture dataset " + source_id,
                "publisher": "Fixture publisher",
                "source_table": "fixture-table",
                "source_period": "fixture-period",
                "sha256": (source_id.lower() * 64)[:64],
                "landing_url": "https://example.test/landing/" + source_id,
                "download_url": "https://example.test/download/" + source_id,
                "raw_relpath": "fixture/raw/" + source_id,
                "retrieved_at": "2026-08-30T20:00:00+09:00",
                "revision": "fixture",
                "verification_level": "fixture_validated",
            }
            for source_id, relpath in relpaths.items()
        ],
    )

    mapping_run = mapping_root / "20260830_220000_dimension_mapping"
    mapping_rows = [
        _mapping_row(
            dimension="nationality_or_region",
            source_id="S08",
            source_entity_kind="country",
            source_label="ベトナム",
            source_context={"region": "アジア州の国", "row_kind": "country", "subcategory": None},
            match_status="matched",
            match_method="exact_label",
            canonical_ids=["isa-nationality:01_037"],
            canonical_labels=["ベトナム"],
            targets_complete=True,
            reason="Exactly one ISA category has the same source label.",
        ),
        _mapping_row(
            dimension="nationality_or_region",
            source_id="S08",
            source_entity_kind="country",
            source_label="中国",
            source_context={"region": "アジア州の国", "row_kind": "country", "subcategory": None},
            match_status="ambiguous",
            match_method="explicit_composite",
            canonical_ids=["isa-nationality:01_022", "isa-nationality:01_023"],
            canonical_labels=["台湾", "中国"],
            targets_complete=False,
            reason="The NPA source footnote includes Taiwan, Hong Kong, etc.",
        ),
        _mapping_row(
            dimension="nationality_or_region",
            source_id="S08",
            source_entity_kind="country",
            source_label="韓国・朝鮮",
            source_context={"region": "アジア州の国", "row_kind": "country", "subcategory": None},
            match_status="ambiguous",
            match_method="explicit_composite",
            canonical_ids=["isa-nationality:01_011", "isa-nationality:01_012"],
            canonical_labels=["韓国", "（朝鮮）"],
            targets_complete=True,
            reason="The NPA source category combines two separately published ISA categories.",
        ),
        _mapping_row(
            dimension="nationality_or_region",
            source_id="S08",
            source_entity_kind="country",
            source_label="その他",
            source_context={"region": "アジア州の国", "row_kind": "country", "subcategory": None},
            match_status="unmatched",
            match_method="explicit_unmatched",
            canonical_ids=[],
            canonical_labels=[],
            targets_complete=False,
            reason="The source does not publish the bucket membership.",
        ),
        _mapping_row(
            dimension="geography",
            source_id="S02",
            source_entity_kind="prefecture",
            source_label="北海道",
            source_context={
                "geography_type": "prefecture",
                "parent_region": "北海道",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="matched",
            match_method="exact_label",
            canonical_ids=["jp-prefecture:01"],
            canonical_labels=["北海道"],
            targets_complete=True,
            reason="Exactly one ISA prefecture category has the same label.",
        ),
        _mapping_row(
            dimension="geography",
            source_id="S02",
            source_entity_kind="prefecture",
            source_label="青森県",
            source_context={
                "geography_type": "prefecture",
                "parent_region": "東北",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="matched",
            match_method="exact_label",
            canonical_ids=["jp-prefecture:02"],
            canonical_labels=["青森県"],
            targets_complete=True,
            reason="Exactly one ISA prefecture category has the same label.",
        ),
        _mapping_row(
            dimension="geography",
            source_id="S02",
            source_entity_kind="police_region",
            source_label="東北",
            source_context={
                "geography_type": "police_region",
                "parent_region": "東北",
                "geography_semantics": "police_reporting_area_unresolved",
            },
            match_status="ambiguous",
            match_method="non_equivalent_geography",
            canonical_ids=[],
            canonical_labels=[],
            targets_complete=False,
            reason="This police statistical aggregate contains multiple prefectures.",
        ),
    ]
    _write_jsonl(mapping_run / "dimension_mappings.jsonl", mapping_rows)
    summary_path = mapping_run / "summary.json"
    _write_json(
        summary_path,
        {
            "mapping_schema_version": 1,
            "generated_at": "2026-08-30T22:00:00+09:00",
            "mapping_record_count": len(mapping_rows),
            "status_counts": {"matched": 3, "ambiguous": 3, "unmatched": 1},
        },
    )
    _write_json(
        mapping_root / "latest.json",
        {
            "mapping_schema_version": 1,
            "generated_at": "2026-08-30T22:00:00+09:00",
            "run_relpath": mapping_run.name,
            "summary_sha256": sha256_file(summary_path),
            "dimension_mappings_sha256": sha256_file(
                mapping_run / "dimension_mappings.jsonl"
            ),
        },
    )

    contracts_path = tmp_path / "indicator_contracts.json"
    _write_json(
        contracts_path,
        {
            "schema_version": 2,
            "processed_input_pins": {
                source_id: sha256_file(
                    processed_root / relpath / "normalized.jsonl"
                )
                for source_id, relpath in relpaths.items()
            },
            "contracts": [
                {
                    "indicator_id": "x_cleared_persons_exact",
                    "label_ja": "全国・国籍別 外国人検挙人員 ÷ 同国籍在留外国人数",
                    "label_en": "National cleared persons for all foreign nationals / resident foreign population of the same nationality",
                    "measure_kind": "public_data_derived_reference_ratio",
                    "canonical_formula": "numerator_value / denominator_value",
                    "numerator_source_id": "S08",
                    "numerator_metric": "cleared_persons",
                    "numerator_year": 2024,
                    "numerator_row_kind": "country",
                    "numerator_population_scope": "all_foreign",
                    "numerator_period_type": "calendar_year_flow",
                    "numerator_geography_semantics": "national_aggregate",
                    "denominator_source_id": "S14_2024_12",
                    "denominator_metric": "resident_population",
                    "denominator_period_end": "2024-12-31",
                    "denominator_population_scope": "resident_foreigners",
                    "denominator_period_type": "year_end_stock",
                    "denominator_geography_semantics": "registered_residence",
                    "geography_grain": "national",
                    "crosswalk_policy": "exact",
                    "expected_numerator_row_count": 4,
                    "display_multiplier": 1000,
                    "display_scale_status": "provisional",
                    "display_unit_label_ja": "人口1,000人当たり",
                    "display_unit_label_en": "per 1,000 persons",
                    "small_number_warning_policy_version": 1,
                    "small_number_warning_policy_status": "approved_project_heuristic",
                    "small_number_warning_denominator_threshold": 1000,
                    "small_number_warning_numerator_threshold": 20,
                    "default_ranking_behavior": "exclude_flagged",
                    "base_mismatch_flags": ["annual_flow_vs_point_in_time_stock"],
                    "ui_caveat": "年間の検挙人員を年末在留人口で割った参考比率。",
                },
                {
                    "indicator_id": "x_cleared_persons_as_published_mismatch",
                    "label_ja": "全国・国籍別 外国人検挙人員 ÷ 対応在留外国人数（公表区分ベース）",
                    "label_en": "National cleared persons for all foreign nationals / mapped resident foreign population (as-published categories)",
                    "measure_kind": "public_data_derived_reference_ratio",
                    "canonical_formula": "numerator_value / denominator_value",
                    "numerator_source_id": "S08",
                    "numerator_metric": "cleared_persons",
                    "numerator_year": 2024,
                    "numerator_row_kind": "country",
                    "numerator_population_scope": "all_foreign",
                    "numerator_period_type": "calendar_year_flow",
                    "numerator_geography_semantics": "national_aggregate",
                    "denominator_source_id": "S14_2024_12",
                    "denominator_metric": "resident_population",
                    "denominator_period_end": "2024-12-31",
                    "denominator_population_scope": "resident_foreigners",
                    "denominator_period_type": "year_end_stock",
                    "denominator_geography_semantics": "registered_residence",
                    "geography_grain": "national",
                    "crosswalk_policy": "as_published_mismatch",
                    "expected_numerator_row_count": 4,
                    "display_multiplier": 1000,
                    "display_scale_status": "provisional",
                    "display_unit_label_ja": "人口1,000人当たり",
                    "display_unit_label_en": "per 1,000 persons",
                    "small_number_warning_policy_version": 1,
                    "small_number_warning_policy_status": "approved_project_heuristic",
                    "small_number_warning_denominator_threshold": 1000,
                    "small_number_warning_numerator_threshold": 20,
                    "default_ranking_behavior": "exclude_flagged",
                    "base_mismatch_flags": ["annual_flow_vs_point_in_time_stock"],
                    "ui_caveat": "国籍区分不一致を残したまま対応する在留人口で割った参考比率。",
                },
                {
                    "indicator_id": "z_cleared_persons_prefecture",
                    "label_ja": "都道府県別 来日外国人検挙人員 ÷ 同都道府県在留外国人数",
                    "label_en": "Prefectural cleared persons for visiting foreign nationals / resident foreign population in the same prefecture",
                    "measure_kind": "public_data_derived_reference_ratio",
                    "canonical_formula": "numerator_value / denominator_value",
                    "numerator_source_id": "S02",
                    "numerator_metric": "cleared_persons",
                    "numerator_year": 2025,
                    "numerator_row_kind": "prefecture",
                    "numerator_offense_scope": "criminal_and_special_law",
                    "numerator_population_scope": "visiting_foreign",
                    "numerator_period_type": "calendar_year_flow",
                    "numerator_geography_semantics": "police_reporting_area_unresolved",
                    "denominator_source_id": "S14",
                    "denominator_metric": "resident_population",
                    "denominator_period_end": "2025-12-31",
                    "denominator_population_scope": "resident_foreigners",
                    "denominator_period_type": "year_end_stock",
                    "denominator_geography_semantics": "registered_residence",
                    "geography_grain": "prefecture",
                    "crosswalk_policy": "exact",
                    "expected_numerator_row_count": 2,
                    "display_multiplier": 1000,
                    "display_scale_status": "provisional",
                    "display_unit_label_ja": "人口1,000人当たり",
                    "display_unit_label_en": "per 1,000 persons",
                    "small_number_warning_policy_version": 1,
                    "small_number_warning_policy_status": "approved_project_heuristic",
                    "small_number_warning_denominator_threshold": 1000,
                    "small_number_warning_numerator_threshold": 20,
                    "default_ranking_behavior": "exclude_flagged",
                    "base_mismatch_flags": [
                        "annual_flow_vs_point_in_time_stock",
                        "visitor_vs_resident_population_mismatch",
                        "police_reporting_area_unresolved",
                    ],
                    "ui_caveat": "警察統計上の都道府県等別集計区分と在留人口を組み合わせた参考比率。",
                },
            ],
        },
    )
    return {
        "catalog_path": processed_root / "_catalog" / "artifacts.jsonl",
        "processed_root": processed_root,
        "mapping_latest_path": mapping_root / "latest.json",
        "contracts_path": contracts_path,
        "output_root": output_root,
    }


def _normalized_path(fixture, source_id: str) -> Path:
    catalog_rows = [
        json.loads(line)
        for line in fixture["catalog_path"].read_text(encoding="utf-8").splitlines()
    ]
    row = next(item for item in catalog_rows if item["source_id"] == source_id)
    return fixture["processed_root"] / row["processed_relpath"] / "normalized.jsonl"


def _rewrite_mapping_rows(fixture, transform) -> None:
    latest = json.loads(fixture["mapping_latest_path"].read_text(encoding="utf-8"))
    mapping_path = (
        fixture["mapping_latest_path"].parent
        / latest["run_relpath"]
        / "dimension_mappings.jsonl"
    )
    rows = [json.loads(line) for line in mapping_path.read_text(encoding="utf-8").splitlines()]
    _write_jsonl(mapping_path, [transform(row) for row in rows])
    latest["dimension_mappings_sha256"] = sha256_file(mapping_path)
    _write_json(fixture["mapping_latest_path"], latest)


def _rewrite_normalized_rows(fixture, source_id: str, rows) -> Path:
    path = _normalized_path(fixture, source_id)
    _write_jsonl(path, rows)
    run_path = path.parent / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["normalized_sha256"] = sha256_file(path)
    run["record_count"] = len(rows)
    _write_json(run_path, run)
    contracts = json.loads(fixture["contracts_path"].read_text(encoding="utf-8"))
    contracts["processed_input_pins"][source_id] = sha256_file(path)
    _write_json(fixture["contracts_path"], contracts)
    return path


def test_load_indicator_contracts_rejects_unknown_policy(tmp_path: Path):
    contracts_path = tmp_path / "indicator_contracts.json"
    _write_json(
        contracts_path,
        {
            "schema_version": 2,
            "contracts": [
                {
                    "indicator_id": "broken",
                    "label_ja": "broken",
                    "label_en": "broken",
                    "measure_kind": "public_data_derived_reference_ratio",
                    "canonical_formula": "numerator_value / denominator_value",
                    "numerator_source_id": "S08",
                    "numerator_metric": "cleared_persons",
                    "numerator_year": 2024,
                    "numerator_row_kind": "country",
                    "numerator_population_scope": "all_foreign",
                    "numerator_period_type": "calendar_year_flow",
                    "numerator_geography_semantics": "national_aggregate",
                    "denominator_source_id": "S14_2024_12",
                    "denominator_metric": "resident_population",
                    "denominator_period_end": "2024-12-31",
                    "denominator_population_scope": "resident_foreigners",
                    "denominator_period_type": "year_end_stock",
                    "denominator_geography_semantics": "registered_residence",
                    "geography_grain": "national",
                    "crosswalk_policy": "unknown",
                    "expected_numerator_row_count": 1,
                    "display_multiplier": 1000,
                    "display_scale_status": "provisional",
                    "display_unit_label_ja": "人口1,000人当たり",
                    "display_unit_label_en": "per 1,000 persons",
                    "small_number_warning_policy_version": 1,
                    "small_number_warning_policy_status": "approved_project_heuristic",
                    "small_number_warning_denominator_threshold": 1000,
                    "small_number_warning_numerator_threshold": 20,
                    "default_ranking_behavior": "exclude_flagged",
                    "base_mismatch_flags": [],
                    "ui_caveat": "broken",
                }
            ],
        },
    )

    try:
        load_indicator_contracts(contracts_path)
    except ValueError as error:
        assert "crosswalk_policy" in str(error)
    else:
        raise AssertionError("Expected invalid crosswalk_policy to be rejected")


def test_generation_stops_on_inconsistent_small_number_policy(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    contracts = json.loads(fixture["contracts_path"].read_text(encoding="utf-8"))
    contracts["contracts"][1]["small_number_warning_numerator_threshold"] = 10
    _write_json(fixture["contracts_path"], contracts)

    with pytest.raises(SchemaError, match="small-number warning policy must match"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:29:00+09:00",
        )


def test_generate_indicator_report_builds_exact_mismatch_and_prefecture_outputs(
    tmp_path: Path,
):
    fixture = _indicator_fixture(tmp_path)

    report = generate_indicator_report(
        catalog_path=fixture["catalog_path"],
        processed_root=fixture["processed_root"],
        mapping_latest_path=fixture["mapping_latest_path"],
        contracts_path=fixture["contracts_path"],
        output_root=fixture["output_root"],
        generated_at="2026-08-30T22:30:00+09:00",
    )

    rows = [
        json.loads(line)
        for line in (report.output_dir / "indicator_records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert report.record_count == len(rows)

    by_key = {
        (row["indicator_id"], row["published_label"]): row
        for row in rows
        if row["published_label"] is not None
    }

    vietnam_exact = by_key[("x_cleared_persons_exact", "ベトナム")]
    assert vietnam_exact["indicator_run_schema_version"] == 2
    assert vietnam_exact["calculation_status"] == "calculated"
    assert vietnam_exact["denominator_value"] == 15
    assert vietnam_exact["numerator_value"] == 3
    assert vietnam_exact["quotient"] == 0.2
    assert vietnam_exact["display_value"] == 200.0
    assert vietnam_exact["measure_kind"] == "public_data_derived_reference_ratio"
    assert vietnam_exact["canonical_formula"] == "numerator_value / denominator_value"
    assert vietnam_exact["display_formula"] == "quotient * display_multiplier"
    assert vietnam_exact["statistical_compatibility"] == "not_established"
    assert vietnam_exact["display_scale_status"] == "provisional"
    assert vietnam_exact["small_number_warning_policy_version"] == 1
    assert (
        vietnam_exact["small_number_warning_policy_status"]
        == "approved_project_heuristic"
    )
    assert vietnam_exact["small_number_warning_flags"] == [
        "small_denominator_base",
        "sparse_numerator_count",
    ]
    assert vietnam_exact["default_ranking_excluded"] is True
    assert vietnam_exact["numerator_context"]["population_scope"] == "all_foreign"
    assert (
        vietnam_exact["denominator_context"]["population_scope"]
        == "resident_foreigners"
    )

    china_exact = by_key[("x_cleared_persons_exact", "中国")]
    assert china_exact["calculation_status"] == "refused"
    assert china_exact["refusal_reason"] == "crosswalk_not_exact"
    assert china_exact["small_number_warning_flags"] == []
    assert china_exact["default_ranking_excluded"] is False

    china_mismatch = by_key[("x_cleared_persons_as_published_mismatch", "中国")]
    assert china_mismatch["calculation_status"] == "calculated"
    assert china_mismatch["denominator_value"] == 23
    assert "nationality_grouping_mismatch" in china_mismatch["mismatch_flags"]
    assert "canonical_target_incomplete" in china_mismatch["mismatch_flags"]

    korea_mismatch = by_key[("x_cleared_persons_as_published_mismatch", "韓国・朝鮮")]
    assert korea_mismatch["denominator_value"] == 10
    assert "nationality_grouping_mismatch" in korea_mismatch["mismatch_flags"]
    assert "canonical_target_incomplete" not in korea_mismatch["mismatch_flags"]

    other_mismatch = by_key[("x_cleared_persons_as_published_mismatch", "その他")]
    assert other_mismatch["calculation_status"] == "refused"
    assert other_mismatch["refusal_reason"] == "no_canonical_denominator_components"

    hokkaido_pref = by_key[("z_cleared_persons_prefecture", "北海道")]
    assert hokkaido_pref["calculation_status"] == "calculated"
    assert hokkaido_pref["denominator_value"] == 50
    assert hokkaido_pref["numerator_value"] == 10
    assert "police_reporting_area_unresolved" in hokkaido_pref["mismatch_flags"]
    assert hokkaido_pref["small_number_warning_flags"] == [
        "small_denominator_base",
        "sparse_numerator_count",
    ]
    assert hokkaido_pref["default_ranking_excluded"] is True

    assert ("z_cleared_persons_prefecture", "東北") not in by_key

    summary = json.loads(report.summary_path.read_text(encoding="utf-8"))
    assert summary["contract_count"] == 3
    assert summary["source_artifacts"]["S08"]["sha256"]
    assert summary["source_artifacts"]["S08"]["normalized_sha256"]
    assert summary["source_artifacts"]["S14"]["landing_url"].startswith("https://")
    assert summary["mismatch_flag_counts"]["annual_flow_vs_point_in_time_stock"] == 10
    assert summary["refusal_reason_counts"]["crosswalk_not_exact"] == 3
    assert summary["small_number_warning_policy"] == {
        "default_ranking_behavior": "exclude_flagged",
        "denominator_threshold": 1000,
        "numerator_threshold": 20,
        "policy_status": "approved_project_heuristic",
        "policy_version": 1,
    }
    assert summary["small_number_warning_counts"] == {
        "default_ranking_excluded": 6,
        "either_warning": 6,
        "small_denominator_base": 6,
        "sparse_numerator_count": 6,
    }

    latest = json.loads(report.latest_path.read_text(encoding="utf-8"))
    assert latest["indicator_run_schema_version"] == 2
    assert latest["indicator_records_csv_sha256"] == sha256_file(report.csv_path)


def test_indicator_cli_reports_generated_paths(tmp_path: Path, capsys):
    fixture = _indicator_fixture(tmp_path)

    result = indicator_main(
        [
            "--catalog",
            str(fixture["catalog_path"]),
            "--processed-root",
            str(fixture["processed_root"]),
            "--mapping-latest",
            str(fixture["mapping_latest_path"]),
            "--contracts",
            str(fixture["contracts_path"]),
            "--output-root",
            str(fixture["output_root"]),
            "--generated-at",
            "2026-08-30T22:30:00+09:00",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert result == 0
    assert summary["record_count"] == 10
    assert summary["status_counts"]["calculated"] == 6
    assert summary["status_counts"]["refused"] == 4
    assert Path(summary["output_dir"]).exists()


def test_contract_requires_strict_denominator_period(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    data = json.loads(fixture["contracts_path"].read_text(encoding="utf-8"))
    data["contracts"][0]["denominator_period_end"] = "2024"
    _write_json(fixture["contracts_path"], data)

    with pytest.raises(SchemaError, match="denominator_period_end"):
        load_indicator_contracts(fixture["contracts_path"])


def test_generation_stops_on_numerator_population_scope_drift(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S08")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["population_scope"] = "unexpected_scope"
    _rewrite_normalized_rows(fixture, "S08", rows)

    with pytest.raises(SchemaError, match="population_scope"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:31:00+09:00",
        )


def test_generation_stops_on_duplicate_numerator_cell(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S08")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows.append(dict(rows[0]))
    _rewrite_normalized_rows(fixture, "S08", rows)

    with pytest.raises(SchemaError, match="Duplicate numerator cell"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:32:00+09:00",
        )


def test_generation_stops_when_expected_prefecture_is_missing(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S02")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    _rewrite_normalized_rows(
        fixture,
        "S02",
        [row for row in rows if row.get("geography") != "青森県"],
    )

    with pytest.raises(SchemaError, match="expected_numerator_row_count"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:33:00+09:00",
        )


def test_exact_policy_refuses_incomplete_mapping_targets(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)

    def mark_vietnam_incomplete(row):
        if row["source_id"] == "S08" and row["source_label"] == "ベトナム":
            row["targets_complete"] = False
        return row

    _rewrite_mapping_rows(fixture, mark_vietnam_incomplete)
    report = generate_indicator_report(
        catalog_path=fixture["catalog_path"],
        processed_root=fixture["processed_root"],
        mapping_latest_path=fixture["mapping_latest_path"],
        contracts_path=fixture["contracts_path"],
        output_root=fixture["output_root"],
        generated_at="2026-08-30T22:34:00+09:00",
    )
    rows = [json.loads(line) for line in report.jsonl_path.read_text(encoding="utf-8").splitlines()]
    vietnam = next(
        row
        for row in rows
        if row["indicator_id"] == "x_cleared_persons_exact"
        and row["published_label"] == "ベトナム"
    )
    assert vietnam["calculation_status"] == "refused"
    assert vietnam["refusal_reason"] == "crosswalk_not_exact"


def test_generation_stops_on_duplicate_catalog_source(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    lines = fixture["catalog_path"].read_text(encoding="utf-8").splitlines()
    fixture["catalog_path"].write_text("\n".join(lines + [lines[0]]) + "\n", encoding="utf-8")

    with pytest.raises(SchemaError, match="Duplicate catalog source_id"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:35:00+09:00",
        )


def test_generation_stops_when_normalized_input_hash_changes(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S08")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["cleared_cases"] += 1
    _write_jsonl(path, rows)

    with pytest.raises(IntegrityError, match="normalized input hash"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:36:00+09:00",
        )


def test_generation_stops_when_run_and_input_differ_from_contract_pin(
    tmp_path: Path,
):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S08")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["cleared_cases"] += 1
    _write_jsonl(path, rows)
    run_path = path.parent / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["normalized_sha256"] = sha256_file(path)
    _write_json(run_path, run)

    with pytest.raises(IntegrityError, match="contract pin"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:38:00+09:00",
        )


def test_generation_stops_on_negative_population_cell(tmp_path: Path):
    fixture = _indicator_fixture(tmp_path)
    path = _normalized_path(fixture, "S14_2024_12")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["value"] = -1
    _rewrite_normalized_rows(fixture, "S14_2024_12", rows)

    with pytest.raises(SchemaError, match="Population value must be non-negative"):
        generate_indicator_report(
            catalog_path=fixture["catalog_path"],
            processed_root=fixture["processed_root"],
            mapping_latest_path=fixture["mapping_latest_path"],
            contracts_path=fixture["contracts_path"],
            output_root=fixture["output_root"],
            generated_at="2026-08-30T22:37:00+09:00",
        )


def test_production_contract_registry_has_current_exact_counts():
    project_root = Path(__file__).resolve().parents[1]
    registry = json.loads(
        (project_root / "config" / "indicator_contracts.json").read_text(
            encoding="utf-8"
        )
    )
    contracts = load_indicator_contracts(project_root / "config" / "indicator_contracts.json")

    assert set(registry["processed_input_pins"]) == {
        "S02",
        "S08",
        "S09",
        "S14",
        "S14_2024_12",
    }
    assert registry["processed_input_pins"]["S08"] == (
        "3fe1d78fe8d4c12b436e09b42641276cd2ba39fc1f1c446af588266d5b6d0029"
    )
    assert len(contracts) == 10
    assert {
        contract.small_number_warning_policy_version for contract in contracts
    } == {1}
    assert {
        contract.small_number_warning_policy_status for contract in contracts
    } == {"approved_project_heuristic"}
    assert {
        contract.small_number_warning_denominator_threshold for contract in contracts
    } == {1000}
    assert {
        contract.small_number_warning_numerator_threshold for contract in contracts
    } == {20}
    assert {contract.default_ranking_behavior for contract in contracts} == {
        "exclude_flagged"
    }
    assert {
        contract.expected_numerator_row_count
        for contract in contracts
        if contract.numerator_source_id == "S02"
    } == {47}
    assert {
        contract.expected_numerator_row_count
        for contract in contracts
        if contract.numerator_source_id == "S08"
    } == {24}
    assert {
        contract.expected_numerator_row_count
        for contract in contracts
        if contract.numerator_source_id == "S09"
    } == {25}
