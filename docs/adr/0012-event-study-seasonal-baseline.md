# ADR 0012 — Event-study seasonal baseline

- Status: Accepted (2026-11-09, Phase 3, before any treatment-effect estimate; deviation 6)

## Context
The plan's event study (§4.1) has a treated x 4-week-bin indicator for every period except the
8-week reference window, plus unit x week-of-year and date fixed effects. Thirteen 28-day bins
span 364 days, so each bin covers almost the same calendar weeks in 2023, 2024, and 2025.

The result is that the treated group's average seasonal profile is nearly collinear with the
bin indicators. Only the reference window and a one-day annual drift separate the two.

On simulated data with a true step of −0.10, the as-written specification recovered the step on
average. But bins 13 apart shared a common error of about +0.03 (for example, bins −19 and −6,
and the post bins at the same season). That error looks like a pre-trend, and like seasonal
"dynamics" after treatment. The pooled DiD is unaffected, because its treated seasonal profile
is identified from 2023 and 2024 together.

## Decision
- **Seasonal baseline:** calendar 2023 identifies each treated unit's seasonal profile and has
  no bin indicators.
- **Indicators:** 2024 pre-period bins (including the reference bins −2 and −1), the
  anticipation window, and the post-period bins.
- **Normalisation:** coefficients are re-expressed relative to the reference window by
  subtracting the mean of bins −2 and −1. This is a linear transformation; the covariance is
  transformed with it.
- **Interpretation:**
  - A 2024 bin measures the change in the treated-minus-control gap compared with the same weeks
    of 2023, net of the same change for the reference window. This is the seasonally aligned
    pre-trend that the Phase 2 descriptives screened.
  - A post bin measures 2025 against the same weeks of 2023, net of the reference window.
- **Validation:** on the same simulated data, pre-bins are within ±0.01 of zero (SE about 0.007),
  and post bins sit at −0.10 with no seasonal pattern (`tests/test_designs.py`).
- **Monthly designs:** the same rule. 2023 is the baseline, Jan–Oct 2024 get indicators, and Sep
  and Oct 2024 are the reference.
- **Headline estimate:** still the pooled DiD, as pre-registered. The event study is for dynamics,
  pre-trend tests, and the Phase 5 HonestDiD bounds.

## Consequences
- Pre-period event-study coefficients exist only for 2024, which gives 10 daily bins, all
  relative to the reference window.
- A differential trend between 2023 and 2024 shows up directly in those bins. That is the right
  input for the HonestDiD relative-magnitudes and smoothness bounds.
- The as-written specification is not reported. Its coefficients are dominated by the
  seasonal-normalisation error described above, and the simulation evidence is in the test suite.
