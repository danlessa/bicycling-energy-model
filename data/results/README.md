# Harness outputs — `data/results/`

Per-ride result CSVs written by the validation harnesses in [`src/harness/`](../../src/harness/).
Everything here is **derived**: it regenerates from the primary data in
[`data/inputs/`](../inputs/) with one command per file (run from anywhere; the scripts
resolve their inputs and this directory relative to their own location).

| File | Producer | Journal entry |
|---|---|---|
| `model_comparison.csv` | `python3 src/harness/compare.py` | 1+ (longões scoreboard) |
| `censo_comparison.csv` | `python3 src/harness/censo_compare.py` | 9 |
| `eps_hypothesis.csv` | `python3 src/harness/eps_hypothesis.py` | 8 |
| `eps_sp.csv` | `python3 src/harness/eps_sp_test.py` | 10 |
| `ppaz_comparison.csv` | `python3 src/harness/ppaz_compare.py` | 12 |
| `time_comparison.csv` | `python3 src/harness/time_compare.py` | 13 |
| `jaam_comparison.csv` | `python3 src/harness/jaam_compare.py` | 14 |
| `param_sweep.csv` / `param_sweep_canon.csv` | `python3 src/harness/param_sweep.py` (`SWEEP_CANON=1` for the latter) | 29–30 |
| `longoes_frozen.csv` | `python3 src/harness/longoes_frozen.py` | 31 |
| `perride_invert.csv` | `python3 src/harness/perride_invert.py` (`INVERT_SMOKE=1`, `INVERT_NOFETCH=1`) | 33 |
| `scurve_deficit.csv` | `python3 src/harness/scurve_deficit.py` (`SCURVE_SMOKE=1`) | 34 |
| `e35_residual.csv` | `python3 src/harness/e35_residual.py` (`E35_SMOKE=1`) | 35 |
| `e36_eps0.csv` | `python3 src/harness/e36_eps0.py` (`E36_SMOKE=1`) | 36 |
| `e38_tau.csv` | `python3 src/harness/e38_tau.py` (`E38_SMOKE=1`) | 38 |
| `e39_tau_reg.csv` | `python3 src/harness/e39_tau_reg.py` (`E39_SMOKE=1`) | 39 |
| `e40_roller.csv` | `python3 src/harness/e40_roller.py` (`E40_SMOKE=1`) | 40 |
| `e41_dem_route.csv` | `python3 src/harness/e41_dem_route.py` (`E41_SMOKE=n`; needs the conda python for gdal, the IGC-SP wide raster and ~1.3 GB of FABDEM tiles; ~1 h cold, ~45 min off the profile cache) | 41 |
| `e42_lump.csv` | `python3 src/harness/e42_lump.py` (`E42_SMOKE=1`) | 42 |
| `cda_estimate.csv`, `param_fit.csv` | `python3 src/harness/cda_estimate.py` / `param_fit.mjs` | 15 |
| `danlessa_comparison.csv` | `python3 src/harness/danlessa_compare.py` | 16 |
| `regime_comparison.csv` | `python3 src/harness/regime_compare.py` | 17–18 |
| `igc_resolution_test.csv` | `python3 src/harness/igc_resolution_test.py` | 19 |
| `goal_calibration.csv` | `python3 src/harness/goal_calibration.py` | 20 |
| `scale_trio.csv` | `python3 src/harness/scale_trio.py` | 21 |
| `longoes_verify.csv` | `python3 src/harness/verify.py` | — (VERIFICATION_NOTES) |
| `e26_pairs.json`, `e26_pair_rides.json` | `python3 src/harness/e26_pairs.py` | 26 (endpoint pairs; **GPS**) |
| `e26_grid.csv`, `e26_grid_cal.csv` | `node ../simujaules/docs/grid-e26.mjs` (`E26_BUNDLE=cal`) | 26 (ladder + portals) |
| `e26_portal_profiles.csv` | `python3 src/harness/e26_portal_profiles.py` | 26 (Q2A) |
| `e26_detour.csv` | `python3 src/harness/e26_detour.py` | 26 (detour secondary) |
| `e26_osm_cache/` | pulled by the two Entry-26 harnesses (offline on re-run) | 26 (OSM spans) |

`python3 src/harness/bootstrap_ci.py` (Entry 22) reads these CSVs and gates the
article's published medians against them.

**Everything except this README is gitignored**: the rows carry ride names,
dates and per-ride energies tied to private activities. Coordinate-stripped
aggregates are available on request (see the article's data-availability note).
