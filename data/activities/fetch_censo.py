#!/usr/bin/env python3
"""Download the Censo Hidrográfico ride tracks listed in censo-hidrografico.xlsx
(columns Q 'Ativ. Strava' / R 'Ativ. RWGPS') into data/activities/censohidrografico/.

Source preference: **RWGPS over Strava** (Danilo's note) — a ride with both links is
pulled from RWGPS; Strava-only rides from Strava. Both carry power (the device records
it), so every ride yields an empirical ∫P·dt for the model comparison.

Auth: RWGPS via .env (RWGPS_API_KEY / RWGPS_AUTH_TOKEN — `source ../../.env` first);
Strava via a Netscape cookie jar passed as argv[1]. Credentials are never printed and
never written into the repo (the whole censohidrografico/ dir is gitignored).

  source ../../.env && python3 fetch_censo.py <strava_cookiejar>

Idempotent: skips a ride whose file already exists. Reuses fetch.py's curl/sniff_ext.
"""
import os, sys, json, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # curl(), sniff_ext()

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "censohidrografico")
MAN = os.path.join(DEST, "manifest.json")

WORKERS = 6
STRAVA_DELAY = 0.0   # seconds; raise (and drop WORKERS to 1) if Strava returns HTML

def main():
    global WORKERS, STRAVA_DELAY
    jar = sys.argv[1] if len(sys.argv) > 1 else None
    if len(sys.argv) > 2: WORKERS = int(sys.argv[2])
    if len(sys.argv) > 3: STRAVA_DELAY = float(sys.argv[3])
    key, tok = os.environ.get("RWGPS_API_KEY"), os.environ.get("RWGPS_AUTH_TOKEN")
    man = json.load(open(MAN))
    os.makedirs(os.path.join(DEST, "rwgps"), exist_ok=True)
    os.makedirs(os.path.join(DEST, "strava"), exist_ok=True)

    def run(e):
        if e["source"] == "rwgps":
            if not (key and tok):
                return (e, None, "no RWGPS creds")
            dest = os.path.join(DEST, "rwgps", f"{e['rwgps_id']}.fit")
            if os.path.exists(dest):
                e["file"] = os.path.relpath(dest, HERE); return (e, "skip", None)
            # NB: apikey/auth_token in the URL are passed on curl's argv, so they are
            # visible to a local `ps` while the fetch runs. Fine for a personal machine;
            # they are read from env (.env), never committed or printed.
            url = f"https://ridewithgps.com/{e['rwgps_kind']}s/{e['rwgps_id']}.fit?apikey={key}&auth_token={tok}"
            code, _ = fetch.curl(url, dest)
            if code != "200" or not os.path.exists(dest) or os.path.getsize(dest) < 200:
                return (e, None, f"rwgps http {code}")
            e["file"] = os.path.relpath(dest, HERE); return (e, "ok", None)
        else:  # strava
            if not jar:
                return (e, None, "no strava cookie")
            tmp = os.path.join(DEST, "strava", f"{e['strava_id']}.bin")
            final_existing = next((os.path.join(DEST, "strava", f"{e['strava_id']}.{x}")
                                   for x in ("fit", "gpx", "tcx")
                                   if os.path.exists(os.path.join(DEST, "strava", f"{e['strava_id']}.{x}"))), None)
            if final_existing:
                e["file"] = os.path.relpath(final_existing, HERE); return (e, "skip", None)
            time.sleep(STRAVA_DELAY)   # Strava rate-limits export_original; pace requests
            code, _ = fetch.curl(f"https://www.strava.com/activities/{e['strava_id']}/export_original",
                                 tmp, cookiejar=jar)
            if code != "200" or not os.path.exists(tmp) or os.path.getsize(tmp) < 200:
                if os.path.exists(tmp): os.remove(tmp)
                return (e, None, f"strava http {code}")
            ext = fetch.sniff_ext(tmp)
            dest = os.path.join(DEST, "strava", f"{e['strava_id']}.{ext}")
            os.replace(tmp, dest)
            e["file"] = os.path.relpath(dest, HERE); return (e, "ok", None)

    ok = skip = fail = 0; fails = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for e, status, err in ex.map(run, man):
            if status == "ok": ok += 1
            elif status == "skip": skip += 1
            else: fail += 1; fails.append(f"{e['name'][:30]} [{e['source']}]: {err}")
    json.dump(man, open(MAN, "w"), ensure_ascii=False, indent=1)  # now carries 'file'
    print(f"downloaded {ok}, skipped {skip}, failed {fail} / {len(man)}")
    for f in fails[:20]: print("  FAIL", f)

if __name__ == "__main__":
    main()
