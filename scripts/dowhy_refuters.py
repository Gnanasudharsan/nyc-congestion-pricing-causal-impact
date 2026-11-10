# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "dowhy==0.14",
#     "pyarrow",
# ]
# ///
"""DoWhy refuters in an isolated, locked environment (deviations 20 and 24).

DoWhy 0.12 fails under pandas 3 (positional Series indexing) and NetworkX 3.5+.
DoWhy 0.14 fixes both but pins SciPy <= 1.15.3, which the project cannot use.
So this script runs in its own environment, pinned by ``dowhy_refuters.py.lock``
(``uv lock --script``). It reads fixed-effect-residualised data (columns y, d,
a) from a Parquet file.

Usage: uv run --script scripts/dowhy_refuters.py INPUT.parquet OUTPUT.json SEED
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dowhy import CausalModel


def main() -> None:
    """Estimate the effect of d on y (adjusting for a) and run three refuters."""
    frame = pd.read_parquet(sys.argv[1])
    seed = int(sys.argv[3])
    np.random.seed(seed)
    model = CausalModel(data=frame, treatment="d", outcome="y", common_causes=["a"])
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(estimand, method_name="backdoor.linear_regression")
    results = []
    for refuter, kwargs in (
        ("placebo_treatment_refuter", {"placebo_type": "permute", "num_simulations": 100}),
        ("random_common_cause", {"num_simulations": 100}),
        ("data_subset_refuter", {"subset_fraction": 0.8, "num_simulations": 100}),
    ):
        refutation = model.refute_estimate(
            estimand, estimate, method_name=refuter, random_seed=seed, **kwargs
        )
        p_value = None
        if refutation.refutation_result:
            p_value = float(refutation.refutation_result["p_value"])
        results.append(
            {
                "refuter": refuter,
                "estimate": float(estimate.value),
                "new_effect": float(refutation.new_effect),
                "p_value": p_value,
            }
        )
    Path(sys.argv[2]).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
