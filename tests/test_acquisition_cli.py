import hashlib
import io
import json
from pathlib import Path

from nationality_crime_atlas import acquisition
from nationality_crime_atlas.acquisition_cli import main


class FakeResponse:
    def __init__(self, payload):
        self._stream = io.BytesIO(payload)
        self.status = 200
        self.headers = {
            "Content-Length": str(len(payload)),
            "Content-Type": "application/octet-stream",
        }

    def read(self, size=-1):
        return self._stream.read(size)

    def geturl(self):
        return "https://example.test/final.xlsx"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_acquisition_cli_loads_registry_and_writes_catalog(
    population_t1_file,
    tmp_path,
    monkeypatch,
    capsys,
):
    payload = population_t1_file.read_bytes()
    artifact_hash = hashlib.sha256(payload).hexdigest()
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
                        "definitions": ["Fixture"],
                        "notes": ["Fixture"],
                    }
                },
                "editions": {
                    "S14": {
                        "series_id": "isa-population",
                        "source_table": "25-12-t1",
                        "expected_format": "xlsx",
                        "filename": "population_t1.xlsx",
                        "landing_url": "https://example.test/landing",
                        "download_url": "https://example.test/download.xlsx",
                        "period": "2025-12-31 stock",
                        "coverage_periods": ["2025-12-31"],
                        "published_at": None,
                        "revision": "initial",
                        "stable_ids": {},
                        "verified_at": "2026-08-30",
                        "verification_level": "fixture",
                        "expected_sha256": artifact_hash,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    profiles = tmp_path / "profiles.json"
    profiles.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": {
                    "S14": {
                        "record_type": "population",
                        "expected_artifact_sha256": artifact_hash,
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
    monkeypatch.setattr(
        acquisition,
        "urlopen",
        lambda request, timeout: FakeResponse(payload),
    )

    status = main(
        [
            "--source-id",
            "S14",
            "--registry",
            str(registry),
            "--profiles",
            str(profiles),
            "--raw-root",
            str(tmp_path / "raw"),
            "--processed-root",
            str(tmp_path / "processed"),
            "--retrieved-at",
            "2026-08-30T09:00:00+09:00",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    assert status == 0
    assert summary["source_id"] == "S14"
    assert summary["quality_passed"] is True
    assert summary["retrieved_at"] == "2026-08-30T09:00:00+09:00"
    assert Path(summary["catalog_jsonl"]).exists()
    assert Path(summary["catalog_csv"]).exists()
