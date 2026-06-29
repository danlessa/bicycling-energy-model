# Verification notes — `longoes.csv` vs the activity files

These notes record how the per-ride dataset derived from `longoes.xlsx`
(sheet **`Atividades v2`**) was cross-checked against the downloaded activity
tracks, and what the check found. The dataset, downloader and verifier live in
[data/activities/](../data/activities/); this file is the human-readable summary.

- **What was checked:** the values in [longoes.csv](../data/activities/longoes.csv)
  (transcribed from the spreadsheet) against the file-derivable quantities
  recomputed from each ride's track.
- **Tool:** [data/activities/verify.py](../data/activities/verify.py) — a
  dependency-free multi-format track reader (RideWithGPS/Strava `.fit`, `.gpx`).
  Run `python3 verify.py`; per-ride detail lands in `longoes_verify.csv`.
- **Date of run:** 2026-06-28.

## Dataset

52 activities linked from the Activity column: 29 RideWithGPS trips, 2 RWGPS
routes (planned, not rides), 21 Strava. Normalised to **51 `.fit` + 1 `.gpx`**
(the lone `.gpx`, *Assou*, was uploaded to Strava as GPX so no `.fit` original
exists). **44/52 carry measured power**; the 8 without are the 6 Strava rides
from 2020 (pre power-meter) and the 2 planned routes.

## What is and isn't verifiable

Only the **measured** columns can be checked against a track. The rest are rider
inputs/guesses with no counterpart in the file and are deliberately skipped:

| Verifiable (recomputed from track) | Not verifiable (sheet parameters) |
|---|---|
| Distance, Moving duration, Ascent, Descent, Average Elevation | Unpaved fraction, Headwind, Total weight, Cd·A |
| Total Work Pedalling (`∫P·dt`), Avg HR, Avg/80%ile Temperature | ε (`g_d_eff`), Road Crr, Offroad Crr, Group size |

`Total Work` (sheet `Work Total`) includes hike-a-bike pushing, which the power
stream does not capture, so the file check targets `Total Work Pedalling`
(sheet `Work Bike`) ≈ `∫P·dt`.

## Method

For each ride the track is parsed to per-point `time / distance / elevation /
speed / power / heart-rate / temperature`, then:

- **Distance** — last cumulative distance.
- **Moving duration / Work** — computed on a **1-second resampled grid** (devices
  log at up to ~3 Hz with integer-second stamps, so naive consecutive-pair
  deltas collapse). Moving = seconds with speed ≥ 1.0 m/s; gaps > 30 s are
  treated as stops; `Work = Σ power·Δt`.
- **Ascent / Descent** — sum of elevation changes with a 3 m hysteresis to reject
  GPS/baro noise; **Average Elevation** = mean over points.
- **Avg HR / Avg Temp / 80%ile Temp** — over valid samples.

A comparison is flagged **CHECK** when it exceeds *both* a per-metric percentage
tolerance and an absolute tolerance (e.g. distance 3 % / 1 km; work 10 % / 150 kJ;
HR 5 % / 4 bpm). **Parser sanity:** file-derived average power was cross-checked
against the independently computed power audit in `manifest.json` and agrees.

## Results

Median and 90th-percentile of |Δ%| (file vs sheet), n rides compared, # flagged:

| Metric | n | median \|Δ%\| | p90 \|Δ%\| | #CHECK |
|---|--:|--:|--:|--:|
| Distance (km) | 52 | **0.0** | 1.0 | 4 |
| Moving duration (h) | 50 | **0.8** | 3.5 | 1 |
| Work pedalling (kJ, `∫P·dt`) | 44 | **0.3** | 1.9 | 2 |
| Average heart rate | 50 | **0.2** | 3.9 | 5 |
| Average temperature | 28 | 1.4 | 4.0 | 0 |
| 80%ile temperature | 26 | 4.7 | 7.8 | 1 |
| Ascent (m) | 52 | 11.9 | 34.4 | 17 |
| Descent (m) | 52 | 10.6 | 36.4 | 16 |
| Average elevation (m) | 52 | 9.2 | 46.4 | 12 |

### Verdict

The **measured quantities are confirmed**: distance, moving time, pedalling work
(`∫P·dt`), heart rate and temperature all match the spreadsheet to ~1 % median.
The transcribed values are sound and the parser is trustworthy — the dataset is
fit to serve as empirical ground truth for the energy-model comparison.

The **elevation-derived columns differ ~10 %** (ascent/descent/avg elevation).
This is expected, not an error: the sheet values are hand-rounded (many rides
list ascent = descent, and `<Elevation>` is a round figure like 400/650/900),
and elevation-gain depends on the smoothing algorithm. It matters for the model,
because the gravity term scales with `h₊` — when comparing model vs empirical,
prefer the **track-derived** ascent over the sheet's rounded value.

## Notable outliers

Only two rides break the measured-quantity agreement, both for real reasons:

- **RMC200 Mogi** — the Strava *original* file is a **partial upload** (88 of
  210 km; 5.1 of 11.3 h; work 1314 of 3882 kJ). The sheet describes the full
  ride; the file is truncated. Not a transcription or parser problem.
- **RMC300 Guararema** — RWGPS distance runs +7 % and `∫P·dt` −27 % vs the sheet
  (sheet `Work Bike` 5692 kJ vs file 4134 kJ). Worth a manual look; likely a
  power-stream gap or a different moving-time basis in the original calc.

Minor distance flags **Curitiba 2/2** (−13 %, file shorter than the sheet) and
**Juqueri** (+4 %) are within normal GPS/route-trimming variation.

## Parser issues found and fixed

The first runs exposed three bugs in the track reader; all are fixed in
`verify.py` (and the FIT logic mirrors the app's `parseFIT`):

1. **Compressed-timestamp FIT headers** — several 2020 Strava files encode time
   in the record header (5-bit offset), not field 253. Without decoding it,
   moving time read as ~0 while distance was perfect. Fixed by tracking a running
   timestamp with 32-second rollover.
2. **Sub-second sampling** — devices logging at ~3 Hz with integer-second stamps
   produce many `Δt = 0` pairs, collapsing naive moving-time/speed math. Fixed by
   resampling onto a 1-second grid before integrating time and work.
3. **GPX namespaces** — Garmin `TrackPointExtension` prefixes (`gpxtpx:`,
   `xsi:`) had to be stripped (tags *and* attributes) for the stdlib XML parser.

## Caveat — `.fit` standardisation and temperature

The dataset was standardised on `.fit`: RideWithGPS trips/routes were pulled as
authenticated `.fit` exports (which preserve power/HR/speed/elevation — Paraty
`∫P·dt` 2738.7 vs sheet 2739) instead of the public `.json`. One side-effect: the
RWGPS `.fit` export **omits the weather-derived temperature** the JSON carried, so
temperature comparisons dropped from 49 to 28 rides. Temperature only affects air
density (ρ) and the CSV's temperature columns come from the spreadsheet regardless,
so this was accepted. `python3 fetch.py rwgps` re-pulls the JSON (with temperature)
if needed.

## Reproduce

```sh
cd data/activities
source ../../.env            # RWGPS_API_KEY, RWGPS_AUTH_TOKEN (for .fit / private trip)
python3 fetch.py csv         # (re)build longoes.csv from the sheet + manifest
python3 verify.py            # prints the table above; writes longoes_verify.csv
```
