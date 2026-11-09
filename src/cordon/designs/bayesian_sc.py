"""Bayesian synthetic-control cross-check with CausalPy (ADR 0009).

Same treated series, donors, and centring as the frequentist estimator in
``cordon.designs.synth``. CausalPy's ``WeightedSumFitter`` puts a Dirichlet prior
on the donor weights, so they are non-negative and sum to 1, matching our
constraint. The anticipation window is dropped, so the model is fit on the
pre-period only.

We report the posterior mean of the average year-1 gap and its 95% equal-tailed
credible interval. This is a cross-check, not a primary estimate.

Environment note: on this macOS toolchain, PyTensor's C backend passes a
``-ld64`` linker flag that the system clang rejects. We therefore disable C
compilation and use PyTensor's Numba backend (``PYTENSOR_FLAGS``), which gives
the same results more slowly.

Run: ``python -m cordon.designs.bayesian_sc``.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

import numpy as np
import polars as pl

from cordon.config import RANDOM_SEED, REPO_ROOT
from cordon.designs import panels, synth

LOG = logging.getLogger(__name__)
OUTPUT = REPO_ROOT / "results" / "bayesian_sc_crosscheck.csv"
SAMPLER = {"draws": 1000, "tune": 1000, "chains": 4, "progressbar": False}

OUTCOMES: dict[str, Callable[[], panels.SyntheticPanel]] = {
    "R1": lambda: panels.ntd_synthetic("treated_r1", "donor_r1"),
    "A1": lambda: panels.air_synthetic("pm25", ["crz_core"]),
}


def year1_gap(panel: panels.SyntheticPanel) -> dict[str, float]:
    """Posterior summary of the average year-1 gap."""
    import causalpy as cp
    import pandas as pd

    w = panel.windows
    keep = ~w.anticipation
    treated = synth.centre(panel.target[:, None], w, detrend=False)[:, 0][keep]
    donors = synth.centre(panel.donors, w, detrend=False)[keep]
    index = pd.DatetimeIndex(
        [pd.Timestamp(p) for p, k in zip(panel.periods, keep, strict=True) if k]
    )
    names = [f"donor_{i}" for i in range(donors.shape[1])]
    frame = pd.DataFrame(donors, columns=names, index=index).assign(treated=treated)
    first_post = index[int(np.argmax(w.post_year1[keep]))]
    model = cp.pymc_models.WeightedSumFitter(sample_kwargs={**SAMPLER, "random_seed": RANDOM_SEED})
    result = cp.SyntheticControl(
        frame, first_post, control_units=names, treated_units=["treated"], model=model
    )
    impact = result.post_impact.sel(treated_units="treated")
    year1 = impact.sel(obs_ind=impact["obs_ind"].dt.year == 2025).mean("obs_ind")
    draws = year1.values.ravel()
    low, high = np.percentile(draws, [2.5, 97.5])
    return {"posterior_mean": float(draws.mean()), "ci_low": float(low), "ci_high": float(high)}


def main() -> None:
    """Write results/bayesian_sc_crosscheck.csv."""
    os.environ.setdefault("PYTENSOR_FLAGS", "cxx=,mode=NUMBA")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    rows = []
    for key, build in OUTCOMES.items():
        panel = build()
        frequentist = synth.fit_one(panel.target, panel.donors, panel.windows, detrend=False)
        bayes = year1_gap(panel)
        rows.append({"key": key, "frequentist_effect": frequentist.effect_year1, **bayes})
        LOG.info(
            "%s: frequentist %.4f, Bayesian %.4f",
            key,
            frequentist.effect_year1,
            bayes["posterior_mean"],
        )
    OUTPUT.parent.mkdir(exist_ok=True)
    pl.DataFrame(rows).write_csv(OUTPUT)


if __name__ == "__main__":
    main()
