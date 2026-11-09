"""National Transit Database monthly ridership -> agency-mode x month panel (R1, R4).

Source: datahub.transportation.gov 8bui-9xvu ("Complete Monthly Ridership, with
adjustments and estimates"). Ridership is unlinked passenger trips (UPT),
summed over types of service (directly operated, purchased transportation).

Donor rules (docs/analysis-plan.md section 5.1):
- R1 (subway): heavy rail (HR) or light rail (LR) units with >= 1 million
  average monthly UPT in 2019, outside the New York--Newark urbanized area.
- R4 (bus): motor bus (MB) units with the same size and location rules.
The treated units are MTA New York City Transit (NTD ID 20008) HR and MB.
"""

from __future__ import annotations

import polars as pl

from cordon.config import PROCESSED_DIR, RAW_DIR

NTD_CSV = RAW_DIR / "socrata" / "ntd_monthly_ridership.csv"
TREATED_NTD_ID = "20008"
NY_UZA_PREFIX = "New York--Jersey City--Newark"
MIN_2019_MONTHLY_UPT = 1_000_000
RAIL_MODES = {"HR", "LR"}
BUS_MODES = {"MB"}


def read_raw(path: str = str(NTD_CSV)) -> pl.DataFrame:
    """Read the NTD export with explicit types."""
    frame = pl.read_csv(path, infer_schema_length=0)
    return frame.select(
        pl.col("NTD ID").alias("ntd_id"),
        pl.col("Agency").alias("agency"),
        pl.col("UZA Name").alias("uza_name"),
        pl.col("Mode").alias("mode"),
        pl.col("TOS").alias("type_of_service"),
        pl.col("Date").str.to_date("%B %Y").alias("month"),
        pl.col("UPT").str.replace_all(",", "").cast(pl.Float64).alias("upt"),
    )


def build_panel(raw: pl.DataFrame) -> pl.DataFrame:
    """Sum over types of service and label treated units and eligible donors."""
    panel = (
        raw.group_by("ntd_id", "agency", "uza_name", "mode", "month")
        .agg(pl.col("upt").sum())
        .with_columns((pl.col("ntd_id") + "_" + pl.col("mode")).alias("unit"))
    )
    size_2019 = (
        panel.filter(pl.col("month").dt.year() == 2019)
        .group_by("unit")
        .agg(pl.col("upt").mean().alias("mean_monthly_upt_2019"))
    )
    panel = panel.join(size_2019, on="unit", how="left").with_columns(
        pl.col("uza_name").fill_null("").str.starts_with(NY_UZA_PREFIX).alias("in_ny_uza"),
        (pl.col("mean_monthly_upt_2019").fill_null(0) >= MIN_2019_MONTHLY_UPT).alias("large_2019"),
    )
    is_treated = pl.col("ntd_id") == TREATED_NTD_ID
    eligible = ~pl.col("in_ny_uza") & pl.col("large_2019") & ~is_treated
    return panel.with_columns(
        pl.when(is_treated & (pl.col("mode") == "HR"))
        .then(pl.lit("treated_r1"))
        .when(is_treated & (pl.col("mode") == "MB"))
        .then(pl.lit("treated_r4"))
        .when(eligible & pl.col("mode").is_in(list(RAIL_MODES)))
        .then(pl.lit("donor_r1"))
        .when(eligible & pl.col("mode").is_in(list(BUS_MODES)))
        .then(pl.lit("donor_r4"))
        .otherwise(pl.lit("not_used"))
        .alias("role")
    ).sort("unit", "month")


def main() -> None:
    """Write data/processed/ntd_unit_month.parquet (2019 onward)."""
    panel = build_panel(read_raw()).filter(pl.col("month") >= pl.date(2019, 1, 1))
    panel.write_parquet(PROCESSED_DIR / "ntd_unit_month.parquet")
    roles = (
        panel.filter(pl.col("role") != "not_used")
        .group_by("role")
        .agg(pl.col("unit").n_unique().alias("units"))
    )
    print(roles.sort("role"))


if __name__ == "__main__":
    main()
