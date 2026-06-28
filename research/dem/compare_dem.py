#!/usr/bin/env python3
"""Compare recorded track elevation against FABDEM, SRTM and COP30 DEMs.

For each ride whose track lies within the available DEM tiles, sample the three
DEMs at every track point (via gdallocationinfo), then compare to the device's
recorded elevation: vertical bias, shape RMS (after removing the mean offset),
and — most relevant to the energy model — the cumulative ascent h+ each source
yields (raw and 3 m-hysteresis). DEMs are independent of the barometric/GPS noise
in the recorded track, so they bound how much of the recorded h+ is real.

Usage: python3 compare_dem.py <coords_dir> <tiles_dir>
  tiles_dir/{fabdem,cop30,srtm}/<TILE>.{tif,tif,hgt}
"""
import sys, os, csv, math, subprocess, statistics

COORDS, TILES = sys.argv[1], sys.argv[2]
DEMS = {"fabdem": ("fabdem", "tif"), "srtm": ("srtm", "hgt"), "cop30": ("cop30", "tif")}

def tile(lat, lon):
    la, lo = math.floor(lat), math.floor(lon)
    return ("S" if la < 0 else "N") + f"{abs(la):02d}" + ("W" if lo < 0 else "E") + f"{abs(lo):03d}"

def have_tile(dem, t):
    sub, ext = DEMS[dem]
    return os.path.exists(os.path.join(TILES, sub, f"{t}.{ext}"))

def sample(dem, t, lonlat, interp="near"):
    """Batch-sample one DEM tile at [(lon,lat),...] -> [elev or None].
    interp = 'near' (default, pixel value) or 'bilinear' (sub-pixel interpolation)."""
    sub, ext = DEMS[dem]
    raster = os.path.join(TILES, sub, f"{t}.{ext}")
    inp = "".join(f"{lon} {lat}\n" for lon, lat in lonlat)
    r = subprocess.run(["gdallocationinfo", "-valonly", "-wgs84", "-r", interp, raster],
                       input=inp, capture_output=True, text=True)
    out = []
    for line in r.stdout.split("\n"):
        line = line.strip()
        if line == "":
            out.append(None); continue
        try:
            v = float(line)
            out.append(None if v <= -1000 or v > 9000 else v)  # nodata / void
        except ValueError:
            out.append(None)
    # gdallocationinfo prints one line per point; pad/truncate defensively
    while len(out) < len(lonlat): out.append(None)
    return out[:len(lonlat)]

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

def descent(h, tau):   # h₋: same hysteresis on the negated series
    return ascent([-x for x in h if x is not None], tau)

def main():
    ids = sorted(f[:-4] for f in os.listdir(COORDS) if f.endswith(".csv") and not f.startswith("_"))
    rows = []
    agg = {d: {"bias": [], "rms": [], "hp3_n": [], "hp3_b": [], "hm3_b": []} for d in DEMS}  # _n near, _b bilinear
    agg_rec = {"hp_raw": 0.0, "hp3": 0.0, "hm3": 0.0}
    for rid in ids:
        pts = list(csv.DictReader(open(os.path.join(COORDS, f"{rid}.csv"))))
        lonlat = [(float(p["lon"]), float(p["lat"])) for p in pts]
        rec = [float(p["ele"]) for p in pts]
        tiles_used = {tile(la, lo) for lo, la in lonlat}
        if not all(have_tile(d, t) for d in DEMS for t in tiles_used):
            continue  # tiles not downloaded for this ride
        # single-tile fast path (all rides here are within one tile)
        if len(tiles_used) != 1:
            continue
        t = next(iter(tiles_used))
        demN = {d: sample(d, t, lonlat, "near") for d in DEMS}       # nearest neighbour
        demB = {d: sample(d, t, lonlat, "bilinear") for d in DEMS}   # bilinear (sub-pixel)
        line = {"id": rid, "n": len(pts), "rec_hp3": ascent(rec, 3), "rec_hm3": descent(rec, 3)}
        agg_rec["hp_raw"] += ascent(rec, 0); agg_rec["hp3"] += line["rec_hp3"]; agg_rec["hm3"] += line["rec_hm3"]
        for d in DEMS:
            dvB = demB[d]
            diffs = [dvB[i] - rec[i] for i in range(len(rec)) if dvB[i] is not None]
            if not diffs: continue
            bias = statistics.mean(diffs)
            rms = math.sqrt(statistics.mean((x - bias) ** 2 for x in diffs))
            line[f"{d}_bias"] = bias; line[f"{d}_rms"] = rms
            agg[d]["bias"].append(bias); agg[d]["rms"].append(rms)
            agg[d]["hp3_n"].append(ascent(demN[d], 3))
            agg[d]["hp3_b"].append(ascent(dvB, 3)); agg[d]["hm3_b"].append(descent(dvB, 3))
        rows.append(line)

    # aggregate
    n = len(rows)
    rec3 = agg_rec["hp3"]
    print(f"AGGREGATE over {n} rides (single-tile S24W047).  recorded 3m-hyst ascent = {rec3:.0f} m")
    print(f"\n{'DEM':8}{'med bias(m)':>12}{'shapeRMS(m)':>13}"
          f"{'Σh+ NEAREST':>13}{'vs rec':>8}{'Σh+ BILINEAR':>14}{'vs rec':>8}")
    print("-" * 76)
    for d in DEMS:
        a = agg[d]
        if not a["bias"]: continue
        hn, hb = sum(a["hp3_n"]), sum(a["hp3_b"])
        print(f"{d:8}{statistics.median(a['bias']):>12.1f}{statistics.median(a['rms']):>13.1f}"
              f"{hn:>13.0f}{(hn-rec3)/rec3*100:>7.0f}%{hb:>14.0f}{(hb-rec3)/rec3*100:>7.0f}%")
    # k_h for DEM-derived h+ and h-  =  recorded baro / DEM (bilinear, 3 m) — the factor
    # that maps a DEM-derived ascent/descent back to the empirical (road) value.
    recm3 = agg_rec["hm3"]
    print(f"\nk_h = recorded / DEM   (bilinear, 3 m-hyst)   recorded h+={rec3:.0f} h-={recm3:.0f} m")
    print(f"{'DEM':8}{'Σ h+ (DEM)':>12}{'k_h(h+)':>9}{'Σ h- (DEM)':>12}{'k_h(h-)':>9}")
    for d in DEMS:
        hp, hm = sum(agg[d]["hp3_b"]), sum(agg[d]["hm3_b"])
        if hp and hm:
            print(f"{d:8}{hp:>12.0f}{rec3/hp:>9.2f}{hm:>12.0f}{recm3/hm:>9.2f}")

if __name__ == "__main__":
    main()
