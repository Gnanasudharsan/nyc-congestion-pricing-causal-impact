# ADR 0002 — Pre-register the analysis plan before estimating effects

- Status: Accepted (2026-11-09)

## Context
Congestion pricing is politically contested, and observational designs have many forking paths.
Choosing specifications after seeing estimates inflates false positives and undermines trust.

## Decision
- `docs/analysis-plan.md` (estimands, units, treated/control groups, designs, specifications,
  inference, primary vs secondary outcomes, multiple-testing approach, falsification tests) is
  committed and tagged `analysis-plan-v1` before any treatment-effect estimate is computed.
- Phase 2 descriptives may show raw trends and pre-period comparisons, but no post-period
  treated-vs-control contrasts.
- Any later change is logged in `docs/deviations.md` (date, what changed, why, whether it was
  made before or after seeing related estimates).
- Analyses not in the plan are labeled **exploratory** wherever they appear.

## Consequences
Some planned designs may turn out weak; we report that rather than swapping them silently.
