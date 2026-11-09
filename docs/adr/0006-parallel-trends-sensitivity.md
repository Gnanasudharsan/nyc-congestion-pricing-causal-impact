# ADR 0006 — Parallel-trends sensitivity (HonestDiD-style)

- Status: Accepted (2026-11-09, pre-registration)

## Context
Event-study pre-trends that are not significant do not prove parallel trends. Rambachan & Roth
(2023) bound the post-period violation relative to the largest pre-period violation (the
"relative magnitudes" restriction, M̄). A Python port exists: `honestdid` 0.1.1 on PyPI, from
<https://github.com/anzonyquispe/honestdid>, released March 2026. It has a single maintainer
and an early version number.

## Decision
- In Phase 3, `honestdid` is validated against the R package's published vignette example: the
  Medicaid-expansion event study and its relative-magnitudes confidence sets. If it reproduces
  those intervals to 2 decimal places, it is used.
- If it does not reproduce them, we implement the relative-magnitudes confidence set ourselves,
  following Rambachan & Roth (2023, §3) via the conditional/hybrid approach, and unit-test it
  against the same example. The implementation choice is logged in `docs/deviations.md` either
  way.
- For each DiD headline result we report the **breakdown M̄**: the smallest M̄ at which the 95%
  robust confidence set includes zero. A result is "robust to parallel-trends violations" only
  if its breakdown M̄ is ≥ 1, meaning post-period violations as large as the worst pre-period
  violation would not overturn it.

## Consequences
Every DiD headline carries a single, interpretable sensitivity number. The validation step costs
some time but protects against relying on an immature dependency.
