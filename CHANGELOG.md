# Changelog

All notable changes are documented here. Format follows Keep a Changelog; phases are tagged
`phase-N`.

## [phase-6] — 2026-11-10
### Added
- Quarto website and paper (`report/`): overview, paper (HTML + PDF), all results, methods,
  data. Every number comes from `report/_variables.yml` and every table from
  `report/_generated/`, both generated from `results/` by `cordon.viz.report_inputs`.
- Interactive event-study explorer (Altair/Vega-Lite, pinned CDN versions).
- Design-token themes, light and dark. Self-hosted Source Serif 4 and Inter Tight (SIL OFL):
  TTFs for the PDF via LuaLaTeX, subset WOFF2 for the site.
- GitHub Pages deployment (`.github/workflows/pages.yml`); the PDF is built in CI with TinyTeX.
- Lighthouse 13.5.0 scores in `results/lighthouse_scores.csv`. Desktop: performance 96–98 and
  100 in every other category. Mobile performance is 67–74, below the 90 target (ADR 0013).
- ADR 0013.

## [phase-5] — 2026-11-09
### Added
- Falsification and re-estimation checks (`cordon.robustness.checks`):
  - placebo date; placebo outcomes (Staten Island trips, Verrazzano-Narrows);
  - control-group swaps; June 2024 pause and holiday weeks dropped;
  - did2s imputation estimator; dose-response; leave-one-out donors; A1/A3 data variants.
  Pass rules were fixed before any check ran (deviation 18).
- HonestDiD relative-magnitudes bounds for every DiD with ≥ 30 clusters. Smoothness bounds for
  T2 and R2 (amendment 1). DoWhy refuters for T2 and A3.
- Claim labels (`cordon.robustness.labels`, `results/claims.csv`) with BH families for the
  secondary outcomes. Generated `docs/results-phase5.md` and a HonestDiD figure.
- Deviations 18–24.
### Changed
- DoWhy runs in an isolated, locked environment: 0.12 fails under pandas 3, and 0.14 needs an
  older SciPy (deviation 24). HonestDiD results are cached by input.
### Fixed
- The A1 donor-completeness check now measures completeness over the panel's weeks.

## [phase-4] — 2026-11-09
### Added
- Spillover outcomes S2 (randomization inference over 56 assignments), S3, S4, S5, A2
  (synthetic control), and A2b (weather-adjusted NO2 DiD). BH q-values across the spillover
  family (`results/spillover_bh.csv`).
- Heterogeneity cuts (`cordon.designs.heterogeneity`): peak vs overnight, weekday vs weekend,
  vehicle class, borough. Stacked regressions with level-specific fixed effects give a valid SE
  for each difference; BH within each cut.
- Equity inputs: ACS 2019–2023 tract tables (keyless summary files), TIGER 2023 tracts, and EH
  Data Portal adult asthma ED rates by NTA at a pinned commit. Allocated to taxi zones by area
  (`data/final/zone_equity.csv`).
- Zone-level S1/S3 effects with placebo-based noise and DerSimonian–Laird empirical-Bayes
  shrinkage, plus exploratory population-weighted associations (`cordon.designs.zone_effects`).
- Generated `docs/results-phase4.md` and Phase 4 figures. Deviations 12–17, logged before
  estimation.
- Tests for the stacked heterogeneity design and the shrinkage.

## [phase-3] — 2026-11-09
### Added
- `cordon.designs`:
  - fixed-effect demeaning;
  - pooled DiD and event study with pre-fitted adjustments (unit trends, weather);
  - cluster-robust SEs that match `pyfixest`;
  - restricted wild cluster bootstrap-t (Webb weights; every replication re-estimates the
    adjustment);
  - randomization inference, demeaned synthetic control (exact NNLS weights) with placebo
    inference, and Holm/BH.
- Estimators unit-tested on simulated data with known effects (`tests/test_designs.py`).
- Phase 3 run (`make analysis`):
  - six primary outcomes with Holm adjustment;
  - non-spillover secondaries T5, R2, R3, R4, A3, A4;
  - detrended specification everywhere, anticipation and 2026 windows;
  - pre-trend tests.
  Writes `results/*.csv` and the generated `docs/results-phase3.md`.
- Replication of Pandey, Guler & Gayah (2026). CausalPy Bayesian synthetic-control
  cross-check. Fitted-synthetic-control MDEs (deviation 2 follow-up).
- HonestDiD port validated against the R reference: 20/20 interval endpoints to 2 dp. It runs in
  an isolated, locked environment.
- ADR 0012 and deviations 6–11. Each was logged before the estimate it affects.
### Changed
- Analysis plan amendment 1 (tag `analysis-plan-v1.1`): adds a pre-period-detrended secondary
  specification for every design, with a stricter claim rule for T2, R4, A1, A3 and R2
  (ADR 0011, deviation 5). Made before any treatment-effect estimate.
- Panel builders moved to `cordon.designs.panels`. CI installs the `causal` group.

## [phase-2] — 2026-11-09
### Added
- Spatial groups for every taxi zone (`data/final/zone_groups.csv`), committed before any outcome
  was joined (ADR 0010).
- Covariates: calendar with study periods and event bins, DST-correct daily weather, NOAA HMS
  smoke days.
- Processed panels: B&T facility-day, TLC zone-day (135 monthly files, each checksummed in the
  manifest), NTD agency-mode-month, air site-day (NYCCAS plus AQS NYC and donor monitors),
  subway station-day, CBD bus route-month.
- `make data`, `make validate` (data tests for every panel), and `make descriptives`.
- Pre-trend figures for every planned comparison (pre-period only), citywide before/after
  trends, seasonality, and pre-period MDEs. All of it is summarised in the generated
  `docs/descriptives.md`.
- Deviations 1–4 logged in `docs/deviations.md`.
### Fixed
- Open-Meteo local-time output ignores DST; weather is now requested in UTC and converted.
- TLC remote reads tripped CDN rate limits; files are now downloaded whole, aggregated, then
  deleted.
- Subway ridership is fetched one day at a time (week and month queries hit server timeouts).
  The Roosevelt Island Tram (`TRAM1`, `TRAM2`) is dropped from the subway panel.

## [phase-1] — 2026-11-09
### Added
- Dataset registry (`config/datasets.yaml`) and audit runner (`python -m cordon.ingest.audit`)
  that profiles every candidate source and writes `data/catalog/profiles.json`.
- Source clients: Socrata (server-side coverage and level queries, retries, probe mode for very
  large tables), TLC parquet via DuckDB, EPA AQS hourly files, NYCCAS real-time PM2.5 at a
  pinned commit, NTD monthly ridership, Citi Bike, Open-Meteo.
- Resumable, size-verified downloads (`cordon.ingest.download`).
- `docs/data-catalog.md` with a coverage table generated from the profiles.
- `docs/analysis-plan.md`, the pre-registration (tag `analysis-plan-v1`), and ADRs 0005–0010.
### Changed
- `docs/literature.md`: findings and specifications from full-text reading of five key sources.
### Findings from the audit
- No regulatory hourly PM2.5 monitor with a pre-period inside the CRZ, and no NO2 monitor in
  Manhattan. The zone air-quality outcome uses the NYCCAS real-time network; NO2 is analysed
  only as a Bronx spillover outcome.
- MTA CRZ Vehicle Entries begins on the treatment date (descriptive only).

## [phase-0] — 2026-11-09
### Added
- Repository layout (`src/cordon/{ingest,clean,features,designs,robustness,viz}`), uv-pinned
  Python 3.12 environment with core, dev, and causal dependency groups.
- `cordon.config` (treatment timing, time zone, paths, seed) and `cordon.manifest`
  (SHA-256 provenance records), with unit tests.
- Makefile (`setup data analysis report all test lint format clean`), ruff, mypy (strict),
  pytest, pre-commit, GitHub Actions CI with a committed-data size guard.
- `CLAUDE.md` working agreement, ADRs 0001–0004, `docs/deviations.md`.
- `docs/literature.md` (existing evidence and the gap) and `docs/confounders.md`
  (first draft of the concurrent-events timeline).
