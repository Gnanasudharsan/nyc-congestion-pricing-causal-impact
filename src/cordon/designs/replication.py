"""Replication of Pandey, Guler & Gayah (2026), analysis plan section 4.2.

Their headline: ride-hail (FHVHV) trips from the CBD fell by beta = -0.0613
log points (SE 0.0157). The specification:
- weekdays in weeks 1-14 of 2025 vs 2024;
- ln(1 + trips) per taxi zone and day;
- control zones in Manhattan north of 60th St, counting trips that do not end in
  the CBD;
- a pooled 2x2 regression (treat, post, treat x post) without fixed effects;
- SEs clustered by zone.

We run it as published (with both plausible week conventions) and then swap
the control group for our far-control zones. The swap shows how much the
result depends on treating upper Manhattan as unaffected.

Run: ``python -m cordon.designs.replication``.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl
import statsmodels.api as sm

from cordon.config import REPO_ROOT
from cordon.designs import panels

LOG = logging.getLogger(__name__)
OUTPUT = REPO_ROOT / "results" / "replication_pandey.csv"
PUBLISHED_BETA = -0.0613
PUBLISHED_SE = 0.0157


def two_by_two(rows: pl.DataFrame) -> tuple[float, float, int, int]:
    """Coefficient and clustered SE on treat x post; also N and the number of zones."""
    treat = (rows["group"] == "treated").to_numpy().astype(float)
    post = rows["post"].to_numpy().astype(float)
    x = sm.add_constant(np.column_stack([treat, post, treat * post]))
    clusters = pl.Series(rows["unit"]).cast(pl.Categorical).to_physical().to_numpy()
    fit = sm.OLS(rows["value"].to_numpy(), x).fit(cov_type="cluster", cov_kwds={"groups": clusters})
    return float(fit.params[3]), float(fit.bse[3]), len(rows), rows["unit"].n_unique()


def main() -> None:
    """Write results/replication_pandey.csv."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    records = []
    for control in ("upper_manhattan", "far_control"):
        for convention in ("iso", "calendar"):
            beta, se, n_obs, n_zones = two_by_two(panels.pandey_panel(control, convention))
            records.append(
                {
                    "control_group": control,
                    "week_convention": convention,
                    "beta": beta,
                    "se": se,
                    "percent": float(100 * np.expm1(beta)),
                    "ci_low": beta - 1.96 * se,
                    "ci_high": beta + 1.96 * se,
                    "published_beta": PUBLISHED_BETA,
                    "published_se": PUBLISHED_SE,
                    "difference_from_published": beta - PUBLISHED_BETA,
                    "n_obs": n_obs,
                    "n_zones": n_zones,
                }
            )
            LOG.info("%s/%s: %.4f (%.4f)", control, convention, beta, se)
    OUTPUT.parent.mkdir(exist_ok=True)
    pl.DataFrame(records).write_csv(OUTPUT)


if __name__ == "__main__":
    main()
