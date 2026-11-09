"""Profile NYC TLC trip-record parquet files remotely with DuckDB.

DuckDB's httpfs extension reads only parquet footers and the columns a query
touches, so row counts and pickup-date ranges cost a few megabytes per file
instead of the full file (FHVHV months are about 500 MB each).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import requests


@dataclass
class TlcFileProfile:
    """Schema and coverage of one monthly TLC file."""

    service: str
    month: str
    url: str
    columns: list[str]
    rows: int
    pickup_min: str
    pickup_max: str
    has_cbd_congestion_fee: bool


def file_url(base_url: str, service: str, month: str) -> str:
    """URL of one monthly file, e.g. .../yellow_tripdata_2025-01.parquet."""
    return f"{base_url}/{service}_tripdata_{month}.parquet"


def month_range(first: str, last: str) -> list[str]:
    """List YYYY-MM strings from first to last inclusive."""
    year, month = int(first[:4]), int(first[5:7])
    end_year, end_month = int(last[:4]), int(last[5:7])
    months: list[str] = []
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months


def available_months(base_url: str, service: str, first: str, today: date) -> list[str]:
    """Return the months for which a file exists (checked with HTTP HEAD)."""
    found: list[str] = []
    for month in month_range(first, f"{today.year:04d}-{today.month:02d}"):
        response = requests.head(file_url(base_url, service, month), timeout=60)
        if response.status_code == 200:
            found.append(month)
    return found


def connect() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with remote file access enabled."""
    connection = duckdb.connect()
    connection.execute("INSTALL httpfs; LOAD httpfs;")
    return connection


def profile_file(
    connection: duckdb.DuckDBPyConnection,
    base_url: str,
    service: str,
    month: str,
    pickup_column: str,
) -> TlcFileProfile:
    """Read schema, row count, and pickup range of one remote parquet file."""
    url = file_url(base_url, service, month)
    schema = connection.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()
    columns = [str(row[0]) for row in schema]
    result = connection.execute(
        f"SELECT count(*), min({pickup_column}), max({pickup_column}) FROM read_parquet('{url}')"
    ).fetchone()
    if result is None:
        raise RuntimeError(f"empty result profiling {url}")
    rows, pickup_min, pickup_max = result
    return TlcFileProfile(
        service=service,
        month=month,
        url=url,
        columns=columns,
        rows=int(rows),
        pickup_min=str(pickup_min),
        pickup_max=str(pickup_max),
        has_cbd_congestion_fee="cbd_congestion_fee" in columns,
    )
