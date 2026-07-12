#!/usr/bin/env python3
"""Emit model_inputs.json: per-ride physical parameters for the model comparison,
taken straight from the 'Atividades v2' sheet (the rider's own values), joined to
the local track file path. Consumed by compare.mjs, which runs the real
approximate()/canonical() engines on each track.

Columns pulled (sheet row-2 headers): M Weight, N CdA, AE efCrr (blended road/
offroad Crr), L Headwind, AA g_d_eff (eps), AT Rho, AR Eff (keff)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # reuse read_cells / extract_links / classify

OUT = fetch.OUT
PARAM_COLS = {  # json key -> sheet column
    "m": "M", "cda": "N", "crr": "AE", "wind_kmh": "L",
    "eps": "AA", "rho": "AT", "keff": "AR",
    "pflat_pavg": "AB",   # rider's flat-power / avg-power ratio (sets P_flat -> v_f)
    "wmes": "S",          # <W>_mes: rider's measured avg power = Work / Moving Time (W)
}

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def main():
    cells = fetch.read_cells()
    man = {e["id"]: e for e in json.load(open(os.path.join(OUT, "manifest.json"))) if e.get("id")}
    rows = []
    for L in fetch.extract_links():
        kind, aid = fetch.classify(L["url"])
        e = man.get(aid, {})
        pw = (e.get("power") or {})
        entry = {
            "label": L["label"], "cell": L["cell"], "source": kind, "id": aid,
            "file": e.get("file"), "has_power": bool(pw.get("has_power")),
        }
        for key, col in PARAM_COLS.items():
            entry[key] = fnum(cells.get(f"{col}{L['row']}", ""))
        rows.append(entry)
    dest = os.path.join(OUT, "model_inputs.json")
    json.dump(rows, open(dest, "w"), ensure_ascii=False, indent=1)
    usable = sum(1 for r in rows if r["file"] and r["has_power"])
    print(f"wrote {dest}: {len(rows)} rides, {usable} with file+power (model-comparable)")

if __name__ == "__main__":
    main()
