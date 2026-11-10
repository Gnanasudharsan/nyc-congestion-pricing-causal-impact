# Cordon: the causal impact of NYC congestion pricing

[![CI](https://github.com/Gnanasudharsan/nyc-congestion-pricing-causal-impact/actions/workflows/ci.yml/badge.svg)](https://github.com/Gnanasudharsan/nyc-congestion-pricing-causal-impact/actions/workflows/ci.yml)
[![Site](https://github.com/Gnanasudharsan/nyc-congestion-pricing-causal-impact/actions/workflows/pages.yml/badge.svg)](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **v1.0.0.**
> [Website](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/) ·
> [Paper (PDF)](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/paper.pdf) ·
> [All results](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/results.html)

## Question

What causal effect did New York City's Congestion Relief Zone toll (Manhattan at or below
60th Street, tolling since January 5, 2025) have on:

1. vehicle traffic and speeds;
2. transit ridership;
3. air quality;
4. the neighbourhoods just outside the zone (spillovers)?

Cordon has two aims:
- **Replicate** published headline findings ([docs/literature.md](docs/literature.md)) with
  transparent, pre-registered methods on public data.
- **Extend** them to spillovers and an exploratory equity lens for the border ring, upper
  Manhattan, and the Bronx.

New Jersey approaches could not be studied: no open Port Authority crossing data with a
pre-period was found.

## What we found

Every claim gets one label (robust, fragile, or not supported) under rules fixed before any
robustness check was run. The labelled table is on the site's
[results page](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/results.html#claim-labels)
and in [docs/results-phase5.md](docs/results-phase5.md).

- **Traffic, speeds, and nearby trips are fragile.** Taxi and ride-hail trips from the zone
  fell relative to distant zones, trip speeds in the zone rose, and trips in the surrounding
  ring fell. All are statistically clear, but none passes the robustness bar:
  - the pre-period data violate parallel trends;
  - HonestDiD breakdown values are small;
  - a placebo toll a year early "finds" a similar decline in trips.
- **Subway ridership, bus ridership, and air quality are not supported.** These designs detect
  no effect. The air-quality designs are limited by having only two usable monitors inside the
  zone.
- **No sign of displacement.** We find no evidence of traffic or pollution pushed into
  neighbouring areas, although the Bronx air-quality designs fail their fit checks and are
  descriptive only.
- **Replication.** Our re-run of a published ride-hail estimate matches it closely. Using
  distant zones as the control instead of upper Manhattan gives a larger decline.

The [paper](https://gnanasudharsan.github.io/nyc-congestion-pricing-causal-impact/paper.html)
gives the numbers with uncertainty, the alternative explanations, and the limitations.

## How the analysis was kept honest

- **Pre-registration.** [docs/analysis-plan.md](docs/analysis-plan.md) was tagged
  `analysis-plan-v1` before any treatment-effect estimate. Its one amendment
  (`analysis-plan-v1.1`) was also made before any estimate.
- **Deviations.** All 24 are logged in [docs/deviations.md](docs/deviations.md). Each is dated
  and says whether it came before or after the related estimates.
- **Methodological choices** are recorded as ADRs in [docs/adr/](docs/adr/).
- **Tested estimators.** Every estimator is unit-tested on simulated data with known effects.
  The simulations caught one design flaw in the plan (ADR 0012).
- **No hand-typed numbers.** The paper and site read every number from `results/`.

## Reproduce

Requires [uv](https://docs.astral.sh/uv/). The paper and site also need
[Quarto](https://quarto.org/) 1.11, and the PDF needs LuaLaTeX. HonestDiD and DoWhy run in
their own locked environments (`scripts/`), which uv creates on first use.

```bash
make setup         # pinned Python 3.12 environment + pre-commit hooks
make test          # unit tests
make data          # download raw data, build and validate processed panels (1-2 hours)
make analysis      # every design, check, and label -> results/ (about 2 hours)
make report        # paper (HTML + PDF) and website (set QUARTO=... if not on PATH)
make all           # data + analysis + report
```

Every raw input is recorded in [data/MANIFEST.json](data/MANIFEST.json) with its download date,
size, SHA-256, and coverage. Random seeds are fixed (`cordon.config.RANDOM_SEED`).

**Not estimated in v1** (deviation 21): T4 (MTA zonal speeds), T6 (DOT link speeds), R5
(PATH/NJ Transit), and R6 (Citi Bike).

## Repository layout

```
src/cordon/        ingest → clean → features → designs → robustness → viz
data/              raw/ interim/ processed/ (gitignored), final/ (small committed aggregates)
data/MANIFEST.json download dates, sizes, checksums, coverage
docs/              literature, confounders, analysis plan, data catalog, ADRs, deviations log
report/            Quarto paper and website
results/           tables generated by code only
scripts/           isolated, locked environments for HonestDiD and DoWhy
notebooks/         exploration only, never the source of reported results
```

## Citation

See [CITATION.cff](CITATION.cff).

## License

Code: MIT © Gnanasudharsan Ashokumar. Vendored fonts in `report/fonts/`: SIL Open Font License
(licences included).
