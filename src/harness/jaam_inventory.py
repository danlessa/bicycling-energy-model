#!/usr/bin/env python3
"""Inventory of JAAM's Strava history export — Python port of
harness/jaam_inventory.mjs (same console output, byte-identical manifest).

data/inputs/activities/strava_jaam/ is gitignored: third-party GPS shared with
consent — an INDEPENDENT rider, not a Pedal Hidrográfico member.
Multi-country (São Paulo + Colombia, Germany, Ukraine, US, …), spanning
mountainous to plain terrain — the strongest external-validity corpus in
the study.

Goal: find CYCLING rides WITH POWER (the empirical ∫P·dt benchmark needs a
power meter). Scans every .fit / .fit.gz, reads sport + record stats +
non-locational terrain metrics (median altitude, raw ascent — characterise
the geographic/terrain spread WITHOUT storing any coordinate), and writes
strava_jaam_manifest.json (gitignored via data/inputs/activities/*.json).

  python3 src/harness/jaam_inventory.py

FIT decoding is bicycling_energy_model's shared parse_fit; the sport enum (msg 12 field 0 /
session msg 18 field 5) arrives via its meta dict.
"""

from __future__ import annotations

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
DIR = os.path.join(DATA, "strava_jaam")
SPORT = {0: "generic", 1: "run", 2: "ride", 5: "swim", 11: "walk", 17: "hike"}

FIT_EPOCH = 631065600   # 1989-12-31 UTC, seconds


def median(xs: list[float]) -> float | None:
    s = sorted(x for x in xs if is_finite(x))
    k = (len(s) - 1) / 2
    return (s[math.floor(k)] + s[math.ceil(k)]) / 2 if s else None


# ---- JSON.stringify(out, null, 1) — byte-identical manifest bytes ----

def stringify(v: object, depth: int = 0) -> str:
    ind = " " * depth
    if isinstance(v, list):
        if not v:
            return "[]"
        inner = ",\n".join(ind + " " + stringify(item, depth + 1) for item in v)
        return "[\n" + inner + "\n" + ind + "]"
    if isinstance(v, dict):
        if not v:
            return "{}"
        inner = ",\n".join(ind + " " + json.dumps(k, ensure_ascii=False) + ": "
                           + stringify(val, depth + 1) for k, val in v.items())
        return "{\n" + inner + "\n" + ind + "}"
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return js_str(v)


files = sorted(f for f in os.listdir(DIR) if f.endswith(".fit") or f.endswith(".fit.gz"))
out = []
errors = 0
for fname in files:
    try:
        with open(os.path.join(DIR, fname), "rb") as fh:
            buf = fh.read()
        if fname.endswith(".gz"):
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
            if "power" in r:
                nPow += 1
                if r["power"] > 0:
                    nPowPos += 1
            if "cad" in r:
                nCad += 1
            if "alt" in r:
                nAlt += 1
                alts.append(r["alt"])
                if lastAlt is not None and r["alt"] > lastAlt:
                    ascentRaw += r["alt"] - lastAlt
                lastAlt = r["alt"]
            if "dist" in r and r["dist"] > maxDist:
                maxDist = r["dist"]
            if "time" in r:
                if t0 is None:
                    t0 = r["time"]
                t1 = r["time"]
        medAlt = median(alts)          # characterises altitude/geography (non-locational)
        sport_name = SPORT.get(sport)
        if sport_name is None:
            sport_name = "unknown" if sport is None else f"sport{js_str(sport)}"
        out.append({
            "id": re.sub(r"\.fit(\.gz)?$", "", fname),
            "file": os.path.join("strava_jaam", fname),
            "sport": sport_name,
            "date": (datetime.fromtimestamp(t0 + FIT_EPOCH, tz=timezone.utc).strftime("%Y-%m-%d")
                     if t0 is not None else None),
            "hours": float(to_fixed((t1 - t0) / 3600, 2)) if t0 is not None else None,
            "km": float(to_fixed(maxDist / 1000, 1)),
            "n": n,
            "powCov": float(to_fixed(nPow / n, 3)),
            "powPos": float(to_fixed(nPowPos / n, 3)),
            "cadCov": float(to_fixed(nCad / n, 3)),
            "altCov": float(to_fixed(nAlt / n, 3)),
            "medAlt": None if medAlt is None else float(to_fixed(medAlt, 0)),               # m
            "ascentRaw": float(to_fixed(ascentRaw, 0)),                                     # m (raw Σ+Δalt)
            "ascentPerKm": (float(to_fixed(ascentRaw / (maxDist / 1000), 1))
                            if maxDist > 500 else None),                                    # m/km terrain proxy
        })
    except Exception:
        errors += 1

with open(os.path.join(DATA, "strava_jaam_manifest.json"), "w", encoding="utf-8") as fh:
    fh.write(stringify(out))

# ---- summary ----
bySport = {}
for a in out:
    bySport.setdefault(a["sport"], []).append(a)
print(f"JAAM STRAVA EXPORT — {len(files)} FIT files, {len(out)} parsed, {errors} errors\n")
print("sport      n     w/ power(>50% cov)   rides>20km w/ power")
for s, arr in sorted(bySport.items(), key=lambda kv: -len(kv[1])):
    pow_ = [a for a in arr if a["powCov"] > 0.5]
    big = [a for a in pow_ if a["km"] > 20]
    print(s.ljust(9) + str(len(arr)).rjust(5) + str(len(pow_)).rjust(13) + str(len(big)).rjust(19))
rides = [a for a in bySport.get("ride", []) if a["powCov"] > 0.5]
if rides:
    dates = sorted(d for d in (r["date"] for r in rides) if d)

    def q(arr: list[float], p: float) -> float:
        s = sorted(x for x in arr if is_finite(x))
        return s[math.floor(p * (len(s) - 1))] if s else float("nan")

    kms = [r["km"] for r in rides]
    alts = [r["medAlt"] for r in rides]
    apk = [r["ascentPerKm"] for r in rides]
    print(f"\nRIDES WITH POWER: {len(rides)}")
    print(f"  dates {dates[0] if dates else 'undefined'} … {dates[-1] if dates else 'undefined'}")
    print(f"  km: min {js_str(q(kms, 0))}  p25 {js_str(q(kms, .25))}  median {js_str(q(kms, .5))}"
          f"  p75 {js_str(q(kms, .75))}  max {js_str(q(kms, 1))}")
    print(f"  median altitude (m): p10 {js_str(q(alts, .1))}  median {js_str(q(alts, .5))}"
          f"  p90 {js_str(q(alts, .9))}  max {js_str(q(alts, 1))}   [geographic/altitude spread]")
    print(f"  ascent/km (m/km): p10 {js_str(q(apk, .1))}  median {js_str(q(apk, .5))}"
          f"  p90 {js_str(q(apk, .9))}  max {js_str(q(apk, 1))}   [terrain: plain↔mountainous]")
    print(f"  rides above 1500 m median alt (high-altitude): "
          f"{len([r for r in rides if r['medAlt'] is not None and r['medAlt'] >= 1500])}")
    print(f"  alt coverage ≥99%: {len([r for r in rides if r['altCov'] >= 0.99])}")
    print(f"  cadence coverage ≥50%: {len([r for r in rides if r['cadCov'] >= 0.5])}")
print("\nwrote strava_jaam_manifest.json")
