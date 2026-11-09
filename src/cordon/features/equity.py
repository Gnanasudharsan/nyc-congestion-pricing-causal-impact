"""Equity covariates for every taxi zone (analysis plan section 9; deviations 12-14).

Census tracts and NTAs do not line up with taxi zones, so values are allocated
by area (areal interpolation). All areas are computed in NY State Plane
(EPSG:2263).

ACS 2019-2023 tract values are allocated by the share of each tract's overlap
with taxi zones that falls in the zone. Shares are normalised within each tract,
so tract totals are preserved:
- **population**: the sum of allocated population;
- **no-vehicle share**: allocated households without a vehicle divided by
  allocated households;
- **poverty rate**: allocated population below poverty divided by the allocated
  poverty universe;
- **median household income**: the population-weighted mean of tract medians.
  This is an approximation: medians cannot be aggregated exactly (deviation 14).

Asthma: the adult ED-visit rate (age-adjusted, per 10,000, 2017-2019) is the
mean of NTA rates weighted by each NTA's overlap area with the zone.

Output: ``data/final/zone_equity.csv`` (small, committed). Cross-sectional
covariates only; they are never outcomes.
Run: ``python -m cordon.features.equity``.
"""

from __future__ import annotations

import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import polars as pl

from cordon.config import FINAL_DIR
from cordon.features.geography import TAXI_ZONES_SHP
from cordon.ingest.equity import ASTHMA_MEASURE, ASTHMA_PERIOD, EQUITY_DIR

LOG = logging.getLogger(__name__)
OUTPUT = FINAL_DIR / "zone_equity.csv"
NYC_COUNTIES = ("005", "047", "061", "081", "085")
STATE_PLANE = "EPSG:2263"
ACS_COLUMNS = {
    "b01003": {"B01003_E001": "population"},
    "b19013": {"B19013_E001": "median_income"},
    "b08201": {"B08201_E001": "households", "B08201_E002": "households_no_vehicle"},
    "b17001": {"B17001_E001": "poverty_universe", "B17001_E002": "below_poverty"},
}


def acs_tracts() -> pd.DataFrame:
    """ACS values for NYC census tracts, keyed by 11-digit GEOID."""
    merged: pd.DataFrame | None = None
    prefixes = tuple(f"1400000US36{county}" for county in NYC_COUNTIES)
    for table, columns in ACS_COLUMNS.items():
        frame = (
            pl.scan_csv(EQUITY_DIR / f"acsdt5y2023-{table}.dat", separator="|", infer_schema=False)
            .filter(
                pl.col("GEO_ID").str.starts_with(prefixes[0])
                | pl.col("GEO_ID").str.starts_with(prefixes[1])
                | pl.col("GEO_ID").str.starts_with(prefixes[2])
                | pl.col("GEO_ID").str.starts_with(prefixes[3])
                | pl.col("GEO_ID").str.starts_with(prefixes[4])
            )
            .select(
                pl.col("GEO_ID").str.slice(9).alias("GEOID"),
                *[
                    pl.col(src).cast(pl.Float64, strict=False).alias(dst)
                    for src, dst in columns.items()
                ],
            )
            .collect()
            .to_pandas()
        )
        merged = frame if merged is None else merged.merge(frame, on="GEOID", how="outer")
    if merged is None:
        raise RuntimeError("no ACS tables configured")
    # Census annotation codes (e.g. -666666666) mark suppressed values.
    numeric = merged.columns.drop("GEOID")
    merged[numeric] = merged[numeric].where(merged[numeric] >= 0)
    return merged


def tract_shapes() -> gpd.GeoDataFrame:
    """NYC census tract polygons with ACS values attached."""
    tracts = gpd.read_file(f"zip://{EQUITY_DIR / 'tl_2023_36_tract.zip'}")
    tracts = tracts[tracts["COUNTYFP"].isin(NYC_COUNTIES)].to_crs(STATE_PLANE)
    tracts = tracts.merge(acs_tracts(), on="GEOID", how="left")
    tracts["tract_area"] = tracts.geometry.area
    return tracts


def zones() -> gpd.GeoDataFrame:
    """Taxi-zone polygons in State Plane."""
    shapes = gpd.read_file(TAXI_ZONES_SHP).to_crs(STATE_PLANE)
    return shapes[["LocationID", "geometry"]].rename(columns={"LocationID": "location_id"})


def allocate_acs(zone_shapes: gpd.GeoDataFrame) -> pd.DataFrame:
    """Area-weighted allocation of tract counts to zones."""
    tracts = tract_shapes()
    pieces = gpd.overlay(tracts, zone_shapes, how="intersection", keep_geom_type=True)
    # Shares sum to 1 within each tract, so tract totals are preserved even where a
    # tract polygon extends over water that no taxi zone covers.
    overlap = pieces.geometry.area
    share = overlap / overlap.groupby(pieces["GEOID"]).transform("sum")
    for column in (
        "population",
        "households",
        "households_no_vehicle",
        "poverty_universe",
        "below_poverty",
    ):
        pieces[column] = pieces[column] * share
    pieces["income_weight"] = np.where(pieces["median_income"].notna(), pieces["population"], 0)
    pieces["income_x_weight"] = pieces["median_income"].fillna(0) * pieces["income_weight"]
    totals = pieces.groupby("location_id")[
        [
            "population",
            "households",
            "households_no_vehicle",
            "poverty_universe",
            "below_poverty",
            "income_weight",
            "income_x_weight",
        ]
    ].sum()
    out = pd.DataFrame(index=totals.index)
    out["population"] = totals["population"]
    out["median_income_popweighted"] = totals["income_x_weight"] / totals["income_weight"]
    out["share_no_vehicle"] = totals["households_no_vehicle"] / totals["households"]
    out["poverty_rate"] = totals["below_poverty"] / totals["poverty_universe"]
    return out.replace([np.inf, -np.inf], np.nan).reset_index()


def asthma_rates() -> gpd.GeoDataFrame:
    """NTA 2010 polygons with the adult asthma ED-visit rate (2017-2019)."""
    raw = json.loads((EQUITY_DIR / "ehdp_indicator_2384.json").read_text())
    table = pd.DataFrame(raw)
    table = table[
        (table["MeasureID"] == ASTHMA_MEASURE)
        & (table["TimePeriodID"] == ASTHMA_PERIOD)
        & (table["GeoType"] == "NTA2010")
    ][["GeoID", "Value"]].rename(columns={"Value": "asthma_ed_rate"})
    shapes = gpd.read_file(EQUITY_DIR / "NTA2010.topo.json")
    if shapes.crs is None:
        shapes = shapes.set_crs("EPSG:4326")  # TopoJSON coordinates are longitude/latitude
    shapes["GeoID"] = pd.to_numeric(shapes["GEOCODE"])
    return shapes.merge(table, on="GeoID", how="inner").to_crs(STATE_PLANE)


def allocate_asthma(zone_shapes: gpd.GeoDataFrame) -> pd.DataFrame:
    """Overlap-area-weighted mean NTA asthma rate per zone."""
    pieces = gpd.overlay(asthma_rates(), zone_shapes, how="intersection", keep_geom_type=True)
    pieces["overlap"] = pieces.geometry.area
    pieces["weighted"] = pieces["asthma_ed_rate"] * pieces["overlap"]
    totals = pieces.groupby("location_id")[["weighted", "overlap"]].sum()
    rate = (totals["weighted"] / totals["overlap"]).rename("asthma_ed_rate_adults")
    return pd.DataFrame(rate).reset_index()


def main() -> None:
    """Write data/final/zone_equity.csv."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    zone_shapes = zones()
    table = allocate_acs(zone_shapes).merge(
        allocate_asthma(zone_shapes), on="location_id", how="outer"
    )
    table = table.sort_values("location_id")
    pl.from_pandas(table).write_csv(OUTPUT)
    LOG.info(
        "zone equity covariates: %d zones; total population %.0f",
        len(table),
        table["population"].sum(),
    )


if __name__ == "__main__":
    main()
