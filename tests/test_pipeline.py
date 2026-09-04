import json
from pathlib import Path

import pytest

from nationality_crime_atlas.errors import PipelineConflictError, QualityGateError
from nationality_crime_atlas.npa_nationality import parse_npa_nationality_totals
from nationality_crime_atlas.npa_prefecture import parse_npa_prefecture_table13
from nationality_crime_atlas.pipeline import run_offline_pipeline


def _metadata(parser, expected_format, source_table):
    edition_id = {"13": "S02", "130": "S08", "131": "S09"}.get(
        source_table,
        "S14",
    )
    return {
        "series_id": "fixture-series",
        "edition_id": edition_id,
        "publisher": "Official publisher",
        "dataset": "Fixture dataset",
        "source_table": source_table,
        "parser": parser,
        "expected_format": expected_format,
        "landing_url": "https://example.test/landing",
        "download_url": "https://example.test/download",
        "period": "Fixture period",
        "license_url": "https://example.test/terms",
        "notes": ["Fixture"],
    }


def _population_profile(expected_record_count=2):
    return {
        "record_type": "population",
        "expected_record_count": expected_record_count,
        "expected_periods": ["2025-12-31"],
        "allowed_values": {"sex": ["男", "女"]},
        "expected_distinct_counts": {"nationality": 2},
        "expected_sums": {"value": 15},
        "anchors": [],
    }


def test_offline_pipeline_promotes_only_passing_output_and_reuses_identical_run(
    population_t1_file,
    tmp_path,
):
    arguments = {
        "source_path": population_t1_file,
        "source_id": "S14",
        "source_metadata": _metadata("population-t1", "xlsx", "25-12-t1"),
        "quality_profile": _population_profile(),
        "retrieved_at": "2026-08-30T09:00:00+09:00",
        "raw_root": tmp_path / "raw",
        "processed_root": tmp_path / "processed",
    }

    first = run_offline_pipeline(**arguments)
    second = run_offline_pipeline(**arguments)

    assert first.reused is False
    assert second.reused is True
    assert first.processed_dir == (
        tmp_path
        / "processed"
        / "fixture-series"
        / "S14"
        / "20260830_090000_s14"
    )
    assert first.normalized_path.exists()
    assert first.artifact_manifest_path.exists()
    assert first.quality_report_path.exists()
    assert first.run_manifest_path.exists()
    assert first.raw_snapshot.artifact_path.exists()

    artifact_manifest = json.loads(
        first.artifact_manifest_path.read_text(encoding="utf-8")
    )
    quality = json.loads(first.quality_report_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(first.run_manifest_path.read_text(encoding="utf-8"))
    assert artifact_manifest["record_count"] == 2
    assert artifact_manifest["normalized_sha256"] == quality["input_sha256"]
    assert quality["passed"] is True
    assert run_manifest["quality_passed"] is True
    assert run_manifest["raw_snapshot_relpath"].endswith(
        "fixture-series/S14/20260830_090000_s14/population_t1.xlsx"
    )


def test_failed_quality_gate_never_promotes_processed_directory(
    population_t1_file,
    tmp_path,
):
    with pytest.raises(QualityGateError) as captured:
        run_offline_pipeline(
            population_t1_file,
            source_id="S14",
            source_metadata=_metadata("population-t1", "xlsx", "25-12-t1"),
            quality_profile=_population_profile(expected_record_count=3),
            retrieved_at="2026-08-30T09:00:00+09:00",
            raw_root=tmp_path / "raw",
            processed_root=tmp_path / "processed",
        )

    assert captured.value.report["passed"] is False
    assert not (
        tmp_path
        / "processed"
        / "fixture-series"
        / "S14"
        / "20260830_090000_s14"
    ).exists()
    assert (
        tmp_path
        / "raw"
        / "fixture-series"
        / "S14"
        / "20260830_090000_s14"
        / "population_t1.xlsx"
    ).exists()


def test_existing_processed_content_is_verified_not_overwritten(
    population_t1_file,
    tmp_path,
):
    arguments = {
        "source_path": population_t1_file,
        "source_id": "S14",
        "source_metadata": _metadata("population-t1", "xlsx", "25-12-t1"),
        "quality_profile": _population_profile(),
        "retrieved_at": "2026-08-30T09:00:00+09:00",
        "raw_root": tmp_path / "raw",
        "processed_root": tmp_path / "processed",
    }
    result = run_offline_pipeline(**arguments)
    with result.normalized_path.open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")

    with pytest.raises(PipelineConflictError, match="processed run"):
        run_offline_pipeline(**arguments)


@pytest.mark.parametrize("kind", ["nationality", "prefecture"])
def test_pipeline_dispatches_both_crime_parser_families(
    kind,
    nationality_table130_file,
    prefecture_table13_file,
    tmp_path,
):
    if kind == "nationality":
        source_path = nationality_table130_file
        source_id = "S08"
        metadata = _metadata("npa-nationality", "xlsx", "130")
        records = parse_npa_nationality_totals(
            source_path,
            table_id="130",
            source_id=source_id,
        )
        profile = {
            "record_type": "nationality_crime",
            "expected_record_count": len(records),
            "expected_years": [2024],
            "allowed_values": {
                "population_scope": ["all_foreign"],
                "row_kind": ["region_total", "country", "subcategory"],
            },
            "expected_distinct_counts": {},
            "expected_sums": {},
            "anchors": [],
        }
    else:
        source_path = prefecture_table13_file
        source_id = "S02"
        metadata = _metadata("npa-prefecture-table13", "xls", "13")
        records = parse_npa_prefecture_table13(source_path, source_id=source_id)
        profile = {
            "record_type": "prefecture_crime",
            "expected_record_count": len(records),
            "expected_years": [2024, 2025],
            "allowed_values": {
                "population_scope": ["visiting_foreign"],
                "offense_scope": [
                    "criminal_and_special_law",
                    "criminal_code",
                    "special_law",
                ],
                "geography_type": [
                    "national",
                    "police_region",
                    "police_subregion",
                    "prefecture",
                ],
            },
            "expected_distinct_counts": {},
            "expected_sums": {},
            "anchors": [],
        }

    result = run_offline_pipeline(
        source_path,
        source_id=source_id,
        source_metadata=metadata,
        quality_profile=profile,
        retrieved_at="2026-08-30T09:00:00+09:00",
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
    )

    assert result.quality_report_path.exists()
    assert json.loads(result.quality_report_path.read_text())["passed"] is True
    run_manifest = json.loads(result.run_manifest_path.read_text())
    assert run_manifest["parser_contract_version"] == (
        2 if kind == "nationality" else 1
    )
