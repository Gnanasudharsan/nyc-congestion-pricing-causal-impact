# ADR 0009 — Synthetic control specification

- Status: Accepted (2026-11-09, pre-registration)

## Context
Two primary outcomes have one treated aggregate and no credible within-NYC control:
- system subway ridership (R1);
- PM2.5 averaged over the CRZ monitors (A1).

Classical synthetic control (Abadie et al. 2010) requires the treated unit to lie inside the
convex hull of the donors in levels. Our donors measure on different scales: transit agencies of
different size, and regulatory monitors versus corrected low-cost sensors.

## Decision
- **Estimator:** demeaned (intercept-shifted) synthetic control. Each unit's outcome is centred
  on its own pre-period mean. Weights are non-negative and sum to 1, and are chosen to minimise
  pre-period MSE (Doudchenko & Imbens 2016; Ferman & Pinto 2021). Implemented with `pysyncon`
  where its API allows; otherwise as a documented constrained least-squares function,
  unit-tested on simulated data with a known effect.
- **Covariates:** none beyond pre-period outcome paths. This avoids specification searching
  over predictor sets.
- **Inference:** in-space placebo permutation using the post/pre RMSPE ratio
  (Abadie et al. 2010). We report the rank p-value, the number of placebos, and the minimum
  attainable p.
- **Fit diagnostic:** if pre-period RMSPE exceeds the median placebo pre-RMSPE, the estimate is
  reported as descriptive only.
- **Cross-check:** CausalPy's Bayesian synthetic control on the same data and donors, reported
  alongside.

## Consequences
The estimates are robust to level differences between donors. A small donor pool limits how
small a permutation p-value can be, and we state that limit.
