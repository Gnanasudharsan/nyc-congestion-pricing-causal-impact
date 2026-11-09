"""Small client for Socrata open-data portals (data.ny.gov, data.cityofnewyork.us).

Profiling runs aggregate SoQL queries on the server, so we can learn a table's
date coverage and size without downloading hundreds of millions of rows.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 20
TIMEOUT_SECONDS = 300
# NYC Open Data answers 503 to non-standard User-Agent strings, so we send the
# requests library default rather than a custom one.


@dataclass
class SocrataProfile:
    """What we learn about one Socrata table without downloading it."""

    dataset_id: str
    name: str
    columns: list[str]
    rows_updated_at: int | None
    row_count: int
    coverage_start: str | None = None
    coverage_end: str | None = None
    levels: dict[str, dict[str, int]] = field(default_factory=dict)


def _get_json(url: str, params: dict[str, str] | None = None) -> Any:
    """GET a JSON response, retrying transient server errors (5xx) with backoff."""
    for attempt in range(MAX_ATTEMPTS):
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        if response.status_code < 500 or attempt == MAX_ATTEMPTS - 1:
            break
        time.sleep(BACKOFF_SECONDS * (attempt + 1))
    response.raise_for_status()
    return response.json()


def resource_url(domain: str, dataset_id: str) -> str:
    """Return the SoQL resource endpoint for a dataset."""
    return f"https://{domain}/resource/{dataset_id}.json"


def coverage_query(date_column: str) -> dict[str, str]:
    """Build the SoQL parameters that return min date, max date, and row count."""
    return {"$select": f"min({date_column}) as start, max({date_column}) as end, count(*) as n"}


def levels_query(column: str, limit: int = 50) -> dict[str, str]:
    """Build SoQL parameters that count rows per level of a categorical column."""
    return {
        "$select": f"{column} as level, count(*) as n",
        "$group": column,
        "$order": "n DESC",
        "$limit": str(limit),
    }


def parse_count(value: Any) -> int:
    """Socrata returns counts as strings; convert defensively."""
    return int(float(value))


def profile_dataset(
    domain: str,
    dataset_id: str,
    date_column: str | None = None,
    group_columns: list[str] | None = None,
) -> SocrataProfile:
    """Profile a Socrata table: columns, row count, date coverage, and category levels."""
    metadata = _get_json(f"https://{domain}/api/views/{dataset_id}.json")
    columns = [c["fieldName"] for c in metadata["columns"] if not c["fieldName"].startswith(":")]
    url = resource_url(domain, dataset_id)

    if date_column:
        summary = _get_json(url, coverage_query(date_column))[0]
        row_count = parse_count(summary["n"])
        start, end = summary.get("start"), summary.get("end")
    else:
        row_count = parse_count(_get_json(url, {"$select": "count(*) as n"})[0]["n"])
        start = end = None

    levels: dict[str, dict[str, int]] = {}
    for column in group_columns or []:
        rows = _get_json(url, levels_query(column))
        levels[column] = {str(r.get("level")): parse_count(r["n"]) for r in rows}

    return SocrataProfile(
        dataset_id=dataset_id,
        name=metadata["name"],
        columns=columns,
        rows_updated_at=metadata.get("rowsUpdatedAt"),
        row_count=row_count,
        coverage_start=None if start is None else str(start),
        coverage_end=None if end is None else str(end),
        levels=levels,
    )


def download_csv(domain: str, dataset_id: str, destination: Path) -> Path:
    """Stream a full CSV export of a dataset to disk (use for small tables only)."""
    url = f"https://{domain}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    partial.rename(destination)
    return destination


def probe_dates(
    domain: str, dataset_id: str, date_column: str, dates: list[str], window_minutes: int = 10
) -> dict[str, int]:
    """Check whether rows exist near 08:00 on given dates, for tables too big to aggregate.

    Returns the number of rows (capped at 5) found in each window. Used for the
    multi-billion-row DOT speed feed, where count(*) and ORDER BY time out.
    """
    found: dict[str, int] = {}
    for day in dates:
        start = f"{day}T08:00:00"
        end = f"{day}T08:{window_minutes:02d}:00"
        rows = _get_json(
            resource_url(domain, dataset_id),
            {"$where": f"{date_column} between '{start}' and '{end}'", "$limit": "5"},
        )
        found[day] = len(rows)
    return found
