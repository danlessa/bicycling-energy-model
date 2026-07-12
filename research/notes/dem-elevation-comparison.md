# DEM vs recorded elevation — FABDEM, SRTM, COP30

Does an external DEM give a better elevation/ascent than the device's recorded track?
This bears directly on the `k_h` ascent-noise work
([MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md) Entry 5,
[../notas.md](../../notas.md) v2): the closed-form climb term `β·h₊` is linear in ascent, so
the *ascent source* matters a lot. Three 30 m global DEMs — and a 5 m local DTM — were
sampled at every track point and compared to the recorded barometric elevation.

- **FABDEM** V1-2 (bare-earth: forest & buildings removed) — `telhas.pedalhidrografi.co/fabdem/`
- **COP30** Copernicus GLO-30 (DSM) — AWS `copernicus-dem-30m`
- **SRTM** GL1 30 m (DSM) — AWS `elevation-tiles-prod/skadi`
- **IGC-SP 2010** (bare-earth DTM, **5 m**, aerophotogrammetry; SIRGAS2000/UTM-23S) —
  limited to the São Paulo region, covering 10 of the 12 test rides

All three are WGS84, ~30 m, read with GDAL (`gdallocationinfo`). Scripts:
[harness/dem/extract_coords.mjs](../../harness/dem/extract_coords.mjs) (track → lon/lat/ele per ride),
[harness/dem/compare_dem.py](../../harness/dem/compare_dem.py) (sample + compare).

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

## Result 3 — k_DEM (geometric) per elevation source

`k_DEM = IGC / source` is the **geometric** correction (source → 5 m survey truth), over the
10 IGC-covered rides (h₊ 3 m-hyst, bilinear). It is the solid result here:

| source | Σ h₊ | vs IGC | **k_DEM** |
|---|--:|--:|--:|
| recorded baro | 13 622 (raw 15 292) | −21 % (raw −11 %) | 1.26 |
| **IGC** 5 m (bare-earth) | **17 162** | reference | 1.00 |
| FABDEM 30 m (bare-earth) | 18 160 | +6 % | 0.95 |
| COP30 30 m (DSM) | 20 310 | +18 % | 0.84 |
| SRTM 30 m (DSM) | 22 951 | +34 % | 0.75 |

**Per-ride `k_DEM`** (= IGC/source per ride) — the spread shows its terrain dependence:

| source | median | min–max |
|---|--:|--:|
| recorded baro | 1.23 | 1.10–1.54 |
| FABDEM 30 m | 0.93 | 0.81–1.09 |
| COP30 30 m | 0.84 | 0.79–0.95 |
| SRTM 30 m | 0.72 | 0.59–0.90 |

- **FABDEM is tight and ≈ the 5 m truth** (0.93 ± ~15 %) — the best, most consistent 30 m
  source; its geometric error is small (matching first-principles intuition).
- **The baro's under-recording is terrain-dependent** (1.10–1.54×): worst on rough/gravel
  rides (r2 arrochai 1.54, Cantareira 2 1.46), where the altimeter smooths most.
- **SRTM is the noisiest** (0.59–0.90), worst on gravel (canopy/roughness).

**No source is ground truth.** The two bare-earth sources agree (IGC 5 m ≈ FABDEM 30 m, within
6 %) — a strong cross-check. The recorded baro *under*-records but is correct at **bridges and
tunnels**, which the DTMs cannot see (a bridge dips into the spanned valley, a tunnel climbs
over the pierced ridge → the DTM over-records there). The DSMs *over*-record (canopy). Truth
bracketed — baro low, DTM high.

**The model's energy `k_h` is a separate, milder correction — not yet cleanly measured.** It
maps geometry → *pedalling energy* (lower, because momentum carries the rider over rollers
without paying `mg·h`). An earlier estimate (`k_h(FABDEM) ≈ 0.56`) **over-stated it** — it
scaled from the baro's Entry-5 `k_h ≈ 0.74`, which is entangled with the `v_f` error (Entry 4)
and a different pipeline. With small `k_DEM` + a mild momentum term, bare-earth `k_h` should be
**~0.8–0.9**. **TODO:** fit `k_h` per source by running the approximate (with corrected `v_f`)
against the empirical `∫P·dt`. (The canonical needs no `k_h` — it handles momentum via KE.)

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
