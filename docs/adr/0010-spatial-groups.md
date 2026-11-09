# ADR 0010 — Treated, spillover, and control geography

- Status: Accepted (2026-11-09, pre-registration)

## Context
Spillovers violate SUTVA when nearby areas serve as controls. Earlier work used upper Manhattan
as the control group (Pandey et al. 2026), which assumes away the question Cordon asks.

## Decision
- **Groups:** taxi zones are assigned to CRZ, border ring (centroid within 3 km of the CRZ
  geofence), upper Manhattan + Bronx, intermediate (3–8 km), and far control (> 8 km, airports
  excluded), using the rules in `docs/analysis-plan.md` §2.
- **Intermediate band:** never used as a control in primary estimates.
- **Fixed before outcomes:** the group assignment is computed from geometry alone in Phase 2 and
  committed (`data/final/zone_groups.csv`) before any outcome is joined.
- **Sensitivity of thresholds:** the 3 km and 8 km thresholds were chosen for interpretability:
  3 km is roughly a 10-minute drive in Manhattan traffic. Sensitivity to 2/4 km and 6/10 km is a
  Phase 5 check, not an alternative primary.

## Consequences
Spillover estimates have a clean comparison group. Far controls are less similar to Manhattan,
and the zone × week-of-year fixed effects and the event-study pre-trend tests address that.
