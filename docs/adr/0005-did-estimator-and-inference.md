# ADR 0005 — DiD estimator and inference

- Status: Accepted (2026-11-09, pre-registration)

## Context
Every unit that the toll treats is treated on the same date: 2025-01-05. The well-known biases
of two-way fixed effects (TWFE) come from *staggered* adoption, where already-treated units
end up serving as controls for later-treated ones, and from heterogeneous effects over time.
Neither arises with a single treatment date and never-treated controls. Some designs, though,
have few clusters (e.g., about 9 MTA bridge and tunnel facilities).

## Decision
- **Estimator:** TWFE DiD and dynamic event studies with unit and date fixed effects, fit with
  `pyfixest` and cross-checked with `linearmodels` on the primary specification. With a single
  treatment date, TWFE equals the canonical 2×2 DiD averaged over periods. A
  heterogeneity-robust estimator (`pyfixest` `did2s`) is reported as a robustness check, not as
  the primary estimator.
- **Seasonality:** unit × week-of-year fixed effects, identified from the two pre-period years
  (2023, 2024). This compares each unit to itself in the same calendar week, as the analysis
  plan's "same-week-prior-year alignment" requires.
- **Inference:**
  - Primary: cluster-robust SEs at the unit level when there are ≥ 30 clusters.
  - With fewer than 30 clusters: wild cluster bootstrap (Webb 6-point weights, 9,999 draws,
    `wildboottest`/`pyfixest`) and randomization inference over the assignment of treated status
    among comparable units.
  - Serial correlation: event-study coefficients use the same clustering. The time-series
    designs use HAC (Newey-West) SEs with bandwidth chosen by the Newey-West (1994) rule.
- **Reported quantity:** effects on log outcomes, reported as percentage changes
  (100 × (exp(β) − 1)) with 95% intervals transformed the same way.

## Consequences
Simple, interview-explainable estimators. The heterogeneity-robust check guards against
mis-specification, and few-cluster inference is conservative by design.
