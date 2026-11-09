"""Build shared daily covariates: calendar, weather, smoke days.

Run with ``python -m cordon.features.build``. Writes Parquet files to
``data/processed/``.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

import geopandas as gpd
import polars as pl

from cordon.config import PROCESSED_DIR
from cordon.features import calendar, smoke, weather
from cordon.features.geography import TAXI_ZONES_SHP

STUDY_START = date(2023, 1, 1)
LOG = logging.getLogger("cordon.features")


def manhattan_area() -> gpd.GeoSeries:
    """Manhattan land area (union of its taxi zones), in longitude/latitude."""
    zones = gpd.read_file(TAXI_ZONES_SHP)
    manhattan = zones[zones["borough"] == "Manhattan"].to_crs("EPSG:4326")
    return gpd.GeoSeries([manhattan.union_all()], crs="EPSG:4326")


def main() -> None:
    """Write calendar.parquet, weather_daily.parquet and smoke_days.parquet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    hourly = weather.read_hourly()
    end = hourly["time"].max().date()  # type: ignore[union-attr]
    calendar.build_calendar(STUDY_START, end).write_parquet(PROCESSED_DIR / "calendar.parquet")
    daily = weather.daily_weather(hourly.filter(pl.col("time").dt.date() >= STUDY_START))
    daily.write_parquet(PROCESSED_DIR / "weather_daily.parquet")
    LOG.info("calendar and weather written through %s", end)

    if not args.skip_smoke:
        area = manhattan_area().iloc[0]
        smoke.build_smoke_days(STUDY_START, end, area).write_parquet(
            PROCESSED_DIR / "smoke_days.parquet"
        )
        LOG.info("smoke days written")


if __name__ == "__main__":
    main()
