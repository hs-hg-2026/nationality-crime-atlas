import hashlib

from nationality_crime_atlas.provenance import build_manifest, detect_file_format


def test_manifest_records_hash_format_and_source_metadata(population_t1_file):
    expected_hash = hashlib.sha256(population_t1_file.read_bytes()).hexdigest()

    manifest = build_manifest(
        population_t1_file,
        source_id="S14",
        landing_url="https://example.test/landing",
        download_url="https://example.test/file.xlsx",
        retrieved_at="2026-08-30T09:00:00+09:00",
        period_end="2025-12-31",
    )

    assert manifest["source_id"] == "S14"
    assert manifest["sha256"] == expected_hash
    assert manifest["file_format"] == "xlsx"
    assert manifest["byte_size"] == population_t1_file.stat().st_size
    assert manifest["derived_by_project"] is False


def test_detect_file_format_recognizes_legacy_xls(prefecture_table13_file):
    assert detect_file_format(prefecture_table13_file) == "xls"
