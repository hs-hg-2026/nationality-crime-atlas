import json
from pathlib import Path

import pytest

from nationality_crime_atlas.dimension_cli import main as dimension_main
from nationality_crime_atlas.dimensions import (
    build_canonical_reference,
    generate_dimension_mapping_report,
    load_dimension_mapping_config,
    map_geography_dimension,
    map_nationality_dimension,
)
from nationality_crime_atlas.errors import SchemaError


def _mapping_config():
    return {
        "schema_version": 1,
        "mapping_scope": (
            "Label/category crosswalk only; it does not establish statistical "
            "compatibility between numerator and denominator."
        ),
        "nationality": {
            "aliases": {
                "アメリカ": {
                    "source_ids": ["S08", "S09"],
                    "target_labels": ["米国"],
                    "reason": "NPA and ISA use different Japanese labels.",
                },
                "イギリス": {
                    "source_ids": ["S08", "S09"],
                    "target_labels": ["英国"],
                    "reason": "NPA and ISA use different Japanese labels.",
                },
            },
            "composites": {
                "中国": {
                    "source_ids": ["S08", "S09"],
                    "target_labels": ["中国", "台湾"],
                    "targets_complete": False,
                    "reason": "The NPA footnote includes Taiwan, Hong Kong, etc.",
                },
                "韓国・朝鮮": {
                    "source_ids": ["S08", "S09"],
                    "target_labels": ["韓国", "（朝鮮）"],
                    "targets_complete": True,
                    "reason": "The NPA category combines two ISA categories.",
                },
            },
            "unmatched": {
                "その他": {
                    "source_ids": ["S08", "S09"],
                    "reason": "The source does not publish the bucket membership.",
                },
                "国籍不明": {
                    "source_ids": ["S08", "S09"],
                    "reason": "No equivalent ISA nationality category is published.",
                },
            },
            "region_code_prefixes": {
                "アジア州の国": {
                    "source_ids": ["S08", "S09"],
                    "prefixes": ["01_"],
                },
                "ヨーロッパ州の国": {
                    "source_ids": ["S08", "S09"],
                    "prefixes": ["02_"],
                },
                "南北アメリカ州の国": {
                    "source_ids": ["S08", "S09"],
                    "prefixes": ["04_", "05_"],
                },
                "アフリカ州の国": {
                    "source_ids": ["S08", "S09"],
                    "prefixes": ["03_"],
                },
                "オセアニア州の国": {
                    "source_ids": ["S08", "S09"],
                    "prefixes": ["06_"],
                },
            },
        },
        "geography": {
            "national": {
                "日本": {
                    "canonical_id": "jp:all",
                    "canonical_label": "日本全国",
                    "reason": "A derived national aggregate, not a source prefecture code.",
                }
            },
            "non_equivalent_types": {
                "police_region": "An aggregate of multiple prefectures.",
                "police_subregion": "A police area below prefecture level.",
            },
        },
    }


def _population_rows():
    labels = [
        ("01_011", "韓国"),
        ("01_012", "（朝鮮）"),
        ("01_022", "台湾"),
        ("01_023", "中国"),
        ("01_037", "ベトナム"),
        ("02_054", "英国"),
        ("04_175", "米国"),
        ("07_000", "無国籍"),
    ]
    return [
        {
            "source_id": "S14_2024_12",
            "nationality_code": code,
            "nationality": label,
            "prefecture_code": "02",
            "prefecture": "青森県",
        }
        for code, label in labels
    ] + [
        {
            "source_id": "S14_2024_12",
            "nationality_code": "01_037",
            "nationality": "ベトナム",
            "prefecture_code": "01",
            "prefecture": "北海道",
        }
    ]


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _report_fixture(tmp_path: Path):
    processed_root = tmp_path / "processed"
    population_rows = _population_rows()
    nationality_rows = [
        {
            "source_id": "S08",
            "row_kind": "region_total",
            "region": "アジア州の国",
            "nationality": None,
            "subcategory": None,
        },
        {
            "source_id": "S08",
            "row_kind": "country",
            "region": "アジア州の国",
            "nationality": "中国",
            "subcategory": None,
        },
        {
            "source_id": "S08",
            "row_kind": "subcategory",
            "region": "南北アメリカ州の国",
            "nationality": "アメリカ",
            "subcategory": "その他",
        },
        {
            "source_id": "S08",
            "row_kind": "country",
            "region": "アジア州の国",
            "nationality": "その他",
            "subcategory": None,
        },
    ]
    geography_rows = [
        {
            "source_id": "S02",
            "geography": "日本",
            "geography_type": "national",
            "parent_region": None,
            "geography_semantics": "police_reporting_area_unresolved",
        },
        {
            "source_id": "S02",
            "geography": "青森県",
            "geography_type": "prefecture",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
        },
        {
            "source_id": "S02",
            "geography": "東北",
            "geography_type": "police_region",
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
        },
        {
            "source_id": "S02",
            "geography": "札幌方面",
            "geography_type": "police_subregion",
            "parent_region": "北海道",
            "geography_semantics": "police_reporting_area_unresolved",
        },
    ]
    paths = {
        "S14_2024_12": "population/S14_2024_12/run",
        "S08": "nationality/S08/run",
        "S02": "geography/S02/run",
    }
    _write_jsonl(
        processed_root / paths["S14_2024_12"] / "normalized.jsonl",
        population_rows,
    )
    _write_jsonl(
        processed_root / paths["S08"] / "normalized.jsonl",
        nationality_rows,
    )
    _write_jsonl(
        processed_root / paths["S02"] / "normalized.jsonl",
        geography_rows,
    )
    catalog_path = processed_root / "_catalog" / "artifacts.jsonl"
    _write_jsonl(
        catalog_path,
        [
            {
                "source_id": source_id,
                "series_id": "fixture-" + source_id.lower(),
                "processed_relpath": relpath,
                "processing_status": "validated",
            }
            for source_id, relpath in paths.items()
        ],
    )
    config_path = tmp_path / "dimension_mappings.json"
    _write_json(config_path, _mapping_config())
    return processed_root, catalog_path, config_path


def test_reference_rejects_a_code_reused_for_a_different_label():
    rows = _population_rows()
    rows.append(
        {
            "source_id": "later",
            "nationality_code": "01_011",
            "nationality": "different label",
            "prefecture_code": "02",
            "prefecture": "青森県",
        }
    )

    with pytest.raises(SchemaError, match="nationality code"):
        build_canonical_reference(rows)


@pytest.mark.parametrize(
    "source_label,expected_status,expected_ids",
    [
        ("ベトナム", "matched", ("isa-nationality:01_037",)),
        ("アメリカ", "matched", ("isa-nationality:04_175",)),
        (
            "韓国・朝鮮",
            "ambiguous",
            ("isa-nationality:01_011", "isa-nationality:01_012"),
        ),
        (
            "中国",
            "ambiguous",
            ("isa-nationality:01_022", "isa-nationality:01_023"),
        ),
        ("その他", "unmatched", ()),
    ],
)
def test_nationality_mapping_never_collapses_composites(
    source_label,
    expected_status,
    expected_ids,
):
    reference = build_canonical_reference(_population_rows())

    result = map_nationality_dimension(
        {
            "source_id": "S08",
            "row_kind": "country",
            "region": "アジア州の国",
            "nationality": source_label,
            "subcategory": None,
        },
        reference=reference,
        config=_mapping_config(),
    )

    assert result.match_status == expected_status
    assert result.canonical_ids == expected_ids
    assert result.source_label == source_label


def test_region_total_is_ambiguous_instead_of_fuzzy_matched():
    reference = build_canonical_reference(_population_rows())

    result = map_nationality_dimension(
        {
            "source_id": "S08",
            "row_kind": "region_total",
            "region": "アジア州の国",
            "nationality": None,
            "subcategory": None,
        },
        reference=reference,
        config=_mapping_config(),
    )

    assert result.match_status == "ambiguous"
    assert "isa-nationality:01_023" in result.canonical_ids
    assert result.source_label == "アジア州の国"


def test_authored_rule_stops_on_an_unreviewed_source_id():
    reference = build_canonical_reference(_population_rows())

    with pytest.raises(SchemaError, match="not reviewed for source_id S99"):
        map_nationality_dimension(
            {
                "source_id": "S99",
                "row_kind": "country",
                "region": "アジア州の国",
                "nationality": "中国",
                "subcategory": None,
            },
            reference=reference,
            config=_mapping_config(),
        )


@pytest.mark.parametrize(
    "geography,geography_type,expected_status,expected_ids",
    [
        ("青森県", "prefecture", "matched", ("jp-prefecture:02",)),
        ("日本", "national", "matched", ("jp:all",)),
        ("東北", "police_region", "ambiguous", ()),
        ("札幌方面", "police_subregion", "ambiguous", ()),
    ],
)
def test_geography_mapping_preserves_non_equivalent_police_areas(
    geography,
    geography_type,
    expected_status,
    expected_ids,
):
    reference = build_canonical_reference(_population_rows())

    result = map_geography_dimension(
        {
            "source_id": "S02",
            "geography": geography,
            "geography_type": geography_type,
            "parent_region": "東北",
            "geography_semantics": "police_reporting_area_unresolved",
        },
        reference=reference,
        config=_mapping_config(),
    )

    assert result.match_status == expected_status
    assert result.canonical_ids == expected_ids
    assert result.source_label == geography


def test_report_is_timestamped_provenance_rich_and_keeps_raw_labels(tmp_path):
    processed_root, catalog_path, config_path = _report_fixture(tmp_path)

    result = generate_dimension_mapping_report(
        catalog_path=catalog_path,
        processed_root=processed_root,
        config_path=config_path,
        output_root=processed_root / "_mappings",
        generated_at="2026-08-30T21:15:30+09:00",
    )

    rows = [json.loads(line) for line in result.jsonl_path.read_text().splitlines()]
    summary = json.loads(result.summary_path.read_text())
    latest = json.loads(result.latest_path.read_text())
    china = next(row for row in rows if row["source_label"] == "中国")
    assert result.output_dir.name == "20260830_211530_dimension_mapping"
    assert result.record_count == 18
    assert china["match_status"] == "ambiguous"
    assert china["source_context"]["region"] == "アジア州の国"
    assert summary["mapping_scope"] == _mapping_config()["mapping_scope"]
    assert summary["status_counts"] == {
        "ambiguous": 4,
        "matched": 13,
        "unmatched": 1,
    }
    assert latest["run_relpath"] == result.output_dir.name
    assert latest["summary_sha256"]
    assert result.csv_path.read_text().splitlines()[0].startswith("mapping_schema_version,")


def test_report_refuses_nonvalidated_catalog_input(tmp_path):
    processed_root, catalog_path, config_path = _report_fixture(tmp_path)
    row = json.loads(catalog_path.read_text().splitlines()[0])
    row["processing_status"] = "raw_only"
    _write_jsonl(catalog_path, [row])

    with pytest.raises(SchemaError, match="validated"):
        generate_dimension_mapping_report(
            catalog_path=catalog_path,
            processed_root=processed_root,
            config_path=config_path,
            output_root=processed_root / "_mappings",
            generated_at="2026-08-30T21:15:30+09:00",
        )


def test_dimension_cli_prints_generated_mapping_locations(tmp_path, capsys):
    processed_root, catalog_path, config_path = _report_fixture(tmp_path)

    exit_code = dimension_main(
        [
            "--catalog",
            str(catalog_path),
            "--processed-root",
            str(processed_root),
            "--config",
            str(config_path),
            "--output-root",
            str(processed_root / "_mappings"),
            "--generated-at",
            "2026-08-30T21:15:30+09:00",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["record_count"] == 18
    assert payload["summary"].endswith("/summary.json")


def test_project_mapping_config_is_valid():
    config = load_dimension_mapping_config(Path("config/dimension_mappings.json"))

    assert config["schema_version"] == 1
    assert config["mapping_scope"].startswith("Label/category crosswalk only")
