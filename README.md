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

## Running BrakeLab

You need **Python 3.11 or 3.12 (64-bit)**. Get the code first — download the ZIP from GitHub and
extract it, or `git clone https://github.com/MarcAlcolea/Brake-Program.git`.

### Windows — the easy way
Double-click **`run.bat`**. The first run creates a local virtual environment and installs
everything (takes a minute); every run after that just launches the GUI.

> If Windows warns about python not being found, install it from
> [python.org](https://www.python.org/downloads/) and **tick "Add python.exe to PATH"** on the first
> screen, then double-click `run.bat` again.

### macOS — the easy way
Double-click **`run.command`** in Finder, or from a terminal in this folder:
```
./run.command
```

### Any platform — from a terminal
```
python -m venv .venv                 # create a virtual environment (once)
# activate it:  Windows -> .venv\Scripts\activate    macOS/Linux -> source .venv/bin/activate
python -m pip install -e .           # install BrakeLab + its dependencies (once)
python -m brakelab                   # launch the GUI
```
Headless / development commands:
```
python -m brakelab.cli configs/2026_baseline.json                    # print results, no GUI
python -m brakelab.cli configs/2026_baseline.json --report out.pdf   # + PDF report
python -m pip install -e ".[dev]"                                    # add the test/dev extras
python -m pytest                                                     # run the test suite
```

> **macOS note:** on the stock CommandLineTools Python a venv's PySide6 can fail to load its Qt
> plugins (*"Could not find the Qt platform plugin cocoa"*). If that happens, use `run.command`
> (it uses the system Python), or install a full Python from [python.org](https://www.python.org)
> and use a venv there.

## Design principles
1. **Correctness first** — physics lives in a pure, fully-tested core validated against
   `docs/calculation_audit.md`; the GUI contains no equations.
2. **One model, many configurations** — the spreadsheet's x1/x2 sheets are just two configs.
3. **Extensible by addition** — new capability = a new `Analysis` subclass, core untouched.
4. **Written for the next student** — explicit units, typed dataclasses, docstrings that cite the
   equation, tests as executable documentation.
