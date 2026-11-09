"""MTA subway hourly ridership -> station-complex x day panel (R2, secondary).

Two source tables are stitched at the year boundary:
- 2020-2024: data.ny.gov wujg-7c2s
- 2025 onward: data.ny.gov 5wq4-mkjj

Aggregation runs on the server one day at a time so each query stays small.
Timestamps are local wall-clock hours. Station complexes are flagged as CRZ
using the ``cbd`` field of the MTA Subway Stations table (39hk-dx4f); a complex
counts as CRZ if any of its stations is flagged.

The ridership tables also report the Roosevelt Island Tram (complex IDs
``TRAM1`` and ``TRAM2``, about 0.2% of entries). It is not a subway station and
has no row in the stations table, so it is dropped from the panel.
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
FIRST_DAY = date(2023, 1, 1)
LAST_DAY = date(2026, 10, 29)  # last day in the 2025+ table at audit time
NON_SUBWAY_COMPLEXES = ("TRAM1", "TRAM2")  # Roosevelt Island Tram


def table_for(day: date) -> str:
    """Which source table holds a given day."""
    return TABLE_BEFORE_2025 if day < date(2025, 1, 1) else TABLE_FROM_2025


def study_days(first: date, last: date) -> list[date]:
    """Every day from first to last inclusive."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def fetch_day(day: date) -> pl.DataFrame:
    """Entries by station complex for one day.

    One-day queries take about 1-2 seconds on the server. Week-long queries
    occasionally exceed the 300-second timeout on the 2025+ table, so we query a
    day at a time; a single day also can never straddle the 2024/2025 table seam.
    """
    next_day = day + timedelta(days=1)
    rows = query_all(
        DOMAIN,
        table_for(day),
        {
            "$select": "station_complex_id, sum(ridership) as entries",
            "$where": f"transit_timestamp >= '{day.isoformat()}T00:00:00' "
            f"and transit_timestamp < '{next_day.isoformat()}T00:00:00'",
            "$group": "station_complex_id",
            "$order": "station_complex_id",
        },
    )
    return pl.DataFrame(
        rows, schema={"station_complex_id": pl.Utf8, "entries": pl.Utf8}
    ).with_columns(pl.lit(day).alias("date"), pl.col("entries").cast(pl.Float64))


def crz_complexes(path: str = str(STATIONS_CSV)) -> pl.DataFrame:
    """Station complexes with a CRZ flag and borough."""
    stations = pl.read_csv(path, infer_schema_length=0)
    return stations.group_by(pl.col("Complex ID").alias("station_complex_id")).agg(
        (pl.col("CBD").str.to_lowercase() == "true").any().alias("is_crz"),
        pl.col("Borough").first().alias("borough"),
        pl.col("Stop Name").first().alias("station_name"),
    )


def main() -> None:
    """Fetch every day (resumable) and write data/processed/subway_station_day.parquet."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for day in study_days(FIRST_DAY, LAST_DAY):
        destination = OUT_DIR / f"{day.isoformat()}.parquet"
        if destination.exists():
            continue
        fetch_day(day).write_parquet(destination)
        if day.day == 1:
            LOG.info("subway %s done", day)
    panel = pl.read_parquet(sorted(OUT_DIR.glob("*.parquet")))
    panel = panel.filter(~pl.col("station_complex_id").is_in(NON_SUBWAY_COMPLEXES))
    panel = panel.join(crz_complexes(), on="station_complex_id", how="left").sort(
        "station_complex_id", "date"
    )
    panel.write_parquet(PROCESSED_DIR / "subway_station_day.parquet")
    LOG.info(
        "subway panel: %d rows, %d complexes", panel.height, panel["station_complex_id"].n_unique()
    )


if __name__ == "__main__":
    main()
