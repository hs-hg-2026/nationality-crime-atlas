import hashlib
import io
import json
from datetime import datetime, timezone

import pytest

from nationality_crime_atlas.acquisition import acquire_source
from nationality_crime_atlas.errors import IntegrityError


class FakeResponse:
    def __init__(self, payload, *, status=200, final_url="https://example.test/final"):
        self._stream = io.BytesIO(payload)
        self.status = status
        self.headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Content-Length": str(len(payload)),
            "ETag": '"fixture-etag"',
            "Last-Modified": "Fri, 29 Aug 2026 00:00:00 GMT",
        }
        self._final_url = final_url

    def read(self, size=-1):
        return self._stream.read(size)

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def _metadata(payload, *, expected_sha256=None):
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
        "download_url": "https://example.test/download.xlsx",
        "period": "2025-12-31 stock",
        "coverage_periods": ["2025-12-31"],
        "published_at": "2026-08-29T10:00:00+09:00",
        "revision": "initial",
        "stable_ids": {"fixture": "S14"},
        "verified_at": "2026-08-30",
        "verification_level": "fixture",
        "expected_sha256": expected_sha256 or hashlib.sha256(payload).hexdigest(),
        "license_url": "https://example.test/terms",
        "dimensions": ["prefecture", "nationality"],
        "definitions": ["Fixture definition"],
        "notes": ["Fixture metadata"],
    }


def _profile(expected_hash):
    return {
        "record_type": "population",
        "expected_artifact_sha256": expected_hash,
        "expected_record_count": 2,
        "expected_periods": ["2025-12-31"],
        "allowed_values": {"sex": ["男", "女"]},
        "expected_distinct_counts": {"nationality": 2},
        "expected_sums": {"value": 15},
        "anchors": [],
    }


def test_acquisition_downloads_to_temporary_storage_then_promotes_and_catalogs(
    population_t1_file,
    tmp_path,
):
    payload = population_t1_file.read_bytes()
    expected_hash = hashlib.sha256(payload).hexdigest()
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout, request.headers["User-agent"]))
        return FakeResponse(payload)

    result = acquire_source(
        source_id="S14",
        source_metadata=_metadata(payload),
        quality_profile=_profile(expected_hash),
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
        opener=opener,
        now=lambda: datetime(2026, 8, 30, 1, 2, 3, tzinfo=timezone.utc),
    )

    assert calls == [
        ("https://example.test/download.xlsx", 60.0, "nationality-crime-atlas/0.1")
    ]
    assert result.pipeline.quality_report_path.exists()
    assert result.catalog_jsonl == tmp_path / "processed" / "_catalog" / "artifacts.jsonl"
    assert result.catalog_csv == tmp_path / "processed" / "_catalog" / "artifacts.csv"

    manifest = json.loads(result.pipeline.raw_snapshot.manifest_path.read_text())
    assert manifest["acquisition_mode"] == "http_download"
    assert manifest["acquisition"]["http_status"] == 200
    assert manifest["acquisition"]["final_url"] == "https://example.test/final"
    assert manifest["acquisition"]["response_headers"]["etag"] == '"fixture-etag"'
    assert manifest["sha256"] == expected_hash
    assert manifest["snapshot_relpath"].startswith(
        "isa-population/S14/20260830_010203_s14/"
    )

    rows = [json.loads(line) for line in result.catalog_jsonl.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["source_id"] == "S14"
    assert rows[0]["series_id"] == "isa-population"
    assert rows[0]["processing_status"] == "validated"
    assert rows[0]["quality_passed"] is True
    assert rows[0]["record_count"] == 2
    assert rows[0]["raw_relpath"].endswith("population_t1.xlsx")


@pytest.mark.parametrize(
    "expected_sha256,max_bytes,error",
    [
        ("0" * 64, 10_000_000, "SHA-256"),
        (None, 32, "maximum size"),
    ],
)
def test_acquisition_integrity_failure_leaves_no_raw_or_processed_data(
    population_t1_file,
    tmp_path,
    expected_sha256,
    max_bytes,
    error,
):
    payload = population_t1_file.read_bytes()
    metadata = _metadata(payload, expected_sha256=expected_sha256)
    if expected_sha256 is None:
        metadata["expected_sha256"] = hashlib.sha256(payload).hexdigest()

    with pytest.raises(IntegrityError, match=error):
        acquire_source(
            source_id="S14",
            source_metadata=metadata,
            quality_profile=_profile(metadata["expected_sha256"]),
            raw_root=tmp_path / "raw",
            processed_root=tmp_path / "processed",
            opener=lambda request, timeout: FakeResponse(payload),
            now=lambda: datetime(2026, 8, 30, 1, 2, 3, tzinfo=timezone.utc),
            max_bytes=max_bytes,
        )

    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "processed").exists()


def test_repeat_acquisition_reuses_validated_edition_without_network_or_duplicate(
    population_t1_file,
    tmp_path,
):
    payload = population_t1_file.read_bytes()
    expected_hash = hashlib.sha256(payload).hexdigest()
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        return FakeResponse(payload)

    arguments = {
        "source_id": "S14",
        "source_metadata": _metadata(payload),
        "quality_profile": _profile(expected_hash),
        "raw_root": tmp_path / "raw",
        "processed_root": tmp_path / "processed",
        "opener": opener,
    }
    first = acquire_source(
        **arguments,
        now=lambda: datetime(2026, 8, 30, 1, 2, 3, tzinfo=timezone.utc),
    )
    second = acquire_source(
        **arguments,
        now=lambda: datetime(2026, 8, 31, 1, 2, 3, tzinfo=timezone.utc),
    )

    assert first.pipeline.reused is False
    assert second.pipeline.reused is True
    assert second.retrieved_at == first.retrieved_at
    assert calls == ["https://example.test/download.xlsx"]
    assert len(list((tmp_path / "raw").rglob("manifest.json"))) == 1
    assert len(second.catalog_jsonl.read_text().splitlines()) == 1


def test_refresh_downloads_but_reuses_same_hash_without_duplicate(
    population_t1_file,
    tmp_path,
):
    payload = population_t1_file.read_bytes()
    expected_hash = hashlib.sha256(payload).hexdigest()
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        return FakeResponse(payload)

    arguments = {
        "source_id": "S14",
        "source_metadata": _metadata(payload),
        "quality_profile": _profile(expected_hash),
        "raw_root": tmp_path / "raw",
        "processed_root": tmp_path / "processed",
        "opener": opener,
    }
    first = acquire_source(
        **arguments,
        now=lambda: datetime(2026, 8, 30, 1, 2, 3, tzinfo=timezone.utc),
    )
    refreshed = acquire_source(
        **arguments,
        now=lambda: datetime(2026, 8, 31, 1, 2, 3, tzinfo=timezone.utc),
        refresh=True,
    )

    assert first.pipeline.reused is False
    assert refreshed.pipeline.reused is True
    assert refreshed.retrieved_at == first.retrieved_at
    assert calls == [
        "https://example.test/download.xlsx",
        "https://example.test/download.xlsx",
    ]
    assert len(list((tmp_path / "raw").rglob("manifest.json"))) == 1
