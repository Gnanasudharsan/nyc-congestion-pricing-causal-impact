import hashlib
import json
from pathlib import Path

from cordon.manifest import ManifestEntry, load_manifest, sha256_file, upsert_entry


def _entry(local_path: str, rows: int) -> ManifestEntry:
    return ManifestEntry(
        dataset="test",
        source_url="https://example.org/data.csv",
        local_path=local_path,
        downloaded_at="2026-11-09T00:00:00-05:00",
        sha256="0" * 64,
        rows=rows,
        coverage_start="2023-01-01",
        coverage_end="2025-12-31",
    )


def test_sha256_matches_hashlib(tmp_path: Path) -> None:
    file = tmp_path / "x.bin"
    payload = b"cordon" * 500_000
    file.write_bytes(payload)
    assert sha256_file(file) == hashlib.sha256(payload).hexdigest()


def test_missing_manifest_returns_skeleton(tmp_path: Path) -> None:
    assert load_manifest(tmp_path / "none.json") == {"schema_version": 1, "entries": {}}


def test_upsert_replaces_entry_and_sorts_keys(tmp_path: Path) -> None:
    path = tmp_path / "MANIFEST.json"
    upsert_entry(path, _entry("raw/b.csv", 1))
    upsert_entry(path, _entry("raw/a.csv", 2))
    upsert_entry(path, _entry("raw/b.csv", 3))
    entries = json.loads(path.read_text())["entries"]
    assert list(entries) == ["raw/a.csv", "raw/b.csv"]
    assert entries["raw/b.csv"]["rows"] == 3
