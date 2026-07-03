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

## Run (the easy way)
Double-click **`run.command`** in Finder, or from a terminal in this folder:
```
./run.command
```
That launches the GUI with the 2026 baseline loaded. No setup, no virtualenv to activate.

## Run (terminal)
```
python3 -m brakelab                                     # launch the GUI
python3 -m brakelab.cli configs/2026_baseline.json      # headless: print results
python3 -m brakelab.cli configs/2026_baseline.json --report out.pdf   # + PDF report
python3 -m pytest                                       # run the test suite
```
Use `python3` (this machine has no `python`/`pip` on the PATH — use `python3 -m pip`).

## Setup on a new machine
Dependencies (installed once, into the system Python's user site):
```
python3 -m pip install -r requirements.txt
```
The code under `src/` is put on the import path by a `brakelab.pth` file in the user site-packages
(so `python3 -m brakelab` works from anywhere), and `run.command` also sets `PYTHONPATH` itself.

> **macOS note:** a `python -m venv` virtualenv is normally preferred, but on the stock
> CommandLineTools Python the venv's PySide6 can fail to load its Qt plugins
> (*"Could not find the Qt platform plugin cocoa"*). If that happens, use the system Python +
> `run.command` as above. Installing a full Python from python.org and using a venv there also
> resolves it.

## Design principles
1. **Correctness first** — physics lives in a pure, fully-tested core validated against
   `docs/calculation_audit.md`; the GUI contains no equations.
2. **One model, many configurations** — the spreadsheet's x1/x2 sheets are just two configs.
3. **Extensible by addition** — new capability = a new `Analysis` subclass, core untouched.
4. **Written for the next student** — explicit units, typed dataclasses, docstrings that cite the
   equation, tests as executable documentation.
