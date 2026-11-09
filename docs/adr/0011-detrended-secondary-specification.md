# ADR 0011 — Pre-period-detrended secondary specification

- Status: Accepted (2026-11-09, plan amendment 1, before any treatment-effect estimate)

## Context
The Phase 2 pre-trend screen ([descriptives.md](../descriptives.md)) compared each 2024 week
with the same week of 2023. For several outcomes the treated-minus-control gap had drifted
before tolling began:

| Outcome | Seasonally aligned gap, mean (SD) |
|---|---|
| T2 | −7.7 (3.7) log pts |
| R4 | +5.3 (2.3) log pts |
| A3 | −2.7 (2.2) µg/m³ |
| A1 | −2.7 (4.0) µg/m³ |
| R2 | +6.0 (7.4) log pts |

If a drift like this continues after 2025-01-05, the primary specification
([ADR 0005](0005-did-estimator-and-inference.md),
[ADR 0009](0009-synthetic-control.md)) attributes it to the policy. The planned HonestDiD
relative-magnitudes bound ([ADR 0006](0006-parallel-trends-sensitivity.md)) covers violations
up to M̄ times the worst pre-period violation. It does not specifically model a steady linear
drift.

## Decision
1. **The primary specification does not change.** The detrended version is secondary and is
   reported next to it, never in place of it.
2. **It applies to every DiD and synthetic-control outcome**, primary and secondary, not only
   the five above. Running it everywhere avoids choosing outcomes after looking at pre-trends.
   The plan commits in advance to discussing the five flagged outcomes.
3. **DiD detrending:**
   - For each unit, fit a linear time trend on pre-period data only: 2023-01-01 to 2024-11-13,
     excluding the anticipation window. The fit uses the same unit x week-of-year and date fixed
     effects as the primary specification.
   - Subtract the extrapolated trend from that unit's outcome for every date.
   - Run the primary event study on the detrended outcome.
   - We do **not** add unit trends to a regression on the full sample. There, post-period
     effects would bend the estimated trend (Wolfers 2006; Borusyak, Jaravel & Spiess 2024).
4. **Synthetic-control detrending:**
   - Detrend every unit's series, treated and donors alike, with a linear trend fitted on its
     own pre-period.
   - Fit the demeaned synthetic control (ADR 0009) on the detrended series.
   - Run the placebos in space through the identical pipeline.
5. **Inference:**
   - Wild cluster bootstrap: each replication re-estimates the trend, so uncertainty in the
     trend carries into the confidence interval.
   - Randomization inference: each permutation re-runs the whole two-step procedure.
6. **Extrapolation horizon:**
   - Linear extrapolation gets less reliable the further it runs.
   - The headline detrended estimate is post year 1 (2025) only.
   - Estimates for 2026 are reported but labelled as depending more heavily on the
     extrapolation.
   - Event-study paths are always shown, so readers can see whether the treated-minus-control
     difference grows with time since tolling.
7. **HonestDiD smoothness bound:**
   - For the flagged DiD outcomes, Phase 5 also reports the smoothness-restriction bound
     (Δ^SD, Rambachan & Roth 2023). With M = 0, that bound is the same as extrapolating a
     linear trend; larger M allows the trend to bend.
   - Before use, it must reproduce the R vignette, under the same validation rule as ADR 0006.
   - If the `honestdid` port cannot reproduce it, we say so in `docs/deviations.md` and report
     only the detrended estimate.
8. **Decision rule** (tightens §8 of the analysis plan):
   - A flagged outcome is labelled **robust** only if the detrended estimate has the same sign
     as the primary estimate and its 95% CI excludes zero. Primary outcomes use the
     Holm-adjusted CI.
   - If the two specifications disagree, the claim is **fragile** and both are reported.
   - For the unflagged outcomes, the detrended estimate is informational.

## Consequences
- Conclusions that depend only on a pre-existing drift become visible.
- Cost 1: unit-specific linear extrapolation can remove part of a real effect if the effect
  ramps up gradually.
- Cost 2: it can produce artefacts if the pre-period drift was temporary. One example is the
  2024 recovery of subway stations in the zone, which may have levelled off.
- Both readings are discussed in the write-up. Neither specification is preferred after seeing
  results.
