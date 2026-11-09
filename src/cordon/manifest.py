"""Record data provenance in data/MANIFEST.json.

Each downloaded file gets an entry with its source, download time, row
count, and SHA-256 checksum, so anyone rebuilding the project can confirm
they are analysing the same bytes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CHUNK_BYTES = 1 << 20


@dataclass(frozen=True)
class ManifestEntry:
    """Provenance for one raw file."""

    dataset: str
    source_url: str
    local_path: str
    downloaded_at: str
    sha256: str
    rows: int | None
    coverage_start: str | None
    coverage_end: str | None
    notes: str = ""


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    """Load the manifest, returning an empty skeleton if it does not exist."""
    if not path.exists():
        return {"schema_version": 1, "entries": {}}
    with path.open() as handle:
        manifest: dict[str, Any] = json.load(handle)
    return manifest


def upsert_entry(path: Path, entry: ManifestEntry) -> None:
    """Insert or replace an entry keyed by its local path, then save sorted JSON."""
    manifest = load_manifest(path)
    manifest["entries"][entry.local_path] = asdict(entry)
    manifest["entries"] = dict(sorted(manifest["entries"].items()))
    path.write_text(json.dumps(manifest, indent=2) + "\n")
