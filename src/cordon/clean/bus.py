"""MTA CBD bus speeds -> route x month panel (R3, secondary).

Source: data.ny.gov r6db-kkzj (Beginning 2023), one row per month x day type x
hour x route x CBD relation, with summed mileage and hours. We recompute speed
as total miles / total hours so that averaging respects how much service ran,
rather than averaging the published hourly average speeds.

The ``cbd_relation`` field marks the portion of each route's service inside the
CBD ("CBD") versus outside it ("Non-CBD"); a route can contribute to both.
"""

from __future__ import annotations

import polars as pl

from cordon.config import PROCESSED_DIR, RAW_DIR

BUS_CSV = RAW_DIR / "socrata" / "cbd_bus_speeds.csv"


def build_panel(path: str = str(BUS_CSV)) -> pl.DataFrame:
    """Route x month x CBD relation x time period, with service-weighted speed."""
    raw = pl.read_csv(path, infer_schema_length=0).select(
        pl.col("Month").str.to_date("%m/%d/%Y").alias("month"),
        pl.col("Day Type").alias("day_type"),
        pl.col("TIme Period").alias("time_period"),
        pl.col("Route Type").alias("route_type"),
        pl.col("Route ID").alias("route_id"),
        pl.col("CBD Relation").alias("cbd_relation"),
        pl.col("Sum Mileage").cast(pl.Float64).alias("miles"),
        pl.col("Sum Time").cast(pl.Float64).alias("hours"),
    )
    panel = (
        raw.group_by("route_id", "route_type", "cbd_relation", "time_period", "month")
        .agg(pl.col("miles").sum(), pl.col("hours").sum())
        .with_columns((pl.col("miles") / pl.col("hours")).alias("speed_mph"))
    )
    return panel.sort("route_id", "cbd_relation", "time_period", "month")


def main() -> None:
    """Write data/processed/bus_route_month.parquet."""
    panel = build_panel()
    panel.write_parquet(PROCESSED_DIR / "bus_route_month.parquet")
    print(panel.group_by("cbd_relation").agg(pl.col("route_id").n_unique(), pl.len()))


if __name__ == "__main__":
    main()
