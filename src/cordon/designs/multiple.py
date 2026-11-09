"""Multiple-testing adjustments (ADR 0008).

- Holm-Bonferroni controls the family-wise error rate across the six primary
  outcomes.
- Benjamini-Hochberg controls the false discovery rate within each family of
  secondary outcomes.
"""

from __future__ import annotations

import numpy as np


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    p = np.asarray(p_values, dtype=np.float64)
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, index in enumerate(order):
        running_max = max(running_max, (m - rank) * p[index])
        adjusted[index] = min(1.0, running_max)
    return adjusted.tolist()


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values, in the input order."""
    p = np.asarray(p_values, dtype=np.float64)
    m = len(p)
    order = np.argsort(p)[::-1]  # largest first
    adjusted = np.empty(m)
    running_min = 1.0
    for position, index in enumerate(order):
        rank = m - position  # 1-based rank in ascending order
        running_min = min(running_min, p[index] * m / rank)
        adjusted[index] = running_min
    return adjusted.tolist()
