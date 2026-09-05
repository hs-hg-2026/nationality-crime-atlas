import json

from nationality_crime_atlas.cli import main


def test_population_cli_writes_jsonl_and_manifest(population_t1_file, tmp_path):
    output = tmp_path / "population.jsonl"
    manifest = tmp_path / "population.manifest.json"

    result = main(
        [
            "population-t1",
            str(population_t1_file),
            "--source-id",
            "S14",
            "--landing-url",
            "https://example.test/landing",
            "--download-url",
            "https://example.test/file.xlsx",
            "--retrieved-at",
            "2026-08-30T09:00:00+09:00",
            "--output",
            str(output),
            "--manifest",
            str(manifest),
        ]
    )

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    metadata = json.loads(manifest.read_text())
    assert result == 0
    assert len(rows) == 2
    assert rows[0]["nationality"] == "韓国"
    assert metadata["source_id"] == "S14"
    assert metadata["record_count"] == 2
    assert metadata["period_end"] == "2025-12-31"


def test_nationality_population_totals_cli_writes_jsonl_and_manifest(
    nationality_population_totals_file,
    tmp_path,
):
    output = tmp_path / "nationality_population_totals.jsonl"
    manifest = tmp_path / "nationality_population_totals.manifest.json"

    result = main(
        [
            "population-nationality-totals",
            str(nationality_population_totals_file),
            "--source-id",
            "S19_2024",
            "--landing-url",
            "https://example.test/landing",
            "--download-url",
            "https://example.test/file.xlsx",
            "--retrieved-at",
            "2026-09-05T20:00:00+09:00",
            "--output",
            str(output),
            "--manifest",
            str(manifest),
        ]
    )

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    metadata = json.loads(manifest.read_text())
    assert result == 0
    assert len(rows) == 8
    assert rows[0]["row_kind"] == "national_total"
    assert metadata["source_id"] == "S19_2024"
    assert metadata["period_end"] == "2024-12-31"
