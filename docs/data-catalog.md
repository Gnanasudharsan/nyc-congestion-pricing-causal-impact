# Data catalog

Every candidate dataset, its coverage, and how Cordon uses it.

**Pre-period rule.** A dataset can serve as an outcome in a before/after, DiD, or synthetic
control design only if it covers at least 365 days before 2025-01-05 (`cordon.ingest.coverage`).
Datasets that begin in January 2025 are **descriptive post-period only**.

**How the coverage table is produced.** It is generated from `data/catalog/profiles.json` by
`python -m cordon.ingest.catalog`. Row counts and dates come from server-side aggregate queries
(Socrata), remote parquet metadata (TLC), or full downloads (EPA, NYCCAS, weather, small Socrata
tables). Each full download is recorded in `data/MANIFEST.json` with its SHA-256 checksum.

## Coverage

<!-- BEGIN GENERATED COVERAGE TABLE -->
_Generated from `data/catalog/profiles.json` (audited 2026-11-09T13:08:35-05:00)._

| Key | Source | Rows | Coverage start | Coverage end | ≥1 yr pre-period | Role |
|---|---|---|---|---|---|---|
| `bt_hourly_crossings` | [ebfx-2m7v](https://data.ny.gov/d/ebfx-2m7v) | 13,753,877 | 2019-01-01 | 2026-10-20 | yes | outcome |
| `bt_hourly_reconciled` | [rtih-nq26](https://data.ny.gov/d/rtih-nq26) | 21,726,299 | 2019-01-01 | 2024-12-31 | yes | outcome |
| `cbd_vmt` | [jbxx-kxff](https://data.ny.gov/d/jbxx-kxff) | 60 | 2024-01-01 | 2026-06-01 | yes | outcome |
| `cbd_taxi_fhv_trips` | [d3qp-nhf8](https://data.ny.gov/d/d3qp-nhf8) | 5,011 | 2019-05-01 | 2026-08-01 | yes | outcome |
| `cbd_taxi_fhv_speeds` | [6p29-6xqn](https://data.ny.gov/d/6p29-6xqn) | 213 | 2019-10-01 | 2025-08-01 | yes | outcome |
| `crz_entries` | [t6yz-b64h](https://data.ny.gov/d/t6yz-b64h) | 6,894,288 | 2025-01-05 | 2026-10-31 | **no** | descriptive_only |
| `dot_traffic_speeds` | [i4gi-tjb9](https://data.cityofnewyork.us/d/i4gi-tjb9) | probe only | 2019-01-01 | 2026-11-03 | yes | outcome |
| `dot_atr_counts` | 7ym2-wayt | error: 503 Server Error: Service Unavailable for url: https://data. | | | | |
| `tlc_zone_monthly` | c5iv-bn4s | error: 503 Server Error: Service Unavailable for url: https://data. | | | | |
| `subway_hourly_2020_2024` | [wujg-7c2s](https://data.ny.gov/d/wujg-7c2s) | 120,855,567 | 2020-01-01 | 2024-12-31 | yes | outcome |
| `subway_hourly_2025` | [5wq4-mkjj](https://data.ny.gov/d/5wq4-mkjj) | 47,409,293 | 2025-01-01 | 2026-10-29 | **no** | outcome |
| `bus_hourly_2020_2024` | [kv7t-n8in](https://data.ny.gov/d/kv7t-n8in) | 447,249,600 | 2020-01-01 | 2024-12-31 | yes | outcome |
| `bus_hourly_2025` | [gxb3-akrn](https://data.ny.gov/d/gxb3-akrn) | 170,690,976 | 2025-01-01 | 2026-10-27 | **no** | outcome |
| `mta_daily_ridership` | [sayj-mze2](https://data.ny.gov/d/sayj-mze2) | 18,421 | 2020-03-01 | 2026-11-05 | yes | outcome |
| `regional_transit_monthly` | [sv2g-g4mz](https://data.ny.gov/d/sv2g-g4mz) | 823 | 2021-01-01 | 2026-12-01 | yes | outcome |
| `cbd_bus_speeds` | [r6db-kkzj](https://data.ny.gov/d/r6db-kkzj) | 686,145 | 2023-01-01 | 2026-09-01 | yes | outcome |
| `bus_speeds_monthly` | [cudb-vcni](https://data.ny.gov/d/cudb-vcni) | 112,388 | 2019-01-01 | 2026-09-01 | yes | outcome |
| `bus_segment_speeds_2023_2024` | [58t6-89vi](https://data.ny.gov/d/58t6-89vi) | 11,656,097 | 2023-01-01 | 2024-12-01 | yes | outcome |
| `bus_segment_speeds_2025` | [kufs-yh3x](https://data.ny.gov/d/kufs-yh3x) | 10,217,290 | 2025-01-01 | 2026-09-01 | **no** | outcome |
| `cbd_geofence` | [srxy-5nxn](https://data.ny.gov/d/srxy-5nxn) | 7 | — | — | n/a | geography |
| `cbd_taxi_zones` | [yfdc-w5jh](https://data.ny.gov/d/yfdc-w5jh) | 38 | — | — | n/a | geography |
| `subway_stations` | [39hk-dx4f](https://data.ny.gov/d/39hk-dx4f) | 496 | — | — | n/a | geography |
| `taxi_zones` | [8meu-9t5y](https://data.cityofnewyork.us/d/8meu-9t5y) | 263 | — | — | n/a | geography |
| `nta_2020` | 9nt8-h7nd | error: 503 Server Error: Service Unavailable for url: https://data. | | | | |
| `ntd_monthly_ridership` | [8bui-9xvu](https://datahub.transportation.gov/d/8bui-9xvu) | 374,103 | 2002-01-01 | 2026-09-01 | yes | outcome |
| `tlc_yellow` | TLC parquet | 45 monthly files (14,086,407 rows in 4 probe months) | 2023-01 | 2026-09 | yes | outcome |
| `tlc_green` | TLC parquet | 45 monthly files (217,207 rows in 4 probe months) | 2023-01 | 2026-09 | yes | outcome |
| `tlc_fhvhv` | TLC parquet | 45 monthly files (80,941,229 rows in 4 probe months) | 2023-01 | 2026-09 | yes | outcome |
| `epa_88101_2023` | EPA AQS hourly | 9,350,315 (5 NYC sites) | 2023-01-01 | 2023-12-31 | yes (multi-year files) | outcome |
| `epa_88101_2024` | EPA AQS hourly | 8,139,551 (6 NYC sites) | 2024-01-01 | 2024-12-31 | yes (multi-year files) | outcome |
| `epa_88101_2025` | EPA AQS hourly | 8,367,660 (9 NYC sites) | 2025-01-01 | 2025-12-31 | yes (multi-year files) | outcome |
| `epa_88101_2026` | EPA AQS hourly | 1,979,862 (9 NYC sites) | 2026-01-01 | 2026-05-31 | yes (multi-year files) | outcome |
| `epa_42602_2023` | EPA AQS hourly | 3,590,973 (4 NYC sites) | 2023-01-01 | 2023-12-31 | yes (multi-year files) | outcome |
| `epa_42602_2024` | EPA AQS hourly | 3,547,016 (4 NYC sites) | 2024-01-01 | 2024-12-31 | yes (multi-year files) | outcome |
| `epa_42602_2025` | EPA AQS hourly | 3,489,728 (4 NYC sites) | 2025-01-01 | 2025-12-31 | yes (multi-year files) | outcome |
| `epa_42602_2026` | EPA AQS hourly | 805,803 (4 NYC sites) | 2026-01-01 | 2026-05-31 | yes (multi-year files) | outcome |
| `citibike` | S3 archives | 45 files | 2013 | 202610 | yes | outcome |
| `open_meteo` | Open-Meteo archive | 42,576 hours | 2022-01-01 | 2026-11-09 | yes | covariate |

**NYCCAS sites** (commit `a6f327e959`): share of the 2023-01-01 to 2024-11-13 pre-period weeks with ≥5 days of ≥18 valid hours.

| Site | First reading | Valid pre-period weeks | Core (≥75%)? |
|---|---|---|---|
| Broadway/35th St | 2019-06-07 | 90/98 (92%) | yes |
| Cross Bronx Expy | 2019-07-25 | 81/98 (83%) | yes |
| Manhattan Bridge | 2020-02-04 | 79/98 (81%) | yes |
| Queensboro Bridge | 2020-03-02 | 78/98 (80%) | yes |
| Queens College | 2019-05-07 | 78/98 (80%) | yes |
| Williamsburg Bridge | 2020-04-06 | 52/98 (53%) | no |
| FDR | 2023-12-01 | 37/98 (38%) | no |
| Van Wyck | 2024-02-22 | 30/98 (31%) | no |
| Mott Haven | 2024-04-10 | 30/98 (31%) | no |
| Hunts Point | 2022-04-14 | 29/98 (30%) | no |
| Glendale | 2024-07-02 | 22/98 (22%) | no |
| Hamilton Bridge | 2024-05-20 | 21/98 (21%) | no |
| Midtown-DOT | 2019-06-06 | 21/98 (21%) | no |
| BQE | 2024-08-15 | 12/98 (12%) | no |
| Port Richmond | 2024-05-21 | 11/98 (11%) | no |
| SI Expwy | 2024-08-13 | 9/98 (9%) | no |
<!-- END GENERATED COVERAGE TABLE -->

## Notes by dataset

### Traffic

| Dataset | Granularity and key columns | Known issues | Use |
|---|---|---|---|
| **B&T Hourly Crossings** `ebfx-2m7v` | facility × hour × direction × vehicle class × payment method; `traffic_count` | Two plazas for RFK (Manhattan, Bronx). Overlaps 2019–2024 with the reconciled table `rtih-nq26`; Phase 2 checks the two agree and documents any differences | **T1, S2** (primary/secondary) |
| B&T Hourly Reconciled `rtih-nq26` | as above, plus revenue; ends 2024-12-31 | No post-period | Consistency check only |
| **CBD Taxi/FHV Trips** `d3qp-nhf8` | month × service × CBD relation (entering/leaving/within) × peak/overnight | MTA-aggregated from TLC records; monthly | Validation of the TLC pipeline; descriptive |
| CBD Taxi/FHV Speeds `6p29-6xqn` | month × zone (CBD / CBD Adjacent / Greater NYC) | Ends Aug 2025. Only 3 units, so no valid cluster inference | **T4** (secondary, descriptive inference) |
| CBD VMT `jbxx-kxff` | month × area (CRZ / ER) | Starts Jan 2024 (12 months pre). "ER" is not defined in the metadata; Phase 2 must confirm it | Exploratory, descriptive |
| CRZ Vehicle Entries `t6yz-b64h` | 10-minute × detection point × vehicle class | **Begins on the treatment date. No pre-period** | Descriptive post-period only |
| **TLC trip records** (yellow, green, FHVHV parquet) | trip; pickup/dropoff time and zone, distance, duration; `cbd_congestion_fee` from 2025 | Timestamps in local floating time; outliers (zero distance, negative duration). FHVHV files are about 500 MB per month, so we read them remotely, columns only | **T2, T3, S1, S3, S4** |
| TLC Pickups/Drop-offs by Zone `c5iv-bn4s` | month × industry × zone | Aggregate | Cross-check of TLC pipeline counts |
| DOT Traffic Speeds `i4gi-tjb9` | sensor link × ~5 min; `speed`, `link_name` | Billions of rows. Server-side aggregation times out, so coverage comes from dated probes. Many links report 0 speed (sensor down); Phase 2 handles this with a documented rule | **T6** (secondary) |
| DOT Automated Traffic Volume Counts `7ym2-wayt` | segment × 15 min, short-duration counts | Counts are campaign-based, not continuous, so a segment rarely has both pre and post data | Exploratory; Phase 2 checks segments with both |

### Transit

| Dataset | Granularity | Known issues | Use |
|---|---|---|---|
| **Subway Hourly Ridership** 2020–2024 `wujg-7c2s` + 2025+ `5wq4-mkjj` | station complex × hour × payment × fare class | Two tables to stitch; check overlap and definitions at the Dec 31/Jan 1 seam. MetroCard sales ended 2025-12-31 (payment mix shifts) | **R2** (secondary) |
| Bus Hourly Ridership `kv7t-n8in` + `gxb3-akrn` | route × hour | Fare evasion is high and changing (`uv5h-dfhp`) | Descriptive |
| MTA Daily Ridership and Traffic `sayj-mze2` | system × mode × day | Includes "CRZ Entries" rows from 2025 only | ITS cross-check for R1 |
| **NTD Complete Monthly Ridership** `8bui-9xvu` | agency × mode × type of service × month; UPT | Includes estimates for late reporters ("with adjustments and estimates"); Phase 2 flags estimated rows | **R1, R4** |
| Regional Transit Ridership `sv2g-g4mz` | operator × mode × month (PATH, NJ Transit, ferries) | Starts 2021 | **R5** |
| **CBD Bus Speeds** `r6db-kkzj` | route × month × hour × CBD relation | Starts 2023; ACE camera rollout confounds some routes | **R3** |
| Bus Speeds (route-month) `cudb-vcni`; segment speeds `58t6-89vi` + `kufs-yh3x` | route-month; segment × hour | Segment tables split at 2025 | Robustness for R3 |
| Citi Bike trip archives | trip; start/end station, time | 2023 is a yearly archive; monthly from 2024. E-bike pricing changed 2025-01-06 | **R6** |

### Air quality

| Dataset | Granularity | Known issues | Use |
|---|---|---|---|
| **NYCCAS real-time PM2.5** (github.com/nychealth/nyccas-data) | site × hour, UTC | Corrected low-cost DustTrak sensors, not regulatory instruments. The correction factor was revised on 2024-06-10 and applied to all history. NY DEC data were removed on 2026-05-12. Sites start at different dates (see `profiles.json`). Downloads are pinned to a commit SHA | **A1, A3, A4, S5**; exploratory for short-pre-period sites |
| **EPA AQS hourly PM2.5** (88101) | monitor × hour | **No hourly regulatory PM2.5 monitor inside the CRZ with a pre-period.** In Manhattan, PS 19 (36-061-0128, inside the CRZ) is a 24-hour filter sampler running about 1 day in 3; Division St (36-061-0134, inside the CRZ) starts 2025-01-29; CCNY (36-061-0135) and IS 143 (36-061-0115) are in upper Manhattan | Donor pool for A1; comparison sites for A3; PS 19 used in a Phase 5 check on filter days |
| **EPA AQS hourly NO2** (42602) | monitor × hour | **No NO2 monitor in Manhattan.** Active NYC sites: IS 52 and Pfizer Lab (Bronx), Queens College 2 and Queens College Near Road. CRZ NO2 is measured only by DOHMH's integrated samplers, which are not open data | **A2** (Bronx spillover only) |
| AirNow hourly archive | site × hour | Includes CCNY and IS 143 hourly before AQS has them; preliminary data | Candidate check for upper-Manhattan spillover (Phase 2) |

### Controls and geography

| Dataset | Use | Notes |
|---|---|---|
| Open-Meteo hourly reanalysis (Central Park; per-monitor for donors) | Weather controls: temperature, precipitation, snowfall, wind, humidity, boundary-layer height | Free, no key. Reanalysis, not station observations; NOAA ISD (Central Park, LGA, JFK) is the robustness check |
| NOAA HMS smoke polygons | Smoke-day flags | Daily shapefiles; downloaded in Phase 2 |
| US federal and NY State holidays; NYC DOE school calendar | Holiday and school-closure indicators | Built in code (`cordon.features`) from published calendars |
| CBD geofence `srxy-5nxn`; CBD taxi zones `yfdc-w5jh`; TLC taxi zones `8meu-9t5y` | Spatial groups (ADR 0010) | |
| NTA 2020 `9nt8-h7nd`; ACS 2019–2023 5-year (Census API, no key needed for low volume) | Phase 4 equity lens | |
| MTA Subway Stations `39hk-dx4f` | Station CBD flag (95 of 496 stations) | |

## Datasets considered and not used as outcomes

| Dataset | Why |
|---|---|
| CRZ Vehicle Entries `t6yz-b64h` | Begins 2025-01-05; descriptive only |
| OpenAQ | Requires an API key (account creation). Its NYC sources overlap AQS and AirNow |
| PurpleAir | Requires an API key. Used by Cook et al.; a possible extension if the user registers |
| Google Maps, Advan, card spending | Proprietary |
| Port Authority crossing traffic | No machine-readable pre-period series found yet; Phase 2 checks monthly PDF reports |
