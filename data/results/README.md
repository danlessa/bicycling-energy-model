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
| `perride_invert.csv` | `python3 src/harness/perride_invert.py` (`INVERT_NOFETCH=1`; `INVERT_SMOKE=1` writes `perride_invert.SMOKE.csv` — before Entry 47 it overwrote the canonical file) | 33 |
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
| `skc_comparison.csv` | `python3 src/harness/skc_compare.py` | 43 (D6, four European riders; **GPS**) |
| `skc_invert.csv` | `python3 src/harness/skc_invert.py` | 43 amendment arm A (D6, regime-consistent aero) |
| `skc_descent_occupancy.csv` | `python3 src/harness/skc_invert.py` | 43 amendment arm B (descent pedalling, all corpora) |
| `skc_eps_vs_pedal.csv` | `python3 src/harness/skc_eps_vs_pedal.py` | 43 amendment arm C (pedalling vs deficit) |
| `e44_scurve_cells.csv`, `e44_scurve_fits.csv` | `python3 src/harness/e44_scurve.py` | 44 (S-curve reopened; occupancy sigmoids) |
| `e45_ridelevel.ledger.csv`, `e45_ridelevel.paper.csv` | `E45_TARGET={ledger,paper} python3 src/harness/e45_ridelevel.py` | 45 (ride-level form contest) |
| `e45_flatseg.csv` | `python3 src/harness/e45_flatseg.py` | 45 amendment (flat-terrain probe) |
| `e51_flatconst.csv` | `python3 src/harness/e51_flatconst.py` | 51 (replacement flat ε, train/test on D3–D6 under P_f,r) |
| `e50_sensitivity.csv` | `python3 src/harness/e50_sensitivity.py` (`E50_SMOKE=1`) | 50 (Sobol variance decomposition of F1–F4 error over m, CdA, Crr, ε) |
| `e49_affine.csv` | `python3 src/harness/e49_affine.py` (`E49_SMOKE=1`) | 49 (affine deficit k₁·ε_coast + k₂; four scopes: P_f,r and P_a,g × gated/all) |
| `e48_equiv.csv` | `python3 src/harness/e48_equiv.py` (`E48_SMOKE=1`) | 48 (TOST equivalence, margin ±1.0 pp, seed 44) |
| `e46_switch.csv` | `python3 src/harness/e46_switch.py` | 46 (regime switch, four arms; a **second-order** output — reads `e47_formselect.csv` rather than the tracks) |
| `e47_formselect.csv` | `python3 src/harness/e47_formselect.py` (`E47_SMOKE=1`) | 47 (deficit-form selection; D1∪D2 calibration + the D3–D6 in-sample arm) |
| `e63_tolls.csv`, `e63_split.csv` (+ `.E63_TAUN2p0` arm) | `python3 src/harness/e63_f5_kebuffer.py` (`E63_SMOKE=1`, `E63_TAUN=2.0`, `E63_DECOMP=1`, `E63_REBUILD=1`) | 63 (F5, the KE-buffer valley toll vs the fitted deadband; per-ride toll sums cached on the 12-arm v_b grid so every refit is arithmetic; joins `e52_aggregates.csv` by ride label). Entry 64 adds `vb_meas_kmh`/`toll_vbm` columns and the F5f/F5m rows |
| `e63_loro.E63_TAUN2p0.csv`, `e63_taupred.E63_TAUN2p0.csv` (+ `.E63_TAUN0p0` filterless arm) | `E63_TAUN=2.0 E63_LORO=1` / `E63_TAUPRED=1 python3 src/harness/e63_f5_kebuffer.py` (`E63_TAUN=0.0` for the amendment arm) | 64 (leave-one-rider-out contest F3 vs F5f/F5m; per-rider τ* vs the measured-h_KE prediction; the τ=0 arm isolates the toll's own share of the F2→F3 gap) |
| `e63_{tolls,split,loro}.E63_TAUN0p0_E63_RAINFLOW1.csv`, `…_E63_SMOOTH15.csv` | `E63_TAUN=0.0 E63_RAINFLOW=1` / `E63_SMOOTH=15 python3 src/harness/e63_f5_kebuffer.py` (+ `E63_LORO=1`) | 65 (the two rival fragmentation fixes — rainflow pairing and Gaussian smoothing — both negative; smooth tolls CSV carries the `sm_*` component columns) |
| `e66_drift.csv` | `python3 src/harness/e66_driftprobe.py` (`E66_SMOKE=1`, `E66_REBUILD=1`) | 66 (closure-pair drift probe, no DTM; scalar drift stats per ride — the strong baro-drift attribution refuted, P1b ρ ≈ 0) |
| `e67_signature.csv`, `e67_stability.csv` | `python3 src/harness/e67_residual.py` (`E67_SMOKE=1`) | 67 (the residual decomposed: coupling weak everywhere, τ\* non-stationary, F3's constants age ~4.7× worse than F5f's within riders — transferable-physics share of the deadband's unique ~25 pp ≈ 0) |
| `e63_tolls.E63_TAUN{1p0,1p5,3p0,4p5,6p0}.csv` | `E63_TAUN=<x> E63_REBUILD=1 E63_F5FCV=1 python3 src/harness/e63_f5_kebuffer.py` | 68 (the τ_n sweep: F5f CV monotone to the F3 anchor, toll margin → 0; the floor needs a measured pin — E66's drift amplitude) |
| `e69_{pins,frontier,loro,aging}.csv` (+ `e63_tolls.E63_TAUN{1p8,2p2,4p0}.csv` walks, `e63_loro`/`e67_*` `.E63_TAUN{3p0,4p5}` cross-checks) | `python3 src/harness/e69_frontier.py` (`E69_SMOKE=1`) | 69 (the frontier collapses: keepability flat in the floor — the harm is fitting τ, not its size; F5p, pinned per corpus by measured drift, matches F3's CV with zero chosen constants and transfers best, p = 0.0001) |

`python3 src/harness/bootstrap_ci.py` (Entry 22) reads these CSVs and gates the
article's published medians against them.

**Everything except this README is gitignored**: the rows carry ride names,
dates and per-ride energies tied to private activities. Coordinate-stripped
aggregates are available on request (see the article's data-availability note).
