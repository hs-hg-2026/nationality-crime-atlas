import json
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import IntegrityError
from nationality_crime_atlas.nationality_comparison import (
    generate_nationality_comparison_report,
    load_nationality_comparison_contract,
)
from nationality_crime_atlas.nationality_comparison_cli import main as comparison_main
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
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    return sha256_file(path)


def _source(source_id: str, processed_relpath: str, source_table: str):
    return {
        "source_id": source_id,
        "series_id": "fixture-%s" % source_id.lower(),
        "dataset": "Fixture %s" % source_id,
        "publisher": "Fixture official publisher",
        "source_table": source_table,
        "source_period": "2024 fixture period",
        "sha256": (source_id[-1].lower() if source_id[-1].lower() in "abcdef" else "1")
        * 64,
        "landing_url": "https://example.test/%s" % source_id.lower(),
        "download_url": "https://example.test/%s/data.xlsx" % source_id.lower(),
        "raw_relpath": "fixture/%s/raw.xlsx" % source_id.lower(),
        "processed_relpath": processed_relpath,
        "retrieved_at": "2026-09-02T20:00:00+09:00",
        "revision": "fixture",
        "verification_level": "binary_and_primary",
        "processing_status": "validated",
    }


def _mapping_row(row, *, status, ids, labels, complete):
    return {
        "mapping_schema_version": 1,
        "dimension": "nationality_or_region",
        "source_id": "S08",
        "source_entity_kind": row["row_kind"],
        "source_label": row["nationality"],
        "source_code": None,
        "source_context": {
            "region": row["region"],
            "row_kind": row["row_kind"],
            "subcategory": row["subcategory"],
        },
        "match_status": status,
        "match_method": "fixture",
        "canonical_ids": ids,
        "canonical_labels": labels,
        "targets_complete": complete,
        "reason": "fixture",
        "mapping_scope": "category crosswalk only",
    }


def _fixture(tmp_path: Path):
    processed_root = tmp_path / "processed"
    relpaths = {
        "S08": "npa-all-foreign/S08/run",
        "S14_2024_12": "isa-population/S14_2024_12/run",
        "S15": "npa-all-persons/S15/run",
        "S17": "statistics-japanese-population/S17/run",
    }
    paths = {
        source_id: processed_root / relpath / "normalized.jsonl"
        for source_id, relpath in relpaths.items()
    }
    s08_rows = [
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": None,
            "subcategory": None,
            "row_kind": "region_total",
            "criminal_code_cleared_persons": 10,
            "source_row": 10,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "ベトナム",
            "subcategory": None,
            "row_kind": "country",
            "criminal_code_cleared_persons": 6,
            "source_row": 20,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "中国",
            "subcategory": None,
            "row_kind": "country",
            "criminal_code_cleared_persons": 4,
            "source_row": 21,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "アジア州の国",
            "nationality": "その他",
            "subcategory": None,
            "row_kind": "country",
            "criminal_code_cleared_persons": 0,
            "source_row": 22,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "南北アメリカ州の国",
            "nationality": None,
            "subcategory": None,
            "row_kind": "region_total",
            "criminal_code_cleared_persons": 5,
            "source_row": 30,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "南北アメリカ州の国",
            "nationality": "アメリカ",
            "subcategory": "軍人",
            "row_kind": "subcategory",
            "criminal_code_cleared_persons": 2,
            "source_row": 31,
        },
        {
            "source_id": "S08",
            "year": 2024,
            "population_scope": "all_foreign",
            "region": "南北アメリカ州の国",
            "nationality": "アメリカ",
            "subcategory": "その他",
            "row_kind": "subcategory",
            "criminal_code_cleared_persons": 3,
            "source_row": 32,
        },
    ]
    s14_rows = [
        {
            "source_id": "S14_2024_12",
            "period_end": "2024-12-31",
            "nationality_code": code,
            "nationality": label,
            "prefecture_code": "00",
            "prefecture": "全国",
            "value": value,
            "suppressed": False,
        }
        for code, label, value in (
            ("01_037", "ベトナム", 1000),
            ("01_022", "中国", 1500),
            ("01_023", "台湾", 500),
            ("04_175", "米国", 500),
        )
    ]
    s15_rows = [
        {
            "source_id": "S15",
            "year": 2024,
            "population_scope": "all_persons",
            "offense_scope": "criminal_code_excluding_traffic_negligence",
            "geography": "日本",
            "geography_type": "national",
            "geography_semantics": "national_aggregate",
            "cleared_persons": 100,
        }
    ]
    s17_rows = [
        {
            "source_id": "S17",
            "year": 2024,
            "reference_date": "2024-10-01",
            "population_scope": "japanese_population",
            "geography": "日本",
            "geography_type": "national",
            "geography_semantics": "national_aggregate",
            "population": 50000,
            "source_value": 50,
            "source_unit": "1000_persons",
            "rounding": "nearest_1000_persons",
        }
    ]
    hashes = {}
    for source_id, rows in (
        ("S08", s08_rows),
        ("S14_2024_12", s14_rows),
        ("S15", s15_rows),
        ("S17", s17_rows),
    ):
        hashes[source_id] = _write_jsonl(paths[source_id], rows)
        _write_json(
            paths[source_id].parent / "run.json",
            {
                "source_id": source_id,
                "normalized_sha256": hashes[source_id],
                "quality_passed": True,
            },
        )

    catalog_path = processed_root / "_catalog" / "artifacts.jsonl"
    _write_jsonl(
        catalog_path,
        [
            _source("S08", relpaths["S08"], "130"),
            _source("S14_2024_12", relpaths["S14_2024_12"], "1"),
            _source("S15", relpaths["S15"], "3"),
            _source("S17", relpaths["S17"], "2"),
        ],
    )

    by_row = {row["source_row"]: row for row in s08_rows}
    mapping_rows = [
        _mapping_row(
            by_row[20],
            status="matched",
            ids=["isa-nationality:01_037"],
            labels=["ベトナム"],
            complete=True,
        ),
        _mapping_row(
            by_row[21],
            status="ambiguous",
            ids=["isa-nationality:01_022", "isa-nationality:01_023"],
            labels=["中国", "台湾"],
            complete=False,
        ),
        _mapping_row(
            by_row[22],
            status="unmatched",
            ids=[],
            labels=[],
            complete=False,
        ),
        _mapping_row(
            by_row[31],
            status="matched",
            ids=["isa-nationality:04_175"],
            labels=["米国"],
            complete=True,
        ),
        _mapping_row(
            by_row[32],
            status="matched",
            ids=["isa-nationality:04_175"],
            labels=["米国"],
            complete=True,
        ),
    ]
    mapping_root = processed_root / "_mappings"
    mapping_run = mapping_root / "20260902_200000_dimension_mapping"
    mapping_path = mapping_run / "dimension_mappings.jsonl"
    mapping_hash = _write_jsonl(mapping_path, mapping_rows)
    mapping_summary = mapping_run / "summary.json"
    _write_json(mapping_summary, {"mapping_record_count": len(mapping_rows)})
    mapping_latest = mapping_root / "latest.json"
    _write_json(
        mapping_latest,
        {
            "mapping_schema_version": 1,
            "run_relpath": mapping_run.name,
            "summary_sha256": sha256_file(mapping_summary),
            "dimension_mappings_sha256": mapping_hash,
        },
    )

    contract_path = tmp_path / "nationality_comparison_contract.json"
    _write_json(
        contract_path,
        {
            "schema_version": 1,
            "processed_input_pins": hashes,
            "comparison": {
                "comparison_id": "nationality_criminal_code_cleared_persons",
                "label_ja": "全国・国籍等別 刑法犯検挙人員 ÷ 対応人口",
                "label_en": "National criminal-code cleared persons by nationality / corresponding population",
                "measure_kind": "public_data_derived_reference_ratio",
                "canonical_formula": "numerator_value / denominator_value",
                "numerator_year": 2024,
                "foreign_numerator_source_id": "S08",
                "foreign_numerator_metric": "criminal_code_cleared_persons",
                "all_person_numerator_source_id": "S15",
                "all_person_numerator_metric": "cleared_persons",
                "foreign_population_source_id": "S14_2024_12",
                "foreign_denominator_period_end": "2024-12-31",
                "japanese_population_source_id": "S17",
                "japanese_denominator_reference_date": "2024-10-01",
                "expected_foreign_country_row_count": 3,
                "expected_foreign_region_total_row_count": 2,
                "foreign_total_outside_region_labels": [],
                "expected_foreign_total_numerator": 15,
                "aggregated_nationality_label": "アメリカ",
                "expected_aggregated_subcategory_row_count": 2,
                "display_multiplier": 1000,
                "display_unit_label_ja": "人口1,000人当たり",
                "display_unit_label_en": "per 1,000 persons",
                "small_number_denominator_threshold": 1000,
                "small_number_numerator_threshold": 20,
                "default_display_behavior": "include_all_with_warnings",
                "interpretation_policy": "observed_values_without_intrinsic_group_inference",
                "ui_caveat": "公表値を機械的に組み合わせた参考比率であり、集団の本質や個人riskを示さない。",
            },
        },
    )
    return {
        "catalog_path": catalog_path,
        "processed_root": processed_root,
        "mapping_latest_path": mapping_latest,
        "contract_path": contract_path,
        "output_root": tmp_path / "output",
        "generated_at": "2026-09-02T21:00:00+09:00",
    }


def _records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_contract_loader_requires_complete_source_and_display_policy(tmp_path):
    paths = _fixture(tmp_path)

    contract, pins = load_nationality_comparison_contract(paths["contract_path"])

    assert contract.comparison_id == "nationality_criminal_code_cleared_persons"
    assert contract.default_display_behavior == "include_all_with_warnings"
    assert contract.interpretation_policy == (
        "observed_values_without_intrinsic_group_inference"
    )
    assert set(pins) == {"S08", "S14_2024_12", "S15", "S17"}


def test_project_contract_pins_reviewed_2024_comparison_inputs():
    contract, pins = load_nationality_comparison_contract(
        "config/nationality_comparison_contract.json"
    )

    assert contract.numerator_year == 2024
    assert contract.expected_foreign_country_row_count == 24
    assert contract.expected_foreign_region_total_row_count == 5
    assert contract.foreign_total_outside_region_labels == ("無国籍", "国籍不明")
    assert contract.expected_foreign_total_numerator == 10464
    assert contract.expected_aggregated_subcategory_row_count == 4
    assert pins == {
        "S08": "3fe1d78fe8d4c12b436e09b42641276cd2ba39fc1f1c446af588266d5b6d0029",
        "S14_2024_12": "32d385ae4d810d18a40dbef8c392db57c8be1e44a216e28ec48971e90a2de83d",
        "S15": "d112ce129e94d635da47aa0efe748d0bb91ae8b76fdf4ad1d5eb46f67bdcf8c6",
        "S17": "f82690c52a318abcdd2252b578075651d3daca5ebca16cbaabbf1278be62203b",
    }


def test_report_includes_japanese_residual_all_published_rows_and_us_aggregate(tmp_path):
    paths = _fixture(tmp_path)

    report = generate_nationality_comparison_report(**paths)

    rows = _records(report.jsonl_path)
    summary = json.loads(report.summary_path.read_text(encoding="utf-8"))
    assert report.record_count == 5
    assert report.status_counts == {"calculated": 4, "refused": 1}
    assert all(row["display_included"] is True for row in rows)

    japanese = next(row for row in rows if row["published_label"] == "日本")
    assert japanese["is_japanese_reference"] is True
    assert japanese["derivation_method"] == "residual_subtraction"
    assert japanese["numerator_source_ids"] == ["S08", "S15"]
    assert japanese["denominator_source_id"] == "S17"
    assert japanese["numerator_value"] == 85
    assert japanese["denominator_value"] == 50000
    assert japanese["display_value"] == pytest.approx(1.7)
    assert "japanese_numerator_derived_by_residual_subtraction" in japanese[
        "mismatch_flags"
    ]

    china = next(row for row in rows if row["published_label"] == "中国")
    assert china["calculation_status"] == "calculated"
    assert china["denominator_value"] == 2000
    assert china["display_value"] == pytest.approx(2.0)
    assert "nationality_grouping_mismatch" in china["mismatch_flags"]

    america = next(row for row in rows if row["published_label"] == "アメリカ")
    assert america["derivation_method"] == "sum_published_subcategories"
    assert america["numerator_value"] == 5
    assert america["denominator_value"] == 500
    assert america["display_value"] == pytest.approx(10.0)
    assert set(component["subcategory"] for component in america["numerator_components"]) == {
        "軍人",
        "その他",
    }

    other = next(row for row in rows if row["published_label"] == "その他")
    assert other["calculation_status"] == "refused"
    assert other["refusal_reason"] == "no_canonical_denominator_components"
    assert other["numerator_value"] == 0
    assert other["display_value"] is None

    assert summary["japanese_numerator_reconciliation"] == {
        "all_person_criminal_code_cleared_persons": 100,
        "all_foreign_criminal_code_cleared_persons": 15,
        "derived_japanese_criminal_code_cleared_persons": 85,
    }
    assert set(summary["source_artifacts"]) == {
        "S08",
        "S14_2024_12",
        "S15",
        "S17",
    }


def test_report_rejects_tampered_processed_input_and_preserves_existing_run(tmp_path):
    paths = _fixture(tmp_path)
    report = generate_nationality_comparison_report(**paths)
    s08_path = (
        paths["processed_root"] / "npa-all-foreign/S08/run/normalized.jsonl"
    )
    with s08_path.open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(IntegrityError, match="run.json"):
        generate_nationality_comparison_report(
            **{**paths, "generated_at": "2026-09-02T21:01:00+09:00"}
        )
    with pytest.raises(IntegrityError, match="already exists"):
        generate_nationality_comparison_report(**paths)
    assert report.jsonl_path.exists()


def test_cli_generates_nationality_comparison_product(tmp_path, capsys):
    paths = _fixture(tmp_path)

    exit_code = comparison_main(
        [
            "--catalog",
            str(paths["catalog_path"]),
            "--processed-root",
            str(paths["processed_root"]),
            "--mapping-latest",
            str(paths["mapping_latest_path"]),
            "--contract",
            str(paths["contract_path"]),
            "--output-root",
            str(paths["output_root"]),
            "--generated-at",
            paths["generated_at"],
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record_count"] == 5
    assert payload["status_counts"] == {"calculated": 4, "refused": 1}
    assert Path(payload["jsonl"]).exists()
