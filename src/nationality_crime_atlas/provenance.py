"""Artifact-level provenance and integrity helpers."""

import hashlib
import csv
import io
from pathlib import Path
from typing import Dict, Optional


OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return a streaming SHA-256 digest for a local artifact."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_file_format(path: Path) -> str:
    """Detect spreadsheet signatures or rectangular text CSV, not suffixes."""

    with Path(path).open("rb") as handle:
        signature = handle.read(8)
    if signature.startswith(b"PK\x03\x04"):
        return "xlsx"
    if signature == OLE_SIGNATURE:
        return "xls"
    payload = Path(path).read_bytes()
    if b"\x00" in payload or payload.lstrip().startswith(b"<"):
        return "unknown"
    for encoding in ("utf-8-sig", "cp932"):
        try:
            rows = list(csv.reader(io.StringIO(payload.decode(encoding)), strict=True))
        except (UnicodeDecodeError, csv.Error):
            continue
        if len(rows) >= 2 and len(rows[0]) >= 2 and all(len(row) == len(rows[0]) for row in rows):
            return "csv"
    return "unknown"


def build_manifest(
    path: Path,
    *,
    source_id: str,
    landing_url: str,
    download_url: str,
    retrieved_at: str,
    period_end: Optional[str] = None,
) -> Dict[str, object]:
    """Build a serializable provenance manifest for one immutable input file."""

    artifact = Path(path)
    manifest = {
        "source_id": source_id,
        "landing_url": landing_url,
        "download_url": download_url,
        "retrieved_at": retrieved_at,
        "local_filename": artifact.name,
        "byte_size": artifact.stat().st_size,
        "sha256": sha256_file(artifact),
        "file_format": detect_file_format(artifact),
        "derived_by_project": False,
    }
    if period_end is not None:
        manifest["period_end"] = period_end
    return manifest
