import json
from pathlib import Path
from typing import Any

import pytest

from cordon.ingest import catalog, nyccas


def test_month_file_path_matches_repository_layout() -> None:
    assert nyccas.month_file_path(2024, 1) == "hist/csv/2024/1.csv"
    assert nyccas.month_file_path(2025, 12) == "hist/csv/2025/12.csv"


def test_download_file_returns_false_on_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeResponse:
        status_code = 404
        content = b""

        def raise_for_status(self) -> None:
            raise AssertionError("should not be called for 404")

    def fake_get(url: str, timeout: int) -> FakeResponse:
        assert "/abc123/" in url  # pinned to the commit SHA
        return FakeResponse()

    monkeypatch.setattr(nyccas.requests, "get", fake_get)
    assert nyccas.download_file("abc123", "hist/csv/2030/1.csv", tmp_path / "x.csv") is False
    assert not (tmp_path / "x.csv").exists()


def _profiles() -> dict[str, Any]:
    return {
        "_audited_at": "2026-11-09T12:00:00-05:00",
        "crz_entries": {
            "kind": "socrata",
            "dataset_id": "t6yz-b64h",
            "url": "https://data.ny.gov/d/t6yz-b64h",
            "row_count": 10,
            "coverage_start": "2025-01-05T00:00:00.000",
            "coverage_end": "2026-10-31T00:00:00.000",
            "usable_pre_period": False,
            "role": "descriptive_only",
        },
        "big_feed": {
            "kind": "socrata",
            "dataset_id": "i4gi-tjb9",
            "url": "https://example/d/i4gi-tjb9",
            "row_count": None,
            "coverage_start": "2019-01-01",
            "coverage_end": "2026-11-03",
            "usable_pre_period": True,
            "role": "outcome",
        },
        "broken": {"kind": "socrata", "id": "zzzz-0000", "error": "503 Server Error"},
    }


def test_render_table_marks_missing_pre_period_and_probe_rows() -> None:
    table = catalog.render_table(_profiles())
    assert table.startswith(catalog.BEGIN) and table.endswith(catalog.END)
    assert "| `crz_entries` |" in table and "**no**" in table
    assert "probe only" in table
    assert "error: 503" in table


def test_update_catalog_preserves_surrounding_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps(_profiles()))
    monkeypatch.setattr(catalog, "PROFILES_PATH", profiles_path)
    doc = tmp_path / "catalog.md"
    doc.write_text(f"intro\n{catalog.BEGIN}\nold\n{catalog.END}\noutro\n")
    catalog.update_catalog(doc)
    text = doc.read_text()
    assert text.startswith("intro\n") and text.endswith("outro\n")
    assert "old" not in text and "t6yz-b64h" in text
