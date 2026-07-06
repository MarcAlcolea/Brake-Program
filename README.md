# FSAE Brake Design Tool (BrakeLab)

A maintainable, extensible desktop application for Formula SAE brake system design — the standard
engineering tool for our Controls team, replacing the legacy braking spreadsheet and the hand
calculations for brake-rotor thermal analysis.

## Status
A verified calculation engine, desktop GUI (design, forward simulation, thermal, optimization,
comparison, sensitivity, PDF reports), save/load presets, a component catalog, and a transient
rotor-temperature simulation with ANSYS-ready CSV export. Distributed as standalone Windows/macOS
apps built by CI. Remaining seams: Monte Carlo, telemetry comparison.

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
packaging/     PyInstaller spec + icons for the standalone apps
.github/       CI — tests on every push; app builds + Release on version tags
```

## Running BrakeLab — just download the app

**No Python, no terminal, no setup.** Go to this repo's
**[Releases page](https://github.com/MarcAlcolea/Brake-Program/releases/latest)** and download the
zip for your machine:

| You have | Download | Then |
|---|---|---|
| Windows | `BrakeLab-Windows.zip` | Extract, open the `BrakeLab` folder, double-click **`BrakeLab.exe`** |
| Mac (Apple Silicon, 2020+) | `BrakeLab-macOS-AppleSilicon.zip` | Double-click the zip, then right-click **`BrakeLab.app` → Open** |

First launch only, because the app isn't code-signed with a paid certificate:
- **Windows** may show *"Windows protected your PC"* — click **More info → Run anyway**.
- **macOS** may block the app — right-click → **Open**, or allow it under
  **System Settings → Privacy & Security → Open Anyway**.

After that it opens like any normal application. Saved setups live in your user account
(not in the app folder), so replacing the app with a newer version keeps your configurations.

### Running from source (developers)

With **Python 3.9+** and the repo cloned: `run.bat` (Windows) or `run.command` (macOS)
double-click launchers work, or from a terminal:
```
python -m venv .venv                 # create a virtual environment (once)
# activate it:  Windows -> .venv\Scripts\activate    macOS/Linux -> source .venv/bin/activate
python -m pip install -e ".[dev]"    # install BrakeLab + dev extras (once)
python -m brakelab                   # launch the GUI
```
Headless / development commands:
```
python -m brakelab.cli configs/2026_baseline.json                    # print results, no GUI
python -m brakelab.cli configs/2026_baseline.json --report out.pdf   # + PDF report
python -m pytest                                                     # run the test suite
```

> **macOS note:** on the stock CommandLineTools Python a venv's PySide6 can fail to load its Qt
> plugins (*"Could not find the Qt platform plugin cocoa"*). If that happens, use `run.command`
> (it uses the system Python), or install a full Python from [python.org](https://www.python.org)
> and use a venv there.

### Releasing a new version

Tag and push: `git tag v1.0.1 && git push origin v1.0.1`. GitHub Actions builds both apps, runs
the test suite, smoke-tests the frozen apps, and publishes the Release automatically
(see [docs/developer_guide.md](docs/developer_guide.md) §7b).

## Design principles
1. **Correctness first** — physics lives in a pure, fully-tested core validated against
   `docs/calculation_audit.md`; the GUI contains no equations.
2. **One model, many configurations** — the spreadsheet's x1/x2 sheets are just two configs.
3. **Extensible by addition** — new capability = a new `Analysis` subclass, core untouched.
4. **Written for the next student** — explicit units, typed dataclasses, docstrings that cite the
   equation, tests as executable documentation.
