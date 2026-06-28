# DEM vs recorded elevation — FABDEM, SRTM, COP30

Does an external DEM give a better elevation/ascent than the device's recorded track?
This bears directly on the `k_h` ascent-noise work
([../data/MODEL_COMPARISON_JOURNAL.md](../data/MODEL_COMPARISON_JOURNAL.md) Entry 5,
[../notas.md](../notas.md) v2): the closed-form climb term `β·h₊` is linear in ascent, so
the *ascent source* matters a lot. Three independent 30 m DEMs were sampled at every
track point and compared to the recorded barometric elevation.

- **FABDEM** V1-2 (bare-earth: forest & buildings removed) — `telhas.pedalhidrografi.co/fabdem/`
- **COP30** Copernicus GLO-30 (DSM) — AWS `copernicus-dem-30m`
- **SRTM** GL1 30 m (DSM) — AWS `elevation-tiles-prod/skadi`

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
variation vs empirical." Quantifying it as `k_h = recorded-baro / DEM` (bilinear, 3 m-hyst),
the scalar that brings a DEM-derived ascent/descent back to the road reference:

| DEM | k_h(h₊) | k_h(h₋) |
|---|--:|--:|
| **FABDEM** | **0.74** | **0.73** |
| COP30 | 0.67 | 0.66 |
| SRTM | 0.59 | 0.58 |

- **`k_h(h₊) ≈ k_h(h₋)`** — the inflation is symmetric, so one factor per DEM corrects both
  (matching the model's `k_h·β·(h₊ − ε·h₋)`).
- **FABDEM's k_h ≈ 0.74 equals the recorded baro's own deadband k_h** (~0.74 at τ=2): a
  bare-earth DEM sampled bilinearly is about as good as the raw baro and needs the same
  correction. The DSMs need more (COP30 0.67, SRTM 0.59).
- These are São-Paulo-tile values; `k_h` is source/terrain-dependent — calibrate per region.

## Implications for the energy model

- **The recorded barometric ascent is the best `h₊` source — do *not* replace it with a
  DEM-sampled ascent.** Even with correct bilinear sampling, DEM-along-GPS ascent is
  35–71 % too high; it would wreck the `β·h₊` climb term far worse than the baro noise the
  `k_h` correction targets. (With nearest-neighbour it is 65–114 % — a trap to avoid.)
- This **reinforces the `k_h` approach**: the recorded baro only needs mild de-noising
  (Entry 5: ~20 % of raw baro `h₊` is sub-3 m jitter), and the true road ascent is likely
  *at or slightly below* the 3 m-hysteresis baro value — the opposite direction from a DEM.
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
