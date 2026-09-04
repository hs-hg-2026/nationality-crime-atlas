import json
from pathlib import Path

from nationality_crime_atlas.pipeline_cli import main


def test_pipeline_cli_loads_registries_and_reports_promoted_paths(
    population_t1_file,
    tmp_path,
    capsys,
):
    registry = tmp_path / "sources.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "series": {
                    "fixture-series": {
                        "publisher": "Official publisher",
                        "dataset": "Fixture dataset",
                        "parser": "population-t1",
                        "license_url": "https://example.test/terms",
                        "dimensions": ["prefecture", "nationality"],
                        "definitions": ["Fixture definition"],
                        "notes": ["Fixture"],
                    }
                },
                "editions": {
                    "S14": {
                        "series_id": "fixture-series",
                        "source_table": "25-12-t1",
                        "expected_format": "xlsx",
                        "filename": "population_t1.xlsx",
                        "landing_url": "https://example.test/landing",
                        "download_url": "https://example.test/download",
                        "period": "Fixture period",
                        "coverage_periods": ["2025-12-31"],
                        "published_at": None,
                        "revision": "initial",
                        "stable_ids": {},
                        "verified_at": "2026-08-30",
                        "verification_level": "fixture",
                        "expected_sha256": None,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    profiles = tmp_path / "quality_profiles.json"
    profiles.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": {
                    "S14": {
                        "record_type": "population",
                        "expected_record_count": 2,
                        "expected_periods": ["2025-12-31"],
                        "allowed_values": {"sex": ["男", "女"]},
                        "expected_distinct_counts": {"nationality": 2},
                        "expected_sums": {"value": 15},
                        "anchors": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = main(
        [
            str(population_t1_file),
            "--source-id",
            "S14",
            "--registry",
            str(registry),
            "--profiles",
            str(profiles),
            "--retrieved-at",
            "2026-08-30T09:00:00+09:00",
            "--raw-root",
            str(tmp_path / "raw"),
            "--processed-root",
            str(tmp_path / "processed"),
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert result == 0
    assert summary["source_id"] == "S14"
    assert summary["quality_passed"] is True
    assert summary["reused"] is False
    assert Path(summary["processed_dir"]).exists()
