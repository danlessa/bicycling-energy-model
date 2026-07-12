"""Physics engines — line-by-line ports of applet/index.html.

Reference functions (same names, camelCase there): flatEqSpeed,
resampleProfile, smoothElevation, canonical, approximate, v2Edge, approxTime,
epsGeom, plus compare.mjs's deadband/ascentHyst. Keep the arithmetic ORDER
identical to the JS — parity is checked to ~1e-9 relative by
analysis/parity/run_parity.py.

Profiles are plain dicts {"x": [m...], "h": [m...]} (ground distance,
elevation). Parameters `p` is a dict: m, Crr, CdA, rho, keff, vmax, vstart,
wind (SI; speeds m/s). Regime powers `pw`: climb, flat, descent (W),
climbThr, descThr (grade fractions).
"""

import math

G = 9.81

_INF = float("inf")


def flat_eq_speed(P, p):
    """Flat-equilibrium GROUND speed at pedal power P (JS flatEqSpeed).

    Solves (Crr*mg + 0.5*rho*CdA*(v+w)*|v+w|) * v = keff*P by bisection with
    SIGNED drag; under a tailwind bisect the monotone branch [-w, 40] first.
    """
    a = p["Crr"] * p["m"] * G
    b = 0.5 * p["rho"] * p["CdA"]
    w = p.get("wind", 0.0) or 0.0

    def wheel(v):
        rel = v + w
        return (a + b * rel * abs(rel)) * v

    target = p["keff"] * P
    lo, hi = max(0.0, -w), 40.0
    if wheel(lo) > target:
        hi, lo = lo, 0.0
    for _ in range(60):
        v = (lo + hi) / 2
        if wheel(v) < target:
            lo = v
        else:
            hi = v
    return (lo + hi) / 2


def resample_profile(src, dx):
    """Resample an arbitrary {x,h} profile onto a uniform dx grid (JS resampleProfile)."""
    sx, sh = src["x"], src["h"]
    total = sx[len(sx) - 1]
    n = max(2, round(total / dx) + 1)
    x = [0.0] * n
    h = [0.0] * n
    j = 0
    for i in range(n):
        d = total if i == n - 1 else total * i / (n - 1)
        while j < len(sx) - 2 and sx[j + 1] < d:
            j += 1
        seg = sx[j + 1] - sx[j]
        f = (d - sx[j]) / seg if seg > 1e-9 else 0.0
        x[i] = d
        h[i] = sh[j] * (1 - f) + sh[j + 1] * f
    return {"x": x, "h": h}


def deadband(h, tau):
    """Deadband (backlash) filter on an elevation ARRAY (compare.mjs deadband)."""
    out = [0.0] * len(h)
    y = h[0]
    out[0] = y
    for i in range(1, len(h)):
        if h[i] > y + tau:
            y = h[i] - tau
        elif h[i] < y - tau:
            y = h[i] + tau
        out[i] = y
    return out


def smooth_elevation(src, tau):
    """Deadband filter on a PROFILE, tau<=0 returns it unchanged (JS smoothElevation)."""
    if not tau > 0:
        return src
    return {"x": src["x"], "h": deadband(src["h"], tau)}


def ascent_hyst(h, tau):
    """Cumulative ascent with hysteresis threshold tau (compare.mjs ascentHyst)."""
    gain = 0.0
    if tau <= 0:
        for i in range(1, len(h)):
            d = h[i] - h[i - 1]
            if d > 0:
                gain += d
        return gain
    ref = h[0]
    for i in range(1, len(h)):
        d = h[i] - ref
        if d >= tau:
            gain += d
            ref = h[i]
        elif d <= -tau:
            ref = h[i]
    return gain


def canonical(prof, pw, p):
    """Forward-dynamics simulation (JS canonical): distance-marching with
    adaptive sub-steps and the SEMI-IMPLICIT propulsion update (safeguarded
    Newton on g(u) = u - A/sqrt(u) - B) — conserves energy exactly; leg
    energy can never fall below the work done. No KE floor: P=0 against
    resistance STALLS the bike."""
    m, Crr, CdA, rho, keff, vmax = p["m"], p["Crr"], p["CdA"], p["rho"], p["keff"], p["vmax"]
    xs, hs = prof["x"], prof["h"]
    n = len(xs)
    DT_MAX, DS_MIN = 0.25, 0.2
    KEinit = 0.5 * m * p["vstart"] * p["vstart"]
    KE = KEinit
    legE = t = Wrr = Waero = Wgrav = Wbrake = 0.0
    speed = [0.0] * n
    brk = [0] * n
    regime = [0] * n
    speed[0] = math.sqrt(2 * KE / m)
    minV = speed[0]
    keCap = 0.5 * m * vmax * vmax
    stalled = False
    wind = p["wind"]
    for i in range(1, n):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        slope = dh / dx
        sec = math.sqrt(1 + slope * slope)
        cos = 1 / sec
        sin = slope / sec
        Frr = Crr * m * G * cos
        Fgrav = m * G * sin
        if slope >= pw["climbThr"]:
            reg, P = 1, pw["climb"]
        elif slope <= pw["descThr"]:
            reg, P = -1, pw["descent"]
        else:
            reg, P = 0, pw["flat"]
        regime[i] = reg
        remaining = dx * sec
        braked = 0
        while remaining > 1e-9:
            v = math.sqrt(2 * KE / m)
            dsSub = min(remaining, max(v * DT_MAX, DS_MIN))
            rel = v + wind
            Faero = 0.5 * rho * CdA * rel * abs(rel)
            R = Frr + Faero + Fgrav
            Pleg = min(max(R * v / keff, 0.0), P) if v >= vmax else P
            A = keff * Pleg * dsSub * math.sqrt(m / 2)
            B = KE - R * dsSub
            if A > 0:
                lo = 1e-12
                hi = max(KE, B, 1.0) + A + 1
                while hi - A / math.sqrt(hi) - B <= 0:
                    hi *= 2
                KEn = KE if (KE > lo and KE < hi) else 0.5 * (lo + hi)
                for _ in range(40):
                    root = math.sqrt(KEn)
                    g = KEn - A / root - B
                    if g > 0:
                        hi = KEn
                    else:
                        lo = KEn
                    nxt = KEn - g / (1 + 0.5 * A / (KEn * root))
                    if not (nxt > lo and nxt < hi):
                        nxt = 0.5 * (lo + hi)
                    if abs(nxt - KEn) <= 1e-9 * KEn + 1e-12:
                        KEn = nxt
                        break
                    KEn = nxt
            else:
                # A = 0 (no propulsion): exact solution, KE falls linearly — NO floor.
                KEn = B
                if KEn <= 0:
                    dsStop = KE / R if R > 0 else 0.0
                    t += math.sqrt(2 * m * max(KE, 0.0)) / R if R > 0 else 0.0
                    Wrr += Frr * dsStop
                    Waero += Faero * dsStop
                    Wgrav += Fgrav * dsStop
                    KE = 0.0
                    stalled = True
                    break
            vNew = math.sqrt(2 * KEn / m)
            dt = dsSub / vNew
            legE += Pleg * dt
            t += dt
            Wrr += Frr * dsSub
            Waero += Faero * dsSub
            Wgrav += Fgrav * dsSub
            KE = KEn
            if KE > keCap:
                Wbrake += KE - keCap
                KE = keCap
                braked = 1
            remaining -= dsSub
        v = math.sqrt(2 * KE / m)
        speed[i] = v
        brk[i] = braked
        if v < minV:
            minV = v
        if stalled:
            break
    dist = xs[n - 1] - xs[0]
    dKE = KE - KEinit
    dispE = dKE + Wrr + Waero + Wbrake
    return {
        "legE": legE, "t": t, "Wrr": Wrr, "Waero": Waero, "Wgrav": Wgrav,
        "Wbrake": Wbrake, "speed": speed, "brk": brk, "regime": regime,
        "stalled": stalled, "avgV": dist / t if t > 0 else 0.0, "minV": minV,
        "KEinit": KEinit, "KEfin": KE, "dKE": dKE, "dispE": dispE,
    }


def approximate(prof, p, vf, eps, opts=None):
    """Closed form E = alpha*x + beta*(h+ - eps*h-) with the climb-aero
    correction modes 'off' | 'zero' | 'vc' (JS approximate). Also returns the
    per-edge clamped sum and the decomposition (roll+aero+climb+recov == E)."""
    beta = p["m"] * G / p["keff"]
    mg = p["m"] * G
    w = p["wind"]
    aero_spd = vf + w
    aRoll = mg * p["Crr"] / p["keff"]
    aAero = 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd) / p["keff"]
    mode = (opts or {}).get("climbAeroMode") or "off"
    climbThr = opts["climbThr"] if opts and opts.get("climbThr") is not None else 0.02
    Pc = (opts or {}).get("climbPower") or 0
    xs, hs = prof["x"], prof["h"]
    X = hplus = hminus = aeroSum = clamped = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        slope = dh / dx
        X += dx
        aeroDx = aAero
        if mode != "off" and slope >= climbThr:
            if mode == "zero":
                aeroDx = 0.0
            else:  # 'vc' — aero at the quasi-steady climb speed
                sec = math.sqrt(1 + slope * slope)
                sin = slope / sec
                cos = 1 / sec
                vc = min(vf, p["keff"] * Pc / (p["Crr"] * mg * cos + mg * sin)) if Pc > 0 else 0.0
                aeroDx = 0.5 * p["rho"] * p["CdA"] * (vc + w) * abs(vc + w) / p["keff"]
        segAero = aeroDx * dx
        aeroSum += segAero
        alphaSeg = aRoll * dx + segAero
        if dh >= 0:
            hplus += dh
            clamped += alphaSeg + beta * dh
        else:
            hminus += -dh
            clamped += max(0.0, alphaSeg - eps * beta * (-dh))
    roll = aRoll * X
    aero = aeroSum
    climb = beta * hplus
    recov = -eps * beta * hminus
    return {
        "E": roll + aero + climb + recov, "clamped": clamped,
        "alpha": aRoll + aAero, "beta": beta, "X": X,
        "hplus": hplus, "hminus": hminus,
        "roll": roll, "aero": aero, "climb": climb, "recov": recov,
    }


def v2_edge(prof, p, vf, opts):
    """The closed form as DEPLOYED in Simujaules (JS v2Edge; journal Entries
    18-21): per-edge grade-local eps(s) = clamp01(min(1, (a/b)/s) - eps0),
    flat aero gated OFF climbs, k_s scaling beta only, dead max(0,.) kept
    verbatim with the pre-clamp minimum reported. opts: kSmooth, epsOffset,
    climbThr."""
    mg = p["m"] * G
    w = p["wind"]
    beta = mg * opts["kSmooth"] / p["keff"]
    aRoll = mg * p["Crr"] / p["keff"]
    aero_spd = vf + w
    aAero = 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd) / p["keff"]
    abRatio = (aRoll + aAero) * p["keff"] / mg  # alpha/beta un-smoothed
    xs, hs = prof["x"], prof["h"]
    E = 0.0
    minPreClamp = _INF
    epsW = Hd = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        if not dx > 0:
            continue
        if dh >= 0:
            aero = aAero * dx if dh < opts["climbThr"] * dx else 0.0
            e = aRoll * dx + aero + beta * dh
        else:
            ndh = -dh
            eps = abRatio * dx / ndh
            if eps > 1:
                eps = 1.0
            eps -= opts["epsOffset"]
            if eps < 0:
                eps = 0.0
            e = aRoll * dx + aAero * dx - eps * beta * ndh
            if e < minPreClamp:
                minPreClamp = e
            if e < 0:
                e = 0.0
            epsW += eps * ndh
            Hd += ndh
        E += e
    return {
        "E": E, "minPreClamp": minPreClamp,
        "epsImplied": epsW / Hd if Hd > 0 else float("nan"), "hminus": Hd,
    }


def approx_time(prof, p, vf, pw):
    """Approximate TIME model t = sum ds/v(s) and the effective k+/k-
    multipliers (JS approxTime; notas.md 'effective flat distance')."""
    mg = p["m"] * G
    w = p["wind"]
    vmax = p["vmax"]
    xs, hs = prof["x"], prof["h"]
    t = X = hplus = hminus = tClimb = xClimb = hpC = tDesc = xDesc = hmD = 0.0
    for i in range(1, len(xs)):
        dx = xs[i] - xs[i - 1]
        dh = hs[i] - hs[i - 1]
        slope = dh / dx
        sec = math.sqrt(1 + slope * slope)
        sin = slope / sec
        cos = 1 / sec
        ds = dx * sec
        X += dx
        if dh > 0:
            hplus += dh
        else:
            hminus += -dh
        if slope >= pw["climbThr"]:  # climb: v_c capped at v_f
            v = min(vf, p["keff"] * pw["climb"] / (p["Crr"] * mg * cos + mg * sin)) if pw["climb"] > 0 else 0.05
            tClimb += ds / v
            xClimb += dx
            hpC += dh
        elif slope <= pw["descThr"]:  # descent: equilibrium, capped at v_max
            lo, hi = 0.05, 45.0
            for _ in range(28):
                vv = 0.5 * (lo + hi)
                f = (0.5 * p["rho"] * p["CdA"] * (vv + w) * abs(vv + w)
                     + p["Crr"] * mg * cos + mg * sin - p["keff"] * pw["descent"] / vv)
                if f < 0:
                    lo = vv
                else:
                    hi = vv
            v = min(vmax, max(0.5, 0.5 * (lo + hi)))
            tDesc += ds / v
            xDesc += dx
            hmD += -dh
        else:
            v = vf
        t += ds / max(v, 0.02)
    kPlus = (vf * tClimb - xClimb) / hpC if hpC > 0 else float("nan")
    kMinus = (xDesc - vf * tDesc) / hmD if hmD > 0 else float("nan")
    return {"t": t, "X": X, "hplus": hplus, "hminus": hminus, "kPlus": kPlus, "kMinus": kMinus}


def eps_geom(prof, p, vf):
    """Geometry-only closed-form eps (JS epsGeom; journal Entry 8): coasting
    limit eps(s) = min(1, (a/b)/s), drop-weighted over 30 m descent cells,
    minus the calibrated 0.13 offset. Uses the MODEL v_f — needs no power."""
    mg = p["m"] * G
    beta = mg / p["keff"]
    aero_spd = vf + p["wind"]
    alpha = (p["Crr"] * mg + 0.5 * p["rho"] * p["CdA"] * aero_spd * abs(aero_spd)) / p["keff"]
    ab = alpha / beta
    px, ph = prof["x"], prof["h"]
    x0 = px[0]
    totalM = px[len(px) - 1] - x0
    DX = 30
    nc = math.floor(totalM / DX)
    if nc < 2:
        return float("nan")
    j = 0

    def h_at(d):
        nonlocal j
        while j < len(px) - 2 and px[j + 1] < d:
            j += 1
        seg = px[j + 1] - px[j]
        f = (d - px[j]) / seg if seg > 1e-9 else 0.0
        return ph[j] * (1 - f) + ph[j + 1] * f

    cellH = [h_at(x0 + k * DX) for k in range(nc + 1)]
    Hd = epsW = 0.0
    for k in range(nc):
        dh = cellH[k + 1] - cellH[k]
        if dh < 0:
            drop = -dh
            Hd += drop
            epsW += drop * min(1.0, ab / (drop / DX))
    if Hd < 1:
        return float("nan")
    return max(0.0, min(1.0, epsW / Hd - 0.13))
