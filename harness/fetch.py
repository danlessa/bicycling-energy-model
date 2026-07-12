#!/usr/bin/env python3
"""Download the empirical ride dataset linked from longoes.xlsx ('Atividades v2').

Each row's Activity column (column B) links to either a RideWithGPS trip/route or
a Strava activity. We pull the richest source that carries MEASURED POWER, to be
used as ground truth for the approximate-vs-canonical energy model comparison:

  - RideWithGPS trips  -> public `<id>.json` (per-second x/y/e/d/s/t/h/c/p track).
                          The `.gpx`/original need auth; the JSON does not and
                          already carries power (`p`, W). Routes are planned-only.
  - Strava activities  -> `export_original` (the literal uploaded .fit/.gpx/.tcx),
                          which needs the owner's session cookies (a Netscape
                          cookie jar). 2020 rides predate the power meter and
                          carry an all-0xFFFF (invalid) power field.

No third-party deps (stdlib + curl), matching the repo's no-build house style.

Usage:
  python3 fetch.py rwgps                  # download RideWithGPS trips+routes
  python3 fetch.py strava <cookiejar>     # download Strava originals (needs auth)
  python3 fetch.py audit                  # (re)compute power summary into manifest
  python3 fetch.py all <cookiejar>        # rwgps + strava + audit
"""
import zipfile, re, json, os, sys, struct, subprocess, tempfile, concurrent.futures
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
XLSX = os.path.join(REPO, "data", "longoes.xlsx")
OUT  = os.path.join(REPO, "data", "activities")
SHEET = "sheet1"  # 'Atividades v2' (superset of the older 'Atividades' sheet)
NS  = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# ----------------------------------------------------------------- xlsx links
def extract_links():
    zf = zipfile.ZipFile(XLSX)
    shared = ["".join(t.text or "" for t in si.iter(NS + "t"))
              for si in ET.fromstring(zf.read("xl/sharedStrings.xml"))]
    root = ET.fromstring(zf.read(f"xl/worksheets/{SHEET}.xml"))
    cells = {}
    for c in root.iter(NS + "c"):
        ref, t, v = c.get("r"), c.get("t"), c.find(NS + "v")
        val = v.text if v is not None else ""
        if t == "s" and val not in (None, ""):
            val = shared[int(val)]
        cells[ref] = val or ""
    relmap = {r.get("Id"): r.get("Target")
              for r in ET.fromstring(zf.read(f"xl/worksheets/_rels/{SHEET}.xml.rels"))}
    links = []
    for h in root.iter(NS + "hyperlink"):
        ref = h.get("ref")
        links.append({"cell": ref, "row": int(re.search(r"\d+", ref).group()),
                      "label": cells.get(ref, ""), "url": relmap.get(h.get(RNS + "id"), "")})
    return sorted(links, key=lambda r: r["row"])

def classify(url):
    for pat, kind in ((r"ridewithgps\.com/trips/(\d+)", "rwgps_trip"),
                      (r"ridewithgps\.com/routes/(\d+)", "rwgps_route"),
                      (r"strava\.com/activities/(\d+)", "strava")):
        m = re.search(pat, url)
        if m:
            return kind, m.group(1)
    return "unknown", None

def build_manifest():
    man = []
    for L in extract_links():
        kind, aid = classify(L["url"])
        man.append({"label": L["label"], "cell": L["cell"], "url": L["url"],
                    "source": kind, "id": aid})
    return man

# ----------------------------------------------------------- csv dataset
# Map each requested CSV column to its 'Atividades v2' spreadsheet column.
# Header names live in row 2 (row 1 is a category-letter marker). Verified
# against the data: 'Off-road' is a 0..1 fraction, 'Tc' the upper-percentile
# temperature, 'Group?' the rider count (0 = solo).
CSV_COLUMNS = [
    ("Activity Title",                                        "B"),   # Activity
    ("Activity file path",                                    None),  # from manifest
    ("Moving duration in hours",                              "D"),   # MT
    ("Distance in km",                                        "F"),   # Distance
    ("Ascent in meters",                                      "G"),   # Uphill
    ("Descent in meters",                                     "H"),   # Downhill
    ("Unpaved fraction",                                      "I"),   # Off-road
    ("Average Elevation",                                     "K"),   # <Elevation>
    ("Headwind in km/h",                                      "L"),   # Headwind
    ("Total weight in kg",                                    "M"),   # Weight
    ("Cd*A in m2",                                            "N"),   # CdA
    ("Total Work in kJ",                                      "O"),   # Work Total
    ("Total Work Pedalling in kJ",                            "P"),   # Work Bike
    ("Average Heart Rate",                                    "U"),   # <HR>
    ("Average Temperature",                                   "W"),   # <T>
    ("80% Percentile over Temperature",                       "X"),   # Tc
    ("Guessed Epsilon (g_d_eff)",                             "AA"),  # g_d_eff
    ("Guessed rolling resistance in paved (Road Crr)",        "AC"),  # Road Crr
    ("Guessed rolling resistance in unpaved (Offroad Crr)",   "AD"),  # Offroad Crr
    ("Group size",                                            "Y"),   # Group?
]

def read_cells(sheet=SHEET):
    zf = zipfile.ZipFile(XLSX)
    shared = ["".join(t.text or "" for t in si.iter(NS + "t"))
              for si in ET.fromstring(zf.read("xl/sharedStrings.xml"))]
    root = ET.fromstring(zf.read(f"xl/worksheets/{sheet}.xml"))
    cells = {}
    for c in root.iter(NS + "c"):
        ref, t, v = c.get("r"), c.get("t"), c.find(NS + "v")
        val = v.text if v is not None else ""
        if t == "s" and val not in (None, ""):
            val = shared[int(val)]
        cells[ref] = val or ""
    return cells

def _fmt(v):
    """Trim float noise from cached cell values; pass strings through."""
    if v in (None, ""):
        return ""
    try:
        f = float(v)
    except ValueError:
        return v
    if f == int(f):
        return str(int(f))
    return f"{round(f, 5):g}"

def cmd_csv(man):
    import csv
    cells = read_cells()
    by_id = {e["id"]: e for e in man if e.get("id")}
    dest = os.path.join(OUT, "longoes.csv")
    n = 0
    with open(dest, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([h for h, _ in CSV_COLUMNS])
        for L in extract_links():               # one row per Activity hyperlink
            row_n = L["row"]
            e = by_id.get(classify(L["url"])[1], {})
            path = ("data/activities/" + e["file"]) if e.get("file") else ""
            out = []
            for header, col in CSV_COLUMNS:
                if header == "Activity file path":
                    out.append(path)
                else:
                    out.append(_fmt(cells.get(f"{col}{row_n}", "")))
            w.writerow(out)
            n += 1
    print(f"wrote {dest}  ({n} activities x {len(CSV_COLUMNS)} columns)")

def load_manifest():
    p = os.path.join(OUT, "manifest.json")
    return json.load(open(p)) if os.path.exists(p) else build_manifest()

def save_manifest(man):
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"),
              ensure_ascii=False, indent=2)

# --------------------------------------------------------------- downloading
def curl(url, dest, cookiejar=None):
    cmd = ["curl", "-sL", "-A", "Mozilla/5.0", "-o", dest, "-w", "%{http_code}"]
    if cookiejar:
        cmd += ["-b", cookiejar]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return (r.stdout or "").strip(), r.returncode

def cmd_rwgps(man):
    os.makedirs(os.path.join(OUT, "rwgps"), exist_ok=True)
    jobs = [e for e in man if e["source"] in ("rwgps_trip", "rwgps_route")]
    def run(e):
        base = "trips" if e["source"] == "rwgps_trip" else "routes"
        dest = os.path.join(OUT, "rwgps", f"{e['source']}_{e['id']}.json")
        code, rc = curl(f"https://ridewithgps.com/{base}/{e['id']}.json", dest)
        if rc == 0 and code.startswith("2") and os.path.getsize(dest) > 200:
            e["file"] = os.path.relpath(dest, OUT); e["status"] = "ok"
            return f"OK  {e['label'][:30]:30} {os.path.getsize(dest):>9}B"
        if os.path.exists(dest):
            os.remove(dest)
        e["status"] = f"unavailable (HTTP {code}; likely private)"; e.pop("file", None)
        return f"ERR {e['label'][:30]:30} HTTP {code}"
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for line in ex.map(run, jobs):
            print(line)

def cmd_rwgps_fit(man):
    """Authenticated: download RideWithGPS trips/routes as ORIGINAL .fit (preserves
    power, HR, temp, speed). Also reaches private trips. Replaces the .json file as
    the canonical track. Reads RWGPS_API_KEY / RWGPS_AUTH_TOKEN from the environment
    (source the repo .env first); credentials are never printed."""
    key = os.environ.get("RWGPS_API_KEY"); tok = os.environ.get("RWGPS_AUTH_TOKEN")
    if not key or not tok:
        sys.exit("set RWGPS_API_KEY and RWGPS_AUTH_TOKEN (e.g. `source ../../.env`)")
    os.makedirs(os.path.join(OUT, "rwgps"), exist_ok=True)
    jobs = [e for e in man if e["source"] in ("rwgps_trip", "rwgps_route")]
    def run(e):
        base = "trips" if e["source"] == "rwgps_trip" else "routes"
        dest = os.path.join(OUT, "rwgps", f"{e['source']}_{e['id']}.fit")
        r = subprocess.run(
            ["curl", "-sL", "-G", f"https://ridewithgps.com/{base}/{e['id']}.fit",
             "--data-urlencode", f"apikey={key}", "--data-urlencode", f"auth_token={tok}",
             "-o", dest, "-w", "%{http_code} %{content_type}"],
            capture_output=True, text=True, timeout=300)
        out = (r.stdout or "").split()
        code = out[0] if out else "?"
        ctype = out[1] if len(out) > 1 else ""
        ok = (r.returncode == 0 and code.startswith("2") and "fit" in ctype
              and os.path.exists(dest) and os.path.getsize(dest) > 2000)
        if ok:
            old = os.path.join(OUT, "rwgps", f"{e['source']}_{e['id']}.json")
            if os.path.exists(old): os.remove(old)        # drop the redundant json
            e["file"] = os.path.relpath(dest, OUT); e["ext"] = "fit"; e["status"] = "ok"
            return f"OK  {e['label'][:28]:28} {os.path.getsize(dest):>9}B  ({base})"
        if os.path.exists(dest): os.remove(dest)
        return f"ERR {e['label'][:28]:28} HTTP {code} {ctype}"
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        for line in ex.map(run, jobs):
            print(line)

def sniff_ext(path):
    head = open(path, "rb").read(512)
    if len(head) >= 12 and head[8:12] == b".FIT":
        return "fit"
    low = head.lstrip().lower()
    if b"trainingcenterdatabase" in low[:400]:
        return "tcx"
    if b"<gpx" in low[:400] or low.startswith(b"<?xml"):
        return "gpx"
    if b"<!doctype html" in low or b"<html" in low:
        return "html"
    return "bin"

def cmd_strava(man, cookiejar):
    os.makedirs(os.path.join(OUT, "strava"), exist_ok=True)
    jobs = [e for e in man if e["source"] == "strava"]
    def run(e):
        tmp = tempfile.mktemp(dir=OUT)
        code, rc = curl(f"https://www.strava.com/activities/{e['id']}/export_original",
                        tmp, cookiejar=cookiejar)
        if rc != 0 or not code.startswith("2") or not os.path.exists(tmp):
            if os.path.exists(tmp): os.remove(tmp)
            e["status"] = f"error HTTP {code}"; return f"ERR {e['label'][:26]:26} HTTP {code}"
        ext = sniff_ext(tmp)
        if ext == "html":
            os.remove(tmp); e["status"] = "login-wall (auth failed)"
            return f"ERR {e['label'][:26]:26} login-wall"
        dest = os.path.join(OUT, "strava", f"{e['id']}.{ext}")
        os.replace(tmp, dest)
        e["file"] = os.path.relpath(dest, OUT); e["ext"] = ext; e["status"] = "ok"
        return f"OK  {e['label'][:26]:26} {ext:4} {os.path.getsize(dest):>9}B"
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for line in ex.map(run, jobs):
            print(line)

# --------------------------------------------------------------- power audit
def fit_powers(path):
    """Return list of valid record-message (global 20) power values (field 7)."""
    b = open(path, "rb").read()
    pos = b[0]
    end = min(b[0] + struct.unpack_from("<I", b, 4)[0], len(b))
    defs, out = {}, []
    while pos < end:
        h = b[pos]; pos += 1
        if h & 0x80:  # compressed-timestamp data header
            d = defs.get((h >> 5) & 3)
            if not d: break
            if d["g"] == 20 and d["off7"] is not None:
                v = struct.unpack_from(("<" if d["arch"] == 0 else ">") + "H", b, pos + d["off7"])[0]
                if v != 0xFFFF: out.append(v)
            pos += d["len"]; continue
        if h & 0x40:  # definition message
            arch = b[pos + 1]
            g = struct.unpack_from((">" if arch else "<") + "H", b, pos + 2)[0]
            nf = b[pos + 4]; pos += 5
            off = off7 = tot = 0; off7 = None
            for _ in range(nf):
                num, size = b[pos], b[pos + 1]
                if g == 20 and num == 7: off7 = off
                off += size; tot += size; pos += 3
            if h & 0x20:  # developer fields — skip by declared size
                nd = b[pos]; pos += 1
                for _ in range(nd):
                    tot += b[pos + 1]; pos += 3
            defs[h & 0xF] = {"g": g, "len": tot, "arch": arch, "off7": off7}
        else:  # data message
            d = defs.get(h & 0xF)
            if not d: break
            if d["g"] == 20 and d["off7"] is not None:
                v = struct.unpack_from(("<" if d["arch"] == 0 else ">") + "H", b, pos + d["off7"])[0]
                if v != 0xFFFF: out.append(v)
            pos += d["len"]
    return out

def gpx_powers(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    return [float(x) for x in re.findall(r"<(?:\w+:)?power>\s*([\d.]+)", txt)]

def summarize(p):
    p = [x for x in p if x and x > 0]
    if not p:
        return {"has_power": False, "power_points": 0}
    return {"has_power": True, "power_points": len(p),
            "avg_power_w": round(sum(p) / len(p), 1), "max_power_w": max(p)}

def cmd_audit(man):
    npow = 0
    print(f"{'LABEL':28} {'SOURCE':12} {'PWR':6} DETAIL")
    print("-" * 78)
    for e in man:
        f = e.get("file")
        path = os.path.join(OUT, f) if f else None
        s = {"has_power": False, "power_points": 0}
        if path and os.path.exists(path):
            if f.endswith(".fit"):   s = summarize(fit_powers(path))
            elif f.endswith(".gpx"): s = summarize(gpx_powers(path))
            elif e["source"] == "rwgps_trip":
                d = json.load(open(path)); tp = d.get("track_points") or []
                s = summarize([p.get("p") for p in tp])
                e["distance_km"] = round((d.get("distance") or 0) / 1000, 2)
                e["elev_gain_m"] = d.get("elevation_gain")
                e["departed_at"] = d.get("departed_at")
            e["power"] = s
        tag = "POWER" if s.get("has_power") else "—"
        npow += s.get("has_power", False)
        det = f"{s.get('power_points', 0):>6} pts"
        if s.get("avg_power_w"): det += f"  avg {s['avg_power_w']}W max {s['max_power_w']}W"
        if not path: det = e.get("status", "no file")
        print(f"{e['label'][:27]:28} {e['source']:12} {tag:6} {det}")
    print("-" * 78)
    print(f"{npow}/{len(man)} activities have measured power")

# ----------------------------------------------------------------------- main
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    man = load_manifest()
    if cmd in ("rwgps", "all"):
        cmd_rwgps(man); save_manifest(man)
    if cmd in ("rwgps-fit", "all"):
        cmd_rwgps_fit(man); save_manifest(man)
    if cmd in ("strava", "all"):
        jar = sys.argv[2] if len(sys.argv) > 2 else None
        if not jar or not os.path.exists(jar):
            sys.exit("strava needs a cookie jar: python3 fetch.py strava <cookiejar>")
        cmd_strava(man, jar); save_manifest(man)
    if cmd == "csv":
        cmd_csv(man); return
    cmd_audit(man); save_manifest(man)
    if cmd == "all":
        cmd_csv(man)

if __name__ == "__main__":
    main()
