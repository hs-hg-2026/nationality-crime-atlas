import json

import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.registry import load_source_registry


def test_project_registry_declares_all_current_sources():
    registry = load_source_registry("config/sources.json")

    assert set(registry) == {
        "S02",
        "S08",
        "S09",
        "S14",
        "S14_2024_12",
        "S15",
        "S16",
        "S17",
    }
    assert registry["S14"]["parser"] == "population-t1"
    assert registry["S14"]["series_id"] == "isa-resident-foreigner-population-t1"
    assert registry["S14"]["edition_id"] == "S14"
    assert registry["S02"]["expected_format"] == "xls"
    assert registry["S08"]["source_table"] == "130"
    assert registry["S09"]["source_table"] == "131"
    assert registry["S14_2024_12"]["coverage_periods"] == ["2024-12-31"]
    assert registry["S14_2024_12"]["expected_sha256"] == (
        "c523f699fed40f1bc7d2a975199c0669918e374c408a7423ce510c60500b3fb4"
    )
    assert registry["S15"]["parser"] == "npa-overall-prefecture-crime"
    assert registry["S15"]["source_table"] == "3"
    assert registry["S16"]["parser"] == "npa-prefecture-population"
    assert registry["S16"]["source_table"] == "144"
    assert registry["S17"]["parser"] == "statistics-bureau-japanese-population"
    assert registry["S17"]["source_table"] == "2"
    assert registry["S17"]["coverage_periods"] == ["2024-10-01"]
    assert registry["S17"]["expected_sha256"] == (
        "171c9930a3c881c42ded00fbaace83b4e6dd226d1a90cfddecd1daca2e376e82"
    )


def test_registry_rejects_missing_required_metadata(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "series": {"series-a": {"publisher": "NPA"}},
                "editions": {"S99": {"series_id": "series-a"}},
            }
        )
    )

    with pytest.raises(SchemaError, match="missing fields"):
        load_source_registry(path)


def test_registry_rejects_unknown_series_and_invalid_hash(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "series": {},
                "editions": {
                    "S99": {
                        "series_id": "missing-series",
                        "source_table": "1",
                        "expected_format": "xlsx",
                        "filename": "file.xlsx",
                        "landing_url": "https://example.test/landing",
                        "download_url": "https://example.test/file.xlsx",
                        "period": "2025",
                        "coverage_periods": ["2025"],
                        "published_at": None,
                        "revision": "initial",
                        "stable_ids": {},
                        "verified_at": "2026-08-30",
                        "verification_level": "primary",
                        "expected_sha256": "not-a-sha256",
                    }
                },
            }
        )
    )

    with pytest.raises(SchemaError, match="unknown series"):
        load_source_registry(path)


def test_registry_rejects_invalid_pinned_hash_for_known_series(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "series": {
                    "series-a": {
                        "publisher": "NPA",
                        "dataset": "Fixture",
                        "parser": "population-t1",
                        "license_url": "https://example.test/terms",
                        "dimensions": [],
                        "definitions": [],
                        "notes": [],
                    }
                },
                "editions": {
                    "S99": {
                        "series_id": "series-a",
                        "source_table": "1",
                        "expected_format": "xlsx",
                        "filename": "file.xlsx",
                        "landing_url": "https://example.test/landing",
                        "download_url": "https://example.test/file.xlsx",
                        "period": "2025",
                        "coverage_periods": ["2025"],
                        "published_at": None,
                        "revision": "initial",
                        "stable_ids": {},
                        "verified_at": "2026-08-30",
                        "verification_level": "primary",
                        "expected_sha256": "not-a-sha256",
                    }
                },
            }
        )
    )

    with pytest.raises(SchemaError, match="expected_sha256"):
        load_source_registry(path)
