import json

from nationality_crime_atlas.catalog import rebuild_artifact_catalog
from nationality_crime_atlas.snapshot import snapshot_artifact


def _metadata():
    return {
        "series_id": "isa-population",
        "edition_id": "S14",
        "publisher": "Immigration Services Agency of Japan",
        "dataset": "Resident-foreigner statistics table 1",
        "source_table": "25-12-t1",
        "parser": "population-t1",
        "expected_format": "xlsx",
        "filename": "population_t1.xlsx",
        "landing_url": "https://example.test/landing",
        "download_url": "https://example.test/file.xlsx",
        "period": "2025-12-31 stock",
        "coverage_periods": ["2025-12-31"],
        "published_at": None,
        "revision": "initial",
        "stable_ids": {},
        "verified_at": "2026-08-30",
        "verification_level": "fixture",
        "expected_sha256": None,
        "license_url": "https://example.test/terms",
        "dimensions": ["prefecture", "nationality"],
        "definitions": ["Fixture definition"],
        "notes": ["Fixture"],
    }


def test_catalog_includes_raw_only_artifact_and_source_mapping(
    population_t1_file,
    tmp_path,
):
    snapshot_artifact(
        population_t1_file,
        raw_root=tmp_path / "raw",
        source_id="S14",
        source_metadata=_metadata(),
        retrieved_at="2026-08-30T09:00:00+09:00",
    )

    result = rebuild_artifact_catalog(
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
    )

    rows = [json.loads(line) for line in result.jsonl_path.read_text().splitlines()]
    assert result.record_count == 1
    assert rows[0]["processing_status"] == "raw_only"
    assert rows[0]["quality_passed"] is False
    assert rows[0]["source_id"] == "S14"
    assert rows[0]["publisher"] == "Immigration Services Agency of Japan"
    assert b"\r\n" not in result.csv_path.read_bytes()
