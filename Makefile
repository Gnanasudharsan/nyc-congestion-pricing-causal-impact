# Cordon build entry points. `make all` rebuilds everything from raw downloads.
# Stages are filled in phase by phase; unimplemented stages say so and exit 0.

.PHONY: help setup audit catalog data validate descriptives analysis report lighthouse all test lint format typecheck clean

UV ?= uv
RUN = $(UV) run

help:  ## List targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup:  ## Create the pinned environment (core + dev + causal) and install git hooks
	$(UV) sync --all-groups
	$(RUN) pre-commit install

audit:  ## Profile every candidate dataset (coverage, rows); downloads small tables, EPA, NYCCAS, weather
	$(RUN) python -m cordon.ingest.audit
	$(RUN) python -m cordon.ingest.catalog

catalog:  ## Regenerate the coverage table in docs/data-catalog.md from data/catalog/profiles.json
	$(RUN) python -m cordon.ingest.catalog

data:  ## Download raw data (audit), build features and processed panels, run data tests
	$(RUN) python -m cordon.ingest.audit
	$(RUN) python -m cordon.ingest.catalog
	$(RUN) python -m cordon.features.geography
	$(RUN) python -m cordon.features.build
	$(RUN) python -m cordon.clean.bt
	$(RUN) python -m cordon.clean.tlc
	$(RUN) python -m cordon.clean.ntd
	$(RUN) python -m cordon.clean.air
	$(RUN) python -m cordon.clean.subway
	$(RUN) python -m cordon.clean.bus
	$(RUN) python -m cordon.ingest.equity
	$(RUN) python -m cordon.features.equity
	$(MAKE) validate

validate:  ## Run data tests on every processed panel (writes data/catalog/validation.json)
	$(RUN) python -m cordon.clean.validate

descriptives:  ## Phase 2 figures, pre-period MDEs, and docs/descriptives.md (no effect estimates)
	$(RUN) python -m cordon.viz.descriptive
	$(RUN) python -m cordon.robustness.mde
	$(RUN) python -m cordon.viz.descriptives_page

analysis: descriptives  ## Run every pre-registered design and write results/ (about 2 hours)
	$(RUN) python -m cordon.robustness.honest
	$(RUN) python -m cordon.designs.run
	$(RUN) python -m cordon.designs.replication
	$(RUN) python -m cordon.designs.bayesian_sc
	$(RUN) python -m cordon.designs.heterogeneity
	$(RUN) python -m cordon.designs.zone_effects
	$(RUN) python -m cordon.robustness.checks
	$(RUN) python -m cordon.robustness.labels
	$(RUN) python -m cordon.viz.estimates
	$(RUN) python -m cordon.designs.results_page

QUARTO ?= quarto

report:  ## Paper (HTML + PDF) and website from results/ (needs Quarto; PDF needs LuaLaTeX)
	$(RUN) python -m cordon.viz.report_inputs
	$(RUN) python -m cordon.viz.site_charts
	$(RUN) python -m cordon.viz.webfonts
	cd report && $(QUARTO) render

lighthouse:  ## Audit the live site with Lighthouse -> results/lighthouse_scores.csv (needs Node + Chrome)
	$(RUN) python -m cordon.viz.lighthouse

all: data analysis report  ## Full rebuild from raw downloads

test:  ## Run unit tests (network tests excluded)
	$(RUN) pytest -m "not network"

lint:  ## Ruff lint + format check + mypy
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) mypy

format:  ## Auto-format code
	$(RUN) ruff format .
	$(RUN) ruff check --fix .

clean:  ## Remove generated (not raw) artifacts
	rm -rf data/interim/* data/processed/* .pytest_cache .mypy_cache .ruff_cache
	touch data/interim/.gitkeep data/processed/.gitkeep
