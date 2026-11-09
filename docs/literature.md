# What is already known: literature review (as of November 2026)

Scope: studies and reports that measure effects of New York City's Congestion Relief Zone (CRZ)
toll, which started January 5, 2025, plus a few foundational references on cordon pricing and
methods. The review describes what each source claims and how; it does not endorse those claims.

**Verification key.** **[V]** means the primary landing page or abstract was read. **[V-partial]**
means the bibliographic record was confirmed but findings come from press material or secondary
summaries. **[U]** means unverified. Several full-text PDFs were not readable when this review was
compiled, so some numbers come from abstracts and digests. Before any number is compared with
Cordon's results in the paper, it gets re-checked against the full text, citing the exact
version (working papers have been revised).

## Summary table

| # | Source | Type | Data | Method | Headline finding (as reported) | Spillovers? | Equity? |
|---|---|---|---|---|---|---|---|
| 1 | Cook et al., NBER w33584 | Working paper | Google Maps speeds, foot traffic, card spending, PM2.5 | Generalized synthetic control (other US cities) | CBD speeds +11% (current version; +15% early version); speeds also up outside the cordon; air quality and spending "barely affected" | Yes (network speeds) | No |
| 2 | Fraser et al., *npj Clean Air* 2025 | Peer-reviewed | 42 PM2.5 monitors | "Modified DiD" vs predicted counterfactual | CRZ daily-max PM2.5 −3.05 µg/m³ (about −22%) | Partly; mixed signals | Controls only |
| 3 | Chikish et al., NBER w35414 | Working paper | EMS records; boundary traffic counts | Difference-in-discontinuities at 60th St | Boundary traffic −18% to −21%; EMS travel time −63 to −70 s | Local boundary only | No |
| 4 | Zhang, Sang & Wu, *TR-A* 2026 | Peer-reviewed | Uber/Lyft trips, subway ridership | TWFE DiD | Ride-hail volume −0.5% to −1.5%; subway +~1% | No | Partly (drivers, trip types) |
| 5 | Pandey, Guler & Gayah, *Findings* 2026 | Peer-reviewed | TLC trip records | DiD by taxi zone, event study | Ride-hail trips −5.95% (SE-based CI excludes 0); shared trips down sharply | Assumes none (upper Manhattan as control) | No |
| 6 | Itzkowitz, Morrison et al., *Am. J. Epidemiology* 2026 | Peer-reviewed | NYC collision records | CRZ vs control zone | Crashes down more in CRZ than control | Calls for study | No |
| 7 | *Safety* (MDPI) 12(3):64, 2026 | Peer-reviewed | Collision records | DiD, matched DiD, generalized SC | Limited short-run safety gains | — | — |
| 8 | NYC DOHMH et al., Aug 2026 | Agency report | NYCCAS + real-time monitors | ITS with one control site | CRZ air quality stable or slightly better; not significant | Yes (EJ highway corridors) | Yes (EJ corridors) |
| 9 | MTA / NY Governor, Jan 2026 | Agency (descriptive) | MTA entries, speeds, ridership | Before/after vs projections | Entries −11%; transit trips into zone up | No | No |
| 10 | Regional Plan Association, Jun 2025 and Jan 2026 | Think tank (descriptive) | Waze jams; dashboard | Observed change minus extrapolated trend | Delay down in CRZ and in Bronx and NJ | Yes (descriptive) | No |
| 11 | Columbia researcher + South Bronx Unite, May 2026 | Unpublished | 19 low-cost PM2.5 sensors | Not public | Small PM2.5 increases at sites near Bronx expressways | Yes | Yes |
| 12 | Ren, Ji & Chow, arXiv 2510.06416 / *TR-A* 2026 | Peer-reviewed (model) | Synthetic trips | Mode and destination choice simulation | Consumer surplus loss vs revenue; distribution across counties | Modeled | Yes (modeled) |

## Detail by source

### Causal and quasi-causal studies

**1. Cook, C., Kreidieh, A., Vasserman, S., Allcott, H., Arora, N., Tomkins, A., Turkel, E., &
van Sambeek, F. "The Network-Wide Effects of Congestion Pricing: Evidence from New York City."**
NBER Working Paper 33584 (first issued March 2025 under the title "The Short-Run Effects of
Congestion Pricing in New York City"; revised through August 2026). [V]
<https://www.nber.org/papers/w33584> · [NBER Digest summary](https://www.nber.org/digest/202506/impact-new-york-citys-congestion-pricing-program)
- *Data:* Google Maps road-segment travel speeds; foot traffic and card-spending data; PM2.5.
  The core data are proprietary.
- *Method:* generalized synthetic control with other US cities as donors (early version:
  Philadelphia, Boston, Chicago, Atlanta, Baltimore).
- *Findings:*
  - Current abstract: speeds inside the cordon rose 11%, and speeds rose outside the cordon
    too, especially on roads cordon-bound drivers use. Air quality, spending, and foot traffic
    were "barely affected". Because unpriced trips far outnumber priced ones, their gains make
    up most of the driver welfare gain.
  - Early version (Sep 2024 – Feb 2025): CBD speeds rose about 15%, from 8.2 to 9.7 mph.
    PM2.5 effects were not significant and imprecise.
- *Limitations:* headline numbers changed across versions. Comparisons with other cities do not
  rule out shocks specific to NYC. Confidence intervals are not in the abstract.

**2. Fraser, T., Park, Y., Lu, M., Tayarani, M., Deng, S., & Gao, H. O. (2025). "A first look into
congestion pricing in the United States: PM2.5 impacts after six months of New York City cordon
pricing."** *npj Clean Air* 1:39. doi:10.1038/s44407-025-00037-2 (Author Correction, Dec 31,
2025). [V]
<https://www.nature.com/articles/s44407-025-00037-2>
- *Data:* 42 PM2.5 monitors, about Jan 2024 – Jun 2025; weather, traffic, and demographics within
  1 km of each monitor.
- *Method:* the authors call it a "modified DiD". They argue no monitor is truly unaffected, so
  they estimate against a predicted counterfactual. Treatment is interacted with days since the
  policy, with week and day-of-week fixed effects, across nine nested specifications. Uncertainty
  comes from Monte Carlo simulation.
- *Findings:* daily-maximum PM2.5 in the CRZ fell 3.05 µg/m³ (reported SE 0.022), about 22%
  against a counterfactual of 13.8 µg/m³. Smaller reductions were reported for the five boroughs
  (−1.07) and the metro area (−0.70).
- *Limitations:* the reported SEs are very small and likely understate uncertainty, since they
  reflect simulation rather than design-based variance. There is no clean control group and the
  post-period is six months. Some internal inconsistencies in day counts. The size of the effect
  conflicts with sources 1 and 8.

**3. Chikish, Y., Colman, G., Dave, D., Humphreys, B., Santamaria, S., & Winship, C. "Congestion
Pricing and Emergency Medical Service Response: Evidence from New York City."** NBER Working
Paper 35414 (July 2026, revised August 2026). [V]
<https://www.nber.org/papers/w35414>
- *Method:* difference-in-discontinuities at the 60th Street boundary. The authors chose it
  because a concurrent FDNY hospital-destination directive would bias a simple DiD.
- *Findings:* vehicle traffic near the boundary fell 18–21%; pedestrian and bicycle activity
  rose; EMS travel time fell 63–70 seconds (5–6%), mostly in hospital transport. The authors
  report little displacement to adjacent areas.
- *Limitations:* estimates are local to the boundary.

**4. Zhang, Y., Sang, Y., & Wu, M. (2026). "Congestion pricing in New York city: Effects on
ride-hailing and transit."** *Transportation Research Part A* 208:104966.
doi:10.1016/j.tra.2026.104966. [V-partial]
<https://trid.trb.org/View/2685545>
- *Method:* two-way fixed effects. Lyft's temporary rider credit in January 2025 helps separate
  platform-specific responses.
- *Findings (abstract):* Uber trips down up to 6% while Lyft rose 2–5% during the credit; total
  ride-hail volume down 0.5–1.5%; subway ridership up about 1%; short and low-fare trips fell
  most; per-trip fares and platform revenue rose.

**5. Pandey, A., Guler, S. I., & Gayah, V. V. (2026). "The Effect of the New York City Congestion
Toll on Trips Served by Transportation Network Companies."** *Findings*, February 2026.
doi:10.32866/001c.155761. [V]
<https://findingspress.org/article/155761-the-effect-of-the-new-york-city-congestion-toll-on-trips-served-by-transportation-network-companies>
- *Data and method:* TLC trip records, weekdays, weeks 1–14 of 2025 vs 2024. DiD on
  ln(1+trips) by taxi zone, SEs clustered by zone, event study. Controls are Manhattan zones north
  of 60th St (alternatives: Brooklyn, Queens).
- *Findings:* ride-hail trips −6.1 log points (SE 0.016), about −5.95%, and −3.8% to −7.2% across
  control groups. Shared-ride requests −38% and matched shared trips −51%.
- *Limitations:* imperfect pre-trends for shared trips. Upper Manhattan as a control assumes no
  spillover, which is exactly what Cordon tests. Short post-period. This is the closest
  open-data analogue to Cordon's TLC design.

**6. Itzkowitz, ..., Morrison, C. N., et al. (2026). Road-safety effects of the CRZ.** *American
Journal of Epidemiology*, advance article. doi:10.1093/aje/kwag090. [V-partial; exact title and
CIs unverified]
<https://academic.oup.com/aje/advance-article/doi/10.1093/aje/kwag090/8702710> ·
[Columbia release](https://www.publichealth.columbia.edu/news/congestion-relief-zone-results-after-year-one-suggest-notable-road-safety-benefits)
- *Findings (press release):* mean monthly crashes went from 549 to 496 in the CRZ, against 502
  to 492 in a control zone. Injurious and fatal crashes fell less. The authors call for study just
  outside the zone.

**7. "Has Congestion Pricing Improved Short-Term Road Safety? A Case Study in New York City."**
*Safety* (MDPI) 12(3):64, May 2026. doi:10.3390/safety12030064. [V-partial; authors and point
estimates unverified]
<https://www.mdpi.com/2313-576X/12/3/64>
- *Method:* DiD, matched DiD, and generalized synthetic control.
- *Conclusion (abstract):* the toll acts mainly as demand management; immediate safety gains likely
  need complementary measures.

### Agency and think-tank reports

**8. NYC Department of Health and Mental Hygiene, with MTA Bridges and Tunnels, NYC DOT, and NYSDOT
(Aug 14, 2026). "Air Quality Impacts of Congestion Relief Zone Tolling."** [V]
<https://a816-dohbesp.nyc.gov/IndicatorPublic/data-features/congestion-pricing-report/>
- *Method:* interrupted time series, 2025 vs 2024, adjusted for weather and for seasonal and
  long-run trends, with one control site (Van Wyck Expressway). Uses the NYC Community Air
  Survey (NYCCAS) and real-time monitors.
- *Findings:* CRZ pollution was stable or slightly lower, with differences from the projection
  not statistically significant. There was no toll-attributable increase along environmental
  justice highway corridors (Major Deegan, Cross Bronx, BQE, SIE, FDR, Trans-Manhattan).
- *Limitations:* a single control site, one post-year, and no numeric estimates in the text
  (they are in charts and an appendix). Note that the report was co-authored by the toll
  operator.

**9. MTA / Office of the Governor (Jan 5, 2026). One-year results.** [V-partial]
<https://www.governor.ny.gov/news/less-traffic-better-transit-its-first-anniversary-governor-hochul-celebrates-transformational>
- *Claims:* about 27 million fewer CRZ entries (−11%) relative to projected entries; faster
  crossing speeds; subway and bus trips into the zone up; net revenue over $550 million.
- *Method:* descriptive comparisons against projections, published by the program operator. Not
  a causal estimate.
- *Data relevance:* the open "CRZ Vehicle Entries" dataset (data.ny.gov `t6yz-b64h`) begins in
  January 2025, so it has no pre-period. Cordon can use it only descriptively.

**10. Regional Plan Association. Weinberger, R. & Cao, ... "Congestion Pricing: Faster All
Around" (Jun 18, 2025)** <https://rpa.org/news/lab/congestion-pricing-getting-around-faster-all-around>
**and "Congestion Pricing One Year Later" (Jan 2, 2026)**
<https://rpa.org/news/lab/congestion-pricing-one-year-later>. [V]
- *Method:* Waze "jam" data, Jan–Apr 2025 vs 2024, minus an extrapolated background trend. No
  formal control group or significance tests. The follow-up is a descriptive dashboard.
- *Findings:* delay down about 25% in the CRZ against the expected trend. Reductions also
  reported for the Bronx and the Bergen and Hudson County, NJ approaches. The one-year dashboard
  reports illegal-parking complaints −14% inside the CRZ and +17% outside, a possible spillover
  signal.
- *Limitations:* a crude congestion metric and no inference. RPA has long advocated for
  congestion pricing.

**11. Columbia University researcher with South Bronx Unite (May 2026). South Bronx PM2.5 sensor
analysis.** Unpublished, not peer-reviewed, methods not public. [V-partial]
<https://www.southbronxunite.org/press-and-media/south-bronx-air-quality-worsens-during-first-year-of-congestion-pricing> ·
[Spectrum News](https://spectrumlocalnews.com/us/snplus/traffic_and_transit/2026/05/05/south-bronx-study-shows-slight-increase-in-air-pollution-post-congestion-pricing)
- *Findings (as reported):* average PM2.5 up about 0.22 µg/m³ across 19 low-cost sensors, with
  larger increases at sites near expressways (up to +1.29 µg/m³ in Mott Haven). MTA and DOHMH
  dispute the findings.
- *Relevance:* the only source reporting harmful spillover to the Bronx. It cannot be evaluated
  without methods, which is a reason for Cordon to test this question transparently with
  regulatory monitors.

**12. Ren, Ji, & Chow. "Distributional welfare impacts and compensatory transit strategies under
NYC congestion pricing."** arXiv:2510.06416 (v3, May 2026); *Transportation Research Part A* 212
(2026) 105159. [V]
<https://arxiv.org/abs/2510.06416>
- *Method:* simulation with mode and destination choice models on synthetic trips across
  NY-NJ-CT-PA. Modeled, not observed.
- *Findings:* consumer surplus loss of about $397M/yr against about $523M/yr net revenue.
  Compensating through transit alone cannot make every county whole; New Jersey residents would
  need much larger transit improvements than NYC residents.

### Foundational references

- Eliasson, J. (2009). "A cost–benefit analysis of the Stockholm congestion charging system."
  *Transportation Research Part A* 43(4):468–480. doi:10.1016/j.tra.2008.11.014.
  <https://ideas.repec.org/a/eee/transa/v43y2009i4p468-480.html> [V-partial]
- Leape, J. (2006). "The London Congestion Charge." *Journal of Economic Perspectives*
  20(4):157–176. doi:10.1257/jep.20.4.157.
  <https://econpapers.repec.org/RePEc:aea:jecper:v:20:y:2006:i:4:p:157-176> [V-partial]
- Abadie, A., Diamond, A., & Hainmueller, J. (2010). "Synthetic Control Methods for Comparative
  Case Studies." *JASA* 105(490):493–505. doi:10.1198/jasa.2009.ap08746.
  <https://dspace.mit.edu/handle/1721.1/59447> [V]
- Rambachan, A., & Roth, J. (2023). "A More Credible Approach to Parallel Trends." *Review of
  Economic Studies* 90(5):2555–2591.
  <https://economics.mit.edu/research/publications/more-credible-approach-parallel-trends> [V]
- Callaway, B., & Sant'Anna, P. H. C. (2021). "Difference-in-Differences with multiple time
  periods." *Journal of Econometrics* 225(2):200–230. doi:10.1016/j.jeconom.2020.12.001.
  <https://arxiv.org/abs/1803.09015> [V]

## Where the evidence agrees, where it conflicts

- **Traffic volume inside the zone:** the sources agree on direction and rough size. Operator
  counts show entries about −11% against projections; boundary counts show −18% to −21% (source
  3); TLC ride-hail trips are down about 6% (source 5).
- **Speeds:** the sources agree speeds rose inside the zone. Source 1 reports +11% in its current
  version, down from +15% in the earlier version, so the magnitude depends on version and window.
- **Air quality: contested.** Source 2 reports about −22% in daily-max PM2.5 in the CRZ. Sources
  1 and 8 report null or not-significant effects. Source 11 reports small increases near Bronx
  expressways. The disagreement plausibly comes from methods (counterfactual prediction vs
  synthetic control vs ITS), metrics (daily max vs mean), monitor sets, and how weather and smoke
  are handled. This is a strong case for a transparent, meteorology-adjusted replication.
- **Spillovers:** speed-based and descriptive sources (1, 10) report improvements outside the
  zone; boundary and DOHMH sources (3, 8) report no displacement; one unpublished sensor study
  (11) reports small harms. No source estimates local volume or pollution spillovers with a
  design that also tests for interference.

## The gap Cordon fills

1. **Transparent replication on open data.** The most-cited causal result (source 1) relies on
   proprietary Google, foot-traffic, and card data. Agency reports are descriptive or publish no
   numeric intervals. Cordon replicates headline traffic, transit, and air-quality effects using
   only public data (TLC trip records, MTA crossings, speeds and ridership, EPA AQS), with a
   pre-registered plan and code that anyone can rerun.
2. **Spillovers as the main question, not an assumption.** Several designs use areas just outside
   the zone (upper Manhattan, boundary areas) as controls, which assumes away spillovers (a SUTVA
   violation if they exist). Cordon treats border neighborhoods, the Bronx, upper Manhattan, and
   the NJ approaches as their own treated groups, compared against farther-away areas. It tests
   whether conclusions change with the choice of control group.
3. **Reconciling the air-quality conflict.** Cordon runs a synthetic control with same-airshed and
   out-of-region donor monitors, adjusts for meteorology, and screens out smoke days. It reports
   how much the estimate depends on metric (mean vs daily max) and specification.
4. **Modern robustness tools on this policy.** HonestDiD-style parallel-trend sensitivity,
   placebo dates and units, leave-one-out donors, and wild cluster bootstrap have not, as far as
   this review found, been applied together to CRZ outcomes. Cordon reports which claims survive.
5. **An empirical equity lens.** Equity evidence so far is either modeled (source 12) or handled
   as controls (source 2). Cordon relates estimated spillover changes to neighborhood income and
   health indicators from public ACS and city data, presented as associations, not causal claims.

Open follow-ups for Phase 1:
- Read the full texts of sources 1, 2, 4, 6, and 8 to extract exact specifications and intervals
  to replicate against.
- Verify source 7's authors and estimates.
- Check for state or city comptroller and NY Fed evaluations, none found so far.
