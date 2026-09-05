import json

import pytest

from nationality_crime_atlas.errors import SchemaError
from nationality_crime_atlas.registry import load_source_registry


def test_project_registry_declares_all_current_sources():
    registry = load_source_registry("config/sources.json")

    assert set(registry) == {
        "S02",
        "S08",
        "S08_2020",
        "S08_2021",
        "S08_2022",
        "S08_2023",
        "S09",
        "S09_2020",
        "S09_2021",
        "S09_2022",
        "S09_2023",
        "S14",
        "S14_2024_12",
        "S15",
        "S15_2020",
        "S15_2021",
        "S15_2022",
        "S15_2023",
        "S16",
        "S17",
        "S17_2021",
        "S17_2022",
        "S17_2023",
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


def test_project_registry_pins_historical_npa_detail_editions():
    registry = load_source_registry("config/sources.json")
    expected = {
        "S15_2020": ("3", "R02_003.xlsx", "308cecb15fa3c33b13ecd4e5d5eaf08890aab326a796f5aed6dc8b7dc6bff956"),
        "S15_2021": ("3", "R03_003.xlsx", "2f007c3d6ef700c3fbbe28f63f3f9ce7abadb67eb86e2207ef4344ed9b2e1270"),
        "S15_2022": ("3", "R04_003.xlsx", "e05be7dcc58815eb894eafba4e24df5204ae67e78ba849c1750b7e786487d053"),
        "S15_2023": ("3", "R05_003.xlsx", "4dfa94cfd558fc98fd571e79fb8a4e79c2ceebe2e8b2e12c5d14b75c1d50915a"),
        "S08_2020": ("130", "R02_130.xlsx", "5e6ceb16a748f9d4be6313e9b4d3b5aed50e026cbf19e0677891c66ae86a2efd"),
        "S08_2021": ("130", "R03_130.xlsx", "45a4bf1c58d5d0cb4b933d4bc9db5068f12fd66646acd401221fabc71df5f36f"),
        "S08_2022": ("130", "R04_130.xlsx", "901cc0c472411468ba21e88de99d7aa9b3442fe4e6047360e6d3234744ead5ba"),
        "S08_2023": ("130", "R05_130.xlsx", "b1a4a6c9351f77171fc40c57cfbdce4e9fb1e90a68156cab7fefd7cf33a8f9e5"),
        "S09_2020": ("131", "R02_131.xlsx", "91c91a661e67f0ecf593766e45ecd8d29a4b8d06dbf858f72696ac11c995a519"),
        "S09_2021": ("131", "R03_131.xlsx", "eabb1b97c0874adb8bb3227cb320aa828fbec3a8d7b954a4d4cc10743048f9ea"),
        "S09_2022": ("131", "R04_131.xlsx", "585e3a413906349261b971485c95640582e916943e80d05bf910aa9eb5ca879c"),
        "S09_2023": ("131", "R05_131.xlsx", "c4c29c849239552b14a9c9ba339c42fd661a3b39b2231cb14a7050f7397f27bb"),
    }

    for source_id, (table, filename, artifact_hash) in expected.items():
        year = int(source_id[-4:])
        metadata = registry[source_id]
        assert metadata["source_table"] == table
        assert metadata["filename"] == filename
        assert metadata["coverage_periods"] == [str(year)]
        assert metadata["expected_sha256"] == artifact_hash
        assert metadata["verified_at"] == "2026-09-05"


def test_project_registry_pins_historical_japanese_population_editions():
    registry = load_source_registry("config/sources.json")
    expected = {
        "S17_2021": (
            "05k2021-2.xlsx",
            "5acd98b56ab29648d39c780098826c8916cd5daddf663bcf72d1198e32aef226",
        ),
        "S17_2022": (
            "05k2022-2.xlsx",
            "c91ad5d7dd29f067f0d20d27575e8fcc1ab1fb8dc7871b1393080a3b5e682fc2",
        ),
        "S17_2023": (
            "05k2023-2.xlsx",
            "53a63aea1b02c672f25a9e9e563f9c698901a52e651dd8d2e81c2ef1092d1a47",
        ),
    }

    for source_id, (filename, artifact_hash) in expected.items():
        year = int(source_id[-4:])
        metadata = registry[source_id]
        assert metadata["series_id"] == "statistics-bureau-japanese-population-prefecture"
        assert metadata["source_table"] == "2"
        assert metadata["filename"] == filename
        assert metadata["coverage_periods"] == [f"{year}-10-01"]
        assert metadata["expected_sha256"] == artifact_hash
        assert metadata["verified_at"] == "2026-09-05"


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
