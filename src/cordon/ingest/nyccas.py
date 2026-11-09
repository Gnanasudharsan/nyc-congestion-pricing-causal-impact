"""Download NYC Community Air Survey (NYCCAS) real-time PM2.5 monitor data.

The NYC Health Department publishes hourly, corrected PM2.5 readings from its
DustTrak network at github.com/nychealth/nyccas-data. The repository is
updated daily and the data are described as preliminary, so every download
is pinned to a specific commit SHA and that SHA is stored in the manifest.

Timestamps are UTC and mark the start of the averaging hour (see the
repository README).
"""

from __future__ import annotations

from pathlib import Path

import requests

REPO_API = "https://api.github.com/repos/nychealth/nyccas-data"
RAW_BASE = "https://raw.githubusercontent.com/nychealth/nyccas-data"


def latest_commit_sha(branch: str = "main") -> str:
    """Return the commit SHA at the tip of the branch, to pin the download."""
    response = requests.get(f"{REPO_API}/commits/{branch}", timeout=60)
    response.raise_for_status()
    sha: str = response.json()["sha"]
    return sha


def month_file_path(year: int, month: int) -> str:
    """Path of one monthly history file inside the repository."""
    return f"hist/csv/{year}/{month}.csv"


def download_file(sha: str, repo_path: str, destination: Path) -> bool:
    """Download one file at a pinned commit. Returns False if it does not exist."""
    response = requests.get(f"{RAW_BASE}/{sha}/{repo_path}", timeout=120)
    if response.status_code == 404:
        return False
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return True
