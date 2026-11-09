"""Remove fixed effects from columns by alternating projections.

Regressing ``y`` on treatment regressors ``X`` plus several sets of fixed
effects gives the same coefficients as regressing demeaned ``y`` on demeaned
``X`` (the Frisch-Waugh-Lovell theorem). With more than one set of fixed
effects there is no closed form for the demeaning. Instead we repeatedly
subtract group means for each set in turn until nothing changes (Guimaraes &
Portugal 2010; this is also what ``fixest`` and ``pyfixest`` do).

Every design in ``cordon.designs.did`` builds on :func:`demean`.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

TOLERANCE = 1e-10
MAX_ITERATIONS = 10_000


def encode(labels: npt.ArrayLike) -> IntArray:
    """Map arbitrary labels to consecutive integer codes 0..(levels - 1)."""
    _, codes = np.unique(np.asarray(labels), return_inverse=True)
    return codes.astype(np.int64)


def subtract_group_means(values: FloatArray, codes: IntArray) -> FloatArray:
    """Subtract, for every column, the mean of its group (one fixed-effect set)."""
    levels = int(codes.max()) + 1
    counts = np.bincount(codes, minlength=levels).astype(np.float64)
    result = np.empty_like(values)
    for column in range(values.shape[1]):
        sums = np.bincount(codes, weights=values[:, column], minlength=levels)
        result[:, column] = values[:, column] - (sums / counts)[codes]
    return result


def demean(values: FloatArray, fixed_effects: list[IntArray]) -> FloatArray:
    """Residualise each column of ``values`` on all fixed-effect sets.

    Args:
        values: an (n, k) array, or an (n,) vector.
        fixed_effects: integer codes, one array of length n per fixed-effect set.

    Returns:
        An array of the same shape, orthogonal to every fixed-effect dummy.

    Raises:
        RuntimeError: if the projections do not converge.

    """
    matrix = np.asarray(values, dtype=np.float64)
    was_vector = matrix.ndim == 1
    if was_vector:
        matrix = matrix[:, None]
    if not fixed_effects:
        return matrix[:, 0] if was_vector else matrix
    current = matrix.copy()
    scale = max(float(np.abs(matrix).max()), 1.0)
    for _ in range(MAX_ITERATIONS):
        previous = current
        for codes in fixed_effects:
            current = subtract_group_means(current, codes)
        if float(np.abs(current - previous).max()) < TOLERANCE * scale:
            return current[:, 0] if was_vector else current
    raise RuntimeError("fixed-effect demeaning did not converge")
