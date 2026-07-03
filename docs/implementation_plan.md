# Implementation Plan — v1 (single-shot, simple but complete)

**Goal:** a working, verified desktop brake-design tool. Simple, correct, extensible. Advanced
analyses (optimization, Monte Carlo, telemetry, full transient thermal) are deferred but the
seams are in place.

## Scope of v1
- **Verified core engine** — the five spreadsheet phases as pure, tested Python, with the audit
  fixes (B1 single weight fraction, B2 factor-of-2 everywhere, B4 one caliper area).
- **Golden-value tests** — engine output vs the corrected spreadsheet numbers.
- **Save/Load** — `VehicleConfig` ⇄ versioned JSON.
- **PDF report** — inputs, results, pass/fail.
- **PySide6 GUI** — categorized input panels, live recompute, a plot, inline validation.
- **Extensibility seam** — `Analysis` ABC + one working `SensitivityAnalysis`.
- **Deferred stubs** — `thermal/` documented for later; optimization / Monte Carlo / telemetry
  slot in as future `Analysis` subclasses (no core change).

## Simplifying decisions (v1)
- **Shared corner spec:** one `Rotor`, `Pad`, `Caliper` used by both axles (as the spreadsheet
  does); per-axle count/inboard/MC-bore differ. Splitting into independent front/rear corners is
  a later, additive change.
- **SI internally**, convert at the boundary; lightweight `units.py` (no `pint` yet).
- **Caliper area unified** to a single `piston_area` (B4); `one_side_area` and `displacing_area`
  derive from it. Line pressure matches the sheet exactly; pedal travel differs by ~0.1% from the
  sheet because the sheet used a second, slightly different area there — this deviation *is* the
  B4 fix and is asserted as such.
- **Compliance always applied** before pedal-travel × pedal-ratio (x2 sheet did this; x1 omitted
  it — the engine is consistent).

## Build order (each a modular commit)
1. `core/units.py`, `core/models.py`, `core/results.py` — schema.
2. `core/dynamics/tires/brakes/hydraulics/pedal_travel.py` + `core/validation.py` + `core/engine.py`.
3. `tests/` — golden + property tests; **gate before UI**.
4. `persistence/config_io.py` + `configs/2026_baseline.json` + `configs/2026_inboard.json`.
5. `reporting/pdf_report.py`.
6. `analyses/base.py` + `analyses/sensitivity.py`; `thermal/base.py` stub.
7. `app/` PySide6 GUI (controller, panels, plot, main) + `__main__` CLI.

## Verification
`pytest` green on golden values (x2 outboarded matches sheet; x1 inboard matches **corrected**
values), plus property invariants (axle loads sum to weight, bias sums to 1). A headless CLI
prints a full result set for eyeball comparison against the audit table.
