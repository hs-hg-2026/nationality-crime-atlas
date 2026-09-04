import json
import shutil

import pytest

from nationality_crime_atlas.errors import IntegrityError, SnapshotConflictError
from nationality_crime_atlas.snapshot import snapshot_artifact


def _source_metadata(expected_format="xlsx"):
    return {
        "series_id": "isa-resident-foreigner-population-t1",
        "edition_id": "S14",
        "publisher": "Immigration Services Agency of Japan",
        "dataset": "Resident-foreigner statistics table 1",
        "source_table": "25-12-t1",
        "parser": "population-t1",
        "expected_format": expected_format,
        "landing_url": "https://example.test/landing",
        "download_url": "https://example.test/file.xlsx",
        "period": "2025-12-31 stock",
        "license_url": "https://example.test/terms",
        "notes": ["Fixture metadata"],
    }


def test_snapshot_copies_artifact_and_writes_complete_manifest(
    population_t1_file,
    tmp_path,
):
    raw_root = tmp_path / "raw"

    result = snapshot_artifact(
        population_t1_file,
        raw_root=raw_root,
        source_id="S14",
        source_metadata=_source_metadata(),
        retrieved_at="2026-08-30T09:00:00+09:00",
        published_at="2026-08-29",
        revision="initial",
    )

    assert result.snapshot_dir == (
        raw_root
        / "isa-resident-foreigner-population-t1"
        / "S14"
        / "20260830_090000_s14"
    )
    assert result.artifact_path.read_bytes() == population_t1_file.read_bytes()
    assert result.manifest_path == result.snapshot_dir / "manifest.json"
    assert result.reused is False

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_id"] == "S14"
    assert manifest["source_table"] == "25-12-t1"
    assert manifest["source_period"] == "2025-12-31 stock"
    assert manifest["file_format"] == "xlsx"
    assert manifest["expected_format"] == "xlsx"
    assert manifest["published_at"] == "2026-08-29"
    assert manifest["revision"] == "initial"
    assert manifest["immutable_snapshot"] is True
    assert manifest["snapshot_schema_version"] == 2
    assert manifest["series_id"] == "isa-resident-foreigner-population-t1"
    assert manifest["edition_id"] == "S14"
    assert manifest["snapshot_relpath"] == (
        "isa-resident-foreigner-population-t1/"
        "S14/20260830_090000_s14/population_t1.xlsx"
    )


def test_identical_snapshot_is_idempotently_reused(population_t1_file, tmp_path):
    arguments = {
        "raw_root": tmp_path / "raw",
        "source_id": "S14",
        "source_metadata": _source_metadata(),
        "retrieved_at": "2026-08-30T09:00:00+09:00",
    }

    first = snapshot_artifact(population_t1_file, **arguments)
    second = snapshot_artifact(population_t1_file, **arguments)

    assert first.snapshot_dir == second.snapshot_dir
    assert second.reused is True
    edition_root = (
        tmp_path / "raw" / "isa-resident-foreigner-population-t1" / "S14"
    )
    assert [path.name for path in edition_root.iterdir()] == [
        "20260830_090000_s14"
    ]


def test_different_content_cannot_reuse_source_and_retrieval_time(
    population_t1_file,
    tmp_path,
):
    raw_root = tmp_path / "raw"
    arguments = {
        "raw_root": raw_root,
        "source_id": "S14",
        "source_metadata": _source_metadata(),
        "retrieved_at": "2026-08-30T09:00:00+09:00",
    }
    original = snapshot_artifact(population_t1_file, **arguments)
    original_bytes = original.artifact_path.read_bytes()

    changed_dir = tmp_path / "changed"
    changed_dir.mkdir()
    changed = changed_dir / population_t1_file.name
    shutil.copyfile(population_t1_file, changed)
    with changed.open("ab") as handle:
        handle.write(b"different official revision")

    with pytest.raises(SnapshotConflictError, match="different artifact"):
        snapshot_artifact(changed, **arguments)

    assert original.artifact_path.read_bytes() == original_bytes


def test_expected_format_mismatch_stops_before_raw_write(population_t1_file, tmp_path):
    raw_root = tmp_path / "raw"

    with pytest.raises(IntegrityError, match="expected xls but detected xlsx"):
        snapshot_artifact(
            population_t1_file,
            raw_root=raw_root,
            source_id="S14",
            source_metadata=_source_metadata(expected_format="xls"),
            retrieved_at="2026-08-30T09:00:00+09:00",
        )

    assert not raw_root.exists()


@pytest.mark.parametrize(
    "source_id,retrieved_at,error",
    [
        ("../S14", "2026-08-30T09:00:00+09:00", "source_id"),
        ("S14", "2026-08-30T09:00:00", "timezone"),
    ],
)
def test_unsafe_identity_or_ambiguous_time_is_rejected_before_write(
    population_t1_file,
    tmp_path,
    source_id,
    retrieved_at,
    error,
):
    raw_root = tmp_path / "raw"

    with pytest.raises(ValueError, match=error):
        snapshot_artifact(
            population_t1_file,
            raw_root=raw_root,
            source_id=source_id,
            source_metadata=_source_metadata(),
            retrieved_at=retrieved_at,
        )

    assert not raw_root.exists()
