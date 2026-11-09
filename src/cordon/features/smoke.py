"""Smoke-day flags from NOAA Hazard Mapping System (HMS) smoke polygons.

HMS analysts draw daily smoke plumes from satellite imagery and tag each
polygon Light, Medium, or Heavy density. The analysis plan (section 5.2)
excludes days on which a Medium or Heavy polygon covers Manhattan.
"""

from __future__ import annotations

import logging
import zipfile
from datetime import date, timedelta
from pathlib import Path

import geopandas as gpd
import polars as pl
import requests
from shapely.geometry.base import BaseGeometry

from cordon.config import RAW_DIR

LOG = logging.getLogger(__name__)
HMS_BASE = "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Smoke_Polygons/Shapefile"
HMS_DIR = RAW_DIR / "hms"
DENSE_LEVELS = {"Medium", "Heavy"}


def hms_url(day: date) -> str:
    """URL of one day's HMS smoke shapefile archive."""
    return f"{HMS_BASE}/{day:%Y}/{day:%m}/hms_smoke{day:%Y%m%d}.zip"


def download_day(day: date, directory: Path = HMS_DIR) -> Path | None:
    """Download one day's archive; return None if NOAA has no file for that day."""
    destination = directory / f"hms_smoke{day:%Y%m%d}.zip"
    if destination.exists():
        return destination
    response = requests.get(hms_url(day), timeout=60)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    directory.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def densest_smoke_over(archive: Path, area: BaseGeometry) -> str:
    """Return the densest smoke level whose polygon intersects ``area`` ('None' if none)."""
    with zipfile.ZipFile(archive) as bundle:
        if not any(name.endswith(".shp") for name in bundle.namelist()):
            return "None"
    polygons = gpd.read_file(f"zip://{archive}")
    if polygons.empty:
        return "None"
    polygons = polygons.to_crs("EPSG:4326")
    hits = polygons[polygons.intersects(area)]
    levels = set(hits["Density"].astype(str)) if "Density" in hits else set()
    for level in ("Heavy", "Medium", "Light"):
        if level in levels:
            return level
    return "None"


def build_smoke_days(start: date, end: date, area: BaseGeometry) -> pl.DataFrame:
    """One row per day: densest smoke over ``area`` and the pre-registered exclusion flag."""
    rows: list[dict[str, object]] = []
    day = start
    while day <= end:
        archive = download_day(day)
        level = "missing" if archive is None else densest_smoke_over(archive, area)
        rows.append({"date": day, "smoke_level": level, "is_smoke_day": level in DENSE_LEVELS})
        day += timedelta(days=1)
    return pl.DataFrame(rows)
