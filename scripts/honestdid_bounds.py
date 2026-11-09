# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "honestdid==0.1.1",
#     "numpy<2",
#     "pandas<3",
# ]
# ///
"""HonestDiD bounds in an isolated, locked environment (ADR 0006, deviation 7).

The only Python port, ``honestdid`` 0.1.1, reproduces the R package's published
example to 2 decimal places, but only on NumPy 1.x: its relative-magnitudes code
calls ``float()`` on 1x1 arrays, which NumPy 2 rejects. The project uses NumPy 2,
so this script runs in its own environment, pinned by ``honestdid_bounds.py.lock``
(``uv lock --script``). It exchanges data only through JSON files.

Usage: uv run --script scripts/honestdid_bounds.py INPUT.json OUTPUT.json

INPUT keys: betahat (list), sigma (list of lists), num_pre, num_post, l_vec
(list), mbar (list, relative magnitudes), m (list, smoothness).
OUTPUT: {"relative_magnitudes": [...rows], "smoothness": [...rows], "original": {...}}.
"""

import json
import sys
from pathlib import Path

import honestdid as hd
import numpy as np


def plain(value):
    """Convert NumPy scalars to Python floats so they serialise as JSON."""
    return float(value) if isinstance(value, (int, float, np.floating)) else value


def records(frame):
    """DataFrame rows as plain dicts."""
    return [{key: plain(value) for key, value in row.items()} for row in frame.to_dict("records")]


def main() -> None:
    """Read the request, compute the bounds, write the response."""
    spec = json.loads(Path(sys.argv[1]).read_text())
    betahat = np.asarray(spec["betahat"], dtype=float)
    sigma = np.asarray(spec["sigma"], dtype=float)
    common = dict(
        betahat=betahat,
        sigma=sigma,
        numPrePeriods=int(spec["num_pre"]),
        numPostPeriods=int(spec["num_post"]),
        l_vec=np.asarray(spec["l_vec"], dtype=float),
    )
    output = {
        "original": records(hd.constructOriginalCS(**common))[0],
        "relative_magnitudes": records(
            hd.createSensitivityResults_relativeMagnitudes(**common, Mbarvec=spec["mbar"])
        )
        if spec.get("mbar")
        else [],
        "smoothness": records(hd.createSensitivityResults(**common, Mvec=spec["m"]))
        if spec.get("m")
        else [],
    }
    Path(sys.argv[2]).write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
