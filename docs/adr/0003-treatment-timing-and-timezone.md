# ADR 0003 — Treatment timing and time zone conventions

- Status: Accepted (2026-11-09)

## Context
Sources report timestamps in different conventions (local time, UTC, floating local time).
DST transitions create duplicate or missing hours. Off-by-hours errors near the treatment date
would contaminate the first post-period day.

## Decision
- Treatment start is `2025-01-05 00:00 America/New_York`, defined once in `cordon.config`.
- All timestamps are converted to time zone-aware `America/New_York` during cleaning. Naive
  timestamps are rejected by helper functions rather than silently assumed.
- Daily aggregates use local calendar days. Hourly panels keep a UTC key alongside local time
  so DST fall-back hours stay unique.
- Placebo date for robustness: `2024-01-07` (the same weekday one year earlier).

## Consequences
Every ingest module must declare the source's time convention, and tests cover the boundary.
