"""Assign TLC taxi zones to treated, spillover, and control groups (ADR 0010).

Rules (docs/analysis-plan.md section 2), applied in this order:

1. ``crz``: zone appears in MTA's CBD taxi-zone list (data.ny.gov yfdc-w5jh).
2. ``excluded``: airports (1 Newark, 132 JFK, 138 LaGuardia).
3. ``border_ring``: zone centroid within 3 km of the CRZ geofence polygon.
4. ``upper_manhattan_bronx``: any remaining Manhattan or Bronx zone.
5. ``intermediate``: centroid 3-8 km from the geofence (never used as a control).
6. ``far_control``: centroid more than 8 km from the geofence.

The output uses geometry only, so it is fixed before any outcome is joined.
Distances are computed in the NY State Plane (EPSG:2263, US feet) projection.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from cordon.config import FINAL_DIR, RAW_DIR

STATE_PLANE = "EPSG:2263"
FEET_PER_KM = 3280.84
RING_KM = 3.0
FAR_KM = 8.0
AIRPORT_ZONES = frozenset({1, 132, 138})

TAXI_ZONES_SHP = RAW_DIR / "geo" / "taxi_zones" / "taxi_zones" / "taxi_zones.shp"
CBD_ZONES_CSV = RAW_DIR / "socrata" / "cbd_taxi_zones.csv"
GEOFENCE_CSV = RAW_DIR / "socrata" / "cbd_geofence.csv"
ZONE_GROUPS_CSV = FINAL_DIR / "zone_groups.csv"


def load_geofence(path: Path = GEOFENCE_CSV) -> BaseGeometry:
    """Union of the MTA CBD geofence polygons, projected to state plane."""
    polygons = [wkt.loads(text) for text in pd.read_csv(path)["polygon"]]
    geofence = gpd.GeoSeries([unary_union(polygons)], crs="EPSG:4326").to_crs(STATE_PLANE)
    shape: BaseGeometry = geofence.iloc[0]
    return shape


def load_crz_zone_ids(path: Path = CBD_ZONES_CSV) -> set[int]:
    """Taxi zone IDs that MTA lists as inside the CBD."""
    return {int(z) for z in pd.read_csv(path)["Taxi Zone"]}


def classify_zone(location_id: int, borough: str, distance_km: float, crz_ids: set[int]) -> str:
    """Apply the pre-registered rules to one zone (see module docstring)."""
    if location_id in crz_ids:
        return "crz"
    if location_id in AIRPORT_ZONES:
        return "excluded"
    if distance_km <= RING_KM:
        return "border_ring"
    if borough in {"Manhattan", "Bronx"}:
        return "upper_manhattan_bronx"
    if distance_km <= FAR_KM:
        return "intermediate"
    return "far_control"


def build_zone_groups(
    zones_path: Path = TAXI_ZONES_SHP,
    cbd_path: Path = CBD_ZONES_CSV,
    geofence_path: Path = GEOFENCE_CSV,
) -> pd.DataFrame:
    """Return one row per taxi zone with its distance to the CRZ and its group."""
    zones = gpd.read_file(zones_path).to_crs(STATE_PLANE)
    # Some zones (e.g. 56, 103) appear as several polygons; dissolve to one row each.
    zones = zones.dissolve(by="LocationID", aggfunc="first").reset_index()
    geofence = load_geofence(geofence_path)
    crz_ids = load_crz_zone_ids(cbd_path)

    centroids = zones.geometry.centroid
    zones["distance_km"] = centroids.distance(geofence) / FEET_PER_KM
    zones["group"] = [
        classify_zone(int(lid), str(boro), float(dist), crz_ids)
        for lid, boro, dist in zip(
            zones["LocationID"], zones["borough"], zones["distance_km"], strict=True
        )
    ]
    table = pd.DataFrame(
        {
            "location_id": zones["LocationID"].astype(int),
            "zone": zones["zone"],
            "borough": zones["borough"],
            "distance_km": zones["distance_km"].round(3),
            "group": zones["group"],
        }
    )
    return table.sort_values("location_id").reset_index(drop=True)


def main() -> None:
    """Write data/final/zone_groups.csv."""
    table = build_zone_groups()
    ZONE_GROUPS_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(ZONE_GROUPS_CSV, index=False)
    print(table["group"].value_counts().to_string())


if __name__ == "__main__":
    main()
