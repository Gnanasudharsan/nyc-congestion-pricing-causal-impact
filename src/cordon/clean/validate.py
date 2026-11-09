"""Data tests for every processed panel.

Run with ``python -m cordon.clean.validate``. Each check returns a list of
failure messages (empty means it passed). Results are written to
``data/catalog/validation.json`` and the command exits non-zero on any failure.

Checks cover: unique keys, expected units and date coverage, value ranges,
internal consistency (parts sum to totals), and DST handling.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import date

import polars as pl

from cordon.config import DATA_DIR, FINAL_DIR, PROCESSED_DIR

Check = Callable[[], list[str]]
RESULTS_PATH = DATA_DIR / "catalog" / "validation.json"


def first_day(frame: pl.DataFrame) -> date:
    """Earliest date in a frame's ``date`` column."""
    value = frame["date"].min()
    if not isinstance(value, date):
        raise TypeError("date column is empty or not a date")
    return value


def last_day(frame: pl.DataFrame) -> date:
    """Latest date in a frame's ``date`` column."""
    value = frame["date"].max()
    if not isinstance(value, date):
        raise TypeError("date column is empty or not a date")
    return value


def duplicate_keys(frame: pl.DataFrame, keys: list[str]) -> list[str]:
    """Report if any key combination appears more than once."""
    duplicates = frame.group_by(keys).len().filter(pl.col("len") > 1).height
    return [f"{duplicates} duplicated keys on {keys}"] if duplicates else []


def missing_days(frame: pl.DataFrame, unit: str, start: date, end: date) -> list[str]:
    """Report units that do not have exactly one row per day from start to end."""
    expected = (end - start).days + 1
    counts = frame.filter(pl.col("date").is_between(start, end)).group_by(unit).len()
    short = counts.filter(pl.col("len") != expected)
    if short.height:
        return [f"{short.height} {unit} values lack {expected} days in {start}..{end}"]
    return []


def nulls_in(frame: pl.DataFrame, columns: list[str]) -> list[str]:
    """Report nulls in columns that must be complete."""
    counts = frame.select(pl.col(columns).null_count()).row(0, named=True)
    return [f"{n} nulls in {c}" for c, n in counts.items() if n]


def check_zone_groups() -> list[str]:
    """Taxi-zone groups: 263 zones, 38 CRZ zones (MTA list), every zone labelled."""
    groups = pl.read_csv(FINAL_DIR / "zone_groups.csv")
    failures = duplicate_keys(groups, ["location_id"])
    if groups.height != 263:
        failures.append(f"expected 263 zones, found {groups.height}")
    if groups.filter(pl.col("group") == "crz").height != 38:
        failures.append("expected 38 CRZ zones")
    return failures + nulls_in(groups, ["group", "distance_km"])


def check_bt() -> list[str]:
    """B&T facility-day panel."""
    panel = pl.read_parquet(PROCESSED_DIR / "bt_facility_day.parquet")
    failures = duplicate_keys(panel, ["facility", "date"])
    failures += missing_days(panel, "facility", date(2023, 1, 1), last_day(panel))
    if panel["facility"].n_unique() != 10:
        failures.append("expected 10 facility plazas")
    classes = panel.select(pl.sum_horizontal(pl.col("^crossings_(bus|car|motorcycle|truck)$")))
    if (classes.to_series() != panel["crossings"]).any():
        failures.append("vehicle classes do not sum to total crossings")
    if ((panel["crossings_peak"] + panel["crossings_offpeak"]) != panel["crossings"]).any():
        failures.append("peak + off-peak do not sum to total crossings")
    if (panel["crossings"] < 0).any():
        failures.append("negative crossings")
    return failures + nulls_in(panel, ["crossings", "facility_group", "is_closure"])


def check_tlc() -> list[str]:
    """TLC zone-day panel: keys, coverage, and consistency of speed sums."""
    panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet")
    keys = ["service", "date", "pu_location_id", "is_peak", "do_group"]
    failures = duplicate_keys(panel, keys)
    months = panel.group_by("service").agg(pl.col("date").dt.strftime("%Y-%m").n_unique())
    for service, n_months in months.iter_rows():
        if n_months != 45:
            failures.append(f"{service}: {n_months} months, expected 45 (2023-01..2026-09)")
    if (panel["speed_trips"] > panel["trips"]).any():
        failures.append("speed-valid trips exceed trips")
    bad_speed = panel.filter(
        (pl.col("speed_trips") > 0)
        & ~(pl.col("speed_miles") / (pl.col("speed_seconds") / 3600)).is_between(0.5, 60)
    )
    if bad_speed.height:
        failures.append(f"{bad_speed.height} cells with aggregate speed outside 0.5-60 mph")
    if first_day(panel) < date(2023, 1, 1) or last_day(panel) > date(2026, 9, 30):
        failures.append("dates outside 2023-01-01..2026-09-30")
    return failures + nulls_in(panel, ["pu_location_id", "do_group", "trips"])


def check_tlc_against_probes() -> list[str]:
    """Check aggregated trip counts against Phase 1 parquet row counts (within 0.5%)."""
    profiles = json.loads((DATA_DIR / "catalog" / "profiles.json").read_text())
    panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet")
    failures = []
    for service, info in profiles["tlc"]["services"].items():
        for probe in info["probes"]:
            month = probe["month"]
            ours = panel.filter(
                (pl.col("service") == service) & (pl.col("date").dt.strftime("%Y-%m") == month)
            )["trips"].sum()
            share = ours / probe["rows"]
            if not 0.995 <= share <= 1.0:
                failures.append(f"{service} {month}: {ours} of {probe['rows']} rows ({share:.2%})")
    return failures


def check_ntd() -> list[str]:
    """NTD unit-month panel."""
    panel = pl.read_parquet(PROCESSED_DIR / "ntd_unit_month.parquet")
    failures = duplicate_keys(panel, ["unit", "month"])
    roles = panel.group_by("role").agg(pl.col("unit").n_unique()).to_dict(as_series=False)
    counts = dict(zip(roles["role"], roles["unit"], strict=True))
    if counts.get("treated_r1") != 1 or counts.get("treated_r4") != 1:
        failures.append("treated NTD units missing")
    if counts.get("donor_r1", 0) < 10:
        failures.append("fewer than 10 R1 donors")
    return failures


def check_air() -> list[str]:
    """Air site-day panel: keys, hour counts, and the core sites."""
    panel = pl.read_parquet(PROCESSED_DIR / "air_site_day.parquet")
    failures = duplicate_keys(panel, ["source", "pollutant", "site_id", "date"])
    if (panel["n_hours"] > 25).any():
        failures.append("more than 25 hourly values in a local day")
    roles = set(panel["role"].unique())
    for role in ("crz_core", "far_core", "spillover_core", "donor", "spillover_no2"):
        if role not in roles:
            failures.append(f"no sites with role {role}")
    return failures + nulls_in(panel, ["daily_mean", "role"])


def check_subway() -> list[str]:
    """Subway station-day panel."""
    panel = pl.read_parquet(PROCESSED_DIR / "subway_station_day.parquet")
    failures = duplicate_keys(panel, ["station_complex_id", "date"])
    if (panel["entries"] < 0).any():
        failures.append("negative entries")
    unmatched = panel.filter(pl.col("is_crz").is_null())["station_complex_id"].n_unique()
    if unmatched:
        failures.append(f"{unmatched} station complexes not in the stations table")
    days = panel["date"].n_unique()
    expected = (last_day(panel) - first_day(panel)).days + 1
    if days != expected:
        failures.append(f"{expected - days} calendar days missing system-wide")
    return failures


def check_features() -> list[str]:
    """Calendar, weather, and smoke: one row per day; weather hours reflect DST."""
    failures: list[str] = []
    for name in ("calendar", "weather_daily", "smoke_days"):
        frame = pl.read_parquet(PROCESSED_DIR / f"{name}.parquet")
        failures += [f"{name}: {m}" for m in duplicate_keys(frame, ["date"])]
    weather = pl.read_parquet(PROCESSED_DIR / "weather_daily.parquet")
    complete = weather.filter(pl.col("date") < last_day(weather))
    odd = complete.filter(~pl.col("weather_hours").is_in([23, 24, 25]))
    if odd.height:
        failures.append(f"weather: {odd.height} days without 23/24/25 hours")
    # DST: spring-forward days have 23 local hours, fall-back days 25.
    for spring, fall in (
        (date(2024, 3, 10), date(2024, 11, 3)),
        (date(2025, 3, 9), date(2025, 11, 2)),
    ):
        hours = dict(
            weather.filter(pl.col("date").is_in([spring, fall]))
            .select("date", "weather_hours")
            .iter_rows()
        )
        if hours.get(spring) != 23 or hours.get(fall) != 25:
            failures.append(f"weather DST hours wrong around {spring.year}: {hours}")
    return failures


CHECKS: dict[str, Check] = {
    "zone_groups": check_zone_groups,
    "bt": check_bt,
    "tlc": check_tlc,
    "tlc_vs_phase1_row_counts": check_tlc_against_probes,
    "ntd": check_ntd,
    "air": check_air,
    "subway": check_subway,
    "features": check_features,
}


def run_all(checks: dict[str, Check] = CHECKS) -> dict[str, list[str]]:
    """Run every check; a missing input file is reported as a failure."""
    results: dict[str, list[str]] = {}
    for name, check in checks.items():
        try:
            results[name] = check()
        except FileNotFoundError as error:
            results[name] = [f"input missing: {error}"]
    return results


def main() -> None:
    """Run all checks, save results, and exit non-zero on failure."""
    results = run_all()
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
    for name, failures in results.items():
        status = "PASS" if not failures else "FAIL"
        print(f"{status:4}  {name}" + "".join(f"\n      - {f}" for f in failures))
    if any(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
