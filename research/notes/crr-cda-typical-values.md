# Typical Crr and CdA values for a cycling energy model

A literature survey to put **priors** on the two parameters the energy model is most
sensitive to — rolling-resistance coefficient `C_rr` and drag area `CdA` — and to sanity-
check the values used in `longoes.xlsx` against published data. Written for the
Pedal Hidrográfico [bicycling-energy-model](../../applet/index.html); see also
[MODEL_COMPARISON_JOURNAL.md](MODEL_COMPARISON_JOURNAL.md).

> **Why this matters for *both* models.** `C_rr` and `CdA` enter the closed-form
> `α = (C_rr·mg + ½ρCdA·(v_f+wind)²)/k_eff` directly — but they also drive the
> **canonical** simulation, because they set the speed, hence the time in each regime,
> hence `legE = ∫P·dt`. Wrong `C_rr`/`CdA` bias canonical too. The good news: the rides
> let us *check* them (see [§3](#3-applying-to-the-energy-model)).

**Confidence legend:** ●●● well-established / multi-source · ●●○ reasonable / some
spread · ●○○ estimated or thin literature (treat as a starting point).

---

## TL;DR — recommended values

**Rolling resistance `C_rr`** (effective, *on the actual surface* — not the smooth-drum
lab number, which is lower):

| Surface | tyre | effective `C_rr` | conf. |
|---|---|--:|:--:|
| Smooth new asphalt | fast 25–30 mm tubeless | 0.004–0.006 | ●●● |
| Typical / aged asphalt | road 25–32 mm | 0.006–0.008 | ●●○ |
| Rough chip-seal / broken tarmac | road 28–32 mm | 0.008–0.012 | ●●○ |
| Smooth hardpack / Cat-1 gravel | gravel 38–45 mm | 0.010–0.018 | ●●○ |
| Typical gravel / dirt road | gravel 40–50 mm or 26×2.0–2.2″ | 0.015–0.025 | ●○○ |
| Rough / loose gravel, washboard | wide MTB 2.0–2.2″ | 0.025–0.045 | ●○○ |
| Sand / mud (extreme) | any | 0.04–0.10+ | ●○○ |

**Drag area `CdA`** for the target rider (**1.63 m, 55–60 kg, drop bars**), scaled down
from average-rider references by body size (≈ ×0.80, [§2.1](#21-fundamentals-and-body-size-scaling)):

| Position | avg-rider `CdA` | **1.63 m/57 kg rider** | conf. |
|---|--:|--:|:--:|
| Upright / on the tops, loaded | 0.38–0.42 | **0.31–0.35** | ●●○ |
| Hoods, relaxed (typical touring/gravel) | 0.36–0.38 | **0.29–0.33** | ●●○ |
| Drops, road | 0.30–0.35 | **0.25–0.29** | ●●○ |
| Aggressive drops (racing fit) | 0.26–0.30 | **0.21–0.25** | ●○○ |

---

## 1. Rolling resistance `C_rr`

### 1.1 How `C_rr` is measured, and why "drum ≠ road"

The reference dataset is [bicyclerollingresistance.com](https://www.bicyclerollingresistance.com/),
which rolls a single tyre on a **smooth steel drum** at 28.8 km/h under a 42.5 kg load
([test method](https://www.bicyclerollingresistance.com/the-test)). That isolates the
tyre's **internal casing hysteresis** — but a smooth drum hides what happens on real
ground. On rough surfaces a second loss appears: **impedance** (a.k.a. "suspension" or
"transmitted" losses), the energy lost shaking the bike+rider when the tyre can't absorb
the surface ([SILCA Part 4B](https://silca.cc/blogs/silca/part-4b-rolling-resistance-and-impedance)).

Tom Anhalt's **breakpoint pressure** is the pressure above which impedance overtakes
casing loss; *"the rougher the surface and the smaller the tyre, the lower that breakpoint."*
SILCA report being **10 psi over** the breakpoint costs ~9 W on new asphalt while 10 psi
under costs only ~1 W — i.e. the penalty is asymmetric, favouring *lower* pressure
([SILCA Part 4B](https://silca.cc/blogs/silca/part-4b-rolling-resistance-and-impedance)).
This is why on gravel a **wider, lower-pressure tyre has a lower *effective* `C_rr`** than
a narrow hard one, even though the narrow one "wins" on the drum. Field testing with the
Chung/virtual-elevation method confirms *"some fast tyres on drum testing remain fast off
road and some less so"* — drum `C_rr` does not rank tyres correctly on rough ground
([J. Karrasch](https://www.johnkarrasch.com/articles/91r4i2zatv4c86444ubl0hw4wx02l0)). ●●●

**Take-away for the model:** the model's `C_rr` is an **effective, on-surface** value, so
use the field ranges in the TL;DR — not the lab drum numbers, which are ~30–50% lower.

### 1.2 Paved — concrete drum numbers (lower bound)

Measured single-tyre drum `C_rr` at 29 km/h
([Best Bike Split](https://www.bestbikesplit.com/blog/rolling-resistance-cycling-triathlon),
[bicyclerollingresistance.com](https://www.bicyclerollingresistance.com/road-bike-reviews)):

| Tyre | drum `C_rr` | note |
|---|--:|---|
| Vittoria Corsa Pro Speed TLR | 0.0022 | fastest tested, race tubeless |
| Continental GP5000 TT TR | 0.0026 | TT tubeless |
| Continental GP5000 S TR (28) | 0.0031 | benchmark all-round tubeless |
| GP5000 clincher + latex | ~0.0040 | clincher |
| Continental Gatorskin | ~0.0060 | durable training tyre |

General drum ranges: **tubeless 0.002–0.004**, **clincher 0.004–0.006**,
**training/touring 0.005–0.007**. ●●● Tube choice moves this 3–7 W/pair (latex/TPU
faster than butyl); 25–28 mm is the rolling-resistance sweet spot at matched pressure.
Adding real-road surface impedance lifts the **effective** value to the 0.004–0.012 band
in the TL;DR depending on roughness. ●●○

### 1.3 Unpaved

Drum tests barely exist for true off-road and under-read field behaviour, so off-road
`C_rr` is reported as **effective** values. A commonly cited jump is from **~0.010 on
smooth asphalt to ~0.050 on unpaved roads**
([Zwift Insider / model summaries](https://zwiftinsider.com/crr/)). Energy-model practice
adds **+0.004 to tarmac for ordinary dirt/gravel**, rising to **+~0.028 for thick sand**
(i.e. ~0.006 → ~0.03 absolute on top of a ~0.005 tarmac base) — see the modelling note in
[arXiv:2005.04229](https://arxiv.org/pdf/2005.04229) and related route-energy models. ●○○

Practical synthesis (effective, typical pressures):

- **Smooth hardpack / well-packed Cat-1 gravel:** 0.010–0.018 — a good gravel tyre here is
  only modestly worse than a road tyre on rough tarmac.
- **Typical loose-over-hard gravel / dirt road:** 0.015–0.025.
- **Rough, loose, washboard:** 0.025–0.045; wide low-pressure tyres pull toward the low
  end via the impedance mechanism above.
- A **26×2.0–2.2″ MTB tyre** at gravel pressures sits in the same 0.015–0.030 band on
  rough ground — its width/volume *helps* off-road (lower impedance) even if its tread and
  weight cost a few watts on smooth surfaces. ●○○

---

## 2. Drag area `CdA`

### 2.1 Fundamentals and body-size scaling

`CdA = C_d · A`. `C_d` (~0.7–1.0 for a cyclist) is roughly position-shape-driven; `A` is
the **projected frontal area**, which scales with body size — so a small rider is
intrinsically lower-drag. The peer-reviewed scaling (Heil, *Eur J Appl Physiol* 2001/2002,
[mass-only](https://link.springer.com/article/10.1007/s004210100424) /
[with posture](https://link.springer.com/article/10.1007/s00421-002-0662-9)):

> `A_p ∝ m_b^0.762` (mass-only, r²≈0.73), or with height
> `A_p = 0.00653·STA^0.183·TA^0.099·m^0.493·h^1.163 + 0.066` (r²≈0.56),
> from a cohort of mean **74.4 kg, 1.82 m**.

Scaling that cohort (~74 kg / 1.82 m) down to the **target 57 kg / 1.63 m**:

- mass-only: `(57/74)^0.762 ≈ 0.81`
- mass+height: `(57/74)^0.49·(1.63/1.82)^1.16 ≈ 0.78`

→ **≈ ×0.78–0.82**: the target rider's `CdA` is ~20% below a same-position average male.
●●○ (The constant `+0.066` term means very small riders scale slightly *less* than the
pure power law — treat ×0.80 as a round figure, not three-digit precision.)

### 2.2 `CdA` by position (reference rider)

Converging numbers from wind-tunnel-backed summaries
([Ride Far](https://ridefar.info/bike/cycling-speed/air-resistance-cyclist/),
[Best Bike Split](https://www.bestbikesplit.com/blog/cda-aerodynamic-drag-coefficient-cycling),
[Martin et al. 1998](https://journals.humankinetics.com/view/journals/jab/14/3/article-p276.xml)):

| Position | `CdA` (m²) | source |
|---|--:|---|
| Loaded bikepacker, flat | 0.40 (0.37 desc / 0.43 climb) | Ride Far |
| Upright / tops | 0.35–0.40 | Best Bike Split |
| Hoods (pro baseline) | ~0.32–0.37 | wind-tunnel / Ride Far |
| Drops, road | 0.30–0.35 | Best Bike Split |
| **Optimised racing drops (Martin 1998)** | **0.269 ± 0.006** | 6 riders, 1.77 m / 71.9 kg |
| Age-group TT (aero bars) | 0.25–0.30 | Best Bike Split |
| Elite TT (skinsuit, aero helmet) | 0.20–0.22 | Best Bike Split |

Relative deltas are consistent and useful: **tops→hoods ≈ −0.03**, **hoods→drops ≈ −0.02**,
**drops→aerobars ≈ −0.03**; tight vs loose clothing ≈ −0.02
([Ride Far](https://ridefar.info/bike/cycling-speed/air-resistance-cyclist/)). ●●○

### 2.3 Scaled for the 1.63 m / 57 kg rider, drop bars

Applying ×0.80 to §2.2 gives the TL;DR table — repeated here with reasoning:

| Position | est. `CdA` | basis |
|---|--:|---|
| Upright / tops, with bags | 0.31–0.35 | 0.40 × ~0.82 |
| **Hoods (likely default)** | **0.29–0.33** | 0.37 × ~0.80 |
| Drops, road | 0.25–0.29 | 0.32 × ~0.80 |
| Aggressive drops | 0.21–0.25 | Martin 0.269 × ~0.82 |

**Uncertainty:** ●○○ for the absolute numbers. Body-size scaling is solid, but individual
`CdA` varies ±0.02–0.03 with flexibility, hip angle, head position and how upright the
rider actually sits — *"two riders of similar height/weight can have wildly different CdA"*
([Best Bike Split](https://www.bestbikesplit.com/blog/cda-aerodynamic-drag-coefficient-cycling)).
There is essentially no wind-tunnel literature specific to 1.6 m riders; these are scaled
estimates, not measurements.

### 2.4 The two bikes — 28c road vs 90s 26×2.2″ MTB → gravel

**Position dominates; tyres are a rounding error.** Aero is ~80% rider, so the frame/tyre
choice matters far less than how the rider sits.

- **28c road bike, drop bars:** a normal road riding position → use §2.3 by where the
  hands are (hoods ~0.29–0.33, drops ~0.25–0.29). The 28 mm tyre adds negligible frontal
  area.
- **1990s 26″ MTB (2.2″ tyres) converted to gravel, drop bars:** the *bike* barely changes
  `CdA` — a 2.2″ (~56 mm) tyre vs 28 mm adds only ~0.003–0.006 m² of frontal area (a couple
  of cm of width, low to the ground). What *does* change it is **posture**: older MTB
  geometry (slacker, shorter reach, taller front via a converted cockpit) tends to sit the
  rider **more upright**, nudging toward the upper end (hoods/upright ~0.31–0.35). So model
  the gravel-MTB **+0.01–0.03 higher** than the road bike *if* it puts the rider more
  upright — driven by position, not the wheels. ●○○ (No direct data for this specific
  conversion; reasoned from the position-dominance result and frontal-area arithmetic.)
  Its real penalty vs the road bike is **off-road `C_rr`**, not aero.

---

## 3. Applying to the energy model

**Comparison with `longoes.xlsx`.** The sheet uses (per ride) roughly:

| param | sheet values | this report's range | verdict |
|---|---|---|---|
| road `C_rr` | 0.004–0.007 | 0.004–0.012 (effective) | **plausible**, low–mid of range |
| offroad `C_rr` | 0.010–0.032 | 0.010–0.045 | **plausible**, spans the band |
| `CdA` | 0.36–0.40 | 0.29–0.35 (hoods, this rider) | **likely a touch high** for a 1.63 m rider unless quite upright/loaded |

**The `CdA` tension (and how the rides adjudicate it).** Literature says ~0.30–0.34 on the
hoods for this rider, vs the sheet's 0.36–0.40 — suggesting the sheet `CdA` is slightly
high. *But* the model's behaviour pointed the other way: in
[Entry 4](MODEL_COMPARISON_JOURNAL.md) the simulated flat speed (23.4 km/h) ran
~6% **above** the measured flat speed (22.1), which means total flat resistance is slightly
**under**-estimated — the opposite of "CdA too high." The most likely reconciliation is
that the *extracted* flat power (0.94× the rider's average) is **too high** (it includes
surges), inflating `v_f`; the `CdA`/`C_rr` themselves look roughly right, just not
separable from `P_flat` on a single flat-speed equation.

**Recommended next step — calibrate from the rides, don't just adopt literature.** Because
`C_rr` and `CdA` separate by their speed dependence (rolling ∝ v, aero ∝ v³ in power), a
clean calibration is: take many near-steady segments across a range of speeds and fit
`k_eff·P = (C_rr·mg)·v + (½ρCdA)·v³` for `(C_rr, CdA)` per bike. The dataset already has
the power+speed+grade streams to do this. Literature ranges here are the **prior / sanity
band**; the rides are the **measurement**. This is the rigorous answer to "if Crr/CdA are
wrong, canonical is wrong too" — calibrate them against measured speed, then the canonical
speed→time→`legE` chain is anchored to data rather than assumed.

**Practical starting values** (this rider, until a per-bike fit is run):

- Road bike on tarmac: `C_rr` 0.005–0.006, `CdA` ~0.31 (hoods) / ~0.27 (drops).
- Gravel-MTB on gravel: `C_rr` 0.018–0.028 (surface-dependent), `CdA` ~0.33 (more upright).
- `ρ` already per-ride from the sheet; keep `k_eff` ~0.97–0.98.

---

## Sources

- [bicyclerollingresistance.com](https://www.bicyclerollingresistance.com/) — drum `C_rr`
  database & [method](https://www.bicyclerollingresistance.com/the-test),
  [road](https://www.bicyclerollingresistance.com/road-bike-reviews) /
  [CX-gravel](https://www.bicyclerollingresistance.com/cx-gravel-reviews) reviews.
- [SILCA — Tyre Pressure Part 4B: Rolling Resistance and Impedance](https://silca.cc/blogs/silca/part-4b-rolling-resistance-and-impedance) — breakpoint pressure, impedance/suspension losses.
- [Best Bike Split — Rolling resistance](https://www.bestbikesplit.com/blog/rolling-resistance-cycling-triathlon) & [CdA explained](https://www.bestbikesplit.com/blog/cda-aerodynamic-drag-coefficient-cycling) — concrete `C_rr` and `CdA` ranges.
- [Ride Far — Air resistance of the cyclist](https://ridefar.info/bike/cycling-speed/air-resistance-cyclist/) — `CdA` by position, relative deltas, bikepacker values.
- [Martin et al. 1998, *J Appl Biomech* 14(3):276–291](https://journals.humankinetics.com/view/journals/jab/14/3/article-p276.xml) — validated power model, wind-tunnel `CdA` 0.269 (1.77 m / 71.9 kg).
- [Heil 2001](https://link.springer.com/article/10.1007/s004210100424) & [Heil 2002](https://link.springer.com/article/10.1007/s00421-002-0662-9) — frontal-area body-mass scaling (`A_p ∝ m^0.76`).
- [J. Karrasch — gravel/MTB tyre field testing](https://www.johnkarrasch.com/articles/91r4i2zatv4c86444ubl0hw4wx02l0) — drum vs field `C_rr`, surface categories.
- [arXiv:2005.04229 — modelling power-meter measurements](https://arxiv.org/pdf/2005.04229); [Zwift Insider — Crr](https://zwiftinsider.com/crr/) — surface `C_rr` adjustments.

*Caveats: road-tyre drum `C_rr` is high-confidence; effective on-surface and especially
off-road `C_rr` are ranges, not points, and depend strongly on pressure/surface. The
small-rider `CdA` figures are body-size-scaled estimates — no wind-tunnel data exists for
1.6 m riders, and the 90s-MTB→gravel `CdA` is reasoned, not measured.*
