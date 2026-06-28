# Empirical ride dataset — `data/activities/`

Ground-truth rides for validating the energy model in
[`energy-model-comparison.html`](../../energy-model-comparison.html): each carries an
elevation profile and (where available) **measured power**, so the *approximate*
closed-form law and the *canonical* forward-dynamics simulation can both be compared
against the rider's actual `∫P·dt`.

## Provenance

Every ride is one hyperlink in the **Activity column (B)** of the **`Atividades v2`**
sheet of `data/longoes.xlsx`. Sources, normalised to **`.fit`** wherever possible:

| Source | Download | Auth | Power |
|---|---|---|---|
| RideWithGPS trip | `trips/<id>.fit` (authed export) | `RWGPS_API_KEY`+`RWGPS_AUTH_TOKEN` | field 7 (W) ✓ |
| RideWithGPS route | `routes/<id>.fit` (course) | same | planned route — none |
| Strava activity | `activities/<id>/export_original` | session cookies | field 7 (W), if a meter was paired |

The RWGPS `.fit` export preserves power/HR/speed/elevation (verified: `∫P·dt` matches
the sheet to <2%). The no-auth public `trips/<id>.json` is the fallback (`fetch.py rwgps`)
and additionally carries weather-derived temperature the `.fit` omits.

**52 activities** — 29 RWGPS trips, 2 RWGPS routes, 21 Strava. Files: **51 `.fit`**, 1 `.gpx`. **44/52 carry measured power.**

### Gaps (no usable power)

- **6 Strava rides from 2020** — BRM200 Campos, S Roque, Barretos, Curitiba 1/2 & 2/2,
  Piracaia — predate the power meter (FIT field present but all `0xFFFF` invalid; HR/
  speed/altitude/cadence still there).
- **2 RWGPS routes** (La Bocainita 2024, Area 51 v2) — planned routes, not rides.
- **1 `.gpx`** — *Assou* (Strava): the original upload was GPX, so Strava cannot export it
  as `.fit`. It has power; it is simply the one file not in `.fit` form.

## Layout

```
data/activities/
  fetch.py        # downloader + power audit + csv builder (stdlib only)
  verify.py       # cross-checks longoes.csv against the track files
  manifest.json   # per-activity metadata + power summary (gitignored)
  rwgps/<source>_<id>.fit    # RideWithGPS trips & routes (gitignored)
  strava/<id>.{fit,gpx}      # Strava originals (gitignored)
```

Raw tracks, `manifest.json` and the CSVs carry GPS / personal data and are **gitignored**;
only `fetch.py`, `verify.py` and this README are committable. The repo may go public.

## Combined CSV — `longoes.csv`

`python3 fetch.py csv` writes **`longoes.csv`**: one row per Activity link, projecting the
per-ride columns of the `Atividades v2` sheet (header row 2) and joining the local `.fit`
path. Map: Title=B, file=manifest, MovingDur=D `MT`, Distance=F, Ascent=G `Uphill`,
Descent=H `Downhill`, Unpaved=I `Off-road` (0..1), AvgElev=K `<Elevation>`, Headwind=L,
Weight=M, CdA=N, TotalWork=O `Work Total`, WorkPedalling=P `Work Bike`, AvgHR=U `<HR>`,
AvgTemp=W `<T>`, P80Temp=X `Tc`, Eps=AA `g_d_eff`, RoadCrr=AC, OffroadCrr=AD, Group=Y `Group?`.
Values are the spreadsheet's own; empty cells stay empty (blank Group ≠ solo). Holds
personal metrics (weight, HR) but no GPS — `git add -f` to commit.

## Verification — `verify.py`

`python3 verify.py` recomputes the *file-derivable* columns from each track (multi-format:
RWGPS/Strava `.fit`, `.gpx`) and compares to `longoes.csv`, writing `longoes_verify.csv`.
Parameters/guesses (weight, CdA, headwind, ε, Crr, group) are not in the files and are
skipped. Latest run — median & 90th-pctile of |Δ%| vs the sheet, n rides, # flagged:

| Metric | n | median \|Δ%\| | p90 \|Δ%\| | #CHECK |
|---|--:|--:|--:|--:|
| distance_km | 52 | 0.0 | 1.0 | 4 |
| moving_h | 50 | 0.8 | 3.5 | 1 |
| work_pedal_kj | 44 | 0.3 | 1.9 | 2 |
| avg_hr | 50 | 0.2 | 3.9 | 5 |
| avg_temp | 28 | 1.4 | 4.0 | 0 |
| p80_temp | 26 | 4.7 | 7.8 | 1 |
| ascent_m | 52 | 11.9 | 34.4 | 17 |
| descent_m | 52 | 10.6 | 36.4 | 16 |
| avg_elev | 52 | 9.2 | 46.4 | 12 |

**Verdict.** The measured quantities — distance, moving time, pedalling work (`∫P·dt`),
HR, temperature — match the sheet to ~1% median: the transcribed values are sound and
the parser is trustworthy. The **elevation columns (ascent/descent/avg elevation) differ
~10%** because the sheet values are hand-rounded (many rides list ascent=descent) and
elevation-gain algorithms vary — relevant since gravity work depends on `h₊`. Outliers:
*RMC200 Mogi* (Strava original is partial, 88/210 km) and *RMC300 Guararema* (RWGPS
distance/work vs the sheet).

## Re-fetching

```sh
source ../../.env                      # RWGPS_API_KEY, RWGPS_AUTH_TOKEN
python3 fetch.py rwgps-fit             # RWGPS trips+routes as authed .fit (incl. private)
python3 fetch.py rwgps                 # fallback: public .json (no auth, adds temperature)
python3 fetch.py strava <cookiejar>    # Strava originals (Netscape cookie jar)
python3 fetch.py audit                 # recompute power summary into manifest.json
python3 fetch.py csv                   # (re)build longoes.csv
python3 verify.py                      # cross-check csv vs files
```
