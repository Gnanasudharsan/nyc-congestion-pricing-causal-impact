"""Audit the published site with Lighthouse and write ``results/lighthouse_scores.csv``.

CLAUDE.md sets a Lighthouse target of at least 90. This module audits every page
of the deployed site (GitHub Pages by default) with a pinned Lighthouse version,
under both the mobile profile (simulated slow 4G, mid-range phone) and the
desktop preset. Scores vary somewhat between runs because Lighthouse simulates
network and CPU throttling. Each page and profile is therefore audited ``RUNS``
times and the median performance run is kept, as Lighthouse's own docs advise.

Needs Node.js (``npx``) and Chrome. Raw JSON reports go to ``results/lighthouse/``
(gitignored).

Run: ``python -m cordon.viz.lighthouse [base URL]``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from cordon.config import REPO_ROOT

LIGHTHOUSE = "lighthouse@13.5.0"
SITE = "https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/"
PAGES = {
    "index": "",
    "paper": "paper.html",
    "results": "results.html",
    "methods": "methods.html",
    "data": "data.html",
}
PROFILES = ("mobile", "desktop")
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
RUNS = 3
RAW_DIR = REPO_ROOT / "results" / "lighthouse"
OUTPUT = REPO_ROOT / "results" / "lighthouse_scores.csv"


def audit(url: str, profile: str, output: Path) -> dict[str, Any]:
    """Run Lighthouse once and return the parsed JSON report."""
    command = [
        "npx",
        "-y",
        LIGHTHOUSE,
        url,
        "--output=json",
        f"--output-path={output}",
        "--chrome-flags=--headless=new",
        "--quiet",
    ]
    if profile == "desktop":
        command.append("--preset=desktop")
    subprocess.run(command, check=True)
    report: dict[str, Any] = json.loads(output.read_text())
    return report


def summarise(page: str, profile: str, report: dict[str, Any], server: str) -> dict[str, Any]:
    """One CSV row: category scores (0-100) and the main timing metrics."""
    audits = report["audits"]
    row: dict[str, Any] = {"page": page, "profile": profile}
    for category in CATEGORIES:
        row[category] = round(100 * report["categories"][category]["score"])
    row["fcp"] = audits["first-contentful-paint"]["displayValue"]
    row["lcp"] = audits["largest-contentful-paint"]["displayValue"]
    row["cls"] = audits["cumulative-layout-shift"]["displayValue"]
    row["lighthouse"] = report["lighthouseVersion"]
    row["server"] = server
    row["date"] = date.today().isoformat()
    return row


def main(base: str = SITE) -> None:
    """Audit every page and profile; keep the median-performance run of each."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    server = "GitHub Pages (live)" if base == SITE else base
    rows = []
    for page, path in PAGES.items():
        for profile in PROFILES:
            runs = []
            for run in range(RUNS):
                output = RAW_DIR / f"{page}-{profile}-{run}.json"
                runs.append(audit(base + path, profile, output))
            runs.sort(key=lambda report: report["categories"]["performance"]["score"])
            rows.append(summarise(page, profile, runs[len(runs) // 2], server))
    pl.DataFrame(rows).write_csv(OUTPUT)


if __name__ == "__main__":
    main(*sys.argv[1:2])
