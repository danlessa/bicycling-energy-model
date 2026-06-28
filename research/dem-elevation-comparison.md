# DEM vs recorded elevation — FABDEM, SRTM, COP30

Does an external DEM give a better elevation/ascent than the device's recorded track?
This bears directly on the `k_h` ascent-noise work
([../data/MODEL_COMPARISON_JOURNAL.md](../data/MODEL_COMPARISON_JOURNAL.md) Entry 5,
[../notas.md](../notas.md) v2): the closed-form climb term `β·h₊` is linear in ascent, so
the *ascent source* matters a lot. Three 30 m global DEMs — and a 5 m local DTM — were
sampled at every track point and compared to the recorded barometric elevation.

- **FABDEM** V1-2 (bare-earth: forest & buildings removed) — `telhas.pedalhidrografi.co/fabdem/`
- **COP30** Copernicus GLO-30 (DSM) — AWS `copernicus-dem-30m`
- **SRTM** GL1 30 m (DSM) — AWS `elevation-tiles-prod/skadi`
- **IGC-SP 2010** (bare-earth DTM, **5 m**, aerophotogrammetry; SIRGAS2000/UTM-23S) —
  limited to the São Paulo region, covering 10 of the 12 test rides

All three are WGS84, ~30 m, read with GDAL (`gdallocationinfo`). Scripts:
[research/dem/extract_coords.mjs](dem/extract_coords.mjs) (track → lon/lat/ele per ride),
[research/dem/compare_dem.py](dem/compare_dem.py) (sample + compare).

**Sampling matters: use bilinear, not nearest.** `gdallocationinfo` defaults to **nearest
neighbour** (the containing pixel's value). On a 30 m grid sampled by a ~50 m-spaced,
GPS-scattered track that snaps to a staircase — every pixel-boundary crossing is a discrete
jump — which **inflates ascent by ~30 percentage points** here. **Bilinear** (`-r bilinear`)
follows the sub-pixel position smoothly and is the correct choice; both are shown below.

**Scope:** the 12 rides whose track lies entirely within the dense São Paulo tile
**S24W047** (Cantareira climbs, flat valleys, gravel) — enough for a consistent result
across varied terrain. The 44 rides span 40 one-degree tiles (down to Roraima, Rondônia,
even Ukraine/Poland); extending is just more tile downloads.

## Result 1 — DEMs are accurate *terrain* models

Sampling the DEMs at the track points and comparing the elevation **shape** (after
removing each ride's mean offset, which is baro-calibration + vertical-datum drift):

| DEM | median bias vs recorded | shape RMS |
|---|--:|--:|
| FABDEM | −6.8 m | 7.3 m |
| COP30 | −2.8 m | 8.0 m |
| SRTM | +0.3 m | 7.8 m |

The DEMs track the recorded elevation to **~7–8 m RMS** with small bias — good terrain
accuracy. Note **SRTM sits ~7 m above FABDEM**: that gap is the **canopy + buildings**
SRTM/COP30 (surface models) retain and FABDEM (bare-earth) removes — visible even at a
single São Paulo point (SRTM 764 m vs FABDEM 738 m).

## Result 2 — but DEM *ascent* (sampled along the GPS track) is inflated

Cumulative ascent `h₊` (3 m-hysteresis) summed over the 12 rides, both sampling modes:

| source | Σ h₊, nearest | Σ h₊, **bilinear** | vs recorded (bilinear) |
|---|--:|--:|--:|
| **recorded (barometric)** | — | **15 833 m** | — |
| FABDEM | 26 120 m | **21 436 m** | **+35 %** |
| COP30 | 29 840 m | 23 759 m | **+50 %** |
| SRTM | 33 895 m | 26 996 m | **+71 %** |

Two effects:

1. **Nearest-neighbour sampling alone added ~30 percentage points** (FABDEM +65 %→+35 %) —
   a pure staircase artifact of snapping a sub-pixel track to a 30 m grid. **Always sample
   a DEM with bilinear** for along-track elevation.
2. **A real residual remains even with bilinear** (FABDEM +35 %, COP30 +50 %, SRTM +71 %),
   because a **DEM is the terrain, not the road**:
   - A road is **engineered** — cuts/fills/embankments/bridges — so the road surface is
     *smoother* than the natural terrain a DEM reports along the same line.
   - **SRTM/COP30 keep canopy and buildings**; FABDEM removes them — exactly why FABDEM
     stays smoothest (+35 % vs SRTM's +71 %).
   - **GPS horizontal scatter** on slopes adds spurious vertical movement.

The recorded **barometric** elevation measures the **road altitude directly**, so it is
inherently smooth and gives the lowest, most road-realistic ascent — even after the
sampling method is fixed.

## Result 3 — k_h for DEM-derived h₊ and h₋

The model's `k_h` ([../notas.md](../notas.md) v2) is "the factor that adjusts DEM height
variation vs empirical." Quantifying it as `k_h = recorded-baro / source` (bilinear,
3 m-hyst), the scalar that brings a source-derived ascent/descent back to the road
reference — including the **IGC-SP 2010 5 m DTM** (bare-earth aerophotogrammetry, covers 10
of the 12 rides):

| source | res | shape RMS | Σ h₊ vs rec | k_h(h₊) | k_h(h₋) |
|---|--|--:|--:|--:|--:|
| SRTM (DSM) | 30 m | 7.6 m | +71 % | 0.59 | 0.58 |
| COP30 (DSM) | 30 m | 7.7 m | +50 % | 0.67 | 0.66 |
| FABDEM (bare-earth) | 30 m | 7.1 m | +35 % | 0.74 | 0.73 |
| **IGC (bare-earth)** | **5 m** | **6.4 m** | **+8 %** | **0.92** | **0.92** |

- **`k_h(h₊) ≈ k_h(h₋)`** for every source — symmetric, so one factor corrects both.
- The table above is `k_h` **relative to the baro**, and the baro is **not** ground truth: it
  lags and smooths, so short climbs read as ~null grade. Taking the **5 m IGC DTM as the
  reference** instead (the bare-earth survey), the picture *inverts* — the baro is the LOW
  outlier (over the 10 IGC-covered rides, h₊ 3 m-hyst):

| source | Σ h₊ vs IGC 5 m | k_h = IGC/source |
|---|--:|--:|
| recorded baro (3 m) | −21 % (raw −11 %) | 1.26 |
| FABDEM 30 m | +6 % | 0.95 |
| COP30 30 m | +18 % | 0.84 |
| SRTM 30 m | +34 % | 0.75 |

- **The two bare-earth sources agree** (IGC 5 m ≈ FABDEM 30 m, within 6 %, ~17–18 km) — a
  strong cross-check on the real terrain ascent.
- **No source is ground truth.** The baro *under*-records (lag / missed climbs) yet is
  correct at **bridges and tunnels**, which the DTMs cannot see (a bridge dips into the
  spanned valley, a tunnel climbs over the pierced ridge → the DTM over-records there). The
  truth is bracketed — baro low, DTM high.
- These DEM `k_h` correct *geometry*; the **model's** `k_h` (notas v2) is different — it maps
  geometry to *pedalling energy*, which is lower still because momentum carries the rider
  over rollers without paying `mg·h` (journal Entry 6). Don't conflate them.

## Implications for the energy model

- **No single source is ground truth for geometric ascent.** The bare-earth DTMs (IGC 5 m ≈
  FABDEM 30 m) agree and are the best terrain reference; the baro *under*-records (lag/missed
  climbs, −11 to −21 % vs IGC) but is right at bridges/tunnels the DTMs miss; the DSMs
  *over*-record (canopy). Use a bare-earth DTM for geometry; the baro for road altitude at
  engineered features.
- **For the energy model, the geometric question is secondary.** `β·h₊` should use the
  *energy-effective* ascent, which is *below* even the baro (momentum carries the rider over
  rollers without paying `mg·h`), so the Entry-5 `k_h ≈ 0.74` deadband on the baro is the
  right lever regardless of the geometric truth. Do **not** swap in a raw DEM-along-GPS
  ascent — the DSMs run 18–34 % above the bare-earth truth (50–71 % above the baro), which
  would wreck the climb term. (NN sampling adds another ~30 pp — always use bilinear.)
- **If a DEM is the only elevation available** (a planned route with no baro track), use
  **FABDEM** (bare-earth, smoothest) and smooth aggressively — but expect it to over-state
  climbing; a DSM (SRTM/COP30) is materially worse over forest/urban terrain.
- DEMs remain useful for the **elevation profile / grade** (Result 1's 7–8 m accuracy) and
  as a **sanity check / void-fill** for a missing baro — just not for raw ascent summation.

## Caveats

- 12 rides in one tile (consistent across all 12, but São Paulo terrain only). Extending
  to the other 39 tiles is mechanical (download + VRT mosaic).
- Vertical datums differ (FABDEM/COP30 EGM2008, SRTM EGM96, baro device-calibrated) — this
  affects *bias* (small here, and removed for the shape RMS) but **not** ascent.
- Bilinear is used for the headline numbers; cubic/cubicspline would smooth marginally more
  but bilinear is the standard correct choice for along-track DEM sampling.
- The residual inflation (terrain-vs-road, canopy, GPS scatter) isn't fully decomposed —
  the practical point is that no along-track DEM sampling recovers the engineered road
  profile that the barometer measures directly.

## Sources

- FABDEM: Hawker et al. 2022, *Environ. Res. Lett.* — bare-earth edit of Copernicus GLO-30.
  Tiles served from `telhas.pedalhidrografi.co/fabdem/`.
- Copernicus GLO-30: ESA/Airbus, [AWS Open Data `copernicus-dem-30m`](https://registry.opendata.aws/copernicus-dem/).
- SRTM GL1 30 m: NASA/USGS, via [`elevation-tiles-prod`](https://registry.opendata.aws/terrain-tiles/) skadi HGT.
