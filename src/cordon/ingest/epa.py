"""Download and profile EPA AQS pre-generated hourly files.

EPA publishes one zip per parameter and year at aqs.epa.gov/aqsweb/airdata.
These are the regulatory-grade monitor data; no API key is required.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import requests

# Counties for the NYC study area and nearby same-airshed donors.
# NY: Bronx 005, Kings 047, New York 061, Queens 081, Richmond 085.
NYC_COUNTIES = {("36", "005"), ("36", "047"), ("36", "061"), ("36", "081"), ("36", "085")}


def hourly_file_name(parameter: str, year: int) -> str:
    """File name EPA uses, e.g. hourly_88101_2025.zip."""
    return f"hourly_{parameter}_{year}.zip"


def download_hourly(base_url: str, parameter: str, year: int, raw_dir: Path) -> Path:
    """Download one hourly zip if it is not already on disk."""
    destination = raw_dir / hourly_file_name(parameter, year)
    if destination.exists():
        return destination
    raw_dir.mkdir(parents=True, exist_ok=True)
    url = f"{base_url}/{hourly_file_name(parameter, year)}"
    # Write to a temporary name and rename at the end, so an interrupted download
    # never leaves a truncated file that a later run would mistake for complete.
    partial = destination.with_suffix(".zip.part")
    with requests.get(url, stream=True, timeout=600) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    partial.rename(destination)
    return destination


def extract_csv(zip_path: Path, interim_dir: Path) -> Path:
    """Extract the single CSV inside an EPA zip into data/interim."""
    interim_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"expected one CSV in {zip_path}, found {names}")
        target = interim_dir / names[0]
        if not target.exists():
            archive.extract(names[0], interim_dir)
    return target


def profile_hourly_csv(csv_path: Path) -> dict[str, object]:
    """Summarise national coverage and per-site coverage for NYC monitors."""
    connection = duckdb.connect()
    source = f"read_csv_auto('{csv_path}', all_varchar=true)"
    national = connection.execute(
        f'SELECT count(*), min("Date Local"), max("Date Local"), '
        f'count(DISTINCT "State Code" || "County Code" || "Site Num") FROM {source}'
    ).fetchone()
    county_filter = " OR ".join(
        f"(\"State Code\" = '{state}' AND \"County Code\" = '{county}')"
        for state, county in sorted(NYC_COUNTIES)
    )
    sites = connection.execute(
        f'SELECT "State Code" || \'-\' || "County Code" || \'-\' || "Site Num" AS site, '
        f'any_value("County Name"), any_value("Latitude"), any_value("Longitude"), '
        f'count(DISTINCT "POC"), count(*), min("Date Local"), max("Date Local") '
        f"FROM {source} WHERE {county_filter} GROUP BY site ORDER BY site"
    ).fetchall()
    if national is None:
        raise RuntimeError(f"empty result profiling {csv_path}")
    return {
        "rows": int(national[0]),
        "coverage_start": national[1],
        "coverage_end": national[2],
        "n_sites_national": int(national[3]),
        "nyc_sites": [
            {
                "site": s[0],
                "county": s[1],
                "latitude": float(s[2]),
                "longitude": float(s[3]),
                "n_instruments": int(s[4]),
                "rows": int(s[5]),
                "start": s[6],
                "end": s[7],
            }
            for s in sites
        ],
    }
