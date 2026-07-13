#!/usr/bin/env python3
"""Extract per-ride GPS track (lat, lon, recorded elevation, cumulative distance)
from the .fit files, downsample by distance, and write one CSV per ride plus a
tile manifest (1° tiles each ride touches). Feeds the DEM elevation comparison.

Python port of the retired extract_coords.mjs (byte-identical output).

Usage: python3 harness/dem/extract_coords.py [OUTDIR] [STEP]
       OUTDIR defaults to harness/dem/coords/ (gitignored — per-ride GPS)
       STEP   defaults to 50 (metres between kept points)
"""

import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "analysis"))

from bem.jsfmt import to_fixed
from bem.v8math import _js_asin, _js_cos, _js_sin

ACT = os.path.join(REPO, "data", "activities")
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "coords")
STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 50   # keep a point every ~STEP metres


# --- parseFIT: the reduced variant this tool carries (record msg 20 only) ---
# NOT bem.parse_fit: that one reads power/speed/time/cadence too and raises a
# different message. This copy is deliberately the verbatim retired-JS logic.
def parse_fit(buf):
    n = len(buf)
    if n < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    if buf[8:12] != b".FIT":
        raise ValueError("no .FIT")
    data_size = struct.unpack_from("<I", buf, 4)[0]
    end = min(header_size + data_size, n)
    pos = header_size
    defs = {}
    records = []

    def read(p, bt, little):
        e = "<" if little else ">"
        t = bt & 0x1F
        if t == 0x01:
            v = struct.unpack_from("b", buf, p)[0]
            return None if v == 0x7F else v
        if t in (0x00, 0x02, 0x0A, 0x0D):
            v = buf[p]
            return None if v == 0xFF else v
        if t == 0x03:
            v = struct.unpack_from(e + "h", buf, p)[0]
            return None if v == 0x7FFF else v
        if t in (0x04, 0x0B):
            v = struct.unpack_from(e + "H", buf, p)[0]
            return None if v == 0xFFFF else v
        if t == 0x05:
            v = struct.unpack_from(e + "i", buf, p)[0]
            return None if v == 0x7FFFFFFF else v
        if t in (0x06, 0x0C):
            v = struct.unpack_from(e + "I", buf, p)[0]
            return None if v == 0xFFFFFFFF else v
        if t == 0x08:
            return struct.unpack_from(e + "f", buf, p)[0]
        if t == 0x09:
            return struct.unpack_from(e + "d", buf, p)[0]
        return None

    while pos < end:
        rh = buf[pos]
        pos += 1
        is_def = has_dev = False
        if rh & 0x80:
            local = (rh >> 5) & 0x03
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
                fields.append({"num": buf[pos], "size": buf[pos + 1], "bt": buf[pos + 2]})
                pos += 3
            dev_size = 0
            if has_dev:
                nd = buf[pos]
                pos += 1
                for _ in range(nd):
                    dev_size += buf[pos + 1]
                    pos += 3
            defs[local] = {"gmn": gmn, "little": little, "fields": fields, "devSize": dev_size}
        else:
            d = defs.get(local)
            if not d:
                break
            p = pos
            rec = {}
            for f in d["fields"]:
                if d["gmn"] == 20:
                    v = read(p, f["bt"], d["little"])
                    if v is not None:
                        if f["num"] == 0:
                            rec["lat"] = v * (180 / 2147483648)
                        elif f["num"] == 1:
                            rec["lon"] = v * (180 / 2147483648)
                        elif f["num"] == 2:
                            if "alt" not in rec:
                                rec["alt"] = v / 5 - 500
                        elif f["num"] == 78:
                            rec["alt"] = v / 5 - 500
                        elif f["num"] == 5:
                            rec["dist"] = v / 100
                p += f["size"]
            pos = p + d["devSize"]
            if d["gmn"] == 20:
                records.append(rec)
    return records


def haversine(a, b):
    R, t = 6371000, math.pi / 180
    s1 = _js_sin((b["lat"] - a["lat"]) * t / 2)
    s2 = _js_sin((b["lon"] - a["lon"]) * t / 2)
    s = s1 * s1 + _js_cos(a["lat"] * t) * _js_cos(b["lat"] * t) * (s2 * s2)
    return 2 * R * _js_asin(math.sqrt(s))


def tile_name(lat, lon):   # 1° tile SW-corner id, e.g. S24W047
    la, lo = math.floor(lat), math.floor(lon)
    return (("S" if la < 0 else "N") + str(abs(la)).rjust(2, "0")
            + ("W" if lo < 0 else "E") + str(abs(lo)).rjust(3, "0"))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    inputs = json.load(open(os.path.join(ACT, "model_inputs.json")))
    tiles = set()
    summary = []
    for e in inputs:
        if not e.get("file") or not e["file"].endswith(".fit"):
            continue   # GPS-bearing fits only
        try:
            with open(os.path.join(ACT, e["file"]), "rb") as fh:
                recs = parse_fit(fh.read())
        except Exception as err:
            summary.append({"ride": e["label"], "err": str(err)})
            continue
        gps = [r for r in recs if "lat" in r and "lon" in r and "alt" in r]
        if len(gps) < 2:
            summary.append({"ride": e["label"], "nrec": len(recs), "gps": len(gps), "note": "no GPS"})
            continue
        # downsample by distance (fall back to index if no dist field)
        out = []
        last_d, cum, prev = -1e9, 0.0, None
        for r in gps:
            d = r.get("dist")
            if d is None:
                if prev:
                    cum += haversine(prev, r)
                d = cum
                prev = r
            if d - last_d >= STEP or not out:
                out.append({"lat": r["lat"], "lon": r["lon"], "ele": r["alt"], "d": d})
                last_d = d
                tiles.add(tile_name(r["lat"], r["lon"]))
        rid = e["id"]
        lines = ["lon,lat,ele,d"] + [
            f'{to_fixed(p["lon"], 6)},{to_fixed(p["lat"], 6)},{to_fixed(p["ele"], 1)},{to_fixed(p["d"], 1)}'
            for p in out]
        with open(os.path.join(OUTDIR, f"{rid}.csv"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        seen, uniq = set(), []
        for p in out:                       # JS: [...new Set(...)] — insertion order
            t = tile_name(p["lat"], p["lon"])
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        summary.append({"ride": e["label"], "id": rid, "pts": len(out), "tiles": " ".join(uniq)})

    with open(os.path.join(OUTDIR, "_tiles.txt"), "w") as fh:
        fh.write("\n".join(sorted(tiles)) + "\n")
    print(f"rides with GPS: {len([s for s in summary if s.get('pts')])}/{len(summary)}")
    for s in summary:
        if s.get("pts"):
            print(f"  {s['ride'][:24].ljust(24)} {str(s['pts']).rjust(5)} pts  [{s['tiles']}]")
        else:
            print(f"  {s['ride'][:24].ljust(24)} -- {s.get('note') or s.get('err')}")
    print(f"\n{len(tiles)} unique 1° tiles -> {os.path.join(OUTDIR, '_tiles.txt')}")
    print(" ".join(sorted(tiles)))


if __name__ == "__main__":
    main()
