"""Estimation panels: one function per outcome, returning long rows.

Every builder returns columns ``period``, ``group`` ("treated"/"control"),
``unit``, ``value`` (and sometimes ``cluster``). The group definitions are the
pre-registered ones (analysis plan sections 2-5; ADR 0010). Phase 2 descriptive
figures use the same builders, so the figures and the estimates rest on the
same data.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from cordon.config import FINAL_DIR, PROCESSED_DIR


def daily_rows(frame: pl.DataFrame, value: str, unit: str, group: str) -> pl.DataFrame:
    """Standardise a daily unit panel to columns period, group, unit, value."""
    return frame.select(
        pl.col("date").alias("period"),
        pl.col(group).alias("group"),
        pl.col(unit).cast(pl.Utf8).alias("unit"),
        pl.col(value).alias("value"),
    )


def to_weekly(rows: pl.DataFrame) -> pl.DataFrame:
    """Aggregate daily unit rows to weeks (mean of daily values; weeks with >= 5 days)."""
    return (
        rows.with_columns(pl.col("period").dt.truncate("1w"))
        .group_by("period", "group", "unit")
        .agg(pl.col("value").mean(), pl.len().alias("days"))
        .filter(pl.col("days") >= 5)
        .drop("days")
    )


# --------------------------------------------------------------------------- builders


def bt_builder(control_group: str, treated_group: str) -> Callable[[], pl.DataFrame]:
    """B&T: log daily crossings per facility, weekly, excluding flagged closures."""

    def build() -> pl.DataFrame:
        panel = pl.read_parquet(PROCESSED_DIR / "bt_facility_day.parquet").filter(
            ~pl.col("is_closure") & pl.col("facility_group").is_in([control_group, treated_group])
        )
        panel = panel.with_columns(
            pl.col("crossings").log().alias("log_crossings"),
            pl.when(pl.col("facility_group") == treated_group)
            .then(pl.lit("treated"))
            .otherwise(pl.lit("control"))
            .alias("role"),
        )
        return daily_rows(panel, "log_crossings", "facility", "role")

    return build


def tlc_trips_builder(treated_group: str) -> Callable[[], pl.DataFrame]:
    """TLC: log(1 + daily trips) by pickup zone, using the plan's counting rules."""

    def build() -> pl.DataFrame:
        groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
            pl.col("location_id").alias("pu_location_id"), pl.col("group").alias("pu_group")
        )
        panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet").join(
            groups, on="pu_location_id", how="inner"
        )
        if treated_group == "crz":
            treated = panel.filter(pl.col("pu_group") == "crz")  # all trips from CRZ zones
        else:
            treated = panel.filter(
                (pl.col("pu_group") == treated_group) & (pl.col("do_group") != "crz")
            )
        control = panel.filter(
            (pl.col("pu_group") == "far_control") & (pl.col("do_group") != "crz")
        )
        daily = (
            pl.concat(
                [
                    treated.with_columns(pl.lit("treated").alias("role")),
                    control.with_columns(pl.lit("control").alias("role")),
                ]
            )
            .group_by("date", "pu_location_id", "role")
            .agg(pl.col("trips").sum())
        )
        daily = daily.with_columns((pl.col("trips") + 1).log().alias("log_trips"))
        return daily_rows(daily, "log_trips", "pu_location_id", "role")

    return build


def tlc_speed_builder(treated_group: str) -> Callable[[], pl.DataFrame]:
    """TLC: log distance-weighted speed of same-group trips, peak hours, by pickup zone."""

    def build() -> pl.DataFrame:
        groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
            pl.col("location_id").alias("pu_location_id"), pl.col("group").alias("pu_group")
        )
        panel = (
            pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet")
            .join(groups, on="pu_location_id", how="inner")
            .filter(pl.col("is_peak") & (pl.col("pu_group") == pl.col("do_group")))
            .filter(pl.col("pu_group").is_in([treated_group, "far_control"]))
        )
        daily = (
            panel.group_by("date", "pu_location_id", "pu_group")
            .agg(
                pl.col("speed_miles").sum(),
                pl.col("speed_seconds").sum(),
                pl.col("speed_trips").sum(),
            )
            .filter(pl.col("speed_trips") >= 20)  # avoid noisy zone-days
            .with_columns(
                (pl.col("speed_miles") / (pl.col("speed_seconds") / 3600)).log().alias("log_mph"),
                pl.when(pl.col("pu_group") == treated_group)
                .then(pl.lit("treated"))
                .otherwise(pl.lit("control"))
                .alias("role"),
            )
        )
        return daily_rows(daily, "log_mph", "pu_location_id", "role")

    return build


def ntd_builder(treated_role: str, donor_role: str) -> Callable[[], pl.DataFrame]:
    """NTD: log monthly unlinked passenger trips; donors averaged with equal weight."""

    def build() -> pl.DataFrame:
        panel = pl.read_parquet(PROCESSED_DIR / "ntd_unit_month.parquet").filter(
            pl.col("role").is_in([treated_role, donor_role]) & (pl.col("upt") > 0)
        )
        return panel.select(
            pl.col("month").alias("period"),
            pl.when(pl.col("role") == treated_role)
            .then(pl.lit("treated"))
            .otherwise(pl.lit("control"))
            .alias("group"),
            pl.col("unit"),
            pl.col("upt").log().alias("value"),
        )

    return build


def subway_builder() -> pl.DataFrame:
    """Subway: log daily entries per station complex, CRZ vs non-CRZ."""
    panel = pl.read_parquet(PROCESSED_DIR / "subway_station_day.parquet").filter(
        pl.col("entries") > 0
    )
    panel = panel.with_columns(
        pl.col("entries").log().alias("log_entries"),
        pl.when(pl.col("is_crz"))
        .then(pl.lit("treated"))
        .otherwise(pl.lit("control"))
        .alias("role"),
    )
    return daily_rows(panel, "log_entries", "station_complex_id", "role")


def bus_builder() -> pl.DataFrame:
    """CBD bus speeds: log monthly speed per route segment type (CBD vs non-CBD), peak."""
    panel = pl.read_parquet(PROCESSED_DIR / "bus_route_month.parquet").filter(
        (pl.col("time_period") == "Peak") & (pl.col("hours") > 0)
    )
    return panel.select(
        pl.col("month").alias("period"),
        pl.when(pl.col("cbd_relation") == "CBD")
        .then(pl.lit("treated"))
        .otherwise(pl.lit("control"))
        .alias("group"),
        (pl.col("route_id") + "_" + pl.col("cbd_relation")).alias("unit"),
        pl.col("speed_mph").log().alias("value"),
    )


def air_builder(
    pollutant: str,
    treated_roles: list[str],
    control_roles: list[str],
    control_source: str | None = None,
) -> Callable[[], pl.DataFrame]:
    """Air: daily-mean concentration per site on valid, non-smoke days (levels, not logs)."""

    def build() -> pl.DataFrame:
        smoke = pl.read_parquet(PROCESSED_DIR / "smoke_days.parquet").select("date", "is_smoke_day")
        panel = (
            pl.read_parquet(PROCESSED_DIR / "air_site_day.parquet")
            .filter((pl.col("pollutant") == pollutant) & pl.col("valid_day"))
            .join(smoke, on="date", how="left")
            .filter(~pl.col("is_smoke_day").fill_null(False))
        )
        treated = panel.filter(pl.col("role").is_in(treated_roles))
        control = panel.filter(pl.col("role").is_in(control_roles))
        if control_source:
            control = control.filter(pl.col("source") == control_source)
        both = pl.concat(
            [
                treated.with_columns(pl.lit("treated").alias("role_label")),
                control.with_columns(pl.lit("control").alias("role_label")),
            ],
            how="diagonal_relaxed",
        ).with_columns((pl.col("source") + ":" + pl.col("site_id")).alias("site_key"))
        return daily_rows(both, "daily_mean", "site_key", "role_label")

    return build
