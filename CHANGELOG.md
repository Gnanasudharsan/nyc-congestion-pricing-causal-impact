# Changelog

All notable changes are documented here. Format follows Keep a Changelog; phases are tagged
`phase-N`.

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
