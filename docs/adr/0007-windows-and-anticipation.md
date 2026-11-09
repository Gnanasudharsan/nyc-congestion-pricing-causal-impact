# ADR 0007 — Study windows and anticipation

- Status: Accepted (2026-11-09, pre-registration)

## Context
- The program was announced for June 30, 2024, paused on June 5, 2024, revived on November 14,
  2024, and federally approved on November 21, 2024.
- 2023 is the first year without major COVID disruption in most series.
- Year two (2026) brings an MTA fare and toll increase on Jan 4, 2026 and an extreme winter.

## Decision
- **Pre-period (estimation):** 2023-01-01 to 2024-11-13.
- **Anticipation window:** 2024-11-14 to 2025-01-04. It is estimated as its own event-study bin
  and excluded from the reference period.
- **Main post-period (year 1):** 2025-01-05 to 2025-12-31. Headline estimates use this window.
- **Extended post-period:** 2026-01-01 to the latest available data. Reported as secondary, with
  an explicit level shift on 2026-01-04 for MTA fare and toll changes.
- **June 2024 pause:** a robustness check drops 2024-05-15 to 2024-07-15.
- **Reference period for event studies:** the last 8 pre-period weeks before the anticipation
  window, ending 2024-11-13.

## Consequences
The anticipation bin lets us measure early responses without contaminating the baseline. Ending
the headline window at year 1 avoids the 2026 fare and toll confounders.
