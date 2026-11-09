# Concurrent events and confounders (first draft, Phase 0)

Treatment: Congestion Relief Zone (CRZ) tolling began **Sunday, January 5, 2025, 00:00 local
time**. This file lists events that could also move traffic, transit, or air quality around that
date, and says how the designs should handle each one. Phase 1's analysis plan has to cite this
file for every design.

**Verification status.** Every row was located in a dated public source. **V** means consistent
dated sources were found. **V-partial** means the date or magnitude is only partly confirmed.
**U** means unverified. This draft was compiled from search results and source summaries. Each
row a design relies on gets checked against the primary document in Phase 1 before it enters the
analysis plan or the paper.

## Key takeaways for design

1. **Same-week shocks at the Hudson crossings.** The Port Authority toll increase took effect the
   same day as CRZ tolling (Jan 5, 2025). The PATH fare increase followed on Jan 12. A sharp
   before/after comparison of trans-Hudson entries cannot separate them from the CRZ. Comparisons
   need units hit by the Port Authority increase but not by the CRZ, such as George Washington
   Bridge traffic to non-CRZ destinations.
2. **Return-to-office is the main demand-side confounder.** Amazon went to 5 days on Jan 2, 2025.
   JPMorgan announced 5 days on Jan 10, 2025, effective March. The federal RTO memo came in late
   January 2025. RTO pushes CBD trips up: it biases traffic reductions toward zero and inflates
   transit gains. Designs need an occupancy or demand proxy, or must state the bias direction.
3. **Air quality needs smoke screening and meteorology adjustment.** Wildfire smoke hit the
   pre-period (Nov 2024; record Jun 2023) and the post-period (Apr, Jun–Aug 2025). January 2025
   was cold and dry. Flag smoke days with NOAA HMS plumes, control for weather, and use same-airshed
   donor monitors in the synthetic control.
4. **Contaminated controls.** Several candidate control units got their own interventions: Queens
   buses (network redesign, Jun 29, 2025), bus routes with new ACE cameras, Cross Bronx and BQE
   truck corridors, and Hudson Yards and Port Authority Bus Terminal construction sites. Exclude
   them from donor and control pools, or model them separately.
5. **Anticipation windows.** The program was paused on Jun 5, 2024, then revived on Nov 14, 2024
   and approved on Nov 21, 2024. Event studies include leads covering Nov 14, 2024 to Jan 4, 2025,
   and robustness checks drop that window (a "donut").
6. **Year-2 comparisons need explicit shocks.** January 2026 brought MTA fare and toll increases,
   a major snowstorm, and extreme cold. Avoid naive Jan 2026 vs Jan 2025 comparisons.

## Timeline

### Policy, tolls, and fares

| Date | Event | Outcomes | Likely bias on CRZ estimate | Handling | Status / source |
|---|---|---|---|---|---|
| Jun 5, 2024 | Gov. Hochul pauses the $15 plan about 3 weeks before its Jun 30 start | Anticipation | Pre-pause adjustments may contaminate a June 2024 baseline | Flag Jun 2024; event-study leads | V — [Axios](https://www.axios.com/2024/06/05/nyc-congestion-pricing-pause-hochul) |
| Nov 14, 2024 (announced); Nov 21 (FHWA approval) | Revived at a $9 base toll ($12 in 2028, $15 in 2031) | Anticipation in Nov–Dec 2024 | Early adjustment shrinks the measured effect | Leads; donut window | V — [Fox 5](https://www.fox5ny.com/news/nyc-congestion-pricing-plan-gets-federal-approval-set-begin-janaury-5), [NJBIZ](https://njbiz.com/with-federal-greenlight-congestion-pricing-moves-closer-to-reality/) |
| Jan 5, 2025 | Toll structure: overnight 75% off; tunnel crossing credits (Lincoln, Holland, Queens-Midtown, Hugh L. Carey); low-income discount; per-trip fees of $0.75 (taxi) and $1.50 (FHV) | Treatment design | Time-of-day and route shifting; taxi substitution | Hour-of-day and entry-point heterogeneity; taxi and FHV analyzed separately | V — [MTA tolling](https://congestionreliefzone.mta.info/tolling), [TLC notice](https://nyc.gov/assets/tlc/downloads/pdf/industry-notices/industry_notice_24_10_english.pdf) |
| **Jan 5, 2025** | Port Authority Hudson and Staten Island crossings +$0.68 (further +$0.25 approved for each of 2026–2028) | Trans-Hudson auto entries | Part of the Hudson-entry drop could be wrongly attributed to the CRZ | Compare with Port Authority traffic not bound for the CRZ | V — [amNY](https://amny.com/nyc-transit/port-authority-bridge-tunnel-toll-increase-2025), [PANYNJ](https://www.panynj.gov/content/dam/corporate/financial-information/Proposed%202025%20Toll%20and%20Fare%20Adjustments%20-%20Hearing%20Handout.pdf) |
| Jan 1, 2025 | NJ Turnpike and Garden State Parkway +3% (annual indexing) | NJ auto trips | Small; roughly neutral between NJ units | Year effects | V — [NBC NY](https://nbcnewyork.com/news/local/new-jersey-turnpike-garden-state-parkway-toll-hikes-january-2025/6003509) |
| Jan 12, 2025 | PATH fare $2.75 → $3.00 | PATH ridership | Hides some of the shift to transit (bias toward zero) | Flag for PATH outcomes | V — [ABC7](https://abc7ny.com/post/path-fares-will-increase-25-cents-275-3-effective-january-12/15648355/) |
| Jul 1, 2024 (+15%); Jul 1, 2025 and each July after (+3%) | NJ Transit fare increases | NJ commuter mode choice | 2024 step falls in the pre-period | Level shift in NJT series | V — [NJ Monitor 2024](https://newjerseymonitor.com/2024/04/10/nj-transit-board-approves-double-digit-fare-hikes/), [NJ Monitor 2025](https://newjerseymonitor.com/2025/07/01/nj-transit-riders-to-see-fare-hike-starting-july-1/) |
| Dec 31, 2025 | MetroCard sales end (OMNY only) | Ridership measurement, tourist trips | Small | Note | V — [6sqft](https://www.6sqft.com/its-the-end-of-the-line-for-the-metrocard/) |
| **Jan 4, 2026** | MTA fare $2.90 → $3.00; bridges and tunnels about +7.5%; commuter rail about +4.4% | Year-2 transit and auto | Shifts year-2 levels | Explicit shock in year-2 analyses | V — [MTA](https://www.mta.info/press-release/mta-board-adopts-fare-and-toll-increases-take-effect-january-2026) |

### Legal and political uncertainty (tolls were collected throughout)

| Date | Event | Handling | Status / source |
|---|---|---|---|
| Feb 19, 2025 | USDOT rescinds the FHWA approval; MTA sues | Sensitivity dummy only; tolls continued | V — [NY1](https://ny1.com/nyc/all-boroughs/news/2025/02/19/trump-administration-pulls-approval-for-congestion-pricing) |
| Mar–May 2025 | Repeated federal deadlines and funding threats | Same | V — [Gothamist](https://api-prod.gothamist.com/news/feds-threaten-nyc-highway-money-if-mta-doesnt-shut-down-congestion-pricing) |
| May 27–28, 2025 | Court blocks federal compliance measures | Note | V — [CBS NY](https://www.cbsnews.com/newyork/news/nyc-congestion-pricing-injunction-hearing) |
| Mar 3, 2026; appeal ~May 2026 | Summary judgment for MTA; appeal to 2nd Circuit pending | Note | V — [SDNY opinion](https://www.nysd.uscourts.gov/sites/default/files/2026-03/25cv1413%20Opinion%203.3.26.pdf), [NJ Monitor](https://newjerseymonitor.com/2026/05/04/trump-administration-appeals-congestion-pricing/) |

### Demand: return to office, tourism, secular recovery

| Date | Event | Likely bias | Handling | Status / source |
|---|---|---|---|---|
| Jan 2, 2025 | Amazon 5-day RTO | Raises CBD demand: traffic reduction biased toward zero, transit gain overstated | Occupancy proxy; Tue–Thu vs Fri heterogeneity | V — [WJLA](https://wjla.com/news/nation-world/amazon-andy-jassy-ceo-jeff-bezos-return-to-work-employees-workers-puget-sound) |
| Jan 10, 2025 memo; effective March 2025 | JPMorgan 5-day RTO (large Midtown footprint) | Same | Same; staggered timing helps separate it from Jan 5 | V — [Fortune](https://fortune.com/2025/01/10/jpmorgan-tells-staff-to-return-to-the-office-five-days-a-week/) |
| Jan 20, 2025 memo (published Jan 28) | Federal RTO memorandum | Small push up | Occupancy proxy | V — [Federal Register](https://www.federalregister.gov/documents/full_text/text/2025/01/28/2025-01907.txt) |
| Mar 2025 → May 31, 2026 | NYC DC 37 remote-work pilot extended (no city-agency RTO mandate found) | Little | None | V — [NYC.gov](https://www.nyc.gov/mayors-office/news/2025/03/mayor-adams-dc-37-executive-director-garrido-extension-remote-work-pilot-city) |
| 2024–2025 | Other 5-day mandates (Dell, AT&T, NBCU, BNY, others) | Push up | Same | **U** — dates not confirmed ([CoStar](https://www.costar.com/article/102840689/heres-how-some-large-employers-are-stepping-up-return-to-office-mandates-this-year)) |
| 2025 | Office occupancy at post-pandemic highs (Kastle NYC peak day about 71%, Jul 2025) | Rising trend in post-period | Trend controls; SC donors with similar recovery | V (metro-wide) — [Kastle](https://www.kastle.com/city-by-city-views-of-americas-office-use/) |
| 2025 | Transit recovery: subway about 85% of pre-COVID, +7% y/y (MTA figures) | Secular growth overstates a transit effect | Pre-trend modeling; external transit donors | V — [NY Governor](https://www.governor.ny.gov/news/governor-hochul-highlights-record-breaking-year-performance-and-ridership-mta-2025) |
| 2025 | International tourism down (Canada about −19%); total visitors about flat | Slightly lower post-period CBD demand | Weekend heterogeneity | V — [6sqft](https://www.6sqft.com/nyc-officials-predict-17-percent-drop-in-international-tourists-due-to-trump-policies/), [AltexSoft](https://www.altexsoft.com/travel-industry-news/nyc-saw-more-tourists-in-2025-but-foreign-travel-fell/) |
| Oct 1 – Nov 12, 2025 | Federal shutdown; FAA flight cuts Nov 7–17 | Lower airport traffic | Period dummy | V — [TT News](https://www.ttnews.com/articles/faa-lifts-order-flights) |

### Transit service and safety

| Date | Event | Handling | Status / source |
|---|---|---|---|
| Jun 28 – Sep 3, 2024 | G train partial shutdown (pre-period) | Exclude affected stations and weeks from controls | V — [MTA](https://mta.info/article/service-changes-g-line-summer-2024) |
| Jan 20, 2025 | NYPD officers on overnight subway trains (9pm–5am) | Do not attribute night ridership changes to the CRZ alone | V — [NY Governor](https://www.governor.ny.gov/news/governor-hochul-announces-new-initiatives-protect-subway-riders-and-transit-workers-increasing) |
| May 16–19, 2025 | NJ Transit engineers' strike | Drop the week / dummy | V — [6sqft](https://www.6sqft.com/nj-transit-strike-ends-service-to-resume-tuesday/) |
| Jun 29 and Aug 31, 2025 | Queens Bus Network Redesign | Remove Queens buses from controls after Jun 2025 | V — [MTA](https://mta.info/press-release/mta-launch-queens-bus-network-redesign-phase-1-june-29) |
| 2024–2025, staggered | ACE bus-lane camera expansions (M2/M4 Apr 2025; more in Sep and Nov 2025) | Route-level activation dates as separate treatments | V — [NY1](https://ny1.com/nyc/all-boroughs/transit/2025/04/28/mta-expanding-bus-lane-camera-enforcement-to-two-more-routes), [6sqft](https://www.6sqft.com/mta-expands-bus-lane-camera-enforcement-to-four-more-routes/) |

### Streets, construction, closures

| Date | Event | Handling | Status / source |
|---|---|---|---|
| Nov 2023 → Mar 2025 | BQE weigh-in-motion enforcement (truck diversion) | Note for Brooklyn spillover | V — [NYC DOT](https://www.nyc.gov/html/dot/html/pr2025/expand-crackdown-overweight-truck-bqe.shtml) |
| 2025–2026 | Cross Bronx bridge repair lane closures | Exclude affected hours and segments from Bronx spillover | V-partial — [Streetsblog](https://empire.streetsblog.org/state-dot-scraps-cross-bronx-expansion-road-on-highway-repair-plan) |
| From May 29, 2025 | Port Authority Bus Terminal replacement | Corridor-level control | V — [6sqft](https://www.6sqft.com/construction-begins-on-new-10b-port-authority-bus-terminal/) |
| From mid-2025 | Gateway Hudson Tunnel construction at Hudson Yards | Exclude nearby monitors or site dummy | V — [ENR](https://www.enr.com/articles/62642-gateway-hudson-tunnel-work-resumes-even-as-funding-uncertainty-mounts) |
| Sep 2024; more 2028–2031 | Broadway pedestrian plazas (Flatiron) | Exclude affected segments | V — [Streetsblog](https://nyc.streetsblog.org/2026/02/27/broadway-vision-city-will-revamp-six-more-blocks-by-2031) |
| Restarted Jun 2026; target fall 2026 | 34th St busway | End the main window before activation | V (opening unconfirmed) — [NYC.gov](https://www.nyc.gov/mayors-office/news/2026/06/mayor-mamdani-advances-34th-street-busway-in-manhattan.html) |
| Ongoing | Lincoln and Holland tunnel overnight lane closures | Port Authority advisories as night-level controls | **U** |

### Weather and air-quality episodes

| Date | Event | Likely bias | Handling | Status / source |
|---|---|---|---|---|
| Jun 6–8, 2023 | Record Canadian smoke (daily PM2.5 about 117 µg/m³) | Would distort a multi-year baseline | Exclude smoke days | V — [Axios](https://www.axios.com/2023/06/08/wildfire-smoke-air-quality-record) |
| Nov 2024 | Regional wildfire smoke during record drought (pre-period) | Overstates post-period air gains | Smoke-day flags (NOAA HMS) | V — [AccuWeather](https://www.accuweather.com/en/weather-news/wildfires-caused-smoky-skies-air-quality-issues-in-new-york-city/1712236) |
| Jan 2025 | Cold, dry January (snow Jan 6, 11, 20) | More heating emissions right after treatment → air gains biased toward zero | Meteorology adjustment | V-partial — [NBC NY](https://www.nbcnewyork.com/weather/weather-stories/january-comes-in-with-a-chill-to-start-the-new-year/6091246/), [NRCC](https://www.nrcc.cornell.edu/services/blog/2025/02/01/) |
| Feb 8–9, 2025 | Snow (about 3") | Transient dip | Weather controls | V — [ABC7](https://abc7ny.com/post/how-snow-winter-storm-2825-snowfall-totals-ny-nj-ct/15884340/) |
| Apr 22–24, 2025 | NJ Jones Road Fire smoke | Understates air gains | Smoke flags | V — [Fox Weather](https://www.foxweather.com/weather-news/new-jersey-jones-road-wildfire-smoke-new-york-city) |
| Jun; late Jul; Aug 4–6, 2025 | Canadian wildfire smoke advisories | Understates air gains | Smoke flags; same-airshed donors | V — [ABC7](https://abc7ny.com/post/air-quality-alert-nyc-warning-continues-tri-state-area-due-canadian-wildfire-smoke/17441726/), [IQAir](https://www.iqair.com/newsroom/east-coast-wildfire-smoke) |
| Jun 23–25, 2025 | Heat wave (99°F in Central Park) | Ozone and PM up | Temperature controls | V — [NWS](https://www.weather.gov/okx/June2025heat) |
| Jan 25, 2026 | Major snowstorm (about 11"); coldest and snowiest winter in 11 years | Year-2 distortion | Weather controls | V — [ABC7](https://abc7ny.com/post/how-snow-winter-storm-12526-snowfall-totals-nyc-ny-nj-ct/18470009/), [CBS NY](https://www.cbsnews.com/newyork/news/2025-2026-nyc-winter-cold-snow) |

### Mobility and for-hire vehicle rules

| Date | Event | Handling | Status / source |
|---|---|---|---|
| Jan 6, 2025; Feb 3, 2025; Jan 2026 | Citi Bike price increases (e-bike per-minute rate, day pass, annual) | Damps a CRZ-driven bike increase; note for bike outcomes | V — [amNY](https://www.amny.com/news/nyc-citi-bike-fee-increases-2025), [Time Out](https://www.timeout.com/newyork/news/citi-bike-prices-are-increasing-again-next-month-123025) |
| Jun 20, 2025; Oct 2025 | E-bike 15 mph limits (Citi Bike fleet, then citywide) | Note | V-partial — [Gothamist](https://api-prod.gothamist.com/news/all-e-bike-citi-bikes-now-restricted-to-15-mph-in-nyc) |
| Sep 22, 2025 | TLC changes to the FHV driver minimum-pay formula | Note for FHV outcomes | V-partial — [NYC Rules](https://rules.cityofnewyork.us/rule/driver-minimum-pay-rule-amendment/) |
| 2026 | Free-bus proposals under the new mayor (not implemented as of Aug 2026) | Monitor | U |
| Jun–Jul 2026 | FIFA World Cup at MetLife Stadium | Drop match days | V — [NBC NY](https://www.nbcnewyork.com/world-cup/nj-transit-lost-nearly-4-million-for-providing-world-cup-service-to-metlife/6540655/) |

### Calendar

- Jan 1, 2025 was a Wednesday; Jan 1, 2024 a Monday. The CRZ started on Sunday, Jan 5, 2025,
  right after the holiday weeks.
- MLK Day: Jan 15, 2024 and Jan 20, 2025 (the latter also Inauguration Day). Easter: Mar 31, 2024
  and Apr 20, 2025.
- Handling: align comparisons on same week-of-year and day of week, not calendar date. Use holiday
  indicators (federal, NY State, NYC public school calendar). Robustness check excludes holiday
  weeks.

## Open items for Phase 1
- Confirm the other RTO mandate dates, the 2025 Lincoln and Holland closure schedule, TLC
  cruising-cap changes, and the 34th St busway opening against primary sources.
- Pick the demand proxy (e.g., MTA entries at office-heavy stations outside the zone, or a
  free occupancy index). It must itself be unaffected by the CRZ. Most candidates are not, which
  is a limitation to state.
