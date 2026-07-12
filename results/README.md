# Harness outputs — `results/`

Per-ride result CSVs written by the validation harnesses in [`harness/`](../harness/).
Everything here is **derived**: it regenerates from the primary data in
[`data/`](../data/) with one command per file (run from anywhere; the scripts
resolve their inputs and this directory relative to their own location).

| File | Producer | Journal entry |
|---|---|---|
| `model_comparison.csv` | `python3 harness/compare.py` | 1+ (longões scoreboard) |
| `censo_comparison.csv` | `node harness/censo_compare.mjs` | 7 |
| `eps_hypothesis.csv` | `node harness/eps_hypothesis.mjs` | 9 |
| `eps_sp.csv` | `node harness/eps_sp_test.mjs` | 10 |
| `ppaz_comparison.csv` | `node harness/ppaz_compare.mjs` | 12 |
| `time_comparison.csv` | `node harness/time_compare.mjs` | 13 |
| `jaam_comparison.csv` | `node harness/jaam_compare.mjs` | 14 |
| `cda_estimate.csv`, `param_fit.csv` | `node harness/cda_estimate.mjs` / `param_fit.mjs` | 15 |
| `danlessa_comparison.csv` | `node harness/danlessa_compare.mjs` | 16 |
| `regime_comparison.csv` | `node harness/regime_compare.mjs` | 17–18 |
| `igc_resolution_test.csv` | `node harness/igc_resolution_test.mjs` | 19 |
| `goal_calibration.csv` | `node harness/goal_calibration.mjs` | 20 |
| `scale_trio.csv` | `node harness/scale_trio.mjs` | 21 |
| `longoes_verify.csv` | `python3 harness/verify.py` | — (VERIFICATION_NOTES) |

`node harness/bootstrap_ci.mjs` (Entry 22) reads these CSVs and gates the
article's published medians against them.

**Everything except this README is gitignored**: the rows carry ride names,
dates and per-ride energies tied to private activities. Coordinate-stripped
aggregates are available on request (see the article's data-availability note).
