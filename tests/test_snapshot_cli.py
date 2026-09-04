import json
from pathlib import Path

from nationality_crime_atlas.snapshot_cli import main


def test_snapshot_cli_uses_registry_and_reports_created_paths(
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
                    "isa-population": {
                        "publisher": "Immigration Services Agency of Japan",
                        "dataset": "Resident-foreigner statistics table 1",
                        "parser": "population-t1",
                        "license_url": "https://example.test/terms",
                        "dimensions": ["prefecture", "nationality"],
                        "definitions": ["Fixture definition"],
                        "notes": ["Fixture metadata"],
                    }
                },
                "editions": {
                    "S14": {
                        "series_id": "isa-population",
                        "source_table": "25-12-t1",
                        "expected_format": "xlsx",
                        "filename": "population_t1.xlsx",
                        "landing_url": "https://example.test/landing",
                        "download_url": "https://example.test/file.xlsx",
                        "period": "2025-12-31 stock",
                        "coverage_periods": ["2025-12-31"],
                        "published_at": "2026-08-29",
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
    raw_root = tmp_path / "raw"

    result = main(
        [
            str(population_t1_file),
            "--source-id",
            "S14",
            "--registry",
            str(registry),
            "--raw-root",
            str(raw_root),
            "--retrieved-at",
            "2026-08-30T09:00:00+09:00",
            "--published-at",
            "2026-08-29",
            "--revision",
            "initial",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert result == 0
    assert summary["source_id"] == "S14"
    assert summary["reused"] is False
    assert summary["artifact_path"].endswith("population_t1.xlsx")
    assert summary["manifest_path"].endswith("manifest.json")
    assert Path(summary["snapshot_dir"]) == (
        raw_root / "isa-population" / "S14" / "20260830_090000_s14"
    )
