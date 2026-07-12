#!/usr/bin/env python3
"""Cross-check longoes.csv (values transcribed from the spreadsheet) against the
downloaded activity files. Recomputes the file-derivable metrics from each track
and reports the delta. Parameters/guesses (weight, CdA, headwind, eps, Crr,
group) are NOT in the files and are skipped.

Track formats: RideWithGPS .json (track_points), Strava .fit (record msg 20),
Strava .gpx (trkpt + Garmin TrackPointExtension).

Usage: python3 verify.py            # console table + longoes_verify.csv
"""
import json, os, re, struct, math, csv, statistics
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(os.path.dirname(HERE), "data", "activities")
RESULTS = os.path.join(os.path.dirname(HERE), "results")
FIT_EPOCH = 631065600          # FIT timestamp 0 == 1989-12-31T00:00:00Z (unix s)
MOVING_V  = 1.0                # m/s (3.6 km/h) threshold for "moving"
DT_CAP    = 30                 # s; ignore gaps larger than this for time/work
ASCENT_TH = 3.0                # m hysteresis for ascent/descent accumulation

# ----------------------------------------------------------------- FIT reader
# base-type number -> (struct char, size, invalid)
BT = {0:('B',1,0xFF),1:('b',1,0x7F),2:('B',1,0xFF),3:('h',2,0x7FFF),4:('H',2,0xFFFF),
      5:('i',4,0x7FFFFFFF),6:('I',4,0xFFFFFFFF),7:('B',1,0x00),8:('f',4,None),
      9:('d',8,None),10:('B',1,0x00),11:('H',2,0),12:('I',4,0),13:('B',1,0xFF),
      14:('q',8,None),15:('Q',8,None),16:('Q',8,0)}
# record (global 20) field -> (name, scale, offset); physical = raw/scale - offset
REC = {253:('t',1,0), 2:('e',5,500), 3:('hr',1,0), 5:('d',100,0), 6:('v',1000,0),
       7:('p',1,0), 13:('temp',1,0), 73:('v',1000,0), 78:('e',5,500)}

def read_fit(path):
    b = open(path, "rb").read()
    pos = b[0]
    end = min(b[0] + struct.unpack_from("<I", b, 4)[0], len(b))
    defs = {}
    pts = []          # each: dict with any of t,e,hr,d,v,p,temp
    last_ts = [None]  # running FIT-seconds timestamp (for compressed headers)
    while pos < end:
        h = b[pos]; pos += 1
        if h & 0x80:  # compressed-timestamp data message
            d = defs.get((h >> 5) & 3)
            if not d: break
            if last_ts[0] is not None:                  # apply 5-bit time offset
                offset = h & 0x1F
                prev = last_ts[0]
                ts = (prev & ~0x1F) | offset
                if offset < (prev & 0x1F):
                    ts += 0x20                          # 32 s rollover
                last_ts[0] = ts
            row = _fit_row(b, pos, d, last_ts)
            if d["g"] == 20:
                if "t" not in row and last_ts[0] is not None:
                    row["t"] = last_ts[0] + FIT_EPOCH
                pts.append(row)
            pos += d["len"]; continue
        if h & 0x40:  # definition
            arch = b[pos+1]
            g = struct.unpack_from((">" if arch else "<")+"H", b, pos+2)[0]
            nf = b[pos+4]; pos += 5
            fields = []; off = 0; tot = 0
            for _ in range(nf):
                num, size, base = b[pos], b[pos+1], b[pos+2]
                fields.append((num, size, base, off)); off += size; tot += size; pos += 3
            if h & 0x20:
                nd = b[pos]; pos += 1
                for _ in range(nd):
                    tot += b[pos+1]; pos += 3
            defs[h & 0xF] = {"g": g, "len": tot, "arch": arch, "fields": fields}
        else:  # data
            d = defs.get(h & 0xF)
            if not d: break
            row = _fit_row(b, pos, d, last_ts)   # also seeds last_ts from any field-253
            if d["g"] == 20:
                pts.append(row)
            pos += d["len"]
    return pts

def _fit_row(b, base_off, d, last_ts):
    row = {}
    pre = "<" if d["arch"] == 0 else ">"
    for (num, size, btype, off) in d["fields"]:
        bt = BT.get(btype & 0x1F)
        if not bt:
            continue
        char, bsize, invalid = bt
        try:
            raw = struct.unpack_from(pre + char, b, base_off + off)[0]
        except struct.error:
            continue
        if num == 253:                       # full timestamp: seed the running clock
            if invalid is None or raw != invalid:
                last_ts[0] = raw
                row["t"] = raw + FIT_EPOCH
            continue
        if num not in REC:
            continue
        if invalid is not None and raw == invalid:
            continue
        name, scale, offset = REC[num]
        val = raw / scale - offset
        if num == 13:                        # temperature is sint8
            val = raw if raw < 128 else raw - 256
        row[name] = val
    return row

# ----------------------------------------------------------------- GPX reader
def read_gpx(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    txt = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", txt)          # drop xmlns declarations
    txt = re.sub(r'(?<=[\s</])[A-Za-z_][\w.\-]*:', "", txt)   # drop all prefixes (tags + attrs)
    root = ET.fromstring(txt)
    pts = []
    cum = 0.0; prev = None
    import datetime
    for tp in root.iter("trkpt"):
        lat = float(tp.get("lat")); lon = float(tp.get("lon"))
        row = {}
        ele = tp.find("ele")
        if ele is not None and ele.text: row["e"] = float(ele.text)
        tm = tp.find("time")
        if tm is not None and tm.text:
            s = tm.text.strip().replace("Z", "+00:00")
            try: row["t"] = datetime.datetime.fromisoformat(s).timestamp()
            except Exception: pass
        for tag, key in (("power","p"), ("hr","hr"), ("atemp","temp")):
            el = next((e for e in tp.iter() if e.tag.endswith(tag)), None)
            if el is not None and el.text:
                row[key] = float(el.text)
        if prev:
            cum += haversine(prev, (lat, lon))
        row["d"] = cum; prev = (lat, lon)
        pts.append(row)
    return pts

def haversine(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0]-a[0]); dl = math.radians(b[1]-a[1])
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

# ------------------------------------------------------------- RWGPS reader
def read_rwgps(path):
    d = json.load(open(path))
    pts = []
    for q in d.get("track_points") or []:
        row = {}
        for src, key in (("t","t"),("e","e"),("d","d"),("s","v"),("p","p"),("h","hr"),("T","temp")):
            if q.get(src) is not None: row[key] = q[src]
        pts.append(row)
    return pts, d

# ----------------------------------------------------------------- metrics
def metrics(pts):
    ts  = [p.get("t") for p in pts]
    dist= [p.get("d") for p in pts]
    ele = [p.get("e") for p in pts]
    vel = [p.get("v") for p in pts]
    pw  = [p.get("p") for p in pts]
    hr  = [p.get("hr") for p in pts]
    tp  = [p.get("temp") for p in pts]
    m = {}
    # distance (cumulative)
    dvals = [x for x in dist if x is not None]
    if dvals: m["distance_km"] = round(max(dvals)/1000, 2)
    # moving time + work — resample onto a 1-second grid first, so devices that
    # log at >1 Hz (integer-second stamps -> many dt==0 pairs) are handled right.
    per = {}   # second -> {d, v, p:[...]}
    for p in pts:
        t = p.get("t")
        if t is None: continue
        s = int(round(t)); cur = per.setdefault(s, {"d": None, "v": None, "p": []})
        if p.get("d") is not None: cur["d"] = p["d"]
        if p.get("v") is not None: cur["v"] = p["v"]
        if p.get("p") is not None: cur["p"].append(p["p"])
    secs = sorted(per)
    moving = work = elapsed = 0.0
    for i in range(len(secs)-1):
        dt = secs[i+1]-secs[i]
        if dt <= 0 or dt > DT_CAP: continue   # gap/pause: not moving, no work
        elapsed += dt
        a, b2 = per[secs[i]], per[secs[i+1]]
        v = a["v"]
        if v is None and a["d"] is not None and b2["d"] is not None:
            v = (b2["d"]-a["d"]) / dt
        if v is not None and v >= MOVING_V: moving += dt
        if a["p"]: work += (sum(a["p"])/len(a["p"])) * dt
    if secs:
        m["moving_h"] = round(moving/3600, 3)
        m["elapsed_h"] = round(elapsed/3600, 3)
    pvals = [x for x in pw if x is not None and x > 0]
    if pvals and work > 0:
        m["work_pedal_kj"] = round(work/1000, 1)
        m["avg_power_w"] = round(sum(pvals)/len(pvals), 1)   # for parser sanity-check
    # ascent / descent (hysteresis)
    evals = [x for x in ele if x is not None]
    if len(evals) > 2:
        gain = loss = 0.0; ref = evals[0]
        for x in evals[1:]:
            dd = x - ref
            if dd >= ASCENT_TH: gain += dd; ref = x
            elif dd <= -ASCENT_TH: loss += -dd; ref = x
        m["ascent_m"] = round(gain); m["descent_m"] = round(loss)
        m["avg_elev"] = round(sum(evals)/len(evals), 1)
    # HR / temperature
    hv = [x for x in hr if x is not None and x > 0]
    if hv: m["avg_hr"] = round(sum(hv)/len(hv), 1)
    tv = [x for x in tp if x is not None]
    if tv:
        m["avg_temp"] = round(sum(tv)/len(tv), 1)
        m["p80_temp"] = round(percentile(tv, 80), 1)
    return m

def percentile(xs, q):
    xs = sorted(xs); k = (len(xs)-1)*q/100
    lo = int(math.floor(k)); hi = int(math.ceil(k))
    if lo == hi: return xs[lo]
    return xs[lo] + (xs[hi]-xs[lo])*(k-lo)

# ----------------------------------------------------------------- compare
# CSV header -> (metric key, tolerance % for PASS, absolute tol)
CHECKS = [
    ("Distance in km",                 "distance_km", 3,  1.0),
    ("Moving duration in hours",       "moving_h",    8,  0.2),
    ("Ascent in meters",               "ascent_m",    15, 50),
    ("Descent in meters",              "descent_m",   15, 50),
    ("Average Elevation",              "avg_elev",    20, 40),
    ("Total Work Pedalling in kJ",     "work_pedal_kj",10, 150),
    ("Average Heart Rate",             "avg_hr",      5,  4),
    ("Average Temperature",            "avg_temp",    15, 2.5),
    ("80% Percentile over Temperature","p80_temp",    15, 3),
]

def fnum(s):
    try: return float(s)
    except (TypeError, ValueError): return None

def main():
    rows = list(csv.DictReader(open(os.path.join(OUT, "longoes.csv"))))
    man = {e["id"]: e for e in json.load(open(os.path.join(OUT,"manifest.json"))) if e.get("id")}
    detail = []
    agg = {k: [] for _, k, _, _ in CHECKS}
    print(f"{'RIDE':22} {'METRIC':14} {'XLSX':>9} {'FILE':>9} {'Δ%':>7}  flag")
    print("-"*72)
    for r in rows:
        path = r["Activity file path"]
        if not path:
            continue
        ap = os.path.join(os.path.dirname(os.path.dirname(OUT)), path)  # repo-root rel
        ap = os.path.join(OUT, "..", "..", path)
        ap = os.path.normpath(ap)
        if not os.path.exists(ap):
            continue
        if path.endswith(".json"):
            if "rwgps_route" in path:   # planned route: only distance/elevation
                pts, _ = read_rwgps(ap)
            else:
                pts, _ = read_rwgps(ap)
        elif path.endswith(".fit"):
            pts = read_fit(ap)
        elif path.endswith(".gpx"):
            pts = read_gpx(ap)
        else:
            continue
        fm = metrics(pts)
        title = r["Activity Title"][:21]
        printed = False
        for header, key, tolpct, tolabs in CHECKS:
            xv = fnum(r.get(header, "")); fv = fm.get(key)
            if xv is None or fv is None:
                continue
            d = fv - xv
            pct = (d/xv*100) if xv else (0 if d == 0 else float("inf"))
            ok = abs(d) <= tolabs or abs(pct) <= tolpct
            agg[key].append(abs(pct))
            flag = "ok" if ok else "CHECK"
            detail.append({"ride": r["Activity Title"], "metric": key,
                           "xlsx": xv, "file": fv, "delta": round(d,2),
                           "pct": round(pct,1), "flag": flag})
            print(f"{(title if not printed else ''):22} {key:14} {xv:9.1f} {fv:9.1f} {pct:7.1f}  {flag}")
            printed = True
        if printed: print()
    # summary
    print("="*72)
    print(f"{'METRIC':16} {'n':>3} {'median|Δ%|':>10} {'p90|Δ%|':>9} {'#CHECK':>7}")
    for _, key, _, _ in CHECKS:
        v = agg[key]
        if not v: continue
        nchk = sum(1 for d in detail if d["metric"]==key and d["flag"]=="CHECK")
        print(f"{key:16} {len(v):3d} {statistics.median(v):10.1f} "
              f"{percentile(v,90):9.1f} {nchk:7d}")
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS,"longoes_verify.csv"),"w",newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ride","metric","xlsx","file","delta","pct","flag"])
        w.writeheader(); w.writerows(detail)
    print(f"\nfull detail -> results/longoes_verify.csv ({len(detail)} comparisons)")

if __name__ == "__main__":
    main()
