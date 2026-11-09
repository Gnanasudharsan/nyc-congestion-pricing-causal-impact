from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import requests

from cordon.ingest import download

PAYLOAD = b"0123456789" * 100


class FakeResponse:
    """Minimal stand-in for a streamed requests.Response."""

    def __init__(self, body: bytes, status: int, fail_after: int | None = None) -> None:
        self.body = body
        self.status_code = status
        self.fail_after = fail_after

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        if self.fail_after is None:
            yield self.body
            return
        yield self.body[: self.fail_after]
        raise requests.ConnectionError("connection dropped")


def test_resumes_after_dropped_connection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, str]] = []

    def fake_get(url: str, stream: bool, timeout: int, headers: dict[str, str]) -> Any:
        calls.append(headers)
        if not headers:  # first attempt drops after 300 bytes
            return FakeResponse(PAYLOAD, 200, fail_after=300)
        start = int(headers["Range"].removeprefix("bytes=").rstrip("-"))
        return FakeResponse(PAYLOAD[start:], 206)

    monkeypatch.setattr(download, "remote_size", lambda url: len(PAYLOAD))
    monkeypatch.setattr(download.requests, "get", fake_get)
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)

    target = tmp_path / "file.zip"
    download.download_with_resume("https://example/file.zip", target)

    assert target.read_bytes() == PAYLOAD
    assert calls == [{}, {"Range": "bytes=300-"}]
    assert not (tmp_path / "file.zip.part").exists()


def test_size_mismatch_is_an_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(download, "remote_size", lambda url: len(PAYLOAD) + 1)
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: FakeResponse(PAYLOAD, 200))
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError):
        download.download_with_resume("https://example/f", tmp_path / "f", attempts=2)
    assert not (tmp_path / "f").exists()
