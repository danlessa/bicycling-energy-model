#!/usr/bin/env python3
"""Inventory of P. Paz's Strava history export — Python port of
harness/ppaz_inventory.mjs (same console report, byte-identical manifest).
(data/inputs/activities/strava_ppaz/, gitignored: third-party GPS shared with
consent — see the article's Ethics section.)

Goal: find which activities are usable for the second-rider model verification —
i.e. CYCLING rides WITH POWER (the empirical ∫P·dt benchmark needs a power meter).
Scans every .fit / .fit.gz, reads sport + record stats, and writes
strava_ppaz_manifest.json (gitignored via data/inputs/activities/*.json).

  python3 src/harness/ppaz_inventory.py

parse_fit is the shared bicycling_energy_model implementation
(src/bicycling_energy_model/fit.py) — it decodes
the cadence field and captures the sport enum (message 12 field 0 / session 18
field 5) via the `meta` dict.
"""

from __future__ import annotations

import gzip
import math
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from bicycling_energy_model import parse_fit
from bicycling_energy_model.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "inputs", "activities")
DIR = os.path.join(DATA, "strava_ppaz")
SPORT = {0: "generic", 1: "run", 2: "ride", 5: "swim", 11: "walk", 17: "hike"}

FIT_EPOCH = 631065600   # 1989-12-31 UTC, seconds


# ---- JSON.stringify(out, null, 1) — byte-compatible writer ----
# json.dumps differs: it escapes non-ASCII (ensure_ascii) and renders
# integer-valued floats with a trailing .0 (JS: String(2.0) === '2').

_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s: str) -> str:
    out = ['"']
    for ch in s:
        if ch in _ESC:
            out.append(_ESC[ch])
        elif ch < " ":
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def jstringify(v: object, ind: str = "") -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return jquote(v)
    if isinstance(v, int):
        return js_str(v)
    if isinstance(v, float):
        return js_str(v) if math.isfinite(v) else "null"   # JSON.stringify(NaN) === 'null'
    ni = ind + " "
    if isinstance(v, list):
        if not v:
            return "[]"
        return "[\n" + ",\n".join(ni + jstringify(x, ni) for x in v) + "\n" + ind + "]"
    if not v:
        return "{}"
    return ("{\n"
            + ",\n".join(ni + jquote(k) + ": " + jstringify(val, ni) for k, val in v.items())
            + "\n" + ind + "}")


# ---- scan ----

files = sorted(f for f in os.listdir(DIR) if f.endswith(".fit") or f.endswith(".fit.gz"))
out = []
errors = 0
for f in files:
    try:
        with open(os.path.join(DIR, f), "rb") as fh:
            buf = fh.read()
        if f.endswith(".gz"):
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
        for r in recs:
            if r.get("power") is not None:
                nPow += 1
                if r["power"] > 0:
                    nPowPos += 1
            if r.get("cad") is not None:
                nCad += 1
            if r.get("alt") is not None:
                nAlt += 1
            if r.get("dist") is not None and r["dist"] > maxDist:
                maxDist = r["dist"]
            if r.get("time") is not None:
                if t0 is None:
                    t0 = r["time"]
                t1 = r["time"]
        sport_name = SPORT.get(sport)
        if sport_name is None:
            sport_name = "unknown" if sport is None else "sport" + js_str(sport)
        out.append({
            "id": re.sub(r"\.fit(\.gz)?$", "", f),
            "file": os.path.join("strava_ppaz", f),
            "sport": sport_name,
            "date": (datetime.fromtimestamp(t0 + FIT_EPOCH, timezone.utc).strftime("%Y-%m-%d")
                     if t0 is not None else None),
            "hours": float(to_fixed((t1 - t0) / 3600, 2)) if t0 is not None else None,
            "km": float(to_fixed(maxDist / 1000, 1)),
            "n": n,
            "powCov": float(to_fixed(nPow / n, 3)),
            "powPos": float(to_fixed(nPowPos / n, 3)),
            "cadCov": float(to_fixed(nCad / n, 3)),
            "altCov": float(to_fixed(nAlt / n, 3)),
        })
    except Exception:
        errors += 1
with open(os.path.join(DATA, "strava_ppaz_manifest.json"), "w", encoding="utf-8") as fh:
    fh.write(jstringify(out))

# ---- summary ----
bySport = {}
for a in out:
    bySport.setdefault(a["sport"], []).append(a)
print(f"P. PAZ STRAVA EXPORT — {len(files)} FIT files, {len(out)} parsed, {errors} errors\n")
print("sport      n     w/ power(>50% cov)   rides>20km w/ power")
for s, arr in sorted(bySport.items(), key=lambda kv: len(kv[1]), reverse=True):
    pow_ = [a for a in arr if a["powCov"] > 0.5]
    big = [a for a in pow_ if a["km"] > 20]
    print(s.ljust(9) + str(len(arr)).rjust(5) + str(len(pow_)).rjust(13) + str(len(big)).rjust(19))
rides = [a for a in bySport.get("ride", []) if a["powCov"] > 0.5]
if rides:
    dates = sorted(r["date"] for r in rides if r["date"])
    kms = sorted(r["km"] for r in rides)
    q = lambda p: kms[math.floor(p * (len(kms) - 1))]
    print(f"\nRIDES WITH POWER: {len(rides)}")
    print(f"  dates {dates[0]} … {dates[-1]}")
    print(f"  km: min {js_str(q(0))}  p25 {js_str(q(.25))}  median {js_str(q(.5))}  "
          f"p75 {js_str(q(.75))}  max {js_str(q(1))}")
    print(f"  alt coverage ≥99%: {len([r for r in rides if r['altCov'] >= 0.99])}")
    print(f"  cadence coverage ≥50%: {len([r for r in rides if r['cadCov'] >= 0.5])}")
print("\nwrote strava_ppaz_manifest.json")
