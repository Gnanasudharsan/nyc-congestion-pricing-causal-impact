"""TLC trip records -> taxi-zone x day panel for T2, T3, S1, S3, S4.

For each monthly parquet file (read remotely with DuckDB, only the columns we
need) we aggregate trips by:

    pickup date, pickup zone, peak flag, dropoff group, service

where "dropoff group" is the dropoff zone's group from data/final/zone_groups.csv
(crz, border_ring, upper_manhattan_bronx, intermediate, far_control, excluded,
unknown). Keeping the dropoff group lets every outcome in the analysis plan be
built later without re-reading the trip files:

- T2: trips with pickup in a CRZ zone (any dropoff).
- S1/S3: trips with pickup in a non-CRZ zone and dropoff outside the CRZ.
- T3/S4: speeds of trips whose pickup and dropoff are in the same group.

TLC timestamps are local (America/New_York) wall-clock times without a zone.
Files contain a few trips dated outside their month; we keep only trips whose
pickup falls inside the file's month, so no trip is counted twice.

Speed-valid trips (plan section 4.3): duration 1-180 min, distance in (0, 50]
miles, implied speed 0.5-60 mph.
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import polars as pl

from cordon.config import FINAL_DIR, INTERIM_DIR, PROCESSED_DIR
from cordon.ingest.tlc import file_url, month_range

LOG = logging.getLogger(__name__)
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
OUT_DIR = INTERIM_DIR / "tlc"
ZONE_GROUPS = FINAL_DIR / "zone_groups.csv"
MAX_ATTEMPTS = 6
BACKOFF_SECONDS = 60
# Pause between files so sustained runs stay well below CloudFront's rate limits.
PAUSE_BETWEEN_FILES_SECONDS = 15


@dataclass(frozen=True)
class ServiceColumns:
    """Column names that differ between TLC services."""

    pickup: str
    dropoff: str
    distance: str
    shared_request: str | None = None
    shared_match: str | None = None


SERVICES = {
    "yellow": ServiceColumns("tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance"),
    "green": ServiceColumns("lpep_pickup_datetime", "lpep_dropoff_datetime", "trip_distance"),
    "fhvhv": ServiceColumns(
        "pickup_datetime",
        "dropoff_datetime",
        "trip_miles",
        "shared_request_flag",
        "shared_match_flag",
    ),
}


def month_bounds(month: str) -> tuple[str, str]:
    """First day of the month and first day of the next month, as ISO dates."""
    year, number = int(month[:4]), int(month[5:7])
    next_year, next_number = (year + 1, 1) if number == 12 else (year, number + 1)
    return f"{year:04d}-{number:02d}-01", f"{next_year:04d}-{next_number:02d}-01"


def aggregation_sql(service: str, month: str) -> str:
    """Build the SQL that aggregates one monthly file, reading only needed columns."""
    cols = SERVICES[service]
    start, end = month_bounds(month)
    url = file_url(BASE_URL, service, month)
    if cols.shared_request and cols.shared_match:
        shared_columns = (
            f"{cols.shared_request} AS shared_request, {cols.shared_match} AS shared_match"
        )
    else:
        shared_columns = "NULL AS shared_request, NULL AS shared_match"
    return f"""
    WITH trips AS (
        SELECT
            {cols.pickup} AS pickup,
            date_diff('second', {cols.pickup}, {cols.dropoff}) AS seconds,
            CAST({cols.distance} AS DOUBLE) AS miles,
            PULocationID AS pu, DOLocationID AS dlo,
            {shared_columns}
        FROM read_parquet('{url}')
        WHERE {cols.pickup} >= TIMESTAMP '{start}' AND {cols.pickup} < TIMESTAMP '{end}'
    ),
    labelled AS (
        SELECT t.*,
            CAST(pickup AS DATE) AS date,
            CASE WHEN isodow(pickup) >= 6
                 THEN hour(pickup) >= 9 AND hour(pickup) < 21
                 ELSE hour(pickup) >= 5 AND hour(pickup) < 21 END AS is_peak,
            coalesce(g.grp, 'unknown') AS do_group,
            (seconds BETWEEN 60 AND 10800) AND miles > 0 AND miles <= 50
              AND miles / (seconds / 3600.0) BETWEEN 0.5 AND 60 AS speed_valid
        FROM trips t LEFT JOIN zone_groups g ON t.dlo = g.location_id
    )
    SELECT
        '{service}' AS service, date, pu AS pu_location_id, is_peak, do_group,
        count(*) AS trips,
        sum(CASE WHEN shared_request = 'Y' THEN 1 ELSE 0 END) AS shared_requests,
        sum(CASE WHEN shared_match = 'Y' THEN 1 ELSE 0 END) AS shared_matches,
        sum(CASE WHEN speed_valid THEN 1 ELSE 0 END) AS speed_trips,
        sum(CASE WHEN speed_valid THEN miles ELSE 0 END) AS speed_miles,
        sum(CASE WHEN speed_valid THEN seconds ELSE 0 END) AS speed_seconds
    FROM labelled
    GROUP BY ALL
    """


def connect(zone_groups: Path = ZONE_GROUPS) -> duckdb.DuckDBPyConnection:
    """DuckDB connection with remote access and the zone-group lookup loaded."""
    connection = duckdb.connect()
    connection.execute(
        "INSTALL httpfs; LOAD httpfs; SET threads = 4; SET enable_progress_bar = false;"
    )
    connection.execute(
        f'CREATE TABLE zone_groups AS SELECT location_id, "group" AS grp '
        f"FROM read_csv_auto('{zone_groups}')"
    )
    return connection


def aggregate_month(connection: duckdb.DuckDBPyConnection, service: str, month: str) -> Path:
    """Aggregate one file to data/interim/tlc/<service>_<month>.parquet (skip if done)."""
    destination = OUT_DIR / f"{service}_{month}.parquet"
    if destination.exists():
        return destination
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    # CloudFront occasionally answers 403/5xx under sustained load; back off and retry.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            connection.execute(
                f"COPY ({aggregation_sql(service, month)}) TO '{partial}' (FORMAT parquet)"
            )
            break
        except duckdb.HTTPException as error:
            if attempt == MAX_ATTEMPTS:
                raise
            LOG.warning("tlc %s %s attempt %d failed: %s", service, month, attempt, error)
            time.sleep(BACKOFF_SECONDS * attempt)
    partial.rename(destination)
    return destination


def combine(out_dir: Path = OUT_DIR) -> pl.DataFrame:
    """Stack all monthly aggregates into one panel."""
    frame = pl.read_parquet(sorted(out_dir.glob("*.parquet")))
    return frame.sort("service", "date", "pu_location_id", "is_peak", "do_group")


def main() -> None:
    """Aggregate every month for every service, then write the combined panel."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", default="2023-01")
    parser.add_argument("--last", default="2026-09")
    parser.add_argument("--services", nargs="*", default=list(SERVICES))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    connection = connect()
    for service in args.services:
        for month in month_range(args.first, args.last):
            if not (OUT_DIR / f"{service}_{month}.parquet").exists():
                aggregate_month(connection, service, month)
                time.sleep(PAUSE_BETWEEN_FILES_SECONDS)
            LOG.info("tlc %s %s done", service, month)
    panel = combine()
    panel.write_parquet(PROCESSED_DIR / "tlc_zone_day.parquet")
    LOG.info("tlc panel: %d rows", panel.height)


if __name__ == "__main__":
    main()
