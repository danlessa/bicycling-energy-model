#!/usr/bin/env python3
"""Inventory of P. Paz's Strava history export — Python port of
harness/ppaz_inventory.mjs (same console report, byte-identical manifest).
(data/activities/strava_ppaz/, gitignored: third-party GPS shared with
consent — see the article's Ethics section.)

Goal: find which activities are usable for the second-rider model verification —
i.e. CYCLING rides WITH POWER (the empirical ∫P·dt benchmark needs a power meter).
Scans every .fit / .fit.gz, reads sport + record stats, and writes
strava_ppaz_manifest.json (gitignored via data/activities/*.json).

  python3 harness/ppaz_inventory.py

parseFIT is the verbatim copy used by all harnesses (censo_compare.mjs), extended
ONLY to also capture the sport enum (message 12 field 0 / session 18 field 5) —
the record decoding is untouched. It is therefore ported locally (the bem copy
has neither the cadence field nor the sport capture).
"""

import gzip
import math
import os
import re
import struct
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem.jsfmt import js_str, to_fixed

DATA = os.path.join(REPO, "data", "activities")
DIR = os.path.join(DATA, "strava_ppaz")
SPORT = {0: "generic", 1: "run", 2: "ride", 5: "swim", 11: "walk", 17: "hike"}


# ---- FIT parsing — the .mjs's EXTENDED copy (cadence field + sport enum) ----

def _reader(buf, little):
    """read(p, bt) closure — FIT base-type reads honouring the definition's
    endianness and the FIT invalid-value markers. Out-of-range reads raise
    (struct.error / IndexError), as DataView throws RangeError in JS."""
    e = "<" if little else ">"

    def read(p, bt):
        b = bt & 0x1F
        if b == 0x01:
            v = struct.unpack_from(e + "b", buf, p)[0]
            return None if v == 0x7F else v
        if b in (0x00, 0x02, 0x0A, 0x0D):
            v = buf[p]
            return None if v == 0xFF else v
        if b == 0x03:
            v = struct.unpack_from(e + "h", buf, p)[0]
            return None if v == 0x7FFF else v
        if b in (0x04, 0x0B):
            v = struct.unpack_from(e + "H", buf, p)[0]
            return None if v == 0xFFFF else v
        if b == 0x05:
            v = struct.unpack_from(e + "i", buf, p)[0]
            return None if v == 0x7FFFFFFF else v
        if b in (0x06, 0x0C):
            v = struct.unpack_from(e + "I", buf, p)[0]
            return None if v == 0xFFFFFFFF else v
        if b == 0x08:
            return struct.unpack_from(e + "f", buf, p)[0]
        if b == 0x09:
            return struct.unpack_from(e + "d", buf, p)[0]
        return None  # strings / 64-bit ignored

    return read


def parse_fit(buf):
    if len(buf) < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    data_size = struct.unpack_from("<I", buf, 4)[0]
    if buf[8:12] != b".FIT":
        raise ValueError("no .FIT")
    end = min(header_size + data_size, len(buf))
    pos = header_size
    defs = {}
    records = []
    last_ts = None   # running timestamp for compressed-timestamp headers (5-bit offset, 32 s rollover)
    sport = None     # first sport enum seen (msg 12 field 0, or session msg 18 field 5)
    while pos < end:
        rh = buf[pos]
        pos += 1
        ts_offset = None
        is_def = has_dev = False
        if rh & 0x80:
            local = (rh >> 5) & 0x03
            ts_offset = rh & 0x1F
        else:
            local = rh & 0x0F
            is_def = bool(rh & 0x40)
            has_dev = bool(rh & 0x20)
        if is_def:
            pos += 1
            little = buf[pos] == 0
            pos += 1
            gmn = struct.unpack_from("<H" if little else ">H", buf, pos)[0]
            pos += 2
            nf = buf[pos]
            pos += 1
            fields = []
            for _ in range(nf):
                fields.append((buf[pos], buf[pos + 1], buf[pos + 2]))  # num, size, bt
                pos += 3
            dev_size = 0
            if has_dev:
                nd = buf[pos]
                pos += 1
                for _ in range(nd):
                    dev_size += buf[pos + 1]
                    pos += 3
            defs[local] = {"gmn": gmn, "little": little, "fields": fields,
                           "devSize": dev_size, "read": _reader(buf, little)}
        else:
            d = defs.get(local)
            if d is None:
                raise ValueError("FIT corrompido (dado sem definição)")
            p = pos
            rec = {}
            read = d["read"]
            gmn = d["gmn"]
            for num, size, bt in d["fields"]:
                if gmn == 20:
                    v = read(p, bt)
                    if v is not None:
                        if num == 0:
                            rec["lat"] = v * (180 / 2147483648)
                        elif num == 1:
                            rec["lon"] = v * (180 / 2147483648)
                        elif num == 2:
                            if "alt" not in rec:
                                rec["alt"] = v / 5 - 500
                        elif num == 78:
                            rec["alt"] = v / 5 - 500
                        elif num == 5:
                            rec["dist"] = v / 100
                        elif num == 6:
                            if "speed" not in rec:
                                rec["speed"] = v / 1000
                        elif num == 73:
                            rec["speed"] = v / 1000
                        elif num == 7:
                            rec["power"] = v
                        elif num == 4:
                            rec["cad"] = v          # cadence (rpm) — 0 ⇒ not pedalling
                        elif num == 253:
                            rec["time"] = v
                elif (gmn == 12 and num == 0) or (gmn == 18 and num == 5):
                    v = read(p, bt)
                    if v is not None and sport is None:
                        sport = v
                elif num == 253:   # any message's timestamp advances the running clock
                    v = read(p, bt)
                    if v is not None:
                        rec["time"] = v
                p += size
            pos = p + d["devSize"]
            # compressed-timestamp header: reconstruct the time from the 5-bit offset
            if ts_offset is not None and "time" not in rec and last_ts is not None:
                ts = (last_ts & ~31) | ts_offset
                if ts < last_ts:
                    ts += 32
                rec["time"] = ts
            if "time" in rec:
                last_ts = rec["time"]
            if gmn == 20:
                records.append(rec)
    return records, sport


FIT_EPOCH = 631065600   # 1989-12-31 UTC, seconds


# ---- JSON.stringify(out, null, 1) — byte-compatible writer ----
# json.dumps differs: it escapes non-ASCII (ensure_ascii) and renders
# integer-valued floats with a trailing .0 (JS: String(2.0) === '2').

_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
        "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def jquote(s):
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


def jstringify(v, ind=""):
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
        recs, sport = parse_fit(buf)
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
