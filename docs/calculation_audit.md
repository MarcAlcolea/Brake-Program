# Calculation Audit — Braking Calculations Spreadsheet

**Audited:** 2026-07-03
**Source:** `reference/Braking Calculations.xlsx` (sheets: *x2 Outboarded*, *x1 Inboarded*, *Rice*)
and `reference/Brake Rotors Simulations 2026.docx` (thermal / ANSYS input calcs).

This document records every engineering calculation in the source material, whether it is
correct, and the issues found. It is the reference against which the Python engine's outputs
will be validated ("golden values"). **No number from the spreadsheet is trusted until it
appears here with a verdict.**

Legend: ✅ correct · ⚠️ correct but assumption/label issue · ❌ error that changes outputs.

---

## Sheet structure

The workbook models the same physics twice as two *design variants*, plus one stub:

| Sheet | Rear setup | Notes |
|---|---|---|
| **x2 Outboarded** | 2 rear rotors/calipers (`N_r = 2`) | Most complete. |
| **x1 Inboarded** | 1 rear rotor/caliper on the diff (`N_r = 1`) | Contains an extra error (see B2). |
| **Rice** | — | Incomplete template: missing CG height, wheelbase, axle distances → `#DIV/0!`. Not authoritative. |

**Architectural takeaway:** these are not two different physics models — they are one model
with `N_f`, `N_r`, and *inboard/outboard* as **configuration**. The Python tool will represent
both (and any future layout) as a single parameterised engine, eliminating the duplicated
sheets and the drift between them.

---

## Phase 1 — Vehicle dynamics & load transfer

| Qty | Formula in sheet | Verdict |
|---|---|---|
| Weight `W = M·g` | `320·9.81 = 3139.2 N` | ✅ |
| Weight transfer `ΔW = W·a·h/L` | `3139.2·1.5·0.3556/1.625 = 1030.4 N` | ✅ (a is in g, so W·a_g = M·a) |
| `b` = front-axle→CG | `0.52·L = 0.845 m` | ⚠️ label vs use — see ❌ B1 |
| `c` = rear-axle→CG | `0.48·L = 0.780 m` | ⚠️ |
| Static front axle load | `W·(b/L) = 1632.4 N` | ❌ **B1** |
| Static rear axle load | `W·(c/L) = 1506.8 N` | ❌ **B1** |
| Dynamic front `= static_f + ΔW` | `2662.8 N` | ✅ formula (input tainted by B1) |
| Dynamic rear `= static_r − ΔW` | `476.4 N` | ✅ formula (input tainted by B1) |

### ❌ B1 — Static axle loads are inconsistent with the stated CG location (CRITICAL)

Front-axle static load is determined by the moment about the **rear** contact patch, so it must
scale with the distance from the CG to the **rear** axle:

```
static_front = W · c/L      (c = rear-axle→CG distance)
static_rear  = W · b/L      (b = front-axle→CG distance)
```

The sheet does the opposite — it multiplies the front load by `b/L` (the *front*-axle→CG
distance). With `b = 0.52·L` labelled "distance from front axle to CG," the CG sits **rearward**
of mid-wheelbase, so the **rear** axle should carry 52% and the front 48%. The sheet instead
puts 52% on the front. **Front and rear static loads are swapped relative to the stated geometry.**

Effect (propagates through torque → clamp force → pressure → pedal force):

| | Sheet | Physically correct (for the stated b/c) |
|---|---|---|
| Static front | 1632.4 N | 1506.8 N |
| Static rear | 1506.8 N | 1632.4 N |
| Dynamic front | 2662.8 N | 2537.2 N |
| Dynamic rear | 476.4 N | 602.0 N |

This is the single most important finding. **Action:** confirm the intended front/rear weight
distribution with the suspension team (the comment cites "Woods, doc 2. Vehicle Parameters").
Two self-consistent fixes exist — either (a) keep `b = 0.52·L` and swap the load formulas, or
(b) keep the load formulas and set `b = 0.48·L`. The result differs, so intent must be
confirmed, not guessed. The engine will take **front weight fraction** as a single validated
input and derive `b`, `c`, and both axle loads from it consistently, making this class of error
impossible.

> **Decision (2026-07-03):** default `front_weight_fraction = 0.52` (front-biased 52F/48R,
> option b). This reproduces the spreadsheet's current output numbers, so golden-value tests can
> be checked against the existing sheet, while the single-input design removes the
> label/formula disagreement. **Still to confirm with suspension** — if the true bias is
> rearward, only this one input changes and everything re-derives correctly.

---

## Phase 2 — Tire & torque requirements

| Qty | Formula | Verdict |
|---|---|---|
| Max friction force / wheel `= (W_axle,dyn/2)·μ_tire` | front `1997.1 N`, rear `357.3 N` | ✅ |
| Required torque / caliper `= F_wheel·R_tire·(2/N)` | front `447.4 N·m` | ✅ |
| Rear torque, x2 (`N_r=2`) | `80.0 N·m` | ✅ |
| Rear torque, x1 (`N_r=1`) | `160.1 N·m` | ✅ (single inboard rotor carries both wheels' torque) |

The `(2/N)` factor correctly distributes total axle braking torque (2 wheels) over `N` calipers.

### ⚠️ B7 — Inboard rear brake and final-drive ratio
The x1 rear torque assumes the inboard rotor sees the **full wheel torque**. That is only true if
the rotor is downstream of the final drive (mounted so it turns at wheel speed). If it is mounted
on the driveshaft/diff **before** the chain reduction, the required brake torque scales by the
final-drive ratio. Confirm rotor mounting location; the engine will expose an optional
`driveline_ratio` for inboard brakes (default 1.0).

---

## Phase 3 — Caliper & rotor sizing

Effective brake torque of one rotor is `T = F_clamp · (2·μ_pad) · R_eff` — the factor **2**
accounts for the two friction faces (pad on each side). Inverting: `F_clamp = T/(2·μ_pad·R_eff)`.

| Qty | Formula | Verdict |
|---|---|---|
| Front clamp `= T_f/(2·μ_pad·R_eff)` | `5265.5 N` | ✅ |
| Front line pressure `= F_clamp/A_cal` | `6.635 MPa` | ✅ (N/mm² = MPa) |
| Rear clamp **x2** `= T_r/(2·μ_pad·R_eff)` | `942.0 N` | ✅ |
| Rear clamp **x1** `= T_r/(μ_pad·R_eff)` | `3768.0 N` | ❌ **B2** |

### ❌ B2 — x1 (inboarded) rear clamp force is missing the factor of 2 (SIGNIFICANT)

The x1 sheet uses `=T_r/(μ_pad·R_eff)` — **no factor of 2** — whereas the front (same sheet) and
the x2 rear both include it. A single rotor always has two friction faces, so the 2 belongs here
too. As written, the x1 sheet **doubles** the required rear clamp force and therefore the rear
line pressure, MC force, and balance-bar demand:

| x1 rear | Sheet | Corrected |
|---|---|---|
| Clamp force | 3768.0 N | 1884.0 N |
| Line pressure | 4.748 MPa | 2.374 MPa |

This made the x1 rear look far more demanding than it is (and contributed to the "requirements
not met" result on that sheet). A single `caliper.clamp_from_torque()` method used everywhere
removes the possibility of this drift.

---

## Phase 4 — Master cylinder & pedal box

| Qty | Formula | Verdict |
|---|---|---|
| MC bore mm `= in·25.4` | ✅ | (values stored as **text** `'0.625'`; parse on import) |
| MC area `= π(d/2)²` | ✅ | |
| MC force req `= P_line·A_mc` | front `1313.3 N` | ✅ (MPa·mm² = N) |
| Force into balance bar `= F_mc/Bias` | front `2020.5 N` | ✅ |
| Pedal force `= F_driver·PR` | `2400 N` | ✅ |
| Requirement check `F_pedal > F_bar` | ✅ logic | ⚠️ **B6, B9** |

### ⚠️ B6 — Balance-bias inputs not constrained
`B_f` and `B_r` are entered as two independent cells (0.65 / 0.35, or 0.64 / 0.36 on x1) with no
check that they sum to 1, and no enforcement of the hardware limit (≈65:35 max). The engine will
store **one** bias value and derive the complement; the validator will flag out-of-range bias.

### ⚠️ B9 — Pass/fail uses strict inequality, no safety margin
Checks are `F_pedal > F_bar` with no design margin. Also worth surfacing: with front demand
(2020 N) far above rear (671 N), the *ideal* bias to balance both would be ≈85:15 front — beyond
the 65:35 hardware limit — so the **front is the binding constraint**. The tool should compute
and display optimal-vs-achievable bias and a configurable safety factor.

### Note — "target deceleration 1.5 g with μ_tire = 1.5"
This is the theoretical maximum (all four tires simultaneously at the friction limit). It is a
valid *sizing target* but the tool should let `a` be swept and show it against the μ-limited
envelope.

---

## Pedal travel

| Qty | Formula | Verdict |
|---|---|---|
| Caliper piston total area `= N_cal·N_piston·A_piston` | ✅ | |
| Fluid volume `= area·piston_travel` | ✅ | |
| MC stroke `= V/A_mc` | ✅ | |
| Effective stroke `= (stroke_f+stroke_r)/2` | ✅ | |
| Stroke + compliance, ×PR → pedal travel | ✅ | ⚠️ **B3, B4, B5** |

### ⚠️ B3 — Piston-travel is an input, not a hidden constant
Pad clearance take-up (`piston_travel`) is **0.15 mm** on x2 and **1.2 mm** on x1. This single
number dominates pedal travel (x2 → 29.4 mm, x1 → 74.7 mm). **Confirmed by Marc (2026-07-03):
0.15 mm is correct.** The engine exposes it as a per-caliper input so the sensitivity is visible
rather than buried; the two sheets simply used different values for their two setups.

### ⚠️ B4 — Caliper piston area used with two different values
Phase 3 uses `A_cal = 793.55 mm²`; pedal-travel uses `A_piston = 792 mm²`. Small, but there
should be **one** source of truth per component. The engine will define a `Caliper` object; both
calculations read its area.

### ⚠️ B5 — BOTS trigger point is dimensionally muddled
`BOTS = (MC stroke incl. compliance) + 3.5 mm` mixes references — pedal travel elsewhere is at
the *pedal* (×PR), but this adds 3.5 mm to an *MC-stroke* quantity. Clarify whether BOTS travel
is specified at the pedal or the master cylinder and keep units consistent.

---

## Thermal calculations (from the ANSYS doc)

Used to generate ANSYS transient-thermal inputs (heat flux + film-coefficient tables). Reviewed
for the tool's future thermal module.

| Qty | Formula | Verdict |
|---|---|---|
| Braking energy `E = ½m(v_i²−v_f²)` | `½·320·(28²−10²) = 109,440 J` | ✅ (writeup has a cosmetic `²` typo; value right) |
| Power `P = E/t` | `36,480 W` | ✅ |
| Per-rotor power `= P·Bias/2` | front `11,856 W`, rear `6,384 W` | ⚠️ **T1, T2** |
| Peak heat flux `= P_rotor/A_swept` | front `505,905`, rear `272,411 W/m²` | ✅ |
| Film coeff `h = 10 + 3v` | 94 → 40 → 94 W/m²·K | ⚠️ **T3** (crude flat-plate estimate, acknowledged) |

- **⚠️ T1 — heat split by hydraulic bias.** Energy into each axle is proportional to actual
  *braking force* at that axle, not the balance-bar setting. 65/35 is a reasonable first-order
  proxy only if the tires aren't locked and MC areas are equal; the *dynamic* front share is
  higher (≈84% at 1.5 g per the ideal-bias calc), so the front rotor may run hotter than 65%
  implies. The thermal module should let heat split follow the dynamics result, not just bias.
- **⚠️ T2 — "divide by 2" assumes 2 rear rotors.** The doc's rear flux assumes the **outboarded**
  (2 rear rotor) layout. If the car uses the **inboarded single** rear rotor, that rotor absorbs
  the *entire* rear energy — rear heat flux ~**doubles**. This must be coupled to the same
  `N_r` used in the mechanical model (another argument for one shared config).
- **⚠️ T3 — 100% of energy into the rotor.** Transient calc puts all energy into the rotor;
  the steady-state note used a ×0.5 partition. Real rotor/pad split is ~85–90% to the rotor.
  Make the partition an explicit parameter.
- Minor doc transcription slips (superseded "OLD" section): clamp `5625` vs correct `5265`;
  rear stress compared to 1018 yield under a "4130" heading. Cosmetic; not in current calcs.

**Material data captured for the thermal module** (from the doc's tables): 1018 and 4130
density, conductivity (incl. temperature dependence), specific heat, emissivity, E, ν, yield,
CTE. These will seed a `materials` library.

---

## Summary of defects to fix in the Python engine

| ID | Severity | Where | Fix in engine |
|---|---|---|---|
| **B1** | Critical | Static axle loads swapped vs CG location | Single validated front-weight-fraction input; derive loads consistently. Confirm intent w/ suspension. |
| **B2** | Significant | x1 rear clamp missing ×2 | One `clamp_from_torque()` used everywhere. |
| **B3** | Moderate | piston-travel 0.15 vs 1.2 mm | Expose as parameter; flag typo; default sane value. |
| **B4** | Low | piston area 793.55 vs 792 | Single `Caliper` object. |
| **B5** | Low | BOTS units | Define at pedal *or* MC explicitly. |
| **B6** | Low | bias not constrained | Store one bias; validator enforces sum & max. |
| **B7** | Verify | inboard driveline ratio | Optional `driveline_ratio` (default 1.0). |
| **B9** | Low | strict check, no margin | Configurable safety factor; optimal-vs-achievable bias. |
| **T1–T3** | Thermal | heat split / rotor count / partition | Parameterise; couple to shared config. |

Once the engine is implemented, `tests/` will assert its outputs equal the **corrected** values
in this table (not the raw spreadsheet cells), with each corrected value traceable to a row here.
