# Closed-form energy models vs the Pedal Hidrográfico urban rides

A second, independent check of the three energy models — **canonical**, **smooth
approximate**, **poor-man's approximate** — on the collective's *own* rides, distinct from
the 44 long power-meter rides used in [MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md)
Entries 1–8. Full log: Journal **Entry 9**. Harness:
[../data/activities/censo_compare.mjs](../data/activities/censo_compare.mjs); downloader
[../data/activities/fetch_censo.py](../data/activities/fetch_censo.py).

*(Corrected per Journal Entry 11's code-fix pass: "6 of 7" → "5 of 7" cadence-clear rides below.)*

## Dataset

Activity links come from `censo-hidrografico.xlsx` (columns *Ativ. Strava* / *Ativ. RWGPS*),
**RWGPS preferred**. **Every factual quantity is derived from the downloaded activity**
(geometry, FIT-extracted regime powers, v_f, ∫P·dt) — the censo's own energy columns are *not*
used. 87 links → 70 downloadable (16 are other riders' Strava, not exportable) → 69 with power
→ **62 after a physical-plausibility cut**.

These are short **urban São Paulo social rides**: median **33 km / 454 m climb / 16.5 km/h /
~14 m·km⁻¹** — hilly but **stop-go** (traffic lights, intersections, corners), and slower than
the long open rides. That contrast is the point of the cross-check.

## Method

- **Benchmark:** measured pedalling energy ∫P·dt per ride.
- **canonical:** forward sim fed the ride's FIT-extracted climb/flat/descent powers.
- **smooth approx:** `α_r·x + α_a·x_flat + β(h₊ − ε·h₋)` on a 2 m deadband-smoothed profile.
- **poor-man's:** same, raw profile, gravity scaled by `k_smooth = 1 − 0.003·x/h₊` (no smoothing).
- **Assumed rider** (only thing not derived): m = 78 kg, CdA = 0.40, C_rr = 0.008, 100 % paved,
  ρ = 1.13, wind = 0, k_eff = 0.98. **ε is swept**: closed-form ε_geom (notas) and constants 0.00–0.25.

## Physical floor — drop the not-fully-pedalled rides

Pedalling energy must cover the (momentum-corrected) climbing PE `mg·h₊_sm/k_eff`. **7 rides
measure below it** (down to 53 %) — impossible for a fully-pedalled ride. Using **cadence** as
the test (pedalling ⇔ cadence > 0): on **5 of the 7**, cadence coverage is 73–100 % and the
walking signal (moving < 4 km/h **with cadence 0**) is only **~1 %**. So those riders were
*pedalling, not walking* — the deficit is a **power-channel problem** (power dropping out while
cadence kept logging, or an under-reading meter), not the bike being pushed. The other 2
(cadence coverage 31 % and 56 %) are genuinely ambiguous — low enough that walking isn't ruled
out, likely a fuller sensor dropout for at least one. Excluded from the headline either way.

## Result — 62 clean rides, Δ% vs measured ∫P·dt

| model | med \|Δ%\| | medΔ% |
|---|--:|--:|
| canonical (fed ride powers) | 6.5 | −3.4 |
| smooth approx · ε = 0.20 | 4.7 | −0.8 |
| **poor-man's · ε = 0.20** | **3.9** | +1.1 |
| poor-man's · ε = geom (0.29) | 6.4 | −3.3 |
| smooth approx · ε = geom (0.29) | 7.6 | −4.9 |
| both · ε = 0.00 | 7.5 / 10.5 | +7.4 / +10.5 |

## Conclusions

1. **All three models reproduce measured energy to ~4–7 % median** — with a *generic assumed
   rider*, not per-ride fitted params. As a **planning tool** the closed form lands within ~5 %.
2. **The poor-man's scalar `k_smooth` is as accurate as the full forward simulation** here
   (3.9 % vs 6.5 %). The low-compute shortcut costs nothing on real urban rides.
3. **Descent recovery is real and needed** — ε = 0 over-predicts +7…+10 %. The error floor sits
   at **ε ≈ 0.15–0.20**; ε-sensitivity is ~12–14 pp across the full 0–0.29 ladder.
4. **The geometry closed-form ε_geom (median 0.29) over-credits descent recovery here**, causing
   ~3–5 % under-prediction. ε_geom assumes *free coasting*, but São Paulo's riding is **stop-go** —
   constant braking for traffic, lights and corners suppresses recovery below the coasting ideal.
   That is the **braking penalty** (Entry 8's intuition #4) the open rural rides couldn't isolate.
   **Use ε_geom (or higher) on open routes you can coast; a flat ε ≈ 0.20 on urban stop-go ones.**
   (A slightly low assumed C_rr for rough city asphalt may also contribute.)

## Privacy

The raw tracks (`censohidrografico/`), the manifest, the derived CSV, and `censo-hidrografico.xlsx`
itself (carries attendance data) are **gitignored**. Only the downloader and the harness are committed.
