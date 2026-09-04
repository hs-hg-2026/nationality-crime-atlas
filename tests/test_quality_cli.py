import json
from dataclasses import asdict

from nationality_crime_atlas.population import parse_population_t1
from nationality_crime_atlas.quality_cli import main


def _write_inputs(population_t1_file, tmp_path, expected_record_count):
    normalized = tmp_path / "population.jsonl"
    records = list(parse_population_t1(population_t1_file, source_id="S14"))
    normalized.write_text(
        "".join(
            json.dumps(asdict(record), ensure_ascii=False) + "\n"
            for record in records
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
                        "expected_record_count": expected_record_count,
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
    manifest = tmp_path / "artifact.manifest.json"
    manifest.write_text(
        json.dumps({"source_id": "S14", "record_count": 2}),
        encoding="utf-8",
    )
    return normalized, profiles, manifest


def test_quality_cli_writes_passing_report(population_t1_file, tmp_path, capsys):
    normalized, profiles, manifest = _write_inputs(
        population_t1_file,
        tmp_path,
        expected_record_count=2,
    )
    report_path = tmp_path / "quality.json"

    result = main(
        [
            str(normalized),
            "--source-id",
            "S14",
            "--profiles",
            str(profiles),
            "--artifact-manifest",
            str(manifest),
            "--report",
            str(report_path),
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result == 0
    assert summary == {"passed": True, "record_count": 2, "source_id": "S14"}
    assert report["passed"] is True


def test_quality_cli_returns_one_and_keeps_failure_report(
    population_t1_file,
    tmp_path,
):
    normalized, profiles, manifest = _write_inputs(
        population_t1_file,
        tmp_path,
        expected_record_count=3,
    )
    report_path = tmp_path / "quality.json"

    result = main(
        [
            str(normalized),
            "--source-id",
            "S14",
            "--profiles",
            str(profiles),
            "--artifact-manifest",
            str(manifest),
            "--report",
            str(report_path),
        ]
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result == 1
    assert report["passed"] is False
    assert any("expected record_count 3" in error for error in report["errors"])
