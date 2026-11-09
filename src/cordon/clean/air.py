"""Air-quality site-day panels for A1-A4 and S5 (docs/analysis-plan.md section 5).

Two sources:

- NYCCAS real-time PM2.5 (hourly, UTC hour-beginning) for NYC street sites.
- EPA AQS hourly PM2.5 (88101) and NO2 (42602) for NYC regulatory monitors and
  for out-of-region donor monitors.

Daily values use local (America/New_York) calendar days. A day is valid with at
least 18 valid hours; hourly values outside [-5, 500] are dropped. For AQS sites
with several instruments (POCs), hourly values are averaged across instruments
before daily aggregation.
"""

from __future__ import annotations

import logging
import math

import duckdb
import polars as pl

from cordon.config import INTERIM_DIR, PROCESSED_DIR, RAW_DIR

LOG = logging.getLogger(__name__)
NYCCAS_DIR = RAW_DIR / "nyccas"
EPA_CSV_DIR = INTERIM_DIR / "epa"
MIN_HOURS_PER_DAY = 18
VALID_RANGE = (-5.0, 500.0)

# Site roles fixed in the analysis plan (sections 3.2, 3.3, 5.2).
NYCCAS_ROLES = {
    "Broadway/35th St": "crz_core",
    "Manhattan Bridge": "crz_core",
    "Williamsburg Bridge": "crz_other",
    "FDR": "crz_other",
    "Midtown-DOT": "crz_other",
    "Queensboro Bridge": "boundary",
    "Cross Bronx Expy": "spillover_core",
    "Queens College": "far_core",
}
NYC_AQS_ROLES = {
    # (site, pollutant): role
    ("36-081-0124", "pm25"): "far_core",  # Queens College 2 (A3 comparison)
    ("36-081-0124", "no2"): "far_core",  # Queens College 2 (A2 design b comparison)
    ("36-081-0125", "pm25"): "far_check",  # Queens College Near Road (Phase 5 only)
    ("36-081-0125", "no2"): "far_core",  # Queens College Near Road (A2 design b comparison)
    ("36-005-0110", "no2"): "spillover_no2",  # IS 52, South Bronx (A2 treated unit)
    ("36-005-0133", "no2"): "spillover_no2_secondary",  # Pfizer Lab, Bronx (A2 design b)
}
NYC_COUNTIES = {"005", "047", "061", "081", "085"}

# Donor rules (section 5.2): these states, > 80 km from Columbus Circle, outside the
# New York metro counties below, and >= 90% valid days in the pre-period.
DONOR_STATES = {"10", "24", "11", "51", "42", "34", "09", "44", "25"}
COLUMBUS_CIRCLE = (40.7681, -73.9819)
MIN_DONOR_KM = 80.0
MIN_DONOR_COMPLETENESS = 0.90
PRE_START, PRE_END = "2023-01-01", "2024-11-13"
# New York-Newark-Jersey City CBSA (35620) counties, plus Orange and Dutchess NY, which
# moved between metro definitions; excluding them is the conservative choice.
NY_METRO_COUNTIES = (
    {
        ("36", c)
        for c in (
            "005",
            "047",
            "061",
            "081",
            "085",
            "059",
            "103",
            "119",
            "079",
            "087",
            "071",
            "027",
        )
    }
    | {
        ("34", c)
        for c in (
            "003",
            "013",
            "017",
            "019",
            "023",
            "025",
            "027",
            "029",
            "031",
            "035",
            "037",
            "039",
        )
    }
    | {("42", "103")}
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def nyccas_site_day() -> pl.DataFrame:
    """NYCCAS hourly readings -> site x local day."""
    low, high = VALID_RANGE
    connection = duckdb.connect()
    sites = connection.execute(
        f"SELECT SiteID, any_value(Location), any_value(Latitude), any_value(Longitude) "
        f"FROM read_csv_auto('{NYCCAS_DIR / 'location.csv'}') GROUP BY 1"
    ).fetchall()
    daily: pl.DataFrame = connection.sql(
        f"""
        WITH hours AS (
            SELECT SiteID AS site_id,
                   timezone('America/New_York', ObservationTimeUTC::TIMESTAMP AT TIME ZONE 'UTC')
                       AS local_time,
                   Value AS value
            FROM read_csv_auto('{NYCCAS_DIR / "*" / "*.csv"}', union_by_name = true)
            WHERE Value BETWEEN {low} AND {high}
        )
        SELECT site_id, local_time::DATE AS date, count(*) AS n_hours,
               avg(value) AS daily_mean, max(value) AS daily_max
        FROM hours GROUP BY 1, 2
        """
    ).pl()
    meta = pl.DataFrame(
        [
            {"site_id": s[0], "site_name": s[1], "latitude": float(s[2]), "longitude": float(s[3])}
            for s in sites
        ]
    )
    return daily.join(meta, on="site_id", how="left").with_columns(
        pl.lit("nyccas").alias("source"),
        pl.lit("pm25").alias("pollutant"),
        pl.col("site_name").replace_strict(NYCCAS_ROLES, default="exploratory").alias("role"),
    )


def aqs_site_day(parameter: str, pollutant: str) -> pl.DataFrame:
    """AQS hourly CSVs -> site x local day, for NYC and candidate donor states."""
    low, high = VALID_RANGE
    states = ", ".join(f"'{s}'" for s in sorted(DONOR_STATES | {"36"}))
    files = str(EPA_CSV_DIR / f"hourly_{parameter}_*.csv")
    connection = duckdb.connect()
    result: pl.DataFrame = connection.sql(
        f"""
        WITH hours AS (
            SELECT "State Code" AS state, "County Code" AS county,
                   "State Code" || '-' || "County Code" || '-' || "Site Num" AS site_id,
                   CAST("Latitude" AS DOUBLE) AS latitude, CAST("Longitude" AS DOUBLE) AS longitude,
                   CAST("Date Local" AS DATE) AS date, "Time Local" AS hour,
                   avg(CAST("Sample Measurement" AS DOUBLE)) AS value
            FROM read_csv_auto('{files}', all_varchar = true, union_by_name = true)
            WHERE "State Code" IN ({states})
              AND CAST("Sample Measurement" AS DOUBLE) BETWEEN {low} AND {high}
            GROUP BY ALL
        )
        SELECT site_id, any_value(state) AS state, any_value(county) AS county,
               any_value(latitude) AS latitude, any_value(longitude) AS longitude,
               date, count(*) AS n_hours, avg(value) AS daily_mean, max(value) AS daily_max,
               'aqs' AS source, '{pollutant}' AS pollutant
        FROM hours GROUP BY site_id, date
        """
    ).pl()
    return result


def label_aqs_roles(daily: pl.DataFrame) -> pl.DataFrame:
    """Apply the pre-registered donor rules and NYC site roles to AQS sites."""
    valid = daily.with_columns((pl.col("n_hours") >= MIN_HOURS_PER_DAY).alias("valid_day"))
    pre = valid.filter(
        pl.col("date").is_between(pl.lit(PRE_START).str.to_date(), pl.lit(PRE_END).str.to_date())
    )
    pre_days = (pl.lit(PRE_END).str.to_date() - pl.lit(PRE_START).str.to_date()).dt.total_days() + 1
    completeness = pre.group_by("site_id").agg(
        (pl.col("valid_day").sum() / pre_days).alias("pre_completeness")
    )
    sites = valid.group_by("site_id").agg(
        pl.col("state").first(),
        pl.col("county").first(),
        pl.col("latitude").first(),
        pl.col("longitude").first(),
    )
    sites = sites.join(completeness, on="site_id", how="left").with_columns(
        pl.col("pre_completeness").fill_null(0.0)
    )
    distances = [
        haversine_km(lat, lon, *COLUMBUS_CIRCLE)
        for lat, lon in zip(sites["latitude"], sites["longitude"], strict=True)
    ]
    in_metro = [
        (state, county) in NY_METRO_COUNTIES
        for state, county in zip(sites["state"], sites["county"], strict=True)
    ]
    sites = sites.with_columns(
        pl.Series("km_from_columbus_circle", distances),
        pl.Series("in_ny_metro", in_metro),
    )
    is_donor = (
        pl.col("state").is_in(list(DONOR_STATES))
        & (pl.col("km_from_columbus_circle") > MIN_DONOR_KM)
        & ~pl.col("in_ny_metro")
        & (pl.col("pre_completeness") >= MIN_DONOR_COMPLETENESS)
    )
    pollutant = str(daily["pollutant"][0])
    nyc_roles = {site: role for (site, pol), role in NYC_AQS_ROLES.items() if pol == pollutant}
    is_nyc = (pl.col("state") == "36") & pl.col("county").is_in(list(NYC_COUNTIES))
    sites = sites.with_columns(
        pl.when(pl.col("site_id").is_in(list(nyc_roles)))
        .then(pl.col("site_id").replace_strict(nyc_roles, default=None))
        .when(is_nyc)
        .then(pl.lit("nyc_other"))
        .when(is_donor)
        .then(pl.lit("donor"))
        .otherwise(pl.lit("not_used"))
        .alias("role")
    )
    return valid.drop("state", "county", "latitude", "longitude").join(
        sites, on="site_id", how="left"
    )


def main() -> None:
    """Write data/processed/air_site_day.parquet."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    nyccas = nyccas_site_day().with_columns(
        (pl.col("n_hours") >= MIN_HOURS_PER_DAY).alias("valid_day")
    )
    frames = [nyccas]
    for parameter, pollutant in (("88101", "pm25"), ("42602", "no2")):
        aqs = label_aqs_roles(aqs_site_day(parameter, pollutant))
        frames.append(aqs.filter(pl.col("role") != "not_used"))
        LOG.info(
            "aqs %s: %d donor sites",
            pollutant,
            aqs.filter(pl.col("role") == "donor")["site_id"].n_unique(),
        )
    panel = pl.concat(frames, how="diagonal_relaxed").sort("source", "pollutant", "site_id", "date")
    panel.write_parquet(PROCESSED_DIR / "air_site_day.parquet")
    LOG.info("air panel: %d rows", panel.height)


if __name__ == "__main__":
    main()
