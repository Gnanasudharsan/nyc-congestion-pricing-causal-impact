# ADR 0008 — Primary outcomes and multiple testing

- Status: Accepted (2026-11-09, pre-registration)

## Decision
- A short list of **primary outcomes** is fixed in the analysis plan. Their p-values are adjusted
  with **Holm–Bonferroni** across the primary family, so the family-wise error rate is 5%.
- **Secondary outcomes** (heterogeneity cuts, alternative metrics, spillover sub-areas) are
  reported with Benjamini–Hochberg q-values within each outcome domain. They are described as
  supporting evidence, never as headline findings.
- **Exploratory** analyses carry that label and have no error-rate claim.
- We report point estimates and intervals for everything, not only the significant ones.
  Interpretation emphasises magnitude and interval width over significance stars.

## Consequences
There are few headline claims, each with honest error control.
