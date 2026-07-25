#!/usr/bin/env python3
"""ENTRY 26 / Experiment 1 — endpoint-pair exporter.

Exports the START/END GPS endpoints of the Entry-19 corpus (the 922 rides
data/results/igc_resolution_test.csv includes: censo + ppaz + jaam + danlessa inside
sampa_geral.tif coverage) as deduplicated source/target pairs for the direction
ladder (Entry 26, Experiment 1 "Data" rules):

  - a ride's pair = FIRST and LAST valid GPS points of its track
    (geo_track_from_fit — the same machinery Entry 19 sampled the DEM with);
  - pairs with endpoints closer than 800 m straight-line are DROPPED
    (Entry 23's floor);
  - near-duplicate pairs are FOLDED: both endpoints within 250 m of a kept
    pair's endpoints, in either orientation A<->B, increment that pair's
    n_rides (first-seen coordinates kept);
  - pair_id = sha256 of the coords rounded to 5 decimals, first 8 hex chars
    (deterministic, carries no ride name).

Corpus membership comes from data/results/igc_resolution_test.csv (regenerable via
src/harness/igc_resolution_test.py) so this list is exactly Entry 19's funnel; each
ride's FIT is re-located through the same manifests the Entry-19 drivers read.

Outputs (both gitignored; written atomically via tmp+os.replace so a re-run can
never hand a partially-written file to a reader — the grid harness reads
e26_pairs.json while it runs):
  data/results/e26_pairs.json — JSON list of
      {pair_id, corpus, lat_a, lon_a, lat_b, lon_b, straight_m, n_rides}
      (schema frozen: the grid harness consumes it)
  data/results/e26_pair_rides.json — {pair_id: [[corpus, ride-label], …]}, the
      member rides folded into each pair. Needed by the Entry-26 secondary
      endpoint (the detour ratio E_opt/E_trackwalk joins a pair's optimal
      energy to its member rides' Entry-19 fixed-route energies).
(endpoints are often homes — NEVER commit; export to the sibling simujaules
repo locally only). stdout is aggregates only, NO coordinates and no ride names.

  /Users/danlessa/conda/bin/python src/harness/e26_pairs.py
"""

import gzip
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, HERE)

from igc_resolution_test import DATA, geo_track_from_fit  # noqa: E402
from regime_compare import haversine  # noqa: E402

RESULTS = os.path.join(REPO, "data", "results")
CSV = os.path.join(RESULTS, "igc_resolution_test.csv")
OUT = os.path.join(RESULTS, "e26_pairs.json")
OUT_RIDES = os.path.join(RESULTS, "e26_pair_rides.json")

MIN_STRAIGHT_M = 800.0   # Entry 23's floor
DUP_RADIUS_M = 250.0     # near-duplicate fold radius (both ends)
CORPORA = ["censo", "ppaz", "jaam", "danlessa"]

# first two CSV cells are JSON-quoted strings (jquote); ride names carry no
# commas (igc_resolution_test's own sanity gate splits naively), but decode
# through json for safety anyway.
_ROW_RE = re.compile(r'^"((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)",')


def included_rides():
    """(corpus, ride-label) list, in igc_resolution_test.csv row order."""
    rides = []
    with open(CSV, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    for line in lines[1:]:
        m = _ROW_RE.match(line)
        if not m:
            continue
        corpus = json.loads('"' + m.group(1) + '"')
        ride = json.loads('"' + m.group(2) + '"')
        rides.append((corpus, ride))
    return rides


def label_to_file():
    """(corpus, label) -> FIT path relative to DATA, from the same manifests
    the Entry-19 drivers read (censo keys on `name`, riders on `id`)."""
    fmap = {}
    with open(os.path.join(DATA, "censohidrografico", "manifest.json"),
              encoding="utf-8") as fh:
        for e in json.load(fh):
            if e.get("file"):
                fmap.setdefault(("censo", str(e.get("name"))), e["file"])
    for corpus, manifest in (("ppaz", "strava_ppaz_manifest.json"),
                             ("jaam", "strava_jaam_manifest.json"),
                             ("danlessa", "strava_danlessa_manifest.json")):
        with open(os.path.join(DATA, manifest), encoding="utf-8") as fh:
            for a in json.load(fh):
                if a.get("file"):
                    fmap.setdefault((corpus, str(a.get("id"))), a["file"])
    return fmap


def endpoints_of(path):
    with open(path, "rb") as fh:
        buf = fh.read()
    if path.endswith(".gz"):
        buf = gzip.decompress(buf)
    geo = geo_track_from_fit(buf)
    if len(geo) < 2:
        return None
    a, b = geo[0], geo[len(geo) - 1]
    return ({"lat": a["lat"], "lon": a["lon"]},
            {"lat": b["lat"], "lon": b["lon"]})


def pair_hash(a, b):
    key = ",".join(f"{v:.5f}" for v in (a["lat"], a["lon"], b["lat"], b["lon"]))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


def main():
    rides = included_rides()
    fmap = label_to_file()

    n_in = {c: 0 for c in CORPORA}
    n_drop = {c: 0 for c in CORPORA}
    n_fold = {c: 0 for c in CORPORA}
    n_new = {c: 0 for c in CORPORA}
    n_miss = {c: 0 for c in CORPORA}
    pairs = []   # kept pairs, first-seen order

    for corpus, ride in rides:
        n_in[corpus] += 1
        rel = fmap.get((corpus, ride))
        if not rel or not os.path.exists(os.path.join(DATA, rel)):
            n_miss[corpus] += 1
            continue
        ep = endpoints_of(os.path.join(DATA, rel))
        if not ep:
            n_miss[corpus] += 1
            continue
        a, b = ep
        straight = haversine(a, b)
        if straight < MIN_STRAIGHT_M:
            n_drop[corpus] += 1
            continue
        folded = False
        for p in pairs:
            pa = {"lat": p["lat_a"], "lon": p["lon_a"]}
            pb = {"lat": p["lat_b"], "lon": p["lon_b"]}
            if ((haversine(a, pa) < DUP_RADIUS_M and haversine(b, pb) < DUP_RADIUS_M)
                    or (haversine(a, pb) < DUP_RADIUS_M
                        and haversine(b, pa) < DUP_RADIUS_M)):
                p["n_rides"] += 1
                p["_rides"].append([corpus, ride])
                n_fold[corpus] += 1
                folded = True
                break
        if folded:
            continue
        pairs.append({"pair_id": pair_hash(a, b), "corpus": corpus,
                      "lat_a": a["lat"], "lon_a": a["lon"],
                      "lat_b": b["lat"], "lon_b": b["lon"],
                      "straight_m": straight, "n_rides": 1,
                      "_rides": [[corpus, ride]]})
        n_new[corpus] += 1

    ids = [p["pair_id"] for p in pairs]
    if len(set(ids)) != len(ids):
        raise ValueError("pair_id hash collision — widen the hash")

    os.makedirs(RESULTS, exist_ok=True)
    # The pairs file's schema is frozen (the grid harness reads it): strip the
    # member-ride bookkeeping into its own file. Both writes are atomic, so a
    # re-run while the grid harness is mid-flight can never expose a partial
    # file — and, being deterministic, a re-run reproduces e26_pairs.json
    # byte-for-byte (a cheap reproducibility gate).
    ride_map = {p["pair_id"]: p["_rides"] for p in pairs}
    public = [{k: v for k, v in p.items() if k != "_rides"} for p in pairs]
    for path, payload in ((OUT, public), (OUT_RIDES, ride_map)):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
            fh.write("\n")
        os.replace(tmp, path)

    # ===== summary — aggregates ONLY (no coordinates, no ride names) =====
    print("ENTRY 26 / Experiment 1 — endpoint pairs from the Entry-19 corpus")
    print(f"corpus list: {CSV}")
    print(f"rules: drop straight-line < {MIN_STRAIGHT_M:.0f} m · "
          f"fold both-ends < {DUP_RADIUS_M:.0f} m (either orientation)")
    print()
    print("corpus     rides-in  pairs-new  folded  drop<800m  unlocatable")
    for c in CORPORA:
        print(f"  {c.ljust(9)}{n_in[c]:>8}{n_new[c]:>11}{n_fold[c]:>8}"
              f"{n_drop[c]:>11}{n_miss[c]:>13}")
    tot = {k: sum(d.values()) for k, d in
           (("in", n_in), ("new", n_new), ("fold", n_fold),
            ("drop", n_drop), ("miss", n_miss))}
    print(f"  {'TOTAL'.ljust(9)}{tot['in']:>8}{tot['new']:>11}{tot['fold']:>8}"
          f"{tot['drop']:>11}{tot['miss']:>13}")
    print()
    ms = sorted(p["straight_m"] for p in pairs)
    med = ms[len(ms) // 2] if ms else float("nan")
    print(f"kept pairs: {len(pairs)} · straight-line m: "
          f"min {ms[0]:.0f} · median {med:.0f} · max {ms[-1]:.0f}")
    mult = sum(1 for p in pairs if p["n_rides"] > 1)
    print(f"pairs with n_rides > 1: {mult} · max n_rides "
          f"{max((p['n_rides'] for p in pairs), default=0)}")
    print(f"wrote {OUT} ({len(pairs)} pairs) — gitignored; NEVER commit")


if __name__ == "__main__":
    main()
