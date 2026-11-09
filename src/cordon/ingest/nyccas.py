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

import duckdb
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


# Completeness rule from docs/analysis-plan.md section 5.2.
MIN_HOURS_PER_DAY = 18
MIN_DAYS_PER_WEEK = 5
VALID_RANGE = (-5.0, 500.0)


def weekly_completeness(raw_dir: Path, start: str, end: str) -> dict[str, dict[str, float]]:
    """Share of weeks in [start, end] with enough valid data, per site.

    Uses only counts of valid readings, never their values. Hours are
    converted from UTC to New York local time before grouping into days.
    """
    connection = duckdb.connect()
    low, high = VALID_RANGE
    files = str(raw_dir / "*" / "*.csv")
    query = f"""
        WITH hours AS (
            SELECT SiteID,
                   timezone('America/New_York', ObservationTimeUTC::TIMESTAMP AT TIME ZONE 'UTC')
                       AS local_time
            FROM read_csv_auto('{files}', union_by_name = true)
            WHERE Value BETWEEN {low} AND {high}
        ),
        days AS (
            SELECT SiteID, local_time::DATE AS day
            FROM hours GROUP BY 1, 2 HAVING count(*) >= {MIN_HOURS_PER_DAY}
        ),
        weeks AS (
            SELECT SiteID, date_trunc('week', day) AS week
            FROM days WHERE day BETWEEN DATE '{start}' AND DATE '{end}'
            GROUP BY 1, 2 HAVING count(*) >= {MIN_DAYS_PER_WEEK}
        )
        SELECT SiteID, count(*) FROM weeks GROUP BY 1
    """
    total_weeks = connection.execute(
        f"SELECT count(DISTINCT date_trunc('week', d)) FROM "
        f"range(DATE '{start}', DATE '{end}' + 1, INTERVAL 1 DAY) AS t(d) "
        f"WHERE date_trunc('week', d) >= DATE '{start}'"
    ).fetchall()[0][0]
    rows = connection.execute(query).fetchall()
    return {
        str(site): {
            "valid_weeks": int(n),
            "total_weeks": int(total_weeks),
            "share": n / total_weeks,
        }
        for site, n in rows
    }
