"""MTA subway hourly ridership -> station-complex x day panel (R2, secondary).

Two source tables are stitched at the year boundary:
- 2020-2024: data.ny.gov wujg-7c2s
- 2025 onward: data.ny.gov 5wq4-mkjj

Aggregation runs on the server one month at a time so each query stays small.
Timestamps are local wall-clock hours. Station complexes are flagged as CRZ
using the ``cbd`` field of the MTA Subway Stations table (39hk-dx4f); a complex
counts as CRZ if any of its stations is flagged.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import polars as pl

from cordon.config import INTERIM_DIR, PROCESSED_DIR, RAW_DIR
from cordon.ingest.socrata import query_all

LOG = logging.getLogger(__name__)
DOMAIN = "data.ny.gov"
TABLE_BEFORE_2025 = "wujg-7c2s"
TABLE_FROM_2025 = "5wq4-mkjj"
OUT_DIR = INTERIM_DIR / "subway"
STATIONS_CSV = RAW_DIR / "socrata" / "subway_stations.csv"
CHUNK_DAYS = 7
FIRST_DAY = date(2023, 1, 1)
LAST_DAY = date(2026, 10, 29)  # last day in the 2025+ table at audit time


def table_for(day: date) -> str:
    """Which source table holds a given day."""
    return TABLE_BEFORE_2025 if day < date(2025, 1, 1) else TABLE_FROM_2025


def week_starts(first: date, last: date) -> list[date]:
    """Chunk starts every 7 days; chunks never cross the Jan 1, 2025 table seam."""
    starts: list[date] = []
    day = first
    while day <= last:
        starts.append(day)
        next_day = day + timedelta(days=CHUNK_DAYS)
        seam = date(2025, 1, 1)
        day = seam if day < seam < next_day else next_day
    return starts


def fetch_chunk(start: date, last: date) -> pl.DataFrame:
    """Daily entries by station complex for one chunk of up to 7 days.

    Server-side aggregation takes about 2 seconds per day of data; a whole month
    in one query exceeds the 300-second timeout, so we query a week at a time.
    """
    end = min(
        start + timedelta(days=CHUNK_DAYS),
        date(2025, 1, 1) if start < date(2025, 1, 1) else last + timedelta(days=1),
        last + timedelta(days=1),
    )
    rows = query_all(
        DOMAIN,
        table_for(start),
        {
            "$select": "station_complex_id, date_trunc_ymd(transit_timestamp) as day, "
            "sum(ridership) as entries",
            "$where": f"transit_timestamp >= '{start.isoformat()}T00:00:00' "
            f"and transit_timestamp < '{end.isoformat()}T00:00:00'",
            "$group": "station_complex_id, day",
            "$order": "station_complex_id, day",
        },
    )
    return (
        pl.DataFrame(
            rows, schema={"station_complex_id": pl.Utf8, "day": pl.Utf8, "entries": pl.Utf8}
        )
        .with_columns(
            pl.col("day").str.slice(0, 10).str.to_date().alias("date"),
            pl.col("entries").cast(pl.Float64),
        )
        .drop("day")
    )


def crz_complexes(path: str = str(STATIONS_CSV)) -> pl.DataFrame:
    """Station complexes with a CRZ flag and borough."""
    stations = pl.read_csv(path, infer_schema_length=0)
    return stations.group_by(pl.col("Complex ID").alias("station_complex_id")).agg(
        (pl.col("CBD").str.to_lowercase() == "true").any().alias("is_crz"),
        pl.col("Borough").first().alias("borough"),
        pl.col("Stop Name").first().alias("station_name"),
    )


def main() -> None:
    """Fetch every month (resumable) and write data/processed/subway_station_day.parquet."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for start in week_starts(FIRST_DAY, LAST_DAY):
        destination = OUT_DIR / f"{start.isoformat()}.parquet"
        if destination.exists():
            continue
        fetch_chunk(start, LAST_DAY).write_parquet(destination)
        LOG.info("subway chunk %s done", start)
    panel = pl.read_parquet(sorted(OUT_DIR.glob("*.parquet")))
    panel = panel.join(crz_complexes(), on="station_complex_id", how="left").sort(
        "station_complex_id", "date"
    )
    panel.write_parquet(PROCESSED_DIR / "subway_station_day.parquet")
    LOG.info(
        "subway panel: %d rows, %d complexes", panel.height, panel["station_complex_id"].n_unique()
    )


if __name__ == "__main__":
    main()
