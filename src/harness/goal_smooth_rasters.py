#!/usr/bin/env python
# ENTRY 20 — Phase A: mask-normalized Gaussian pre-smoothing of the deployed IGC-SP 5 m raster.
#
# Run with the conda base python (numpy 2.3.5 / scipy 1.16.3 / rasterio 1.4.3):
#   /Users/danlessa/conda/bin/python goal_smooth_rasters.py
#
# SCHEME (pre-registered, amended to the DEPLOYABLE form — the app will run this in place at
# 135M cells with O(row) temp memory, so the harness tests exactly what ships):
#   SEQUENTIAL PER-AXIS MASK-NORMALIZED GAUSSIAN PASSES.
#   - validity mask m = (h > 0.5), FIXED for both passes (sampa_geral.tif declares no nodata;
#     0 = un-surveyed). Invalid cells stay invalid (value 0), are excluded from every pass, and
#     never receive a smoothed value.
#   - per-axis sigma in pixels from the geotransform: sigma_px = sigma_m / pixel_size_m for that
#     axis, with meters-per-degree = pi/180 * 6371000 = 111194.92664455873 (the harness's
#     haversine sphere); lon pixel size scaled by cos(center latitude).
#       pixel height 0.000047840435119 deg -> 5.3196 m (lat / axis 0 / columns pass)
#       pixel width  0.000047840435124 deg * cos(-23.5895870 deg) -> 4.8758 m (lon / axis 1 / rows pass)
#   - truncation radius r = ceil(3 * sigma_px); kernel weights w_k = exp(-k^2 / (2 sigma_px^2)),
#     k = -r..r, UNNORMALIZED — at each output cell the sum is normalized by the total weight of
#     the VALID in-window cells only (one rule handles borders and nodata holes alike).
#   - pass 1 smooths each ROW (axis 1): out1 = corr1d(h*m, w_x) / corr1d(m, w_x), evaluated at
#     valid cells only (zero-padded boundary: out-of-bounds contributes 0 to both sums).
#   - pass 2 smooths each COLUMN (axis 0) of that intermediate with the SAME mask m:
#     out = corr1d(out1*m, w_y) / corr1d(m, w_y) at valid cells.
#   This is identical to exact 2-D normalized convolution away from nodata holes and differs
#   only near hole edges. Implemented with scipy.ndimage.correlate1d per axis on (values*m) and
#   m separately (mode='constant', cval=0), which reproduces the per-axis rule exactly.
#   float32 throughout; geotransform/CRS copied from the source; no compression.
#
# Outputs (idempotent — skipped when the file exists with the right shape and the parameter
# sidecar goal_smooth_params.json matches):
#   $SCRATCH/sampa_geral_sm10m.tif ... sampa_geral_sm45m.tif   (sigma_m in {10,15,20,30,45})
import json, math, os, sys, time

import numpy as np
import rasterio
from scipy.ndimage import correlate1d

SRC = '/Users/danlessa/repos/pedalhidro/simujaules/dem/sampa_geral.tif'
SCRATCH = '/private/tmp/claude-501/-Users-danlessa-repos-pedalhidro-simujaules/6a419542-bc75-4ec1-aced-8e8de9a58ae3/scratchpad'
SIGMAS_M = [10, 15, 20, 30, 45]
M_PER_DEG = math.pi / 180.0 * 6371000.0   # 111194.92664455873 — matches the harness haversine sphere
VALID_FLOOR = 0.5                          # h > 0.5 m = surveyed (band min is 0.0 = un-surveyed)

def out_path(sig):
    return os.path.join(SCRATCH, f'sampa_geral_sm{sig}m.tif')

def kernel(sigma_px):
    r = math.ceil(3.0 * sigma_px)
    k = np.arange(-r, r + 1, dtype=np.float64)
    return np.exp(-(k * k) / (2.0 * sigma_px * sigma_px))

def masked_pass(vals, m, w, axis):
    # corr1d(vals*m)/corr1d(m) at valid cells; invalid cells -> 0. Zero-padded boundary.
    num = correlate1d(vals * m, w, axis=axis, mode='constant', cval=0.0)
    den = correlate1d(m, w, axis=axis, mode='constant', cval=0.0)
    out = np.zeros_like(vals)
    np.divide(num, den, out=out, where=(m > 0))
    return out

def main():
    os.makedirs(SCRATCH, exist_ok=True)
    with rasterio.open(SRC) as ds:
        prof = ds.profile.copy()
        h = ds.read(1).astype(np.float32)
        tr = ds.transform
    H, W = h.shape
    px_lat_m = abs(tr.e) * M_PER_DEG
    center_lat = tr.f + (H / 2.0) * tr.e
    px_lon_m = tr.a * M_PER_DEG * math.cos(math.radians(center_lat))
    params = { 'src': SRC, 'shape': [int(H), int(W)], 'm_per_deg': M_PER_DEG,
               'px_lat_m': px_lat_m, 'px_lon_m': px_lon_m, 'center_lat': center_lat,
               'valid_floor': VALID_FLOOR, 'scheme': 'sequential-per-axis-mask-normalized, fixed mask, r=ceil(3sigma), zero-padded',
               'sigmas_m': SIGMAS_M }
    side = os.path.join(SCRATCH, 'goal_smooth_params.json')
    prev = json.load(open(side)) if os.path.exists(side) else None
    print(f'px_lat_m={px_lat_m:.6f} px_lon_m={px_lon_m:.6f} center_lat={center_lat:.7f}')

    m = (h > VALID_FLOOR).astype(np.float32)
    n_valid = int((m > 0).sum())
    print(f'raster {W}x{H}, valid cells {n_valid} ({100.0*n_valid/(H*W):.2f}%)')

    prof.update(dtype='float32', count=1, compress=None, tiled=False)
    for sig in SIGMAS_M:
        p = out_path(sig)
        if os.path.exists(p) and prev == params:
            with rasterio.open(p) as d0:
                if d0.width == W and d0.height == H:
                    print(f'sigma={sig} m: exists with right shape + params match — skipped')
                    continue
        t0 = time.time()
        sx = sig / px_lon_m   # axis 1 (rows pass, lon direction)
        sy = sig / px_lat_m   # axis 0 (columns pass, lat direction)
        wx, wy = kernel(sx), kernel(sy)
        pass1 = masked_pass(h, m, wx, axis=1)
        out = masked_pass(pass1, m, wy, axis=0)
        del pass1
        out[m == 0] = 0.0
        with rasterio.open(p, 'w', **prof) as dst:
            dst.write(out, 1)
        print(f'sigma={sig} m: sigma_px=({sx:.4f},{sy:.4f}) r=({math.ceil(3*sx)},{math.ceil(3*sy)}) '
              f'-> {p} ({time.time()-t0:.1f} s)')
        del out
    json.dump(params, open(side, 'w'), indent=1)
    print('done')

if __name__ == '__main__':
    main()
