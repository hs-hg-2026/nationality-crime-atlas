import json
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import IntegrityError
from nationality_crime_atlas.nationality_trend import (
    generate_nationality_trend_report,
    load_nationality_trend_contract,
)
from nationality_crime_atlas.nationality_trend_cli import main as trend_main
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


def _catalog_source(source_id: str, processed_relpath: str, source_table: str):
    return {
        "source_id": source_id,
        "series_id": "fixture-%s" % source_id.lower(),
        "dataset": "Fixture %s" % source_id,
        "publisher": "Fixture official publisher",
        "source_table": source_table,
        "source_period": "fixture period",
        "sha256": "1" * 64,
        "landing_url": "https://example.test/%s" % source_id.lower(),
        "download_url": "https://example.test/%s/data.xlsx" % source_id.lower(),
        "raw_relpath": "fixture/%s/raw.xlsx" % source_id.lower(),
        "processed_relpath": processed_relpath,
        "retrieved_at": "2026-09-07T10:00:00+09:00",
        "revision": "fixture",
        "verification_level": "binary_and_primary",
        "processing_status": "validated",
    }


def _foreign_rows(source_id: str, year: int, scale: int):
    def row(
        source_row,
        region,
        nationality,
        row_kind,
        cases,
        persons,
        subcategory=None,
    ):
        return {
            "source_id": source_id,
            "year": year,
            "population_scope": "all_foreign",
            "region": region,
            "nationality": nationality,
            "subcategory": subcategory,
            "row_kind": row_kind,
            "criminal_code_cleared_cases": cases * scale,
            "criminal_code_cleared_persons": persons * scale,
            "source_row": source_row,
        }

    return [
        row(10, "アジア州の国", None, "region_total", 18, 10),
        row(20, "アジア州の国", "ベトナム", "country", 10, 6),
        row(21, "アジア州の国", "中国", "country", 8, 4),
        row(22, "アジア州の国", "その他", "country", 0, 0),
        row(30, "南北アメリカ州の国", None, "region_total", 7, 5),
        row(31, "南北アメリカ州の国", "アメリカ", "subcategory", 4, 2, "軍人"),
        row(32, "南北アメリカ州の国", "アメリカ", "subcategory", 3, 3, "その他"),
    ]


def _mapping_rows(source_id: str, foreign_rows):
    configurations = {
        20: ("matched", ["isa-nationality:vn"], ["ベトナム"], True),
        21: (
            "ambiguous",
            ["isa-nationality:cn", "isa-nationality:tw"],
            ["中国", "台湾"],
            False,
        ),
        22: ("unmatched", [], [], False),
        31: ("matched", ["isa-nationality:us"], ["米国"], True),
        32: ("matched", ["isa-nationality:us"], ["米国"], True),
    }
    rows = []
    for row in foreign_rows:
        if row["source_row"] not in configurations:
            continue
        status, ids, labels, complete = configurations[row["source_row"]]
        rows.append(
            {
                "mapping_schema_version": 1,
                "dimension": "nationality_or_region",
                "source_id": source_id,
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
        )
    return rows


def _fixture(tmp_path: Path):
    years = (2023, 2024)
    processed_root = tmp_path / "processed"
    source_ids = {
        2023: {
            "foreign": "S08_2023",
            "all_person": "S15_2023",
            "foreign_population": "S19_2023",
            "japanese_population": "S17_2023",
        },
        2024: {
            "foreign": "S08",
            "all_person": "S15",
            "foreign_population": "S19_2024",
            "japanese_population": "S17",
        },
    }
    pins = {}
    catalog_rows = []
    mapping_rows = []
    for year in years:
        sources = source_ids[year]
        scale = year - 2022
        rows_by_source = {
            sources["foreign"]: _foreign_rows(sources["foreign"], year, scale),
            sources["all_person"]: [
                {
                    "source_id": sources["all_person"],
                    "year": year,
                    "population_scope": "all_persons",
                    "offense_scope": "criminal_code_excluding_traffic_negligence",
                    "geography": "日本",
                    "geography_type": "national",
                    "geography_semantics": "national_aggregate",
                    "cleared_cases": 100 * scale,
                    "cleared_persons": 80 * scale,
                }
            ],
            sources["foreign_population"]: [
                {
                    "source_id": sources["foreign_population"],
                    "period_end": "%d-12-31" % year,
                    "nationality": label,
                    "region": "fixture",
                    "row_kind": "country_or_area",
                    "population": value * scale,
                }
                for label, value in (
                    ("ベトナム", 1000),
                    ("中国", 1500),
                    ("台湾", 500),
                    ("米国", 500),
                )
            ],
            sources["japanese_population"]: [
                {
                    "source_id": sources["japanese_population"],
                    "year": year,
                    "reference_date": "%d-10-01" % year,
                    "population_scope": "japanese_population",
                    "geography": "日本",
                    "geography_type": "national",
                    "geography_semantics": "national_aggregate",
                    "population": 50_000 * scale,
                    "source_value": 50 * scale,
                    "source_unit": "1000_persons",
                    "rounding": "nearest_1000_persons",
                }
            ],
        }
        for source_id, rows in rows_by_source.items():
            relpath = "fixture/%s/run" % source_id.lower()
            normalized_path = processed_root / relpath / "normalized.jsonl"
            pins[source_id] = _write_jsonl(normalized_path, rows)
            _write_json(
                normalized_path.parent / "run.json",
                {
                    "source_id": source_id,
                    "normalized_sha256": pins[source_id],
                    "quality_passed": True,
                },
            )
            catalog_rows.append(_catalog_source(source_id, relpath, "fixture"))
        mapping_rows.extend(
            _mapping_rows(sources["foreign"], rows_by_source[sources["foreign"]])
        )

    catalog_path = processed_root / "_catalog" / "artifacts.jsonl"
    _write_jsonl(catalog_path, catalog_rows)
    mapping_root = processed_root / "_mappings"
    mapping_run = mapping_root / "20260907_100000_dimension_mapping"
    mapping_path = mapping_run / "dimension_mappings.jsonl"
    mapping_hash = _write_jsonl(mapping_path, mapping_rows)
    mapping_summary = mapping_run / "summary.json"
    _write_json(mapping_summary, {"mapping_record_count": len(mapping_rows)})
    mapping_latest_path = mapping_root / "latest.json"
    _write_json(
        mapping_latest_path,
        {
            "mapping_schema_version": 1,
            "run_relpath": mapping_run.name,
            "summary_sha256": sha256_file(mapping_summary),
            "dimension_mappings_sha256": mapping_hash,
        },
    )

    contract_path = tmp_path / "nationality_trend_contract.json"
    _write_json(
        contract_path,
        {
            "schema_version": 1,
            "processed_input_pins": pins,
            "trend": {
                "trend_id": "nationality_criminal_code_clearance_reference_ratio_trend",
                "label_ja": "日本を含む国籍等別の刑法犯検挙参考比率の推移",
                "label_en": "Criminal-code clearance reference-ratio trend by nationality including Japan",
                "years": list(years),
                "metrics": ["cleared_cases", "cleared_persons"],
                "foreign_numerator_sources": {
                    str(year): source_ids[year]["foreign"] for year in years
                },
                "all_person_numerator_sources": {
                    str(year): source_ids[year]["all_person"] for year in years
                },
                "foreign_population_sources": {
                    str(year): source_ids[year]["foreign_population"] for year in years
                },
                "japanese_population_sources": {
                    str(year): source_ids[year]["japanese_population"] for year in years
                },
                "foreign_population_label_aliases": {},
                "expected_foreign_country_row_count": 3,
                "expected_foreign_region_total_row_count": 2,
                "foreign_total_outside_region_labels": [],
                "aggregated_nationality_label": "アメリカ",
                "expected_aggregated_subcategory_row_count": 2,
                "display_multiplier": 1000,
                "display_unit_label_ja": "人口1,000人当たり",
                "display_unit_label_en": "per 1,000 persons",
                "small_number_denominator_threshold": 1000,
                "small_number_numerator_threshold": 20,
                "default_display_behavior": "include_all_with_warnings",
                "interpretation_policy": "observed_time_series_without_intrinsic_group_inference",
                "ui_caveat": "年間の公表値と年末または10月1日人口を機械的に組み合わせた参考比率である。",
            },
        },
    )
    return {
        "catalog_path": catalog_path,
        "processed_root": processed_root,
        "mapping_latest_path": mapping_latest_path,
        "contract_path": contract_path,
        "output_root": tmp_path / "trend",
        "generated_at": "2026-09-07T10:30:00+09:00",
    }


def _records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_contract_requires_five_point_project_series():
    contract, pins = load_nationality_trend_contract(
        Path("config/nationality_trend_contract.json")
    )

    assert contract.years == (2020, 2021, 2022, 2023, 2024)
    assert contract.metrics == ("cleared_cases", "cleared_persons")
    assert len(pins) == 20
    assert contract.foreign_population_label_aliases == {"（朝鮮）": "朝鮮"}
    assert "10月1日の日本人人口" in contract.ui_caveat
    assert "10月1日の日本人口" not in contract.ui_caveat
    assert set(contract.foreign_numerator_sources.values()) == {
        "S08_2020",
        "S08_2021",
        "S08_2022",
        "S08_2023",
        "S08",
    }


def test_report_keeps_full_entity_year_metric_grid_and_exact_values(tmp_path):
    paths = _fixture(tmp_path)

    report = generate_nationality_trend_report(**paths)

    rows = _records(report.jsonl_path)
    assert report.record_count == 20
    assert report.status_counts == {"calculated": 16, "refused": 4}
    assert {
        (row["year"], row["metric"], row["published_label"])
        for row in rows
    } == {
        (year, metric, label)
        for year in (2023, 2024)
        for metric in ("cleared_cases", "cleared_persons")
        for label in ("日本", "ベトナム", "中国", "その他", "アメリカ")
    }

    japanese_cases = next(
        row
        for row in rows
        if row["year"] == 2024
        and row["metric"] == "cleared_cases"
        and row["is_japanese_reference"]
    )
    assert japanese_cases["numerator_value"] == 150
    assert japanese_cases["denominator_value"] == 100_000
    assert japanese_cases["display_value"] == pytest.approx(1.5)
    assert japanese_cases["numerator_source_ids"] == ["S08", "S15"]
    assert japanese_cases["derivation_method"] == "residual_subtraction"
    assert "japanese_numerator_derived_by_residual_subtraction" in japanese_cases[
        "mismatch_flags"
    ]

    vietnam_persons = next(
        row
        for row in rows
        if row["year"] == 2023
        and row["metric"] == "cleared_persons"
        and row["published_label"] == "ベトナム"
    )
    assert vietnam_persons["numerator_value"] == 6
    assert vietnam_persons["denominator_value"] == 1000
    assert vietnam_persons["display_value"] == pytest.approx(6.0)

    other = next(
        row
        for row in rows
        if row["year"] == 2024
        and row["metric"] == "cleared_cases"
        and row["published_label"] == "その他"
    )
    assert other["calculation_status"] == "refused"
    assert other["display_value"] is None
    assert other["refusal_reason"] == "no_canonical_denominator_components"

    china = next(
        row
        for row in rows
        if row["year"] == 2024
        and row["metric"] == "cleared_cases"
        and row["published_label"] == "中国"
    )
    assert china["calculation_status"] == "calculated"
    assert china["targets_complete"] is False
    assert "nationality_grouping_mismatch" in china["mismatch_flags"]

    entities_by_series_key = {}
    for row in rows:
        key = (row["metric"], row["entity_id"])
        entities_by_series_key.setdefault(key, []).append(row)
    assert all(len(series_rows) == 2 for series_rows in entities_by_series_key.values())
    assert all(row["display_included"] is True for row in rows)


def test_report_rejects_changed_processed_input(tmp_path):
    paths = _fixture(tmp_path)
    data = json.loads(paths["contract_path"].read_text(encoding="utf-8"))
    data["processed_input_pins"]["S08"] = "0" * 64
    _write_json(paths["contract_path"], data)

    with pytest.raises(IntegrityError, match="contract pin"):
        generate_nationality_trend_report(**paths)


def test_cli_generates_nationality_trend_product(tmp_path, capsys):
    paths = _fixture(tmp_path)

    exit_code = trend_main(
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
    assert payload["record_count"] == 20
    assert payload["status_counts"] == {"calculated": 16, "refused": 4}
    assert Path(payload["records"]).exists()
