# Architecture and methods decision records

One file per decision: `NNNN-short-title.md`, with Status, Context, Decision, Consequences.
Methodological choices (estimators, control groups, windows, inference) get an ADR before they
are used for results. Superseded ADRs stay in place and link to their replacement.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-decisions.md) | Record decisions as ADRs | Accepted |
| [0002](0002-preregistration.md) | Pre-register the analysis plan before estimating effects | Accepted |
| [0003](0003-treatment-timing-and-timezone.md) | Treatment timing and time zone conventions | Accepted |
| [0004](0004-tooling-stack.md) | Tooling stack and dependency groups | Accepted |
| [0005](0005-did-estimator-and-inference.md) | DiD estimator and inference | Accepted |
| [0006](0006-parallel-trends-sensitivity.md) | Parallel-trends sensitivity (HonestDiD-style) | Accepted |
| [0007](0007-windows-and-anticipation.md) | Study windows and anticipation | Accepted |
| [0008](0008-multiple-testing.md) | Primary outcomes and multiple testing | Accepted |
| [0009](0009-synthetic-control.md) | Synthetic control specification | Accepted |
| [0010](0010-spatial-groups.md) | Treated, spillover, and control geography | Accepted |
| [0011](0011-detrended-secondary-specification.md) | Pre-period-detrended secondary specification | Accepted |
| [0012](0012-event-study-seasonal-baseline.md) | Event-study seasonal baseline | Accepted |
| [0013](0013-publishing.md) | Publishing the paper and website | Accepted |
