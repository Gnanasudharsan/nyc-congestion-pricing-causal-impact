"""MTA Bridges and Tunnels crossings: facility-day panel for T1 and S2.

Source: data.ny.gov ebfx-2m7v (hourly crossings, 2019 onward). We aggregate on
the server to facility x day x vehicle class and facility x day x hour, which
turns 14 million rows into a few hundred thousand.

The facility groups are fixed in docs/analysis-plan.md section 4.1.
Closure rule (section 10): a facility-day is flagged and dropped if crossings
are zero or below 20% of that facility's median for the same weekday.
"""

from __future__ import annotations

import logging

import polars as pl

from cordon.config import INTERIM_DIR, PROCESSED_DIR
from cordon.ingest.socrata import query_all

LOG = logging.getLogger(__name__)
DOMAIN = "data.ny.gov"
DATASET = "ebfx-2m7v"
START = "2023-01-01T00:00:00"

FACILITY_GROUPS = {
    "Hugh L. Carey Tunnel": "treated",
    "Queens Midtown Tunnel": "treated",
    "Robert F. Kennedy Bridge Manhattan": "spillover",
    "Robert F. Kennedy Bridge Bronx": "spillover",
    "Henry Hudson Bridge": "spillover",
    "Throgs Neck Bridge": "control",
    "Bronx - Whitestone Bridge": "control",
    "Verrazzano - Narrows Bridge": "control",
    "Cross Bay Bridge": "control",
    "Marine Parkway Bridge": "control",
}
CLOSURE_SHARE = 0.20


def fetch_by_class() -> pl.DataFrame:
    """Daily crossings by facility and vehicle class category."""
    rows = query_all(
        DOMAIN,
        DATASET,
        {
            "$select": "facility, date, vehicle_class_category, sum(traffic_count) as crossings",
            "$where": f"date >= '{START}'",
            "$group": "facility, date, vehicle_class_category",
            "$order": "facility, date, vehicle_class_category",
        },
    )
    return pl.DataFrame(rows).with_columns(
        pl.col("date").str.slice(0, 10).str.to_date(),
        pl.col("crossings").cast(pl.Float64).cast(pl.Int64),
    )


def fetch_by_hour() -> pl.DataFrame:
    """Daily crossings by facility and hour of day (for peak vs overnight)."""
    rows = query_all(
        DOMAIN,
        DATASET,
        {
            "$select": "facility, date, hour, sum(traffic_count) as crossings",
            "$where": f"date >= '{START}'",
            "$group": "facility, date, hour",
            "$order": "facility, date, hour",
        },
    )
    return pl.DataFrame(rows).with_columns(
        pl.col("date").str.slice(0, 10).str.to_date(),
        pl.col("hour").cast(pl.Float64).cast(pl.Int8),
        pl.col("crossings").cast(pl.Float64).cast(pl.Int64),
    )


def is_peak_hour(hour: pl.Expr, weekday: pl.Expr) -> pl.Expr:
    """CRZ peak hours: weekdays 5am-9pm, weekends 9am-9pm (local time)."""
    weekend = weekday >= 6
    return pl.when(weekend).then((hour >= 9) & (hour < 21)).otherwise((hour >= 5) & (hour < 21))


def flag_closures(panel: pl.DataFrame) -> pl.DataFrame:
    """Flag facility-days that look like closures or reporting outages."""
    with_median = panel.with_columns(
        pl.col("crossings")
        .median()
        .over(["facility", pl.col("date").dt.weekday()])
        .alias("weekday_median")
    )
    return with_median.with_columns(
        (
            (pl.col("crossings") == 0)
            | (pl.col("crossings") < CLOSURE_SHARE * pl.col("weekday_median"))
        ).alias("is_closure")
    ).drop("weekday_median")


def build_panel(by_class: pl.DataFrame, by_hour: pl.DataFrame) -> pl.DataFrame:
    """Combine class and hour aggregates into one facility-day panel."""
    unknown = set(by_class["facility"].unique()) - set(FACILITY_GROUPS)
    if unknown:
        raise ValueError(f"facilities missing from the pre-registered groups: {unknown}")

    classes = by_class.pivot(
        on="vehicle_class_category", index=["facility", "date"], values="crossings"
    ).fill_null(0)
    class_columns = [c for c in classes.columns if c not in ("facility", "date")]
    classes = classes.rename({c: f"crossings_{c.lower()}" for c in class_columns})

    hours = by_hour.with_columns(
        is_peak_hour(pl.col("hour"), pl.col("date").dt.weekday()).alias("is_peak")
    )
    peak = hours.group_by("facility", "date").agg(
        pl.col("crossings").filter(pl.col("is_peak")).sum().alias("crossings_peak"),
        pl.col("crossings").filter(~pl.col("is_peak")).sum().alias("crossings_offpeak"),
        pl.col("hour").n_unique().alias("hours_reported"),
    )
    totals = by_class.group_by("facility", "date").agg(pl.col("crossings").sum())
    panel = (
        totals.join(classes, on=["facility", "date"], how="left")
        .join(peak, on=["facility", "date"], how="left")
        .with_columns(pl.col("facility").replace_strict(FACILITY_GROUPS).alias("facility_group"))
        .sort("facility", "date")
    )
    return flag_closures(panel)


def main() -> None:
    """Fetch aggregates and write data/processed/bt_facility_day.parquet."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    by_class = fetch_by_class()
    by_hour = fetch_by_hour()
    by_class.write_parquet(INTERIM_DIR / "bt_by_class.parquet")
    by_hour.write_parquet(INTERIM_DIR / "bt_by_hour.parquet")
    panel = build_panel(by_class, by_hour)
    panel.write_parquet(PROCESSED_DIR / "bt_facility_day.parquet")
    LOG.info("bt panel: %d rows, %d closures flagged", panel.height, panel["is_closure"].sum())


if __name__ == "__main__":
    main()
