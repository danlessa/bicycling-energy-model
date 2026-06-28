#!/usr/bin/env python3
"""Compare recorded track elevation against FABDEM, SRTM, COP30 (30 m global) and,
where covered, the IGC-SP 2010 5 m aerophotogrammetric DTM.

For each ride within the DEM tiles, sample each source at every track point
(bilinear via gdallocationinfo), then compare to the device's recorded elevation:
vertical bias, shape RMS (after removing the mean offset), the cumulative ascent
h+ / descent h- each source yields, and k_h = recorded / source — the factor that
maps a source-derived h+/h- back to the recorded (road) value.

Usage: python3 compare_dem.py <coords_dir> <tiles_dir> [igc.tif]
  tiles_dir/{fabdem,cop30,srtm}/<TILE>.{tif,tif,hgt}
"""
import sys, os, csv, math, subprocess, statistics

COORDS, TILES = sys.argv[1], sys.argv[2]
IGC = sys.argv[3] if len(sys.argv) > 3 else None
IGC_BBOX = (-47.457, -24.126, -45.609, -23.058)   # WGS84 lon_min, lat_min, lon_max, lat_max
DEMS = {"fabdem": ("fabdem", "tif"), "srtm": ("srtm", "hgt"), "cop30": ("cop30", "tif")}

def tile(lat, lon):
    la, lo = math.floor(lat), math.floor(lon)
    return ("S" if la < 0 else "N") + f"{abs(la):02d}" + ("W" if lo < 0 else "E") + f"{abs(lo):03d}"

def have_tile(dem, t):
    sub, ext = DEMS[dem]
    return os.path.exists(os.path.join(TILES, sub, f"{t}.{ext}"))

def query(raster, lonlat, interp):
    """Batch-sample a raster at [(lon,lat),...] (WGS84) -> [elev or None]."""
    inp = "".join(f"{lon} {lat}\n" for lon, lat in lonlat)
    r = subprocess.run(["gdallocationinfo", "-valonly", "-wgs84", "-r", interp, raster],
                       input=inp, capture_output=True, text=True)
    out = []
    for line in r.stdout.split("\n"):
        line = line.strip()
        if line == "":
            out.append(None); continue
        try:
            v = float(line); out.append(None if v <= -1000 or v > 9000 else v)
        except ValueError:
            out.append(None)
    while len(out) < len(lonlat): out.append(None)
    return out[:len(lonlat)]

def sample(dem, t, lonlat, interp="near"):
    sub, ext = DEMS[dem]
    return query(os.path.join(TILES, sub, f"{t}.{ext}"), lonlat, interp)

def ascent(h, tau):
    vals = [x for x in h if x is not None]
    if len(vals) < 2: return 0.0
    if tau <= 0:
        return sum(max(0, vals[i] - vals[i-1]) for i in range(1, len(vals)))
    gain, ref = 0.0, vals[0]
    for x in vals[1:]:
        d = x - ref
        if d >= tau: gain += d; ref = x
        elif d <= -tau: ref = x
    return gain

def descent(h, tau):
    return ascent([-x for x in h if x is not None], tau)

def stats(diffs):
    bias = statistics.mean(diffs)
    return bias, math.sqrt(statistics.mean((x - bias) ** 2 for x in diffs))

def main():
    ids = sorted(f[:-4] for f in os.listdir(COORDS) if f.endswith(".csv") and not f.startswith("_"))
    rides = []
    for rid in ids:
        pts = list(csv.DictReader(open(os.path.join(COORDS, f"{rid}.csv"))))
        lonlat = [(float(p["lon"]), float(p["lat"])) for p in pts]
        rec = [float(p["ele"]) for p in pts]
        tiles_used = {tile(la, lo) for lo, la in lonlat}
        if len(tiles_used) != 1 or not all(have_tile(d, t) for d in DEMS for t in tiles_used):
            continue
        t = next(iter(tiles_used))
        r = {"id": rid, "rec_raw": ascent(rec, 0), "rec3": ascent(rec, 3), "recm3": descent(rec, 3)}
        for d in DEMS:
            dvB = sample(d, t, lonlat, "bilinear")
            diffs = [dvB[i] - rec[i] for i in range(len(rec)) if dvB[i] is not None]
            if diffs: r[d + "_bias"], r[d + "_rms"] = stats(diffs)
            r[d + "_hp3"] = ascent(dvB, 3); r[d + "_hm3"] = descent(dvB, 3)
            r[d + "_hp3_n"] = ascent(sample(d, t, lonlat, "near"), 3)
        if IGC and all(IGC_BBOX[0] <= lo <= IGC_BBOX[2] and IGC_BBOX[1] <= la <= IGC_BBOX[3] for lo, la in lonlat):
            iv = query(IGC, lonlat, "bilinear")
            if sum(1 for x in iv if x is not None) / len(iv) > 0.99:
                diffs = [iv[i] - rec[i] for i in range(len(rec)) if iv[i] is not None]
                r["igc"] = True; r["igc_bias"], r["igc_rms"] = stats(diffs)
                r["igc_raw"] = ascent(iv, 0); r["igc_hp3"] = ascent(iv, 3); r["igc_hm3"] = descent(iv, 3)
        rides.append(r)

    # Table 1 — all rides, recorded baro as the reference (its own limitations noted below)
    rec3 = sum(r["rec3"] for r in rides)
    print(f"TABLE 1 — {len(rides)} rides (S24W047), recorded-baro reference (h+ 3m = {rec3:.0f} m)")
    print(f"{'source':8}{'res':>5}{'med bias':>10}{'shapeRMS':>10}{'Σh+ near':>10}{'Σh+ bilin':>11}{'vs baro':>9}")
    for d in DEMS:
        hn = sum(r[d + "_hp3_n"] for r in rides); hb = sum(r[d + "_hp3"] for r in rides)
        bias = statistics.median(r[d + "_bias"] for r in rides if d + "_bias" in r)
        rms = statistics.median(r[d + "_rms"] for r in rides if d + "_rms" in r)
        print(f"{d:8}{'30':>4}m{bias:>10.1f}{rms:>10.1f}{hn:>10.0f}{hb:>11.0f}{(hb-rec3)/rec3*100:>8.0f}%")

    # Table 2 — IGC 5 m DTM as reference (baro lags/misses climbs; DTM misses bridges/tunnels)
    ig = [r for r in rides if r.get("igc")]
    if ig:
        I3 = sum(r["igc_hp3"] for r in ig)
        b3 = sum(r["rec3"] for r in ig); braw = sum(r["rec_raw"] for r in ig)
        print(f"\nTABLE 2 — IGC 5 m DTM as reference, over {len(ig)} covered rides (h+ 3 m-hyst)")
        print(f"  IGC (5 m, bilinear)     {I3:>6.0f} m   = reference")
        print(f"  recorded baro (3 m)     {b3:>6.0f} m   {b3/I3*100-100:+.0f}% vs IGC   (raw {braw:.0f}, {braw/I3*100-100:+.0f}%)   k_h=IGC/baro {I3/b3:.2f}")
        for d in DEMS:
            h3 = sum(r[d + "_hp3"] for r in ig)
            print(f"  {d:8} (30 m, bilinear) {h3:>6.0f} m   {h3/I3*100-100:+.0f}% vs IGC                       k_h=IGC/{d[:5]} {I3/h3:.2f}")

if __name__ == "__main__":
    main()
