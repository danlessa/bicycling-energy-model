#!/usr/bin/env python3
"""Inventory of the author's Strava history export — Python port of
harness/danlessa_inventory.mjs (same console output and byte-identical
strava_danlessa_manifest.json).

Scans every .fit / .fit.gz in data/inputs/activities/strava_danlessa/ (gitignored),
reads sport + record stats + non-locational terrain metrics (median altitude,
raw ascent — characterise the geographic/terrain spread WITHOUT storing any
coordinate), and writes strava_danlessa_manifest.json (gitignored via
data/inputs/activities/*.json).

FIT parsing is bicycling_energy_model.parse_fit (records + meta["sport"]);
out-of-bounds reads raise (as the JS DataView does) so corrupt files count as
errors exactly as in Node. Run: python3 src/harness/danlessa_inventory.py
"""

import gzip
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import is_finite, parse_fit
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
DIR = os.path.join(DATA, "strava_danlessa")
SPORT = {0: "generic", 1: "run", 2: "ride", 5: "swim", 11: "walk", 17: "hike"}
FIT_EPOCH = 631065600   # 1989-12-31 UTC, seconds


def median(xs):
    s = sorted(x for x in xs if is_finite(x))
    if not s:
        return None
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2


# ---- scan ----

files = sorted(fn for fn in os.listdir(DIR)
               if fn.endswith(".fit") or fn.endswith(".fit.gz"))
out = []
errors = 0
for fn in files:
    try:
        with open(os.path.join(DIR, fn), "rb") as fh:
            buf = fh.read()
        if fn.endswith(".gz"):
            buf = gzip.decompress(buf)
        meta = {}
        recs = parse_fit(buf, meta)
        sport = meta["sport"]
        if len(recs) < 2:
            raise ValueError("sem registros")
        n = len(recs)
        nPow = nPowPos = nCad = nAlt = 0
        maxDist = 0
        t0 = t1 = None
        alts = []
        ascentRaw = 0
        lastAlt = None
        for r in recs:
            if r.get("power") is not None:
                nPow += 1
                if r["power"] > 0:
                    nPowPos += 1
            if r.get("cad") is not None:
                nCad += 1
            if r.get("alt") is not None:
                nAlt += 1
                alts.append(r["alt"])
                if lastAlt is not None and r["alt"] > lastAlt:
                    ascentRaw += r["alt"] - lastAlt
                lastAlt = r["alt"]
            if r.get("dist") is not None and r["dist"] > maxDist:
                maxDist = r["dist"]
            if r.get("time") is not None:
                if t0 is None:
                    t0 = r["time"]
                t1 = r["time"]
        medAlt = median(alts)          # characterises altitude/geography (non-locational)
        sport_label = SPORT.get(sport)
        if sport_label is None:
            sport_label = "unknown" if sport is None else "sport" + js_str(sport)
        out.append({
            "id": re.sub(r"\.fit(\.gz)?$", "", fn),
            "file": "strava_danlessa/" + fn,
            "sport": sport_label,
            "date": (datetime.fromtimestamp(t0 + FIT_EPOCH, timezone.utc).strftime("%Y-%m-%d")
                     if t0 is not None else None),
            "hours": float(to_fixed((t1 - t0) / 3600, 2)) if t0 is not None else None,
            "km": float(to_fixed(maxDist / 1000, 1)),
            "n": n,
            "powCov": float(to_fixed(nPow / n, 3)),
            "powPos": float(to_fixed(nPowPos / n, 3)),
            "cadCov": float(to_fixed(nCad / n, 3)),
            "altCov": float(to_fixed(nAlt / n, 3)),
            "medAlt": None if medAlt is None else float(to_fixed(medAlt, 0)),           # m
            "ascentRaw": float(to_fixed(ascentRaw, 0)),                                 # m (raw Σ+Δalt)
            "ascentPerKm": (float(to_fixed(ascentRaw / (maxDist / 1000), 1))            # m/km terrain proxy
                            if maxDist > 500 else None),
        })
    except Exception:
        errors += 1


# JSON.stringify(out, null, 1) byte-for-byte: 1-space indent, JS number
# rendering (integer-valued doubles print without '.0'), no trailing newline.
def _jval(v):
    if v is None:
        return "null"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return js_str(v)


if out:
    _items = []
    for o in out:
        _fields = ",\n".join('  "' + k + '": ' + _jval(v) for k, v in o.items())
        _items.append(" {\n" + _fields + "\n }")
    _text = "[\n" + ",\n".join(_items) + "\n]"
else:
    _text = "[]"
with open(os.path.join(DATA, "strava_danlessa_manifest.json"), "w") as fh:
    fh.write(_text)

# ---- summary ----
by_sport = {}
for a in out:
    by_sport.setdefault(a["sport"], []).append(a)
print(f"AUTHOR (danlessa) STRAVA EXPORT — {len(files)} FIT files, {len(out)} parsed, {errors} errors\n")
print("sport      n     w/ power(>50% cov)   rides>20km w/ power")
for s, arr in sorted(by_sport.items(), key=lambda kv: -len(kv[1])):
    pow_ = [a for a in arr if a["powCov"] > 0.5]
    big = [a for a in pow_ if a["km"] > 20]
    print(s.ljust(9) + str(len(arr)).rjust(5) + str(len(pow_)).rjust(13) + str(len(big)).rjust(19))
rides = [a for a in by_sport.get("ride", []) if a["powCov"] > 0.5]
if rides:
    dates = sorted(r["date"] for r in rides if r["date"])

    def q(arr, p):
        s = sorted(x for x in arr if is_finite(x))
        return s[math.floor(p * (len(s) - 1))] if s else float("nan")

    kms = [r["km"] for r in rides]
    alts = [r["medAlt"] for r in rides]
    apk = [r["ascentPerKm"] for r in rides]
    print(f"\nRIDES WITH POWER: {len(rides)}")
    d_first = dates[0] if dates else "undefined"
    d_last = dates[-1] if dates else "undefined"
    print(f"  dates {d_first} … {d_last}")
    print(f"  km: min {js_str(q(kms, 0))}  p25 {js_str(q(kms, .25))}  median {js_str(q(kms, .5))}"
          f"  p75 {js_str(q(kms, .75))}  max {js_str(q(kms, 1))}")
    print(f"  median altitude (m): p10 {js_str(q(alts, .1))}  median {js_str(q(alts, .5))}"
          f"  p90 {js_str(q(alts, .9))}  max {js_str(q(alts, 1))}   [geographic/altitude spread]")
    print(f"  ascent/km (m/km): p10 {js_str(q(apk, .1))}  median {js_str(q(apk, .5))}"
          f"  p90 {js_str(q(apk, .9))}  max {js_str(q(apk, 1))}   [terrain: plain↔mountainous]")
    print("  rides above 1500 m median alt (high-altitude): "
          f"{len([r for r in rides if r['medAlt'] is not None and r['medAlt'] >= 1500])}")
    print(f"  alt coverage ≥99%: {len([r for r in rides if r['altCov'] >= 0.99])}")
    print(f"  cadence coverage ≥50%: {len([r for r in rides if r['cadCov'] >= 0.5])}")
print("\nwrote strava_danlessa_manifest.json")
