# FSAE Brake Design Tool (BrakeLab)

A maintainable, extensible desktop application for Formula SAE brake system design — the standard
engineering tool for our Controls team, replacing the legacy braking spreadsheet and the hand
calculations for brake-rotor thermal analysis.

## Status — v1 implemented
A verified calculation engine, desktop GUI, save/load, PDF reports, and an extensibility seam with
one working analysis. 20 tests pass. Advanced analyses (optimization, Monte Carlo, telemetry, full
transient thermal) are deferred but their seams are in place.

- [`docs/calculation_audit.md`](docs/calculation_audit.md) — every spreadsheet/thermal calculation
  checked, the bugs found (B1 static-load swap, B2 missing ×2 on the inboard rear, …), and the
  corrected golden values the engine is tested against.
- [`docs/architecture.md`](docs/architecture.md) — layered, OOP, extensible design.
- [`docs/implementation_plan.md`](docs/implementation_plan.md) — v1 scope and build order.

## Layout
```
docs/          engineering audit + architecture + plan
reference/     original spreadsheet & thermal doc (validation source of truth)
configs/       saved vehicle configurations (JSON): 2026_baseline, 2026_inboard
src/brakelab/
  core/        pure calculation engine (models, 5 phases, validation, engine) — no GUI/IO
  analyses/    pluggable studies over (config, engine); SensitivityAnalysis included
  thermal/     rotor thermal analysis (documented stub for later)
  persistence/ versioned JSON save/load
  reporting/   PDF report generation
  app/         PySide6 GUI (controller, panels, plot, main)
tests/         golden-value + property + round-trip tests
```

## Install
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```
python -m brakelab                              # launch the GUI (loads the 2026 baseline)
python -m brakelab.cli configs/2026_baseline.json          # headless: print results
python -m brakelab.cli configs/2026_baseline.json --report out.pdf   # + PDF report
pytest                                          # run the test suite
```

## Design principles
1. **Correctness first** — physics lives in a pure, fully-tested core validated against
   `docs/calculation_audit.md`; the GUI contains no equations.
2. **One model, many configurations** — the spreadsheet's x1/x2 sheets are just two configs.
3. **Extensible by addition** — new capability = a new `Analysis` subclass, core untouched.
4. **Written for the next student** — explicit units, typed dataclasses, docstrings that cite the
   equation, tests as executable documentation.
