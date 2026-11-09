# ADR 0001 — Record decisions as ADRs

- Status: Accepted (2026-11-09)

## Context
Causal results depend on many researcher choices (control groups, windows, covariates,
inference). Undocumented choices make results hard to trust and easy to accuse of p-hacking.

## Decision
Every methodological or architectural choice gets a short ADR in `docs/adr/` before it is used
to produce a reported result. ADRs are never edited after acceptance except to mark them
superseded.

## Consequences
Reviewers can trace each number to a dated decision. Slightly more writing per phase.
