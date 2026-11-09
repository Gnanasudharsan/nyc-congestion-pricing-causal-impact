"""HonestDiD sensitivity bounds (Rambachan & Roth 2023) and their validation.

ADR 0006 requires the Python port to reproduce the R package's published
example to 2 decimal places before it is used. The port only runs on NumPy 1.x,
so the bounds are computed by ``scripts/honestdid_bounds.py`` in its own locked
environment (deviation 7). This module prepares the inputs, runs that script,
and reads the results back.

Run ``python -m cordon.robustness.honest`` to (re)validate. It downloads the
example data, re-estimates the R example's event study with pyfixest, computes
both bounds, compares them with the R output, and writes
``results/honestdid_validation.csv``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import requests

from cordon.config import DATA_DIR, INTERIM_DIR, RAW_DIR, REPO_ROOT
from cordon.manifest import ManifestEntry, sha256_file, upsert_entry

LOG = logging.getLogger(__name__)
SCRIPT = REPO_ROOT / "scripts" / "honestdid_bounds.py"
REFERENCE = REPO_ROOT / "config" / "honestdid_reference.json"
WORK_DIR = INTERIM_DIR / "honestdid"
RESULTS = REPO_ROOT / "results" / "honestdid_validation.csv"
DECIMALS = 2  # ADR 0006 validation tolerance


def bounds(
    betahat: np.ndarray,
    sigma: np.ndarray,
    num_pre: int,
    num_post: int,
    l_vec: np.ndarray,
    mbar: list[float],
    m: list[float],
    tag: str,
) -> dict[str, Any]:
    """Relative-magnitudes and smoothness confidence sets for l_vec' tau_post."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    request = WORK_DIR / f"{tag}_input.json"
    response = WORK_DIR / f"{tag}_output.json"
    request.write_text(
        json.dumps(
            {
                "betahat": np.asarray(betahat).tolist(),
                "sigma": np.asarray(sigma).tolist(),
                "num_pre": num_pre,
                "num_post": num_post,
                "l_vec": np.asarray(l_vec).tolist(),
                "mbar": mbar,
                "m": m,
            }
        )
    )
    subprocess.run(
        ["uv", "run", "--quiet", "--script", str(SCRIPT), str(request), str(response)],
        check=True,
    )
    result: dict[str, Any] = json.loads(response.read_text())
    return result


def example_data() -> Path:
    """Download the R vignette's Medicaid example data (once) and record it."""
    reference = json.loads(REFERENCE.read_text())
    path = RAW_DIR / "honestdid" / "ehec_data.dta"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        reply = requests.get(reference["data"], timeout=60)
        reply.raise_for_status()
        path.write_bytes(reply.content)
        upsert_entry(
            DATA_DIR / "MANIFEST.json",
            ManifestEntry(
                dataset="honestdid_ehec_example",
                source_url=reference["data"],
                local_path=str(path.relative_to(REPO_ROOT)),
                downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
                sha256=sha256_file(path),
                rows=None,
                coverage_start=None,
                coverage_end=None,
                notes="Validation data for the HonestDiD port (ADR 0006); not an analysis input.",
            ),
        )
    return path


def example_event_study() -> tuple[np.ndarray, np.ndarray]:
    """Re-estimate the R vignette's TWFE event study with pyfixest."""
    import pandas as pd
    import pyfixest as pf

    frame = pd.read_stata(example_data(), convert_categoricals=False)
    frame = frame[(frame["year"] < 2016) & (frame["yexp2"].isna() | (frame["yexp2"] != 2015))]
    frame = frame.assign(D=(frame["yexp2"] == 2014).astype(int))
    fit = pf.feols(
        "dins ~ i(year, D, ref=2013) | stfips + year", data=frame, vcov={"CRV1": "stfips"}
    )
    return fit.coef().to_numpy(), np.asarray(fit._vcov)


def validate() -> pl.DataFrame:
    """Compare the port's bounds with the R output; one row per interval endpoint."""
    reference = json.loads(REFERENCE.read_text())
    betahat, sigma = example_event_study()
    l_vec = np.array([1.0, 0.0])  # first post-period effect, the R default
    result = bounds(
        betahat,
        sigma,
        reference["num_pre"],
        reference["num_post"],
        l_vec,
        mbar=[row["Mbar"] for row in reference["relative_magnitudes"]],
        m=[row["M"] for row in reference["smoothness"]],
        tag="validation",
    )
    rows = []
    for kind, key in (("relative_magnitudes", "Mbar"), ("smoothness", "M")):
        for ref_row, port_row in zip(reference[kind], result[kind], strict=True):
            for side in ("lb", "ub"):
                rows.append(
                    {
                        "restriction": kind,
                        "parameter": ref_row[key],
                        "endpoint": side,
                        "r_package": ref_row[side],
                        "python_port": round(float(port_row[side]), 5),
                        "matches_2dp": round(ref_row[side], DECIMALS)
                        == round(float(port_row[side]), DECIMALS),
                    }
                )
    table = pl.DataFrame(rows)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    table.write_csv(RESULTS)
    return table


def main() -> None:
    """Validate and report."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    table = validate()
    with pl.Config(tbl_rows=-1):
        print(table)
    passed = bool(table["matches_2dp"].all())
    LOG.info("HonestDiD port %s the R reference to 2 dp", "matches" if passed else "DOES NOT match")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
