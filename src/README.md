# src/ — the research workflow in Python

A pure-Python (stdlib-only, no dependencies) port of the research workflow,
so the analysis can be **independently reviewed and verified** without
reading JavaScript. Two pieces:

- **`bicycling_energy_model/`** — the engine/parser package. Line-by-line
  transliterations of the JS reference implementation (the app
  `applet/index.html`), same names, same evaluation order:
  `canonical`, `approximate`, `v2_edge`, `approx_time`, `flat_eq_speed`,
  `eps_geom`, `deadband`/`ascent_hyst`/`smooth_elevation`, `parse_fit`,
  `pts_from_fit`, `build_profile`, `pts_from_gpx`, `extract_regime_powers`,
  `eps_from_balance`, `measured_flat_speed`, and the per-ride pipeline
  `analyze_ride` (compare.py wiring: dx = 5 m, deadband τ = 2 m, mean
  regime powers, auto v_f, v_max 38, v_start 15 km/h).
- **`harness/`** — the validation harnesses (the repo `CLAUDE.md` maps
  script → journal entry). They import the engines/parsers from
  `bicycling_energy_model` rather than carrying copies; the tracks they
  read live in `data/inputs/activities/`, their outputs in `data/results/`
  (both gitignored).

**JS parity — retired.** A cross-language parity harness used to generate
synthetic profiles, parameter grids and a synthetic binary FIT file, run
both implementations (this package and the frozen verbatim JS of the retired
harness engines), and assert agreement to float64 round-off — 8 514
comparisons within 1e-9 relative. That was the evidence that the Python port
computes the same thing as the JS the journal used; having proven the port,
the harness was retired, and git history keeps it.

The Quarto notebook that mirrors the journal entry by entry lives at
`research/journal/journal.qmd`.

## Sync rule

`bicycling_energy_model/` is **the** implementation of the engines: since the
harnesses were converted from JS to Python they import from here, so there is
no longer a fleet of `.mjs` copies to keep in step. Exactly **two** copies
remain — `bicycling_energy_model/` and the standalone app
(`applet/index.html`, deliberately dependency-free vanilla JS). A change to
any engine or parser must land in both; with the JS parity harness retired,
that rule is kept by review rather than machine-checked.

## Reproducing the journal scoreboards

With the local (never-committed) tracks in place, the per-ride pipeline
reproduces the harness rows:

```python
import sys; sys.path.insert(0, "src")
from bicycling_energy_model import analyze_ride, load_pts
r = analyze_ride(load_pts("data/inputs/activities/rwgps/ride.fit"),
                 {"m": 74.3, "crr": 0.008, "cda": 0.4, "rho": 1.13,
                  "keff": 0.98, "wind_kmh": 0}, eps=0.20)
print(r["emp_kj"], r["canon_kj"], r["cfS_kj"])
```

`research/journal/journal.qmd` wraps exactly this into per-entry reproduction
cells.
