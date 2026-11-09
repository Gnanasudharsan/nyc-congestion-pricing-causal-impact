"""Citi Bike file listing and Open-Meteo hourly weather downloads."""

from __future__ import annotations

import re
from pathlib import Path

import requests

KEY_PATTERN = re.compile(r"<Key>([^<]+)</Key>")
PERIOD_PATTERN = re.compile(r"(\d{6}|\d{4})-citibike")


def list_citibike_files(bucket_url: str) -> list[str]:
    """List NYC (not Jersey City) trip-data archives in the public S3 bucket."""
    response = requests.get(bucket_url, timeout=60)
    response.raise_for_status()
    keys = KEY_PATTERN.findall(response.text)
    return sorted(k for k in keys if k.endswith(".zip") and not k.startswith("JC-"))


def citibike_coverage(keys: list[str]) -> tuple[str, str]:
    """Return the first and last period (YYYY or YYYYMM) present in the file names."""
    periods: list[str] = []
    for key in keys:
        match = PERIOD_PATTERN.match(key)
        if match is not None:
            periods.append(match.group(1))
    if not periods:
        raise ValueError("no dated Citi Bike files found")
    periods.sort()
    return periods[0], periods[-1]


HOURLY_WEATHER_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "snowfall",
    "wind_speed_10m",
    "wind_direction_10m",
    "relative_humidity_2m",
    "boundary_layer_height",
]


def download_open_meteo(
    archive_url: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    destination: Path,
) -> Path:
    """Download hourly reanalysis weather as CSV with UTC timestamps.

    Open-Meteo's ``timezone=America/New_York`` option returns a fixed UTC-5 offset
    with no daylight saving time, so we request GMT and convert in our own code.
    """
    params = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY_WEATHER_VARIABLES),
        "timezone": "GMT",
        "format": "csv",
    }
    response = requests.get(archive_url, params=params, timeout=300)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination
