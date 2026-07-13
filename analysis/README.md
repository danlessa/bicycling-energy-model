# analysis/ — the research workflow in Python

A pure-Python (stdlib-only, no dependencies) port of the research workflow,
so the analysis can be **independently reviewed and verified** without
reading JavaScript. Three pieces:

- **`bem/`** — the engine/parser package. Line-by-line transliterations of
  the JS reference implementations (the app `applet/index.html`
  and the frozen JS in `parity/reference.mjs`), same names, same
  evaluation order:
  `canonical`, `approximate`, `v2_edge`, `approx_time`, `flat_eq_speed`,
  `eps_geom`, `deadband`/`ascent_hyst`/`smooth_elevation`, `parse_fit`,
  `pts_from_fit`, `build_profile`, `pts_from_gpx`, `extract_regime_powers`,
  `eps_from_balance`, `measured_flat_speed`, and the per-ride pipeline
  `analyze_ride` (compare.py wiring: dx = 5 m, deadband τ = 2 m, mean
  regime powers, auto v_f, v_max 38, v_start 15 km/h).
- **`parity/`** — the cross-language verification harness. Generates
  synthetic profiles, parameter grids and a synthetic binary FIT file,
  runs BOTH implementations (the JS functions are extracted verbatim from
  the app/harness sources at run time — no copies to drift), and asserts
  agreement to float64 round-off. **This is the evidence that the Python
  port computes the same thing as the JS the journal used.** Run:

  ```sh
  cd analysis/parity && python3 run_parity.py   # needs node in PATH
  ```

- **`journal.qmd`** — a Quarto notebook that mirrors
  `research/notes/MODEL_COMPARISON_JOURNAL.md` entry by entry, with runnable
  Python cells. Synthetic demonstrations run anywhere; cells that
  reproduce measured numbers detect the local (gitignored) tracks and skip
  gracefully when absent. Render with `quarto render analysis/journal.qmd`
  or convert to Jupyter with `quarto convert`.

## Sync rule

`bem/` is **the** implementation of the engines: since the harnesses were
converted from JS to Python they import from here, so there is no longer a
fleet of `.mjs` copies to keep in step. Exactly **two** copies remain — `bem/`
and the standalone app (`applet/index.html`, deliberately dependency-free
vanilla JS). A change to any engine or parser must land in both, and
`parity/run_parity.py` must pass afterwards: it evaluates the frozen verbatim
JS in `parity/reference.mjs` and asserts `bem` agrees, which makes the rule
machine-checkable instead of aspirational.

## Reproducing the journal scoreboards

With the local (never-committed) tracks in place, the per-ride pipeline
reproduces the harness rows:

```python
import sys; sys.path.insert(0, "analysis")
from bem import analyze_ride, load_pts
r = analyze_ride(load_pts("data/activities/rwgps/ride.fit"),
                 {"m": 74.3, "crr": 0.008, "cda": 0.4, "rho": 1.13,
                  "keff": 0.98, "wind_kmh": 0}, eps=0.20)
print(r["emp_kj"], r["canon_kj"], r["cfS_kj"])
```

`journal.qmd` wraps exactly this into per-entry reproduction cells.
