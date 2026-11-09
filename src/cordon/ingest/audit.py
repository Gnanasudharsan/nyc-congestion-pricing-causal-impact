"""Phase 1 data audit: profile every candidate dataset and record provenance.

Run with ``python -m cordon.ingest.audit``. Outputs:

- ``data/catalog/profiles.json`` (committed): coverage, row counts, columns,
  category levels, and whether a usable pre-period exists, for every source.
- ``data/raw/...`` (gitignored): full downloads of the small tables, the EPA
  hourly files, and weather, each recorded in ``data/MANIFEST.json``.

Large tables (hourly subway/bus ridership, hourly crossings, TLC trip records)
are profiled server-side here and downloaded in Phase 2 by ``make data``.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from cordon.config import (
    DATA_DIR,
    INTERIM_DIR,
    MANIFEST_PATH,
    RAW_DIR,
    REPO_ROOT,
    TIMEZONE,
)
from cordon.ingest import epa, misc_sources, nyccas, socrata, tlc
from cordon.ingest.coverage import has_usable_pre_period, pre_period_days
from cordon.manifest import ManifestEntry, sha256_file, upsert_entry

LOG = logging.getLogger("cordon.audit")
REGISTRY_PATH = REPO_ROOT / "config" / "datasets.yaml"
PROFILES_PATH = DATA_DIR / "catalog" / "profiles.json"

# Socrata tables at or below this size are downloaded in full during the audit.
FULL_DOWNLOAD_MAX_ROWS = 2_000_000


def now_local() -> str:
    """Return the current New York time in ISO format, for provenance records."""
    return datetime.now(TIMEZONE).isoformat(timespec="seconds")


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the dataset registry YAML."""
    with path.open() as handle:
        registry: dict[str, Any] = yaml.safe_load(handle)
    return registry


def count_csv_rows(path: Path) -> int:
    """Count data rows in a CSV file (lines minus the header)."""
    with path.open("rb") as handle:
        return sum(1 for _ in handle) - 1


def record_download(
    dataset: str, url: str, path: Path, rows: int | None, start: str | None, end: str | None
) -> None:
    """Add a downloaded file to data/MANIFEST.json."""
    upsert_entry(
        MANIFEST_PATH,
        ManifestEntry(
            dataset=dataset,
            source_url=url,
            local_path=str(path.relative_to(REPO_ROOT)),
            downloaded_at=now_local(),
            sha256=sha256_file(path),
            rows=rows,
            coverage_start=start,
            coverage_end=end,
        ),
    )


def save_profiles(profiles: dict[str, Any]) -> None:
    """Write profiles to disk after every source, so a failure loses nothing."""
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2, default=str) + "\n")


def audit_socrata(entry: dict[str, Any], download: bool) -> dict[str, Any]:
    """Profile one Socrata table and download it if it is small."""
    if entry.get("probe_dates"):
        found = socrata.probe_dates(
            entry["domain"], entry["id"], entry["date_column"], entry["probe_dates"]
        )
        present = [day for day, n in found.items() if n > 0]
        return {
            "kind": "socrata",
            "dataset_id": entry["id"],
            "id": entry["id"],
            "domain": entry["domain"],
            "role": entry["role"],
            "domain_area": entry["domain_area"],
            "url": f"https://{entry['domain']}/d/{entry['id']}",
            "probe_only": True,
            "probes": found,
            "row_count": None,
            "coverage_start": present[0] if present else None,
            "coverage_end": present[-1] if present else None,
            "pre_period_days": pre_period_days(present[0]) if present else 0,
            "usable_pre_period": bool(present) and has_usable_pre_period(present[0]),
            "downloaded": False,
            "notes": "Too large to aggregate server-side; coverage from dated probes only.",
        }
    profile = socrata.profile_dataset(
        entry["domain"], entry["id"], entry.get("date_column"), entry.get("group_columns")
    )
    result: dict[str, Any] = asdict(profile)
    result.update(
        kind="socrata",
        domain=entry["domain"],
        role=entry["role"],
        domain_area=entry["domain_area"],
        url=f"https://{entry['domain']}/d/{entry['id']}",
        pre_period_days=pre_period_days(profile.coverage_start),
        usable_pre_period=has_usable_pre_period(profile.coverage_start),
        downloaded=False,
    )
    if download and profile.row_count <= FULL_DOWNLOAD_MAX_ROWS:
        path = RAW_DIR / "socrata" / f"{entry['key']}.csv"
        socrata.download_csv(entry["domain"], entry["id"], path)
        rows = count_csv_rows(path)
        record_download(
            entry["key"], result["url"], path, rows, profile.coverage_start, profile.coverage_end
        )
        result["downloaded"] = True
        result["downloaded_rows"] = rows
    return result


def audit_tlc(config: dict[str, Any]) -> dict[str, Any]:
    """List available TLC months per service and profile a few probe months."""
    connection = tlc.connect()
    output: dict[str, Any] = {"kind": "tlc", "role": config["role"], "services": {}}
    for service, spec in config["services"].items():
        months = tlc.available_months(
            config["base_url"], service, config["first_month"], date.today()
        )
        probes = [
            asdict(
                tlc.profile_file(
                    connection, config["base_url"], service, month, spec["pickup_column"]
                )
            )
            for month in config["probe_months"]
            if month in months
        ]
        output["services"][service] = {
            "months_available": months,
            "coverage_start": months[0] if months else None,
            "coverage_end": months[-1] if months else None,
            "usable_pre_period": bool(months) and has_usable_pre_period(months[0]),
            "probes": probes,
        }
        LOG.info("tlc %s: %d months", service, len(months))
    return output


def audit_epa(config: dict[str, Any], download: bool) -> dict[str, Any]:
    """Download EPA hourly files and profile NYC monitor coverage."""
    output: dict[str, Any] = {"kind": "epa_aqs", "role": config["role"], "files": {}}
    if not download:
        return output
    for parameter, label in config["parameters"].items():
        for year in config["years"]:
            zip_path = epa.download_hourly(config["base_url"], parameter, year, RAW_DIR / "epa")
            csv_path = epa.extract_csv(zip_path, INTERIM_DIR / "epa")
            summary = epa.profile_hourly_csv(csv_path)
            summary["parameter_label"] = label
            url = f"{config['base_url']}/{epa.hourly_file_name(parameter, year)}"
            record_download(
                f"epa_hourly_{parameter}",
                url,
                zip_path,
                int(str(summary["rows"])),
                str(summary["coverage_start"]),
                str(summary["coverage_end"]),
            )
            output["files"][f"{parameter}_{year}"] = summary
            LOG.info("epa %s %d: %s rows", parameter, year, summary["rows"])
    return output


def audit_nyccas(config: dict[str, Any], download: bool) -> dict[str, Any]:
    """Download NYCCAS real-time PM2.5 history at a pinned commit and profile sites."""
    output: dict[str, Any] = {"kind": "nyccas", "role": config["role"]}
    if not download:
        return output
    sha = nyccas.latest_commit_sha()
    raw_dir = RAW_DIR / "nyccas"
    location_path = raw_dir / "location.csv"
    nyccas.download_file(sha, "hist/csv/location.csv", location_path)
    record_download(
        "nyccas_locations",
        f"{nyccas.RAW_BASE}/{sha}/hist/csv/location.csv",
        location_path,
        count_csv_rows(location_path),
        None,
        None,
    )
    months: list[str] = []
    total_rows = 0
    for year in config["years"]:
        for month in range(1, 13):
            repo_path = nyccas.month_file_path(year, month)
            destination = raw_dir / str(year) / f"{month:02d}.csv"
            if not nyccas.download_file(sha, repo_path, destination):
                continue
            rows = count_csv_rows(destination)
            total_rows += rows
            months.append(f"{year}-{month:02d}")
            record_download(
                "nyccas_hourly_pm25",
                f"{nyccas.RAW_BASE}/{sha}/{repo_path}",
                destination,
                rows,
                f"{year}-{month:02d}",
                f"{year}-{month:02d}",
            )
    with location_path.open() as handle:
        header = handle.readline().strip().split(",")
        sites = [dict(zip(header, line.strip().split(","), strict=False)) for line in handle]
    output.update(
        commit_sha=sha,
        months=months,
        coverage_start=months[0] if months else None,
        coverage_end=months[-1] if months else None,
        rows=total_rows,
        sites=[
            {
                "site_id": s["SiteID"],
                "name": s["Location"],
                "start": s["StartTime"],
                "end": s["EndTime"],
                "pre_period_days": pre_period_days(s["StartTime"]),
                "usable_pre_period": has_usable_pre_period(s["StartTime"]),
            }
            for s in sites
        ],
    )
    return output


def audit_citibike(config: dict[str, Any]) -> dict[str, Any]:
    """Record which Citi Bike monthly archives exist."""
    keys = misc_sources.list_citibike_files(config["bucket_url"])
    start, end = misc_sources.citibike_coverage(keys)
    return {
        "kind": "citibike",
        "role": config["role"],
        "files": keys,
        "coverage_start": start,
        "coverage_end": end,
        "usable_pre_period": has_usable_pre_period(start[:4] + "-" + (start[4:6] or "01")),
    }


def audit_weather(config: dict[str, Any], download: bool) -> dict[str, Any]:
    """Download hourly Central Park weather for the full study window."""
    output: dict[str, Any] = {"kind": "open_meteo", "role": config["role"]}
    if not download:
        return output
    path = RAW_DIR / "weather" / "open_meteo_central_park_hourly.csv"
    end = date.today().isoformat()
    misc_sources.download_open_meteo(
        config["archive_url"], config["latitude"], config["longitude"], "2022-01-01", end, path
    )
    rows = count_csv_rows(path) - 3  # Open-Meteo CSV has a 3-line location header
    record_download("open_meteo_hourly", config["archive_url"], path, rows, "2022-01-01", end)
    output.update(rows=rows, coverage_start="2022-01-01", coverage_end=end)
    return output


def main() -> None:
    """Run the audit for all sources, or the subset named on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="registry keys or source kinds to audit")
    parser.add_argument("--no-download", action="store_true", help="profile without downloading")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    registry = load_registry()
    profiles: dict[str, Any] = (
        json.loads(PROFILES_PATH.read_text()) if PROFILES_PATH.exists() else {}
    )
    profiles["_audited_at"] = now_local()
    wanted = set(args.only or [])
    download = not args.no_download

    def selected(name: str) -> bool:
        return not wanted or name in wanted

    for entry in registry["socrata"]:
        if not (selected(entry["key"]) or selected("socrata")):
            continue
        LOG.info("socrata %s (%s)", entry["key"], entry["id"])
        try:
            profiles[entry["key"]] = audit_socrata(entry, download)
        except Exception as error:  # record and continue: one bad source must not stop the audit
            LOG.warning("failed %s: %s", entry["key"], error)
            profiles[entry["key"]] = {"kind": "socrata", "id": entry["id"], "error": str(error)}
        save_profiles(profiles)

    if selected("tlc"):
        profiles["tlc"] = audit_tlc(registry["tlc"])
        save_profiles(profiles)
    if selected("epa_aqs"):
        profiles["epa_aqs"] = audit_epa(registry["epa_aqs"], download)
        save_profiles(profiles)
    if selected("nyccas"):
        profiles["nyccas"] = audit_nyccas(registry["nyccas"], download)
        save_profiles(profiles)
    if selected("citibike"):
        profiles["citibike"] = audit_citibike(registry["citibike"])
        save_profiles(profiles)
    if selected("open_meteo"):
        profiles["open_meteo"] = audit_weather(registry["open_meteo"], download)
        save_profiles(profiles)


if __name__ == "__main__":
    main()
