import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import nationality_crime_atlas.compact_export as compact_export_module
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


def _source_artifact(source_id: str, source_table: str):
    return {
        "series_id": "fixture-%s" % source_id.lower(),
        "dataset": "Fixture source %s" % source_id,
        "publisher": "Fixture official publisher",
        "source_table": source_table,
        "source_period": "2024 fixture period",
        "sha256": (source_id[-1].lower() if source_id[-1].lower() in "abcdef" else "5")
        * 64,
        "landing_url": "https://example.test/%s" % source_id.lower(),
        "download_url": "https://example.test/%s/data.xlsx" % source_id.lower(),
        "retrieved_at": "2026-09-01T13:00:00+09:00",
        "revision": "fixture",
        "verification_level": "binary_and_primary",
        "normalized_sha256": "6" * 64,
        "raw_relpath": "/private/local/raw/%s.xlsx" % source_id.lower(),
        "processed_relpath": "/private/local/processed/%s" % source_id.lower(),
    }


def _s08_source_artifact():
    return {
        "series_id": "npa-all-foreign-nationality-crime",
        "dataset": "NPA nationality table fixture",
        "publisher": "National Police Agency of Japan",
        "source_table": "130",
        "source_period": "2024 annual",
        "sha256": "1" * 64,
        "landing_url": "https://example.test/npa",
        "download_url": "https://example.test/npa/table130.xlsx",
        "retrieved_at": "2026-09-01T13:00:00+09:00",
        "revision": "fixture",
        "verification_level": "binary_and_primary",
        "normalized_sha256": "2" * 64,
        "raw_relpath": "/private/local/raw/s08.xlsx",
        "processed_relpath": "/private/local/processed/s08",
    }


def _indicator_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "processed" / "_indicators"
    run_dir = root / "20260901_133239_indicators"
    records_path = run_dir / "indicator_records.jsonl"
    summary_path = run_dir / "summary.json"
    records_hash = _write_jsonl(
        records_path,
        [
            {
                "indicator_run_schema_version": 2,
                "indicator_id": "x_cleared_cases_as_published_mismatch",
                "label_ja": "全国・国籍別 外国人検挙件数 ÷ 対応在留外国人数（公表区分ベース）",
                "label_en": "National cleared cases / mapped resident foreign population",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "display_formula": "quotient * display_multiplier",
                "statistical_compatibility": "not_established",
                "entity_dimension": "nationality",
                "geography_label": "日本全国",
                "geography_id": "jp:all",
                "geography_type": "national",
                "published_label": "イラン",
                "year": 2024,
                "period_end": "2024-12-31",
                "numerator_source_id": "S08",
                "denominator_source_id": "S14_2024_12",
                "numerator_metric": "cleared_cases",
                "denominator_metric": "resident_population",
                "numerator_value": 79,
                "denominator_value": 4399,
                "quotient": 0.01795862696067288,
                "display_multiplier": 1000.0,
                "display_scale_status": "provisional",
                "display_unit_label_ja": "人口1,000人当たり",
                "display_unit_label_en": "per 1,000 persons",
                "display_value": 17.95862696067288,
                "crosswalk_policy": "as_published_mismatch",
                "crosswalk_status": "matched",
                "targets_complete": True,
                "calculation_status": "calculated",
                "refusal_reason": None,
                "mismatch_flags": [
                    "all_foreign_vs_resident_population_mismatch",
                    "annual_flow_vs_point_in_time_stock",
                ],
                "canonical_component_ids": ["isa-nationality:01_006"],
                "canonical_component_labels": ["イラン"],
                "numerator_context": {
                    "geography_semantics": "national_aggregate",
                    "period_type": "calendar_year_flow",
                    "population_scope": "all_foreign",
                    "region": "アジア州の国",
                    "row_kind": "country",
                },
                "denominator_context": {
                    "geography_grain": "national",
                    "geography_semantics": "registered_residence",
                    "period_end": "2024-12-31",
                    "period_type": "year_end_stock",
                    "population_scope": "resident_foreigners",
                },
                "ui_caveat": "official crime rateではない。",
                "small_number_warning_policy_version": 1,
                "small_number_warning_policy_status": "approved_project_heuristic",
                "small_number_warning_flags": [],
                "default_ranking_behavior": "exclude_flagged",
                "default_ranking_excluded": False,
            },
            {
                "indicator_run_schema_version": 2,
                "indicator_id": "z_recognized_cases_prefecture_all_residents",
                "label_ja": "都道府県別 aggregate",
                "label_en": "Prefecture aggregate",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "display_formula": "quotient * display_multiplier",
                "statistical_compatibility": "not_established",
                "entity_dimension": "prefecture",
                "geography_label": "東京都",
                "geography_id": "jp-prefecture:13",
                "geography_type": "prefecture",
                "published_label": "東京都",
                "year": 2025,
                "period_end": "2025-12-31",
                "numerator_source_id": "S02",
                "denominator_source_id": "S14",
                "numerator_metric": "recognized_cases",
                "denominator_metric": "resident_population",
                "numerator_value": None,
                "denominator_value": None,
                "quotient": None,
                "display_multiplier": 1000.0,
                "display_scale_status": "provisional",
                "display_unit_label_ja": "人口1,000人当たり",
                "display_unit_label_en": "per 1,000 persons",
                "display_value": None,
                "crosswalk_policy": "exact",
                "crosswalk_status": "matched",
                "targets_complete": True,
                "calculation_status": "refused",
                "refusal_reason": "no_canonical_denominator_components",
                "mismatch_flags": ["numerator_not_published"],
                "canonical_component_ids": [],
                "canonical_component_labels": [],
                "numerator_context": {"row_kind": "prefecture"},
                "denominator_context": {"population_scope": "resident_foreigners"},
                "ui_caveat": "official crime rateではない。",
                "small_number_warning_policy_version": 1,
                "small_number_warning_policy_status": "approved_project_heuristic",
                "small_number_warning_flags": [],
                "default_ranking_behavior": "exclude_flagged",
                "default_ranking_excluded": False,
            },
        ],
    )
    _write_json(
        summary_path,
        {
            "indicator_run_schema_version": 2,
            "generated_at": "2026-09-01T13:32:39+09:00",
            "indicator_record_count": 2,
            "status_counts": {"calculated": 1, "refused": 1},
            "source_artifacts": {
                "S08": _s08_source_artifact(),
                "S14_2024_12": _source_artifact("S14_2024_12", "T1"),
                "S02": _source_artifact("S02", "13"),
                "S14": _source_artifact("S14", "T1"),
            },
        },
    )
    _write_json(
        root / "latest.json",
        {
            "indicator_run_schema_version": 2,
            "generated_at": "2026-09-01T13:32:39+09:00",
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "indicator_records_sha256": records_hash,
            "indicator_records_csv_sha256": "0" * 64,
        },
    )
    return root / "latest.json"


def _all_resident_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "processed" / "_all_resident_context"
    run_dir = root / "20260901_153100_all_resident_context"
    records_path = run_dir / "regional_context_records.jsonl"
    summary_path = run_dir / "summary.json"
    recognized_rows = [
            {
                "all_resident_context_schema_version": 1,
                "context_id": "all_resident_recognized_cases",
                "label_ja": "都道府県等別 刑法犯認知件数 ÷ 10月1日総人口",
                "label_en": "Recognized criminal-code cases / October 1 total population",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "display_formula": "quotient * display_multiplier",
                "statistical_compatibility": "not_established",
                "geography_label": "東京都",
                "geography_id": "jp-prefecture:13",
                "geography_type": "prefecture",
                "year": 2024,
                "reference_date": "2024-10-01",
                "numerator_source_id": "S15",
                "denominator_source_id": "S16",
                "numerator_metric": "recognized_cases",
                "denominator_metric": "total_population",
                "numerator_value": 93359,
                "denominator_value": 13969000,
                "quotient": 0.006683370320710144,
                "display_multiplier": 100000.0,
                "display_scale_status": "provisional",
                "display_unit_label_ja": "人口10万人当たり",
                "display_unit_label_en": "per 100,000 residents",
                "display_value": 668.3370320710143,
                "crosswalk_policy": "exact",
                "crosswalk_status": "matched",
                "targets_complete": True,
                "calculation_status": "calculated",
                "refusal_reason": None,
                "mismatch_flags": [
                    "annual_flow_vs_point_in_time_population",
                    "criminal_code_scope_only",
                    "numerator_residency_scope_not_established",
                    "police_reporting_area_unresolved",
                    "police_reporting_area_vs_population_estimate_prefecture",
                    "total_population_rounded_to_nearest_1000",
                ],
                "canonical_component_ids": ["jp-prefecture:13"],
                "canonical_component_labels": ["東京都"],
                "numerator_context": {
                    "population_scope": "all_persons",
                    "period_type": "annual_flow",
                    "residency_scope": "not_established",
                    "offense_scope": "criminal_code_excluding_traffic_negligence",
                    "geography_semantics": "police_reporting_area_unresolved",
                    "parent_region": "関東",
                },
                "denominator_context": {
                    "population_scope": "total_population",
                    "period_type": "point_in_time_stock",
                    "reference_date": "2024-10-01",
                    "geography_semantics": "population_estimate_prefecture",
                    "source_unit": "1000_persons",
                    "rounding": "nearest_1000_persons",
                },
                "ui_caveat": "official crime rateではない。",
            },
            {
                "all_resident_context_schema_version": 1,
                "context_id": "all_resident_recognized_cases",
                "label_ja": "都道府県等別 刑法犯認知件数 ÷ 10月1日総人口",
                "label_en": "Recognized criminal-code cases / October 1 total population",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "display_formula": "quotient * display_multiplier",
                "statistical_compatibility": "not_established",
                "geography_label": "都道府県別",
                "geography_id": "request-scope:jp-prefectures:japanese",
                "geography_type": "prefecture_collection",
                "year": 2024,
                "reference_date": "2024-10-01",
                "numerator_source_id": None,
                "denominator_source_id": "S16",
                "numerator_metric": "recognized_cases",
                "denominator_metric": "total_population",
                "numerator_value": None,
                "denominator_value": None,
                "quotient": None,
                "display_multiplier": 100000.0,
                "display_scale_status": "provisional",
                "display_unit_label_ja": "人口10万人当たり",
                "display_unit_label_en": "per 100,000 residents",
                "display_value": None,
                "crosswalk_policy": "exact",
                "crosswalk_status": None,
                "targets_complete": False,
                "calculation_status": "refused",
                "refusal_reason": "japanese_prefecture_numerator_unpublished",
                "mismatch_flags": [
                    "numerator_not_published",
                    "primary_baseline_is_all_residents",
                ],
                "canonical_component_ids": [],
                "canonical_component_labels": [],
                "numerator_context": {
                    "requested_geography_grain": "prefecture",
                    "requested_population_scope": "japanese_nationals",
                    "requested_metric": "recognized_cases",
                    "requested_year": 2024,
                },
                "denominator_context": {
                    "population_scope": "total_population",
                    "period_type": "point_in_time_stock",
                    "reference_date": "2024-10-01",
                },
                "ui_caveat": "非公表なので生成しない。",
            },
        ]
    cleared_rows = []
    for source_row in recognized_rows:
        row = dict(source_row)
        row.update(
            {
                "context_id": "all_resident_cleared_cases",
                "label_ja": "都道府県等別 刑法犯検挙件数 ÷ 10月1日総人口",
                "label_en": "Cleared criminal-code cases / October 1 total population",
                "numerator_metric": "cleared_cases",
                "ui_caveat": "official crime rateではない。",
            }
        )
        row["numerator_context"] = dict(source_row["numerator_context"])
        if row["calculation_status"] == "calculated":
            row["numerator_value"] = 33_961
            row["quotient"] = 33_961 / 13_969_000
            row["display_value"] = row["quotient"] * 100_000
        else:
            row["numerator_context"]["requested_metric"] = "cleared_cases"
        cleared_rows.append(row)
    records_hash = _write_jsonl(records_path, recognized_rows + cleared_rows)
    _write_json(
        summary_path,
        {
            "all_resident_context_schema_version": 1,
            "generated_at": "2026-09-01T15:31:00+09:00",
            "record_count": 4,
            "status_counts": {"calculated": 2, "refused": 2},
            "source_artifacts": {
                "S15": _source_artifact("S15", "3"),
                "S16": {
                    "series_id": "npa-total-population-prefecture",
                    "dataset": "NPA population table fixture",
                    "publisher": "National Police Agency of Japan; Statistics Bureau of Japan",
                    "source_table": "144",
                    "source_period": "2024-10-01 total population",
                    "sha256": "3" * 64,
                    "landing_url": "https://example.test/npa",
                    "download_url": "https://example.test/npa/table144.xlsx",
                    "retrieved_at": "2026-09-01T13:01:00+09:00",
                    "revision": "fixture",
                    "verification_level": "binary_and_primary",
                    "normalized_sha256": "4" * 64,
                    "raw_relpath": "/private/local/raw/s16.xlsx",
                    "processed_relpath": "/private/local/processed/s16",
                }
            },
        },
    )
    _write_json(
        root / "latest.json",
        {
            "all_resident_context_schema_version": 1,
            "generated_at": "2026-09-01T15:31:00+09:00",
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "regional_context_records_sha256": records_hash,
            "regional_context_records_csv_sha256": "0" * 64,
        },
    )
    return root / "latest.json"


def _comparison_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "processed" / "_nationality_comparison"
    run_dir = root / "20260903_070000_nationality_comparison"
    records_path = run_dir / "nationality_comparison_records.jsonl"
    summary_path = run_dir / "summary.json"
    records_hash = _write_jsonl(
        records_path,
        [
            {
                "nationality_comparison_schema_version": 1,
                "comparison_id": "nationality_criminal_code_cleared_persons",
                "label_ja": "全国・国籍等別 刑法犯検挙人員 ÷ 対応人口",
                "label_en": "National criminal-code cleared persons by nationality / corresponding population",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "display_formula": "quotient * display_multiplier",
                "statistical_compatibility": "not_established",
                "display_multiplier": 1000.0,
                "display_unit_label_ja": "人口1,000人当たり",
                "display_unit_label_en": "per 1,000 persons",
                "default_display_behavior": "include_all_with_warnings",
                "interpretation_policy": "observed_values_without_intrinsic_group_inference",
                "ui_caveat": "集団の本質や個人riskを示さない。",
                "entity_dimension": "nationality",
                "entity_id": "jp-nationality:japanese",
                "published_label": "日本",
                "display_label": "日本（残差による参考値）",
                "source_order": 0,
                "is_japanese_reference": True,
                "year": 2024,
                "denominator_reference_date": "2024-10-01",
                "numerator_source_ids": ["S08", "S15"],
                "denominator_source_id": "S17",
                "numerator_metric": "criminal_code_cleared_persons",
                "denominator_metric": "corresponding_population",
                "numerator_value": 181362,
                "denominator_value": 120296000,
                "quotient": 0.001507631176431469,
                "display_value": 1.507631176431469,
                "calculation_status": "calculated",
                "refusal_reason": None,
                "crosswalk_status": None,
                "targets_complete": True,
                "canonical_component_ids": ["jp-nationality:japanese"],
                "canonical_component_labels": ["日本"],
                "derivation_method": "residual_subtraction",
                "derivation_formula": "S15 - S08",
                "numerator_components": [
                    {"source_id": "S15", "role": "minuend", "value": 191826},
                    {"source_id": "S08", "role": "subtrahend", "value": 10464},
                ],
                "mismatch_flags": [
                    "japanese_numerator_derived_by_residual_subtraction"
                ],
                "small_number_warning_flags": [],
                "display_included": True,
                "numerator_context": {"population_scope": "derived_japanese_residual"},
                "denominator_context": {"population_scope": "japanese_population"},
            }
        ],
    )
    _write_json(
        summary_path,
        {
            "nationality_comparison_schema_version": 1,
            "generated_at": "2026-09-03T07:00:00+09:00",
            "record_count": 1,
            "status_counts": {"calculated": 1, "refused": 0},
            "source_artifacts": {
                "S08": _s08_source_artifact(),
                "S14_2024_12": _source_artifact("S14_2024_12", "T1"),
                "S15": _source_artifact("S15", "3"),
                "S17": _source_artifact("S17", "2"),
            },
        },
    )
    _write_json(
        root / "latest.json",
        {
            "nationality_comparison_schema_version": 1,
            "generated_at": "2026-09-03T07:00:00+09:00",
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "nationality_comparison_records_sha256": records_hash,
            "nationality_comparison_records_csv_sha256": "0" * 64,
        },
    )
    return root / "latest.json"


def _offense_composition_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "processed" / "_offense_composition"
    run_dir = root / "20260903_080000_offense_composition"
    records_path = run_dir / "offense_composition_records.jsonl"
    summary_path = run_dir / "summary.json"
    categories = [
        ("heinous", "凶悪犯", "#b5443c", "official_high_severity_category"),
        ("assaultive", "粗暴犯", "#d17c32", "not_a_project_severity_classification"),
        ("theft", "窃盗犯", "#c7a83d", "not_a_project_severity_classification"),
        ("intellectual", "知能犯", "#327a92", "not_a_project_severity_classification"),
        ("morals", "風俗犯", "#775d9b", "not_a_project_severity_classification"),
        ("other_criminal_code", "その他の刑法犯", "#778187", "not_a_project_severity_classification"),
    ]
    entities = [
        (
            "jp-nationality:japanese",
            "日本",
            "日本（残差による参考値）",
            0,
            True,
            "derived_japanese_residual",
            "residual_subtraction",
            ["S15", "S08"],
            (10, 20, 30, 10, 5, 5),
            (5, 10, 15, 5, 3, 2),
        ),
        (
            "npa:S08:row-22",
            "中国",
            "中国",
            22,
            False,
            "published_nationality",
            "published_row",
            ["S08"],
            (2, 4, 8, 2, 1, 3),
            (1, 2, 4, 1, 1, 1),
        ),
    ]
    records = []
    for (
        entity_id,
        published_label,
        display_label,
        source_order,
        is_japanese_reference,
        entity_kind,
        derivation_method,
        source_ids,
        case_values,
        person_values,
    ) in entities:
        case_total = sum(case_values)
        person_total = sum(person_values)
        for index, (offense_id, label, color, severity_role) in enumerate(
            categories, start=1
        ):
            records.append(
                {
                    "offense_composition_schema_version": 1,
                    "composition_id": "nationality_criminal_code_offense_composition",
                    "label_ja": "日本を含む国籍等別・刑法犯上位6区分の構成",
                    "label_en": "Criminal-code offense composition by nationality including Japan",
                    "interpretation_policy": "patterns_without_intrinsic_group_inference",
                    "ui_caveat": "構成比は犯罪の多寡や個人riskを示さない。",
                    "year": 2024,
                    "entity_id": entity_id,
                    "published_label": published_label,
                    "display_label": display_label,
                    "source_order": source_order,
                    "entity_kind": entity_kind,
                    "is_japanese_reference": is_japanese_reference,
                    "offense_id": offense_id,
                    "offense_label": label,
                    "category_display_order": index,
                    "category_color": color,
                    "official_severity_role": severity_role,
                    "cleared_cases": case_values[index - 1],
                    "cleared_persons": person_values[index - 1],
                    "criminal_code_cleared_cases_total": case_total,
                    "criminal_code_cleared_persons_total": person_total,
                    "cleared_cases_share": case_values[index - 1] / case_total,
                    "cleared_persons_share": person_values[index - 1] / person_total,
                    "cleared_cases_share_status": "calculated",
                    "cleared_persons_share_status": "calculated",
                    "calculation_status": "calculated",
                    "refusal_reason": None,
                    "derivation_method": derivation_method,
                    "derivation_formula": "fixture formula",
                    "numerator_source_ids": source_ids,
                    "source_components": [],
                    "mismatch_flags": [],
                    "small_number_warning_flags": [],
                    "display_included": True,
                }
            )
    records_hash = _write_jsonl(records_path, records)
    category_definitions = [
        {
            "offense_id": offense_id,
            "label_ja": label,
            "color": color,
            "display_order": index,
            "official_severity_role": severity_role,
        }
        for index, (offense_id, label, color, severity_role) in enumerate(
            categories, start=1
        )
    ]
    clustering = {
        metric: {
            "distance": "jensen_shannon",
            "log_base": 2,
            "linkage": "average",
            "input": "within_entity_composition_share",
            "order": [entity[0] for entity in entities],
            "not_clustered_zero_total_entity_ids": [],
        }
        for metric in ("cleared_cases", "cleared_persons")
    }
    _write_json(
        summary_path,
        {
            "offense_composition_schema_version": 1,
            "generated_at": "2026-09-03T08:00:00+09:00",
            "composition_id": "nationality_criminal_code_offense_composition",
            "record_count": len(records),
            "entity_count": len(entities),
            "small_number_total_threshold": 20,
            "status_counts": {"calculated": len(records), "refused": 0},
            "category_definitions": category_definitions,
            "clustering": clustering,
            "source_artifacts": {
                "S08": _s08_source_artifact(),
                "S15": _source_artifact("S15", "3"),
            },
        },
    )
    _write_json(
        root / "latest.json",
        {
            "offense_composition_schema_version": 1,
            "generated_at": "2026-09-03T08:00:00+09:00",
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "offense_composition_records_sha256": records_hash,
            "offense_composition_records_csv_sha256": "0" * 64,
        },
    )
    return root / "latest.json"


def _clearance_share_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "processed" / "_clearance_share_trend"
    run_dir = root / "20260905_181000_clearance_share_trend"
    records_path = run_dir / "clearance_share_records.jsonl"
    summary_path = run_dir / "summary.json"
    records = []
    values = {
        "all_foreign": {
            "label": "外国人全体",
            "source_id": "S08",
            "cleared_cases": (60, 600),
            "cleared_persons": (40, 300),
        },
        "visiting_foreign": {
            "label": "来日外国人",
            "source_id": "S09",
            "source_ids": ["S09"],
            "cleared_cases": (40, 600),
            "cleared_persons": (25, 300),
        },
        "all_foreign_minus_visiting_foreign": {
            "label": "外国人全体−来日外国人（差分）",
            "source_id": "S08",
            "source_ids": ["S08", "S09"],
            "cleared_cases": (20, 600),
            "cleared_persons": (15, 300),
        },
    }
    for foreign_scope, definition in values.items():
        for metric in ("cleared_cases", "cleared_persons"):
            numerator, denominator = definition[metric]
            records.append(
                {
                    "national_clearance_share_schema_version": 2,
                    "trend_id": "national_criminal_code_clearance_foreign_share",
                    "label_ja": "全国の刑法犯検挙（日本人等を含む）に占める外国人区分の割合",
                    "label_en": "Foreign-scope share of national criminal-code clearances",
                    "interpretation_policy": "share_of_clearances_not_population_risk",
                    "ui_caveat": "検挙全体に占める構成比であり、人口当たりの犯罪率ではない。",
                    "year": 2024,
                    "foreign_scope": foreign_scope,
                    "foreign_scope_label_ja": definition["label"],
                    "metric": metric,
                    "metric_label_ja": "検挙件数" if metric == "cleared_cases" else "検挙人員",
                    "numerator_value": numerator,
                    "denominator_value": denominator,
                    "quotient": numerator / denominator,
                    "display_multiplier": 100,
                    "display_unit_label_ja": "%",
                    "display_value": numerator / denominator * 100,
                    "calculation_status": "calculated",
                    "refusal_reason": None,
                    "numerator_source_id": definition["source_id"],
                    "numerator_source_ids": definition.get(
                        "source_ids", [definition["source_id"]]
                    ),
                    "denominator_source_id": "S15",
                    "derivation_method": "direct_published_counts_division",
                    "derivation_formula": "fixture formula",
                    "source_components": [],
                    "mismatch_flags": [
                        "share_of_clearance_counts_not_population_rate"
                    ],
                }
            )
    records_hash = _write_jsonl(records_path, records)
    _write_json(
        summary_path,
        {
            "national_clearance_share_schema_version": 2,
            "generated_at": "2026-09-05T18:10:00+09:00",
            "trend_id": "national_criminal_code_clearance_foreign_share",
            "record_count": len(records),
            "year_count": 1,
            "years": [2024],
            "status_counts": {"calculated": len(records), "refused": 0},
            "source_artifacts": {
                "S08": _s08_source_artifact(),
                "S09": _source_artifact("S09", "131"),
                "S15": _source_artifact("S15", "3"),
            },
        },
    )
    _write_json(
        root / "latest.json",
        {
            "national_clearance_share_schema_version": 2,
            "generated_at": "2026-09-05T18:10:00+09:00",
            "run_relpath": run_dir.name,
            "summary_sha256": sha256_file(summary_path),
            "clearance_share_records_sha256": records_hash,
            "clearance_share_records_csv_sha256": "0" * 64,
        },
    )
    return root / "latest.json"


def test_generate_compact_export_builds_public_dashboard_payload(tmp_path):
    from nationality_crime_atlas.compact_export import generate_compact_export

    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)

    report = generate_compact_export(
        indicator_latest_path=indicator_latest_path,
        all_resident_latest_path=all_resident_latest_path,
        nationality_comparison_latest_path=comparison_latest_path,
        offense_composition_latest_path=offense_latest_path,
        clearance_share_latest_path=clearance_share_latest_path,
        output_root=tmp_path / "output" / "compact_export",
        generated_at="2026-09-01T18:00:00+09:00",
    )

    payload = json.loads((report.output_dir / "dashboard_export.json").read_text(encoding="utf-8"))
    latest = json.loads(report.latest_path.read_text(encoding="utf-8"))
    summary = json.loads(report.summary_path.read_text(encoding="utf-8"))

    assert payload["compact_export_schema_version"] == 7
    assert payload["publication_policy"]["primary_view"] == "all_resident_context"
    assert payload["publication_policy"]["secondary_view"] == "nationality_comparison"
    assert payload["publication_policy"]["supplementary_view"] == "nationality_indicators"
    assert payload["publication_policy"]["composition_view"] == "offense_composition"
    assert payload["publication_policy"]["clearance_share_view"] == (
        "national_criminal_code_clearance_foreign_share"
    )
    assert payload["source_runs"]["nationality_indicators"]["latest_manifest"]["run_relpath"] == (
        "20260901_133239_indicators"
    )
    assert payload["source_runs"]["all_resident_context"]["latest_manifest"]["run_relpath"] == (
        "20260901_153100_all_resident_context"
    )
    assert payload["source_runs"]["nationality_comparison"]["latest_manifest"][
        "run_relpath"
    ] == "20260903_070000_nationality_comparison"
    assert payload["source_runs"]["offense_composition"]["latest_manifest"][
        "run_relpath"
    ] == "20260903_080000_offense_composition"
    assert payload["source_runs"]["clearance_share_trend"]["latest_manifest"][
        "run_relpath"
    ] == "20260905_181000_clearance_share_trend"
    assert payload["definitions"]["indicator_ids"]["x_cleared_cases_as_published_mismatch"][
        "label_ja"
    ].startswith("全国・国籍別")
    assert payload["definitions"]["context_ids"]["all_resident_recognized_cases"][
        "display_unit_label_ja"
    ] == "人口10万人当たり"
    gap_definition = payload["definitions"]["context_ids"][
        "all_resident_same_year_recognition_clearance_gap"
    ]
    assert gap_definition["display_unit_label_ja"] == "%"
    assert gap_definition["canonical_formula"] == (
        "(recognized_cases - cleared_cases) / recognized_cases"
    )
    assert gap_definition["interpretation_policy"] == (
        "same_year_flow_difference_not_cohort_unresolved"
    )
    assert payload["definitions"]["nationality_comparison_ids"][
        "nationality_criminal_code_cleared_persons"
    ]["default_display_behavior"] == "include_all_with_warnings"
    offense_definition = payload["definitions"]["offense_composition_ids"][
        "nationality_criminal_code_offense_composition"
    ]
    assert offense_definition["clustering"]["cleared_persons"]["distance"] == (
        "jensen_shannon"
    )
    assert offense_definition["small_number_total_threshold"] == 20
    assert payload["definitions"]["offense_category_ids"]["heinous"][
        "official_severity_role"
    ] == "official_high_severity_category"
    assert payload["definitions"]["clearance_share_ids"][
        "national_criminal_code_clearance_foreign_share"
    ]["interpretation_policy"] == "share_of_clearances_not_population_risk"
    assert "label_ja" not in payload["records"]["nationality_indicators"][0]
    assert "label_en" not in payload["records"]["all_resident_context"][0]
    assert "label_ja" not in payload["records"]["nationality_comparison"][0]
    assert "label_ja" not in payload["records"]["offense_composition"][0]
    assert "offense_label" not in payload["records"]["offense_composition"][0]
    assert "label_ja" not in payload["records"]["clearance_share_trends"][0]
    assert payload["records"]["nationality_indicators"][0]["indicator_id"] in payload[
        "definitions"
    ]["indicator_ids"]
    assert payload["records"]["all_resident_context"][0]["context_id"] in payload[
        "definitions"
    ]["context_ids"]
    assert payload["records"]["nationality_comparison"][0]["comparison_id"] in payload[
        "definitions"
    ]["nationality_comparison_ids"]
    assert payload["records"]["offense_composition"][0]["composition_id"] in payload[
        "definitions"
    ]["offense_composition_ids"]
    assert payload["records"]["offense_composition"][0]["offense_id"] in payload[
        "definitions"
    ]["offense_category_ids"]
    assert payload["records"]["clearance_share_trends"][0]["trend_id"] in payload[
        "definitions"
    ]["clearance_share_ids"]
    residual_share = next(
        row
        for row in payload["records"]["clearance_share_trends"]
        if row["foreign_scope"] == "all_foreign_minus_visiting_foreign"
        and row["metric"] == "cleared_cases"
    )
    assert residual_share["numerator_value"] == 20
    assert residual_share["numerator_source_ids"] == ["S08", "S09"]
    assert payload["records"]["nationality_comparison"][0]["numerator_source_ids"] == [
        "S08",
        "S15",
    ]
    assert "annual_flow_vs_point_in_time_population" in payload["records"][
        "all_resident_context"
    ][0]["mismatch_flags"]
    assert payload["records"]["all_resident_context"][1]["refusal_reason"] == (
        "japanese_prefecture_numerator_unpublished"
    )
    gap_row = next(
        row
        for row in payload["records"]["all_resident_context"]
        if row["context_id"]
        == "all_resident_same_year_recognition_clearance_gap"
        and row["geography_id"] == "jp-prefecture:13"
    )
    assert gap_row["recognized_cases_value"] == 93_359
    assert gap_row["cleared_cases_value"] == 33_961
    assert gap_row["numerator_value"] == 59_398
    assert gap_row["denominator_value"] == 93_359
    assert gap_row["display_value"] == pytest.approx(59_398 / 93_359 * 100)
    assert "not_unresolved_case_cohort" in gap_row["mismatch_flags"]
    assert report.record_counts == {
        "nationality_indicators": 2,
        "all_resident_context": 6,
        "nationality_comparison": 1,
        "offense_composition": 12,
        "clearance_share_trends": 6,
    }
    assert latest["run_relpath"] == "20260901_180000_compact_export"
    assert latest["dashboard_export_sha256"] == sha256_file(report.export_path)
    assert latest["summary_sha256"] == sha256_file(report.summary_path)
    assert summary["source_runs"]["nationality_indicators"]["record_count"] == 2
    assert summary["record_counts"]["all_resident_context"] == 6
    assert summary["record_counts"]["nationality_comparison"] == 1
    assert summary["record_counts"]["offense_composition"] == 12
    assert summary["record_counts"]["clearance_share_trends"] == 6
    assert payload["sources"]["S08"]["publisher"] == "National Police Agency of Japan"
    assert payload["sources"]["S16"]["source_table"] == "144"
    assert payload["sources"]["S17"]["source_table"] == "2"
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert str(tmp_path) not in serialized
    assert "/private/local/" not in serialized


def test_same_year_gap_keeps_negative_values_instead_of_clamping(tmp_path):
    from nationality_crime_atlas.compact_export import (
        derive_same_year_recognition_clearance_gap,
    )

    latest_path = _all_resident_fixture(tmp_path)
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    records_path = latest_path.parent / latest["run_relpath"] / "regional_context_records.jsonl"
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if (
            row["context_id"] == "all_resident_cleared_cases"
            and row["geography_id"] == "jp-prefecture:13"
        ):
            row["numerator_value"] = 100_000

    _definition, derived_rows = derive_same_year_recognition_clearance_gap(rows)
    gap_row = next(
        row
        for row in derived_rows
        if row["geography_id"] == "jp-prefecture:13"
    )

    assert gap_row["numerator_value"] == -6_641
    assert gap_row["display_value"] == pytest.approx(-6_641 / 93_359 * 100)
    assert gap_row["calculation_status"] == "calculated"


def test_same_year_gap_refuses_a_percentage_when_recognized_count_is_zero(tmp_path):
    from nationality_crime_atlas.compact_export import (
        derive_same_year_recognition_clearance_gap,
    )

    latest_path = _all_resident_fixture(tmp_path)
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    records_path = latest_path.parent / latest["run_relpath"] / "regional_context_records.jsonl"
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["geography_id"] == "jp-prefecture:13":
            row["numerator_value"] = 0

    _definition, derived_rows = derive_same_year_recognition_clearance_gap(rows)
    gap_row = next(
        row
        for row in derived_rows
        if row["geography_id"] == "jp-prefecture:13"
    )

    assert gap_row["numerator_value"] == 0
    assert gap_row["display_value"] is None
    assert gap_row["calculation_status"] == "refused"
    assert gap_row["refusal_reason"] == "zero_recognized_cases"


def test_generate_compact_export_rejects_latest_hash_mismatch(tmp_path):
    from nationality_crime_atlas.compact_export import generate_compact_export

    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)
    indicator_latest = json.loads(indicator_latest_path.read_text(encoding="utf-8"))
    indicator_latest["summary_sha256"] = "f" * 64
    _write_json(indicator_latest_path, indicator_latest)

    with pytest.raises(IntegrityError, match="summary hash differs"):
        generate_compact_export(
            indicator_latest_path=indicator_latest_path,
            all_resident_latest_path=all_resident_latest_path,
            nationality_comparison_latest_path=comparison_latest_path,
            offense_composition_latest_path=offense_latest_path,
            clearance_share_latest_path=clearance_share_latest_path,
            output_root=tmp_path / "output" / "compact_export",
            generated_at="2026-09-01T18:00:00+09:00",
        )


def test_compact_export_cli_writes_timestamped_bundle(tmp_path, capsys):
    from nationality_crime_atlas.compact_export_cli import main

    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)

    exit_code = main(
        [
            "--indicator-latest",
            str(indicator_latest_path),
            "--all-resident-latest",
            str(all_resident_latest_path),
            "--nationality-comparison-latest",
            str(comparison_latest_path),
            "--offense-composition-latest",
            str(offense_latest_path),
            "--clearance-share-latest",
            str(clearance_share_latest_path),
            "--output-root",
            str(tmp_path / "output" / "compact_export"),
            "--generated-at",
            "2026-09-01T18:00:00+09:00",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record_counts"] == {
        "all_resident_context": 6,
        "nationality_comparison": 1,
        "nationality_indicators": 2,
        "offense_composition": 12,
        "clearance_share_trends": 4,
    }
    assert payload["output_dir"].endswith("20260901_180000_compact_export")


def test_compact_export_rejects_hash_closed_but_inaccurate_source_summary(tmp_path):
    from nationality_crime_atlas.compact_export import generate_compact_export

    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)
    latest = json.loads(indicator_latest_path.read_text(encoding="utf-8"))
    summary_path = indicator_latest_path.parent / latest["run_relpath"] / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["indicator_record_count"] = 999
    _write_json(summary_path, summary)
    latest["summary_sha256"] = sha256_file(summary_path)
    _write_json(indicator_latest_path, latest)

    with pytest.raises(SchemaError, match="record_count differs"):
        generate_compact_export(
            indicator_latest_path=indicator_latest_path,
            all_resident_latest_path=all_resident_latest_path,
            nationality_comparison_latest_path=comparison_latest_path,
            offense_composition_latest_path=offense_latest_path,
            clearance_share_latest_path=clearance_share_latest_path,
            output_root=tmp_path / "output" / "compact_export",
            generated_at="2026-09-01T18:00:00+09:00",
        )


def test_compact_export_hashes_the_same_latest_bytes_that_it_parses(tmp_path, monkeypatch):
    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)
    original_latest_sha256 = sha256_file(indicator_latest_path)
    original_sha256_file = compact_export_module.sha256_file
    mutation_performed = False

    def mutate_latest_before_a_second_path_read(path):
        nonlocal mutation_performed
        if Path(path) == indicator_latest_path and not mutation_performed:
            changed = json.loads(indicator_latest_path.read_text(encoding="utf-8"))
            changed["generated_at"] = "2099-01-01T00:00:00+09:00"
            _write_json(indicator_latest_path, changed)
            mutation_performed = True
        return original_sha256_file(path)

    monkeypatch.setattr(
        compact_export_module,
        "sha256_file",
        mutate_latest_before_a_second_path_read,
    )

    report = compact_export_module.generate_compact_export(
        indicator_latest_path=indicator_latest_path,
        all_resident_latest_path=all_resident_latest_path,
        nationality_comparison_latest_path=comparison_latest_path,
        offense_composition_latest_path=offense_latest_path,
        clearance_share_latest_path=clearance_share_latest_path,
        output_root=tmp_path / "output" / "compact_export",
        generated_at="2026-09-01T18:00:00+09:00",
    )
    payload = json.loads(report.export_path.read_text(encoding="utf-8"))

    assert payload["source_runs"]["nationality_indicators"]["latest_sha256"] == (
        original_latest_sha256
    )
    assert payload["source_runs"]["nationality_indicators"]["latest_manifest"][
        "generated_at"
    ] == "2026-09-01T13:32:39+09:00"


def test_concurrent_compact_exports_publish_a_hash_closed_latest_pointer(
    tmp_path, monkeypatch
):
    indicator_latest_path = _indicator_fixture(tmp_path)
    all_resident_latest_path = _all_resident_fixture(tmp_path)
    comparison_latest_path = _comparison_fixture(tmp_path)
    offense_latest_path = _offense_composition_fixture(tmp_path)
    clearance_share_latest_path = _clearance_share_fixture(tmp_path)
    output_root = tmp_path / "output" / "compact_export"
    original_replace = Path.replace
    latest_barrier = threading.Barrier(2)

    def synchronized_replace(path, target):
        if Path(target).name == "latest.json":
            latest_barrier.wait(timeout=5)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", synchronized_replace)

    def generate(generated_at):
        return compact_export_module.generate_compact_export(
            indicator_latest_path=indicator_latest_path,
            all_resident_latest_path=all_resident_latest_path,
            nationality_comparison_latest_path=comparison_latest_path,
            offense_composition_latest_path=offense_latest_path,
            clearance_share_latest_path=clearance_share_latest_path,
            output_root=output_root,
            generated_at=generated_at,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = list(
            executor.map(
                generate,
                ["2026-09-01T18:01:00+09:00", "2026-09-01T18:02:00+09:00"],
            )
        )

    assert len(reports) == 2
    latest = json.loads((output_root / "latest.json").read_text(encoding="utf-8"))
    run_dir = output_root / latest["run_relpath"]
    assert latest["summary_sha256"] == sha256_file(run_dir / "summary.json")
    assert latest["dashboard_export_sha256"] == sha256_file(
        run_dir / "dashboard_export.json"
    )
