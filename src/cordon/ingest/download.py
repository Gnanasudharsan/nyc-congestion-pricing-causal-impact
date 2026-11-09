"""Robust file download: resume interrupted transfers and verify the size.

Large public files (EPA zips, Citi Bike archives) sometimes stall mid-stream.
We write to ``<name>.part``, resume with an HTTP Range request after a
failure, and only rename to the final name once the byte count matches the
server's Content-Length. A truncated file is therefore never mistaken for a
complete one.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

LOG = logging.getLogger(__name__)
CHUNK_BYTES = 1 << 20


def remote_size(url: str) -> int | None:
    """Return the server-reported size in bytes, or None if unknown."""
    response = requests.head(url, timeout=60, allow_redirects=True)
    response.raise_for_status()
    length = response.headers.get("Content-Length")
    return int(length) if length is not None else None


def download_with_resume(
    url: str, destination: Path, attempts: int = 6, backoff_seconds: float = 10
) -> Path:
    """Download ``url`` to ``destination``, resuming after dropped connections."""
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    expected = remote_size(url)

    for attempt in range(1, attempts + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        if expected is not None and offset == expected:
            break
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with requests.get(url, stream=True, timeout=120, headers=headers) as response:
                response.raise_for_status()
                # 206 means the server honoured the range; 200 means start again.
                mode = "ab" if response.status_code == 206 else "wb"
                with partial.open(mode) as handle:
                    for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                        handle.write(chunk)
            if expected is None or partial.stat().st_size == expected:
                break
        except requests.RequestException as error:
            LOG.warning("download attempt %d/%d failed for %s: %s", attempt, attempts, url, error)
            time.sleep(backoff_seconds * attempt)
    else:
        raise RuntimeError(f"could not download {url} after {attempts} attempts")

    actual = partial.stat().st_size
    if expected is not None and actual != expected:
        raise RuntimeError(f"size mismatch for {url}: got {actual}, expected {expected}")
    partial.rename(destination)
    return destination
