# Pre-analysis plan (v1)

- **Status:** pre-registered. This document is committed and tagged `analysis-plan-v1`
  before any treatment-effect estimate is computed. Every later change is logged in
  [deviations.md](deviations.md).
- **Author:** Gnanasudharsan Ashokumar. **Date:** 2026-11-09.
- **Data basis:** the Phase 1 audit ([data-catalog.md](data-catalog.md),
  `data/catalog/profiles.json`). No outcome has been compared between treated and control units
  after the treatment date. The audit looked at coverage, row counts, and category levels only.
- **Method choices:** recorded as ADRs 0005–0010 in [adr/](adr/).

## 1. Policy and treatment

- **Treatment:** Congestion Relief Zone (CRZ) tolling, Manhattan at or below 60th St (excluding
  the FDR Drive, West Side Highway/Route 9A, and the Hugh L. Carey Tunnel connections to West
  St), starting **2025-01-05 00:00 America/New_York**.
- **Base toll:** $9 for E-ZPass passenger vehicles during peak hours (weekdays 5am–9pm, weekends
  9am–9pm), 75% off overnight.
- **Crossing credits:** at the Lincoln, Holland, Hugh L. Carey, and Queens-Midtown tunnels.
- **Per-trip surcharges:** $0.75 for taxis and $1.50 for high-volume for-hire vehicles (FHVHV),
  on trips that start, end, or pass within the zone.
- **Timing:** every treated unit is treated on the same date (no staggered adoption).

**Windows** ([ADR 0007](adr/0007-windows-and-anticipation.md)):

| Window | Dates | Use |
|---|---|---|
| Pre-period | 2023-01-01 to 2024-11-13 | estimation baseline |
| Reference bin for event studies | 2024-09-19 to 2024-11-13 (8 weeks) | omitted category |
| Anticipation | 2024-11-14 to 2025-01-04 | own bin; excluded from baseline |
| Post, year 1 (**headline**) | 2025-01-05 to 2025-12-31 | primary estimates |
| Post, extended | 2026-01-01 to latest data | secondary; level shift at 2026-01-04 for MTA fare and toll changes |

Monthly-frequency designs use a pre-period of Jan 2023 – Oct 2024, an anticipation bin of
Nov – Dec 2024, and a post-period of Jan – Dec 2025.

## 2. Geography of treatment, spillover, and control

Areas are built in Phase 2 from these pre-registered rules. The resulting lists are committed
before any outcome is merged in.

| Group | Taxi-zone rule | Role |
|---|---|---|
| **CRZ** | Taxi zones in MTA's CBD taxi-zone list (`yfdc-w5jh`) | Treated |
| **Border ring** | Non-CRZ zones whose centroid lies within 3 km of the CRZ geofence (`srxy-5nxn`) | Spillover |
| **Upper Manhattan + Bronx** | Remaining Manhattan zones north of the ring, plus all Bronx zones | Spillover |
| **Intermediate** | Zones with centroid 3–8 km from the CRZ that are not in the groups above | Reported, never a control |
| **Far control** | Zones with centroid > 8 km from the CRZ, excluding airports (zones 1, 132, 138) | Control |

The intermediate band is never a control. That keeps nearby areas, where spillovers are most
likely, out of the comparison group. This is the central difference from earlier work that used
upper Manhattan as a control (Pandey et al. 2026).

## 3. Outcomes

### 3.1 Primary outcomes (Holm-adjusted family, [ADR 0008](adr/0008-multiple-testing.md))

| ID | Outcome | Data | Unit × time | Design |
|---|---|---|---|---|
| **T1** | Vehicle crossings at MTA tunnels feeding the CRZ | B&T Hourly Crossings `ebfx-2m7v` | facility × day | DiD/event study |
| **T2** | Taxi + FHV trips originating in the CRZ | TLC trip records (yellow, green, FHVHV) | taxi zone × day | DiD/event study |
| **T3** | Travel speed of taxi + FHV trips within the CRZ | TLC trip records | taxi zone × day | DiD/event study |
| **R1** | Subway ridership (system) | NTD Complete Monthly Ridership `8bui-9xvu` | agency-mode × month | Synthetic control |
| **A1** | PM2.5 at CRZ monitors | NYCCAS real-time network (GitHub, pinned commit) | site group × week | Synthetic control |
| **S1** | Taxi + FHV trips in the border ring (both trip ends outside the CRZ) | TLC trip records | taxi zone × day | DiD/event study |

All six tests are two-sided. Signs are not pre-committed, because spillovers could plausibly go
either way.

### 3.2 Secondary outcomes (BH q-values within each domain)

| ID | Outcome | Data | Design |
|---|---|---|---|
| T4 | MTA CBD taxi/FHV zonal speed (CBD vs CBD-adjacent vs Greater NYC), monthly, to Aug 2025 | `6p29-6xqn` | DiD, 3 units (descriptive inference only) |
| T5 | Taxi/FHV trips by service type (yellow, FHVHV separately); shared-ride requests | TLC | as T2 |
| T6 | Highway link speeds on CRZ approaches and spillover corridors | DOT Traffic Speeds `i4gi-tjb9` | DiD on link × day |
| R2 | Station entries, CRZ vs non-CRZ stations | Subway Hourly Ridership `wujg-7c2s` + `5wq4-mkjj` | DiD; biased toward zero by design (see §6) |
| R3 | Bus speeds, CBD vs non-CBD routes | CBD Bus Speeds `r6db-kkzj` | DiD on route × month |
| R4 | MTA bus ridership (system) | NTD | Synthetic control |
| R5 | PATH and NJ Transit ridership | Regional Transit Ridership `sv2g-g4mz` | ITS with seasonal terms |
| R6 | Citi Bike trips starting in the CRZ | Citi Bike trip archives | DiD on zone × day |
| A2 | NO2 at the South Bronx spillover monitor (no Manhattan NO2 monitor exists) | EPA AQS hourly `42602` | Synthetic control + DiD (§5.3) |
| A3 | PM2.5, within-NYC meteorology-adjusted DiD (CRZ sites vs far NYC sites) | NYCCAS + AQS | DiD |
| A4 | Daily-maximum PM2.5 (the Fraser et al. metric) | NYCCAS | as A1 |
| S2 | Crossings at spillover facilities (RFK Manhattan and Bronx plazas, Henry Hudson Bridge) | B&T | DiD vs control facilities |
| S3 | Taxi + FHV trips in upper Manhattan + Bronx | TLC | as S1 |
| S4 | Taxi + FHV speeds within the border ring | TLC | as T3 |
| S5 | PM2.5 at the Cross Bronx Expwy monitor (the only spillover site meeting the 75% rule; 83%) | NYCCAS | as A1 |

### 3.3 Exploratory (no error-rate claim)

- PM2.5 at sites below the 75% completeness rule: Hunts Point, which has no 2024 data, plus
  Mott Haven, Hamilton Bridge, BQE, Van Wyck, and SI Expwy.
- CRZ vehicle entries by detection point. The source `t6yz-b64h` begins 2025-01-05, so it is
  **descriptive post-period only**.
- CBD vehicle miles traveled (`jbxx-kxff`, starts Jan 2024, 12 months of pre-period). Monthly
  descriptive comparison only.
- NJ approaches: no public pre-period traffic data were found for the Port Authority Hudson
  crossings. Phase 2 checks the Port Authority's published monthly traffic reports. If none
  exist, NJ spillovers are covered only through TLC trips to and from Newark-area zones and PATH
  ridership, and the gap is stated as a limitation.
- Phase 4 equity lens (§9).

## 4. Traffic designs (T1–T3, S1–S4)

### 4.1 T1 — crossings at CRZ-feeding facilities

**Facility groups.** Fixed in advance, from the facility list in the audit:

| Group | Facilities |
|---|---|
| Treated | Hugh L. Carey Tunnel, Queens-Midtown Tunnel (both open directly into the CRZ) |
| Spillover (S2) | Robert F. Kennedy Bridge Manhattan plaza, RFK Bronx plaza, Henry Hudson Bridge |
| Control | Throgs Neck, Bronx-Whitestone, Verrazzano-Narrows, Cross Bay, Marine Parkway |

- **Outcome:** log daily crossings, all vehicle classes and directions. Vehicle class is a Phase 4
  heterogeneity cut.
- **Specification:**

  `log(Y_fd) = Σ_k β_k · 1[d ∈ bin k] · Treated_f + α_f × week-of-year + γ_d + ε_fd`

  The event study uses 4-week bins. The pooled DiD replaces the bins with a single
  `Post_d × Treated_f` term. Spillover facilities are excluded from T1's estimation sample.
- **Inference:** randomization inference over all C(7,2) = 21 assignments of "treated" to 2 of
  the 7 non-spillover facilities. The smallest attainable p-value is 1/21 ≈ 0.048, and we say so.
  A wild cluster bootstrap is reported too, with the caveat that it over-rejects when there are
  only 2 treated clusters (MacKinnon & Webb 2018).
- **Concurrent events:**
  - The same-day Port Authority toll increase does not apply to MTA facilities, so it is not a
    confounder here.
  - The Jan 2026 MTA toll increase applies to all facilities and falls outside the headline
    window.

### 4.2 T2, S1, S3 — taxi and FHV trip counts

- **Data:** TLC yellow, green, and FHVHV trip records, 2023-01 onward. We read only these
  columns: pickup/dropoff time, pickup/dropoff zone, distance, duration (FHVHV `trip_time`),
  shared-request flags, and `cbd_congestion_fee` (2025+, used only for validation).
- **Outcome:** log(1 + daily trips) by pickup zone.
  - For CRZ zones: all pickups in the zone.
  - For every non-CRZ zone: only trips with **both ends outside the CRZ**, so control and
    spillover counts are not mechanically treated by the trip fee.
- **Specification:** as T1, with zone × week-of-year and date fixed effects. T2 compares CRZ with
  far control. S1 compares the border ring with far control. S3 compares upper Manhattan +
  Bronx with far control. Each pair is estimated separately.
- **Inference:** SEs clustered by taxi zone. A wild cluster bootstrap (9,999 draws) is reported
  as a check.
- **Replication step:** before running our own specification, reproduce Pandey, Guler & Gayah
  (2026) exactly:
  - FHVHV pickups, weekdays only;
  - weeks 1–14 of 2025 vs 2024;
  - Manhattan control zones north of 60th St, counting only trips that do not go to the CBD;
  - pooled 2×2 regression, SEs clustered by zone;
  - target β = −0.0613 (SE 0.0157).

  We report our replicated estimate next to theirs, then show how the result changes when
  upper Manhattan is reclassified as a spillover area.

### 4.3 T3, S4 — speeds

- **Outcome:** log daily distance-weighted speed, computed as Σ miles / Σ hours over trips whose
  pickup and dropoff are both in the same group (CRZ-internal, ring-internal, far-internal).
  Speeds are computed separately by pickup zone and restricted to peak toll hours.
- **Trip filters** (documented in Phase 2):
  - duration 1–180 minutes;
  - distance > 0 and ≤ 50 miles;
  - implied speed 0.5–60 mph;
  - pickup and dropoff zone known.
- **Specification and inference:** as T2.
- **Comparison with prior work:** Cook et al. (2026) find CBD road-segment speeds +11% using
  Google Maps data. TLC trip speeds measure a different quantity: door-to-door trip speed,
  including stops. We expect to agree on direction, not on magnitude.

## 5. Transit and air designs

### 5.1 R1 — subway ridership synthetic control

- **Treated unit:** MTA New York City Transit, heavy rail (NTD mode HR).
- **Donor pool:** heavy-rail and light-rail modes of US agencies with ≥ 1 million monthly
  unlinked passenger trips in 2019, **excluding agencies in the New York–Newark urbanized area**
  (PATH, NJ Transit, LIRR, Metro-North), which could themselves be affected.
- **Outcome:** log monthly unlinked passenger trips (UPT), each unit demeaned by its own
  pre-period mean. Demeaning allows level differences
  ([ADR 0009](adr/0009-synthetic-control.md)).
- **Pre-period fit:** Jan 2023 – Oct 2024 (22 months). We report pre-period RMSPE.
- **Inference:** in-space placebos, with each donor treated as if it were treated. The p-value is
  the rank of the treated unit's post/pre RMSPE ratio. Leave-one-out donors is a Phase 5 check.
- **Interpretation caveat:** RTO mandates (Amazon, JPMorgan, federal) also raised ridership in
  donor cities. NYC-specific RTO intensity is not differenced out, and any residual inflates the
  transit estimate.

### 5.2 A1 — PM2.5 at CRZ monitors

- **Site completeness rule.** A site is a *core* site if at least 75% of pre-period weeks
  (2023-01-01 to 2024-11-13; 98 weeks) are valid. A valid week has at least 5 valid local days,
  and a valid day has at least 18 valid hours.
  - The 75% threshold was set during the Phase 1 audit, after looking at per-site *data
    availability* (counts of valid hours) and before looking at any PM2.5 values.
  - Availability by site is listed in [data-catalog.md](data-catalog.md).
- **Treated sites (core CRZ):** Broadway/35th St (92% of pre-period weeks valid) and Manhattan
  Bridge / Canal St (81%).
  - **Only two treated monitors meet the rule. This is a major limitation of A1 and is stated
    with every A1 estimate.**
  - The other CRZ sites are Williamsburg Bridge / Delancey St (53%), FDR / E 10th St (38%), and
    Midtown-DOT / W 39th St (21%). They enter a Phase 5 robustness check that uses all five CRZ
    sites.
  - Queensboro Bridge (E 60th St, 80%) sits on the boundary. It is excluded from A1 and
    reported on its own.
- **Treated series:** for each week, the mean of the available core sites' site-demeaned weekly
  values. A week counts only if both core sites are valid; it is dropped otherwise.
- **Outcome:** weekly mean of daily-mean PM2.5 (µg/m³), averaged across the treated sites.
  - A local day counts only if it has ≥ 18 valid hours. A week counts only if it has ≥ 5 valid
    days.
  - Hourly values below −5 or above 500 µg/m³ are dropped.
  - NYCCAS timestamps are UTC hour-beginning. They are converted to local time before daily
    aggregation.
- **Smoke-day rule:** days when NOAA HMS medium or heavy smoke polygons cover New York County
  are excluded from every unit in the primary analysis and included in a robustness check.
- **Donor pool:**
  - AQS hourly PM2.5 (parameter 88101) monitors in DE, MD, DC, VA, PA, NJ, CT, RI, and MA.
  - Each donor must be > 80 km from Columbus Circle, outside the New York–Newark–Jersey City
    CBSA, and ≥ 90% complete (in valid days) in the pre-period.
  - These donors share the regional airshed, weather, and smoke episodes with NYC but are not
    plausibly affected by the toll.
- **Estimator:** demeaned synthetic control (non-negative weights summing to 1, plus an
  intercept), fit on pre-period weeks.
- **Inference:** in-space placebos (RMSPE-ratio rank) and leave-one-out donors (Phase 5).
- **Measurement caveat:** NYCCAS sensors are DustTrak instruments corrected to match regulatory
  monitors. Donors are regulatory FEM/FRM monitors. The intercept absorbs level differences, but
  differences in sensor noise remain.
- **A3 — within-NYC, meteorology-adjusted DiD:**
  - Treated: the same two core CRZ sites.
  - Comparison: far NYC sites with hourly pre-period data: Queens College (NYCCAS, 80% valid
    pre-period weeks) and AQS Queens College 2 (36-081-0124).
  - AQS Fresh Kills (36-085-0111) has no hourly data before 2025 and is not used. Queens
    College Near Road (36-081-0125) starts in 2024 and enters only as a Phase 5 check.
  - Specification: site-day DiD with site × week-of-year FE, date FE, and group-specific slopes
    on temperature, relative humidity, wind speed, wind direction (8 sectors), precipitation, and
    boundary-layer height, all from Open-Meteo hourly reanalysis averaged to days. The weather
    slopes are estimated on the pre-period only, so they can't absorb the post-period effect.
  - Inference: wild cluster bootstrap by site, plus randomization inference.
- **A4:** daily-maximum PM2.5, to compare directly with Fraser et al. (2025) and DOHMH (2026).
  Those sources report −3.05 µg/m³ (−22%) and −0.29 µg/m³ (95% CI −3.01 to 2.42) respectively.

### 5.3 A2 — NO2 (spillover only; secondary)

**What the audit found.** EPA's AQS monitor registry (Phase 1 audit) lists **no NO2 monitor in
Manhattan**. The NYC NO2 monitors active through 2026 are:
- IS 52 (36-005-0110), in the South Bronx near the Major Deegan and Bruckner expressways;
- Pfizer Lab (36-005-0133), in the Bronx;
- Queens College 2 (36-081-0124);
- Queens College Near Road (36-081-0125), beside the Long Island Expressway.

DOHMH measures NO2 inside the CRZ with NYCCAS integrated samplers, but those data are available
only on request and are not open. **A causal NO2 estimate for the CRZ itself is therefore not
feasible with open data.** This is reported as a limitation, not worked around.

**Re-scoped A2:**
- **Outcome:** weekly mean of daily-mean NO2 (ppb).
- **Treated unit:** IS 52, the South Bronx spillover corridor.
- **Designs:**
  - **(a)** demeaned synthetic control. Donors are AQS NO2 monitors in DE, MD, DC, VA, PA, NJ,
    CT, RI, and MA, using the same distance, CBSA, and completeness rules as A1.
  - **(b)** DiD of the Bronx sites (IS 52, Pfizer Lab) against the Queens College pair, with the
    weather adjustment from A3.
- **Sign:** two-sided. Diversion would raise Bronx NO2; regional traffic reductions would lower
  it.
- **Family:** A2 belongs to the secondary spillover family, BH-adjusted with S2–S5.

## 6. Known biases, stated in advance

| Design | Likely bias | Direction |
|---|---|---|
| R2 station DiD | Drivers who switch to the subway board at stations outside the zone in the morning | Toward zero |
| R1, R2 | NYC-specific RTO intensity in 2025 | Inflates ridership effect |
| T2, T3 | RTO raises CBD demand | Shrinks traffic reduction |
| T2 | Trip fee charged to CRZ trips also lowers trips via price, not congestion | Part of the estimand (total policy effect) |
| A1, A3 | Cold, dry January 2025 raises heating emissions | Toward zero (smaller measured improvement) |
| A1 | Regional, policy-driven PM2.5 change (Fraser et al. claim a metro-wide effect) | Excluded by out-of-CBSA donors |
| All | Concurrent events in [confounders.md](confounders.md) | Per row |

## 7. Falsification tests (Phase 5) that would make us doubt a result

1. **Pre-trends.** A joint Wald test of pre-period event-study bins with p < 0.10 flags the
   design. We then rely on the HonestDiD-style bound
   ([ADR 0006](adr/0006-parallel-trends-sensitivity.md)).
2. **Placebo date.** 2024-01-07, estimated with data before 2024-11-14 only. An "effect" of
   similar size to the real estimate undermines the result.
3. **Placebo outcomes.**
   - TLC trips entirely within Staten Island, compared with the rest of the far-control group.
   - Verrazzano-Narrows crossings, compared with the other control facilities.
   - PM2.5 at donor monitors (in-space placebos).
   None of these should move.
4. **Dose-response.** The toll is 75% lower overnight, so overnight effects should be smaller in
   magnitude than peak effects. If overnight effects are as large or larger, we doubt that the
   toll is what's driving the estimate.
5. **Anticipation bin.** A large effect before 2025-01-05 is reported and discussed, not
   absorbed.
6. **Control-group sensitivity.** T2, S1, and T3 are re-estimated with Brooklyn-only and
   Queens-only far controls, and with the intermediate band as a control. The last one is
   expected to shrink the estimates if spillovers exist.
7. **Leave-one-out donors** for R1 and A1. Re-estimate dropping each donor with non-zero weight.
8. **DoWhy refuters** (placebo treatment, random common cause, data subset) on T2 and A3.

## 8. Decision rules for claims

Each headline claim gets one label in the Phase 5 robustness table:

- **Robust:** the primary estimate is significant after Holm adjustment, and its sign holds
  across checks 2–7. For DiD designs, the breakdown M̄ is ≥ 1. For synthetic controls, the
  permutation p is ≤ 0.10 and the result survives leave-one-out.
- **Fragile:** significant, but it fails at least one of the checks above. Every failure is
  reported.
- **Not supported:** the primary interval includes zero. We then report the range of effects
  the interval rules out (for example, "declines larger than X% are ruled out at 95%").

If a design's identifying assumption visibly fails (pre-trends, poor synthetic-control fit with
pre-RMSPE above the placebo median), its estimate is downgraded to descriptive and the claim is
weakened. **No specification is chosen after seeing estimates.** Minimum detectable effects for
each primary outcome are computed in Phase 2 from placebo-in-time estimates on pre-period data
only.

## 9. Heterogeneity and equity (Phase 4)

**Pre-specified heterogeneity cuts** (secondary, BH within each cut):
- peak vs overnight;
- weekday vs weekend;
- vehicle class (B&T: car vs truck; TLC: yellow vs FHVHV);
- borough (for S1/S3).

**Equity lens** (exploratory, associations only):
- Zone-level spillover estimates from S1/S3, empirical-Bayes shrunk, are related to:
  - ACS 2019–2023 median household income;
  - share of households without a vehicle;
  - poverty rate;
  - asthma emergency-department visit rates from the NYC Environment & Health Data Portal.
- Method: population-weighted correlations and a weighted regression with SEs. No causal
  interpretation.

## 10. Data handling rules

- **Time:** all sources are converted to America/New_York
  ([ADR 0003](adr/0003-treatment-timing-and-timezone.md)).
  - B&T, subway, TLC: local floating time.
  - NYCCAS: UTC.
  - AQS: `Date Local`/`Time Local`.
  - Open-Meteo: requested in local time.
- **Missing data:** facility-days with zero crossings, or with crossings below 20% of that
  facility's median for the same weekday, are flagged as closures and dropped. Every drop is
  logged with counts.
- **Holidays:** federal and NY State holidays and NYC public school closures are used as
  indicators in robustness checks. Holiday weeks are excluded in a robustness check.
- **Data versions:** every input is recorded in `data/MANIFEST.json` with its SHA-256. TLC files
  are recorded by URL and ETag, since they are read remotely.
