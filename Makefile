# Cordon build entry points. `make all` rebuilds everything from raw downloads.
# Stages are filled in phase by phase; unimplemented stages say so and exit 0.

.PHONY: help setup data analysis report all test lint format typecheck clean

UV ?= uv
RUN = $(UV) run

help:  ## List targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup:  ## Create the pinned environment (core + dev + causal) and install git hooks
	$(UV) sync --all-groups
	$(RUN) pre-commit install

data:  ## Download raw data, update data/MANIFEST.json, build processed panels
	@echo "make data: ingest pipeline arrives in Phase 1-2 (not yet implemented)."

analysis: data  ## Run every pre-registered design and write results/
	@echo "make analysis: designs arrive in Phase 3-5 (not yet implemented)."

report: analysis  ## Render the Quarto paper (PDF) and website
	@echo "make report: Quarto paper and site arrive in Phase 6 (not yet implemented)."

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
