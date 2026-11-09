# Changelog

All notable changes are documented here. Format follows Keep a Changelog; phases are tagged
`phase-N`.

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
