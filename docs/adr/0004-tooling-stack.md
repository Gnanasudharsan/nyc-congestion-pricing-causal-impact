# ADR 0004 — Tooling stack and dependency groups

- Status: Accepted (2026-11-09)

## Context
The project must be free, reproducible on a Mac, and fast in CI. Bayesian and causal libraries
(CausalPy → PyMC) are heavy.

## Decision
- Python 3.12 with uv; all versions pinned in `uv.lock`.
- Dependency groups: core (`duckdb`, `polars`, `pandas`, `statsmodels`, `linearmodels`, plotting),
  `dev` (ruff, mypy, pytest, pre-commit), `causal` (`causalpy`, `pysyncon`, `dowhy`, `pyfixest`,
  `wildboottest`). CI lint/test installs core + dev; jobs that run designs install `causal` too.
- `pyfixest` is the default for fixed-effects DiD, event studies, and heterogeneity-robust
  estimators (e.g., did2s, local projections) because it supports clustered SEs and wild cluster
  bootstrap in one API; `linearmodels` is a cross-check.
- The HonestDiD-style sensitivity implementation is decided in Phase 3/5 (separate ADR) after
  checking whether a maintained Python port exists.

## Consequences
Two-stage install in CI. Estimator choices still get their own ADRs before use.
