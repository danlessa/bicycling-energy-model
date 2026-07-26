"""Binary FIT parsing — port of the app's parseFIT + compare.mjs's
ptsFromFIT/finishPts/empiricalKJ/overallMeanPower.

Minimal parser of `record` messages (global message 20): distance, altitude,
lat/lon, speed, power, timestamp. Honors per-definition endianness,
compressed-timestamp headers, developer fields, and FIT invalid-value
markers. Points use None where the JS uses `undefined`.
"""

from __future__ import annotations

import math
import struct
from typing import Callable

from .types import Points

from .profiles import haversine

_SEMI = 180 / 2147483648


def _reader(buf: bytes, little: bool) -> Callable[[int, int], float | None]:
    e = "<" if little else ">"

    def read(p: int, bt: int) -> float | None:
        b = bt & 0x1F
        try:
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
        except struct.error:
            return None
        return None  # strings / 64-bit ignored

    return read


def parse_fit(buf: bytes, meta: dict | None = None) -> list[dict]:
    """Parse a FIT byte buffer into a list of `record` dicts.

    Honors per-definition endianness, compressed-timestamp headers, developer
    fields and FIT invalid-value markers. `record` is global message 20; every
    message's field 253 advances the running clock.

    Each record may carry: lat, lon, alt, dist, speed, power, cad, time.

    Pass a dict as `meta` to also collect the file-level fields some harnesses
    need — it is filled with:
      manufacturer -- file_id (msg 0) field 1; 260 == Zwift, i.e. a virtual ride
      sport        -- first sport enum seen (msg 12 field 0, or session msg 18
                      field 5), used by the inventories to keep only cycling
    """
    if meta is not None:
        meta.setdefault("manufacturer", None)
        meta.setdefault("sport", None)
    if len(buf) < 14:
        raise ValueError("FIT muito curto")
    header_size = buf[0]
    data_size = struct.unpack_from("<I", buf, 4)[0]
    if buf[8:12] != b".FIT":
        raise ValueError("assinatura .FIT ausente")
    end = min(header_size + data_size, len(buf))
    pos = header_size
    defs = {}
    records = []
    last_ts = None
    while pos < end:
        rh = buf[pos]
        pos += 1
        ts_offset = None
        is_def = has_dev = False
        if rh & 0x80:  # compressed-timestamp data message
            local = (rh >> 5) & 0x03
            ts_offset = rh & 0x1F
        else:
            local = rh & 0x0F
            is_def = bool(rh & 0x40)
            has_dev = bool(rh & 0x20)
        if is_def:
            pos += 1  # reserved
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
                            rec["lat"] = v * _SEMI
                        elif num == 1:
                            rec["lon"] = v * _SEMI
                        elif num == 2:
                            if "alt" not in rec:
                                rec["alt"] = v / 5 - 500
                        elif num == 78:
                            rec["alt"] = v / 5 - 500  # enhanced altitude (preferred)
                        elif num == 5:
                            rec["dist"] = v / 100
                        elif num == 6:
                            if "speed" not in rec:
                                rec["speed"] = v / 1000  # m/s
                        elif num == 73:
                            rec["speed"] = v / 1000  # enhanced_speed (preferred)
                        elif num == 7:
                            rec["power"] = v
                        elif num == 4:
                            rec["cad"] = v  # cadence (rpm) — 0 ⇒ not pedalling
                        elif num == 253:
                            rec["time"] = v
                elif meta is not None and gmn == 0 and num == 1:
                    v = read(p, bt)  # file_id manufacturer (260 = Zwift ⇒ virtual)
                    if v is not None:
                        meta["manufacturer"] = v
                elif meta is not None and ((gmn == 12 and num == 0)
                                           or (gmn == 18 and num == 5)):
                    v = read(p, bt)  # sport enum — first one seen wins
                    if v is not None and meta["sport"] is None:
                        meta["sport"] = v
                elif num == 253:  # any message's timestamp advances the clock
                    v = read(p, bt)
                    if v is not None:
                        rec["time"] = v
                p += size
            pos = p + d["devSize"]
            # compressed-timestamp header: rebuild time from the 5-bit offset
            if ts_offset is not None and "time" not in rec and last_ts is not None:
                ts = (last_ts & ~31) | ts_offset
                if ts < last_ts:
                    ts += 32
                rec["time"] = ts
            if "time" in rec:
                last_ts = rec["time"]
            if gmn == 20:
                records.append(rec)
    return records


def finish_pts(pts: Points) -> None:
    """dt weight (clamp pauses) + speed fallback (compare.mjs finishPts)."""
    for i in range(len(pts)):
        raw = (pts[i]["t"] - pts[i - 1]["t"]
               if i > 0 and pts[i].get("t") is not None and pts[i - 1].get("t") is not None
               else None)
        w = min(max(raw, 0), 10) if raw is not None else 1
        pts[i]["dt"] = w
        if pts[i].get("v") is None and i > 0:
            dtv = raw if (raw is not None and raw > 0) else w
            if dtv > 0:
                pts[i]["v"] = (pts[i]["x"] - pts[i - 1]["x"]) / dtv


def pts_from_fit(buf: bytes, meta: dict | None = None) -> Points:
    """FIT buffer -> point list {x, alt, power, cad, t, v, dt}.

    Distance is interpolated by record index between dist anchors so devices
    that log distance and altitude in separate records keep every altitude
    sample; for normal files this reproduces the raw distance exactly.
    `meta` is passed through to parse_fit (manufacturer / sport).
    """
    recs = parse_fit(buf, meta)
    if len(recs) < 2:
        raise ValueError("FIT sem registros")
    pts = []
    if any("dist" in r for r in recs):
        di, dv = [], []
        for i, r in enumerate(recs):
            if "dist" in r:
                di.append(i)
                dv.append(max(r["dist"], dv[-1]) if dv else r["dist"])
        last_alt = None
        k = 0
        for i, r in enumerate(recs):
            if "alt" in r:
                last_alt = r["alt"]
            if last_alt is None:
                continue
            while k < len(di) - 1 and di[k + 1] <= i:
                k += 1
            if i <= di[0]:
                x = dv[0]
            elif i >= di[-1]:
                x = dv[-1]
            else:
                f = (i - di[k]) / (di[k + 1] - di[k])
                x = dv[k] + (dv[k + 1] - dv[k]) * f
            pts.append({"x": x, "alt": last_alt, "power": r.get("power"),
                        "cad": r.get("cad"), "t": r.get("time"),
                        "v": r.get("speed")})
    else:
        geo = [r for r in recs if "lat" in r and "lon" in r and "alt" in r]
        if len(geo) < 2:
            raise ValueError("FIT sem distância nem GPS")
        cum = 0.0
        pts.append({"x": 0.0, "alt": geo[0]["alt"], "power": geo[0].get("power"),
                    "cad": geo[0].get("cad"), "t": geo[0].get("time"),
                    "v": geo[0].get("speed")})
        for i in range(1, len(geo)):
            cum += haversine(geo[i - 1], geo[i])
            pts.append({"x": cum, "alt": geo[i]["alt"], "power": geo[i].get("power"),
                        "cad": geo[i].get("cad"), "t": geo[i].get("time"),
                        "v": geo[i].get("speed")})
    finish_pts(pts)
    return pts


def empirical_kj(pts: Points) -> float:
    """Measured pedalling energy sum(power*dt), J -> kJ (compare.mjs empiricalKJ)."""
    e = 0.0
    for q in pts:
        if q.get("power") is not None:
            e += q["power"] * (q.get("dt") or 0)
    return e / 1000


def overall_mean_power(pts: Points) -> float:
    """Time-weighted mean power over samples that carry power (compare.mjs)."""
    sw = swp = 0.0
    for q in pts:
        if q.get("power") is not None:
            w = q.get("dt") or 1
            sw += w
            swp += w * q["power"]
    return swp / sw if sw else 0.0
