"""Daily weather covariates from Open-Meteo hourly reanalysis.

The archive request snaps to the nearest reanalysis grid cell (about 25 km);
for the Central Park request this is the cell centred near 40.81 N, 74.02 W,
which covers Manhattan. Timestamps are requested in UTC and converted here to
America/New_York, so local days have 23 or 25 hours on DST transition dates.
"""

from __future__ import annotations

import math
from pathlib import Path

import polars as pl

from cordon.config import RAW_DIR

WEATHER_CSV = RAW_DIR / "weather" / "open_meteo_central_park_hourly.csv"
HEADER_LINES = 3  # location metadata block before the hourly table

COLUMN_NAMES = {
    "time": "time",
    "temperature_2m (°C)": "temp_c",
    "precipitation (mm)": "precip_mm",
    "snowfall (cm)": "snow_cm",
    "wind_speed_10m (km/h)": "wind_kmh",
    "wind_direction_10m (°)": "wind_dir_deg",
    "relative_humidity_2m (%)": "rh_pct",
    "boundary_layer_height (m)": "pbl_m",
}

SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def wind_sector(u_mean: float, v_mean: float) -> str:
    """Map a mean wind vector to one of 8 compass sectors (direction wind comes FROM)."""
    # Meteorological convention: direction is where wind blows from, clockwise from north.
    direction = (math.degrees(math.atan2(-u_mean, -v_mean)) + 360) % 360
    return SECTORS[int(((direction + 22.5) % 360) // 45)]


def read_hourly(path: Path = WEATHER_CSV) -> pl.DataFrame:
    """Read the hourly CSV and rename columns to short names."""
    frame = pl.read_csv(path, skip_rows=HEADER_LINES).rename(COLUMN_NAMES)
    utc = pl.col("time").str.to_datetime("%Y-%m-%dT%H:%M", time_zone="UTC")
    local = utc.dt.convert_time_zone("America/New_York").dt.replace_time_zone(None)
    return frame.with_columns(local.alias("time"))


def daily_weather(hourly: pl.DataFrame) -> pl.DataFrame:
    """Aggregate hourly weather to local calendar days."""
    radians = pl.col("wind_dir_deg").radians()
    with_vectors = hourly.with_columns(
        # u, v components of the wind (blowing TOWARD), used for a proper vector mean.
        (-pl.col("wind_kmh") * radians.sin()).alias("u"),
        (-pl.col("wind_kmh") * radians.cos()).alias("v"),
    )
    daily = (
        with_vectors.group_by(pl.col("time").dt.date().alias("date"))
        .agg(
            pl.len().alias("weather_hours"),
            pl.col("temp_c").mean().alias("temp_mean_c"),
            pl.col("temp_c").min().alias("temp_min_c"),
            pl.col("temp_c").max().alias("temp_max_c"),
            pl.col("precip_mm").sum().alias("precip_mm"),
            pl.col("snow_cm").sum().alias("snow_cm"),
            pl.col("wind_kmh").mean().alias("wind_mean_kmh"),
            pl.col("rh_pct").mean().alias("rh_mean_pct"),
            pl.col("pbl_m").mean().alias("pbl_mean_m"),
            pl.col("u").mean().alias("u_mean"),
            pl.col("v").mean().alias("v_mean"),
        )
        .sort("date")
    )
    sectors = [wind_sector(u, v) for u, v in zip(daily["u_mean"], daily["v_mean"], strict=True)]
    return daily.with_columns(pl.Series("wind_sector", sectors)).drop("u_mean", "v_mean")
