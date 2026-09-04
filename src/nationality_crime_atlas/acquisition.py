"""Safe HTTP acquisition for pinned official statistical artifacts."""

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Optional
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .catalog import CatalogResult, rebuild_artifact_catalog
from .errors import AcquisitionError, IntegrityError
from .pipeline import PipelineResult, run_offline_pipeline
from .provenance import sha256_file


USER_AGENT = "nationality-crime-atlas/0.1"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_BYTES = 256 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class AcquisitionResult:
    """Validated pipeline result and regenerated artifact catalogs."""

    pipeline: PipelineResult
    catalog_jsonl: Path
    catalog_csv: Path
    retrieved_at: str


def _retrieved_at(now: Callable[[], datetime]) -> str:
    value = now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Acquisition clock must return a timezone-aware datetime")
    return value.isoformat(timespec="seconds")


def _response_header(headers: object, name: str) -> Optional[str]:
    if hasattr(headers, "get"):
        value = headers.get(name)
        return str(value) if value is not None else None
    return None


def _validated_https_url(value: object, label: str) -> str:
    if not isinstance(value, str) or urlsplit(value).scheme.lower() != "https":
        raise AcquisitionError("%s must be an HTTPS URL" % label)
    return value


def _existing_manifest(
    raw_root: Path,
    *,
    series_id: object,
    source_id: str,
) -> Optional[Path]:
    if not isinstance(series_id, str):
        return None
    edition_root = Path(raw_root) / series_id / source_id
    manifests = sorted(edition_root.glob("*/manifest.json"))
    return manifests[-1] if manifests else None


def _read_manifest(path: Path) -> Mapping[str, object]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise IntegrityError("Existing raw manifest is invalid: %s" % path) from error
    if not isinstance(manifest, dict):
        raise IntegrityError("Existing raw manifest must contain an object: %s" % path)
    return manifest


def _reuse_existing(
    manifest_path: Path,
    *,
    source_id: str,
    source_metadata: Mapping[str, object],
    quality_profile: Mapping[str, object],
    raw_root: Path,
    processed_root: Path,
) -> AcquisitionResult:
    manifest = _read_manifest(manifest_path)
    if (
        manifest.get("source_id") != source_id
        or manifest.get("series_id") != source_metadata.get("series_id")
    ):
        raise IntegrityError("Existing raw manifest identity does not match registry")
    relative = manifest.get("snapshot_relpath")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise IntegrityError("Existing raw manifest snapshot path is unsafe")
    pipeline = run_offline_pipeline(
        Path(raw_root) / relative,
        source_id=source_id,
        source_metadata=source_metadata,
        quality_profile=quality_profile,
        retrieved_at=str(manifest.get("retrieved_at")),
        raw_root=Path(raw_root),
        processed_root=Path(processed_root),
        published_at=(
            str(manifest["published_at"])
            if manifest.get("published_at") is not None
            else None
        ),
        revision=(
            str(manifest["revision"]) if manifest.get("revision") is not None else None
        ),
        acquisition=(
            manifest.get("acquisition")
            if isinstance(manifest.get("acquisition"), dict)
            else None
        ),
    )
    catalog = rebuild_artifact_catalog(
        raw_root=Path(raw_root),
        processed_root=Path(processed_root),
    )
    return AcquisitionResult(
        pipeline=pipeline,
        catalog_jsonl=catalog.jsonl_path,
        catalog_csv=catalog.csv_path,
        retrieved_at=str(manifest.get("retrieved_at")),
    )


def acquire_source(
    *,
    source_id: str,
    source_metadata: Mapping[str, object],
    quality_profile: Mapping[str, object],
    raw_root: Path,
    processed_root: Path,
    opener=None,
    now: Optional[Callable[[], datetime]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    refresh: bool = False,
) -> AcquisitionResult:
    """Download, integrity-check, snapshot, parse, validate, and catalog one edition."""

    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    download_url = _validated_https_url(
        source_metadata.get("download_url"), "download_url"
    )
    filename = source_metadata.get("filename")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise AcquisitionError("Registered filename is unsafe")
    existing_manifest = _existing_manifest(
        Path(raw_root),
        series_id=source_metadata.get("series_id"),
        source_id=source_id,
    )
    if existing_manifest is not None and not refresh:
        return _reuse_existing(
            existing_manifest,
            source_id=source_id,
            source_metadata=source_metadata,
            quality_profile=quality_profile,
            raw_root=Path(raw_root),
            processed_root=Path(processed_root),
        )
    effective_opener = urlopen if opener is None else opener
    effective_now = (lambda: datetime.now().astimezone()) if now is None else now
    retrieved_at = _retrieved_at(effective_now)
    request = Request(
        download_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*;q=0.8",
        },
    )

    with tempfile.TemporaryDirectory(prefix="nca-download-") as temporary:
        downloaded = Path(temporary) / filename
        with effective_opener(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status != 200:
                raise AcquisitionError("Official download returned HTTP status %r" % status)
            final_url = _validated_https_url(response.geturl(), "redirected download URL")
            content_length_value = _response_header(response.headers, "Content-Length")
            try:
                content_length = (
                    int(content_length_value) if content_length_value is not None else None
                )
            except ValueError:
                content_length = None
            if content_length is not None and content_length > max_bytes:
                raise IntegrityError(
                    "Official artifact exceeds maximum size of %d bytes" % max_bytes
                )

            byte_size = 0
            with downloaded.open("wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    byte_size += len(chunk)
                    if byte_size > max_bytes:
                        raise IntegrityError(
                            "Official artifact exceeds maximum size of %d bytes"
                            % max_bytes
                        )
                    handle.write(chunk)
            if content_length is not None and byte_size != content_length:
                raise IntegrityError(
                    "Official artifact byte size differs from Content-Length"
                )

            response_headers = {
                "content_type": _response_header(response.headers, "Content-Type"),
                "content_length": content_length,
                "etag": _response_header(response.headers, "ETag"),
                "last_modified": _response_header(response.headers, "Last-Modified"),
            }

        observed_hash = sha256_file(downloaded)
        expected_hash = source_metadata.get("expected_sha256")
        if expected_hash is not None and observed_hash != expected_hash:
            raise IntegrityError(
                "Official artifact SHA-256 differs from pinned edition: "
                "expected %s, observed %s" % (expected_hash, observed_hash)
            )
        if existing_manifest is not None:
            existing = _read_manifest(existing_manifest)
            if existing.get("sha256") == observed_hash:
                return _reuse_existing(
                    existing_manifest,
                    source_id=source_id,
                    source_metadata=source_metadata,
                    quality_profile=quality_profile,
                    raw_root=Path(raw_root),
                    processed_root=Path(processed_root),
                )
            raise IntegrityError(
                "Official edition content changed; register and review a new revision"
            )
        acquisition = {
            "mode": "http_download",
            "requested_url": download_url,
            "final_url": final_url,
            "http_status": status,
            "response_headers": response_headers,
            "user_agent": USER_AGENT,
        }
        pipeline = run_offline_pipeline(
            downloaded,
            source_id=source_id,
            source_metadata=source_metadata,
            quality_profile=quality_profile,
            retrieved_at=retrieved_at,
            raw_root=Path(raw_root),
            processed_root=Path(processed_root),
            published_at=(
                str(source_metadata["published_at"])
                if source_metadata.get("published_at") is not None
                else None
            ),
            revision=(
                str(source_metadata["revision"])
                if source_metadata.get("revision") is not None
                else None
            ),
            acquisition=acquisition,
        )

    catalog: CatalogResult = rebuild_artifact_catalog(
        raw_root=Path(raw_root),
        processed_root=Path(processed_root),
    )
    return AcquisitionResult(
        pipeline=pipeline,
        catalog_jsonl=catalog.jsonl_path,
        catalog_csv=catalog.csv_path,
        retrieved_at=retrieved_at,
    )
