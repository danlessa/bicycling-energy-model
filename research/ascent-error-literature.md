# Cumulative-ascent error: consumer barometers vs DEMs — literature vs our measurements

*2026-07-11. Question: what does the literature say the typical cumulative ascent (h₊)
error is (a) for consumer-grade barometric altimeters and (b) for DEM-derived elevation
— FABDEM and high-resolution aerophotogrammetric DTMs — and how does that compare to
what we measured ([MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md) Entries 6,
19–21; [dem-elevation-comparison.md](dem-elevation-comparison.md))?*

**Headline: the literature agrees with our two central findings — (1) consumer
barometers are the best consumer-grade ascent source (~1–5% device-level error,
excellent consistency), and (2) DEM-along-track ascent is systematically *inflated*,
by tens of percent, growing with sample spacing/grid mismatch — but almost all of it
validates *per-point elevation*, not *accumulated ascent*, and none of it validates
ascent against measured pedalling energy. The deepest point in the literature is also
ours: cumulative ascent has no single true value; it is scale-dependent, so every
"error" is relative to a chosen smoothing scale.**

## 1. Consumer barometric altimeters

| finding | value | source |
|---|---|--:|
| Between-unit consistency, Garmin head units (same climb ×6 + 138 km event) | CV **1.5%** (Garmin) vs 0.2% (SRM); brands differ by ~3% | Menaspà et al. 2014, *IJSPP* 9:884–886 |
| Absolute error vs known climb, dry conditions | SRM ≈ **−5%**, Garmin ≈ **−2%** (both under-read) | Menaspà et al. 2016 abstract¹ |
| Std. error of total ascent, 28 devices, one cycling trip | **1.5–1.9%** | as cited in Johnson et al. 2023 (PLOS One) |
| Trail activities vs aerial-photogrammetry benchmark, 202 efforts | baro watch consistently **over**-estimates, GPS-only consistently **under**-estimates; post-processing shrinks ≈ −5% → −1% | Sánchez & Villena 2020 |
| Grade from baro vs from GPS altitude | RMSE **0.5%** grade vs 2.6% grade | Meng et al., as cited in Johnson et al. 2023 |
| Pressure (weather) drift over a 6 h ride | ~13 m altitude drift → ~**15 m spurious gain** in 6 h | Wood (audax Edge 305 field test) |
| DEM "elevation correction" applied on top of a baro ride | **+5–10%** ascent (Garmin correction); ~+18% (Strava basemap, anecdote) | Menaspà 2014; Spoke Twist blog |

¹ *Abstract-level source (ResearchGate, paywalled) — numbers recovered from the abstract
snippet, not the full text; treat as indicative.*

Reading: device-level cumulative-ascent error for consumer barometric units is
**~1–5%** under benign conditions, with between-unit consistency at the ~1–2% level —
the sensor is not the problem. The *sign* is contested (Menaspà: under; Sánchez: over)
because the benchmarks differ in smoothing scale — which is the real lesson (see §3).
Weather drift is a second-order effect for ascent: pressure moves metres-per-hour
slowly, so with any hysteresis threshold it contributes tens of metres per multi-hour
ride (~15 m/6 h measured), i.e. ≲1% on a 1500 m-gain ride — it dominates *absolute*
altitude error, not h₊. Rain/temperature shocks are the known failure mode of the
dry-conditions numbers.

## 2. DEM-derived ascent (FABDEM, photogrammetric DTMs)

**Per-point vertical accuracy (what the DEM literature actually validates):**

| source | per-point accuracy | reference |
|---|---|--:|
| FABDEM | MAE **1.12 m** built-up / **2.88 m** forest | Hawker et al. 2022 |
| FABDEM (independent, flood-prone sites) | MAE **1.43 m**, RMSE **2.62 m** — best of 6 global DEMs | Bielski et al. 2024, *Int. J. Digital Earth* |
| Copernicus GLO-30 (FABDEM's source) | MAE 2.53 m, RMSE 4.89 m | ibid. |
| SRTM | MAE 3.72 m, RMSE 5.38 m | ibid. |
| Aerophotogrammetric 5 m DTM (IGC-SP class: 1:10,000-compatible product) | sub-metre to ~1 m σz class | IGC/Emplasa product spec; ASPRS-type standards |
| Airborne LiDAR DTM | ~0.1–0.6 m RMSE (slope/canopy-dependent) | multiple |

**Accumulated ascent (the far thinner literature):** per-point RMSE does *not*
transfer — metre-scale noise, summed signed over thousands of track points, inflates
h₊ by tens of percent. The one study that measures this directly (Sánchez et al. 2024,
ICECET — trail running, 20 cm LiDAR benchmark, GPS-track sampling, bilinear):

- a raw **4 m DEM** gave ascent error ~**12 pp worse** than the consumer watches it
  was meant to correct;
- ascent error grows monotonically with grid coarsening: ≈0 at 0.4 m, **+11 pp** at
  3.2 m, **+24 pp** at 6.4 m, **+33 pp** at 12.8 m, **+43 pp** at 25.6 m, **+48 pp**
  at 51.2 m (vs raw-device benchmark);
- **nearest-neighbour resampling is severely worse than bilinear** at all resolutions.

Prior work cited therein agrees in direction: GPS-only under-estimates ascent, DEM
correction *over*-estimates it. Consumer-facing documentation says the same: Strava
prioritises barometric data over its own DEM basemap and smooths DEM-corrected rides
harder; Ride-with-GPS documents DEM-vs-recorded discrepancies as expected behaviour.

## 3. The scale-dependence consensus

Swiss Federal Office of Topography (geo.admin.ch) documents elevation gain as a
**coastline paradox**: finer sampling → more ascent, without a converged "true" value
(their example: walking over a rock adds 0.5 m of "climb"). Field anecdotes show the
size of the effect: doubling GPS sampling interval changed a hike's gain 1052 → 675 ft;
50 ft vs 100 ft app smoothing changed an 18-mile route by ~1200 ft. This is Rapaport's
point, already cited in [literature-context.md](literature-context.md): *there is no
single true elevation gain, only a value at a chosen smoothing scale.* Every number in
§1–2 is therefore benchmark-relative: Menaspà's under-reading is measured against a
long monotone climb (scale-insensitive); Sánchez's over-reading against a
photogrammetric trail survey (fine scale, micro-relief counted as truth).

## 4. Comparison with our journal entries

- **Baro device-level error (lit ~1–5%, consistency 1–2%) vs Entry 6's baro
  under-read of −11% (raw) / −21% (3 m hyst.) against the IGC 5 m DTM
  (`k_DEM = 1.26`, per-ride 1.10–1.54).** Not a contradiction — a scale gap. The
  literature's 2–5% is device-vs-device or vs monotone-climb benchmarks; our −11/−21%
  is baro-vs-*terrain-micro-relief at 5 m*, exactly the regime where §3 says the
  reference definition dominates. The per-ride spread (worst on rough gravel, 1.46–1.54)
  matches the mechanism: the baro reads the smooth road/effective path, the DTM reads
  the terrain. Sánchez 2020's *over*-estimating baro (vs fine photogrammetric truth on
  foot trails) is the same comparison run in the regime where the athlete's path *does*
  follow the micro-relief — runners pay for 20 cm bumps, road bikes don't.
- **DEM ascent inflation (lit: +12 pp @4 m raw, +24–48 pp at 6–50 m grids, trail) vs
  Entry 6's FABDEM +35%, COP30 +50%, SRTM +71% over baro (bilinear, 12 rides) and
  Entry 19's igc5 h₊ > igc30 on 919/922 rides (censo median +14%).** Direction and
  order of magnitude agree; our numbers sit inside the literature's band. The
  nearest-neighbour warning is identically replicated (our NN staircase added ~30 pp;
  ICECET finds NN "does not perform well" everywhere).
- **FABDEM per-point accuracy (lit MAE 1.4–2.9 m, best global DEM) vs Entry 19's
  FABDEM ascent failure (h₊ +57% pooled, +101/135% on flat lowland riders; a 27 km
  ride: 99 m → 391 m).** Both true at once, and that is the point: per-pixel
  metre-level noise on *flat* terrain accumulates into doubled ascent. The DEM
  validation literature stratifies error by land cover and slope but — as far as
  located — never propagates it into accumulated along-track ascent. Entry 19's
  terrain-regime dependence (fine on hilly longões, catastrophic on flat urban) is a
  sharper statement than anything found; Entry 6's "FABDEM ≈ IGC within 6%" was the
  hilly-regime slice of it.
- **Photogrammetric 5 m DTM as benchmark.** The lit uses exactly this class as *truth*
  (Sánchez 2020's Chilean Air Force survey; our IGC-SP). Entry 19's twist — that
  deployment-grade truth at native 5 m *over-charges energy* (censo med |Δ%| 22.1 vs
  12.0 on baro) because real survey micro-relief isn't ridden — has no located
  precedent; the closest is ICECET's "raw 4 m DEM worse than the watch", which agrees.
- **The mitigation matches.** Our σ\* = 10 m pre-smoothing / ~30 m averaging
  (Entries 19–20) is the same lever the lit reaches for: bilinear sampling, harder
  smoothing of DEM-corrected profiles (Strava), post-processing that cuts −5% → −1%
  (Sánchez 2020). And §3 explains why a *fitted* smoothing scale (per-rider kSmooth,
  Entry 20) is legitimate: the "true" scale is the one the vehicle's suspension +
  rider's line actually integrates, which is rider/terrain-dependent (Entry 21).
- **Gap we occupy.** No located study validates DEM- or baro-derived ascent against
  measured *pedalling energy* (`∫P·dt`, 900+ rides, Entry 19) — the literature stops
  at geometry. The energy endpoint is what turns "which h₊ is right?" (ill-posed, §3)
  into a decidable question.

## Sources

- Menaspà P., Impellizzeri F.M., Haakonssen E.C., Martin D.T., Abbiss C.R.,
  *Consistency of commercial devices for measuring elevation gain*, IJSPP 2014 —
  <https://pubmed.ncbi.nlm.nih.gov/24338100/>
- Menaspà et al., *Accuracy in measurement of elevation gain in road cycling* (abstract) —
  <https://www.researchgate.net/publication/297769660_Accuracy_in_measurement_of_elevation_gain_in_road_cycling>
- Sánchez R., Villena M., *Comparative evaluation of wearable devices for measuring
  elevation gain in mountain physical activities*, Proc IMechE Part P, 2020 —
  <https://journals.sagepub.com/doi/10.1177/1754337120918975>
- Sánchez R. et al., *Assessing the impact of DEM resolution on elevation gain
  estimations in trail running*, ICECET 2024 —
  <https://ieeexplore.ieee.org/document/10698606/> (PDF: <http://raimundos.cl/papers/dem_resolution_for_elevation.pdf>)
- Johnson et al., *By cyclists, for cyclists: road grade and elevation estimation from
  crowd-sourced fitness application data*, PLOS One 2023 —
  <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0295027>
- Hawker L. et al., *A 30 m global map of elevation with forests and buildings removed*,
  ERL 2022 — <https://www.researchgate.net/publication/357986448>
- Bielski et al., *Vertical accuracy assessment of freely available global DEMs (FABDEM,
  Copernicus DEM, NASADEM, AW3D30, SRTM) in flood-prone environments*, Int. J. Digital
  Earth 2024 — <https://www.tandfonline.com/doi/full/10.1080/17538947.2024.2308734>
- Wood J., *Accuracy of elevation measurement using GPS* (Garmin Edge 305 audax test) —
  <https://www.staff.city.ac.uk/~jwo/landserf/audax/elevation>
- swisstopo, *Elevation profile — the coastline paradox's trap* —
  <https://www.geo.admin.ch/en/map-viewer-instructions-explanations-elevation-profile>
- Simoni J., *Gotchas when estimating trip elevation gain/loss* —
  <https://justinsimoni.com/gotchas-when-estimating-trip-elevation-gain-loss/>
- Strava elevation FAQ — <https://support.strava.com/hc/en-us/articles/115001294564-Elevation-on-Strava-FAQs>;
  Spoke Twist, *Strava elevation woes* — <https://spoketwist.com/strava-elevation-woes/>
- Ride with GPS, *Grade, elevation, and GPS accuracy FAQ* —
  <https://support.ridewithgps.com/hc/en-us/articles/4419010957467>
