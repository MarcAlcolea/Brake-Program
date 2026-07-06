# Developer Guide

How the project is organised, how to extend it (new inputs / outputs / equations / components), and
how to run it on another computer. Written for the next student on the team.

---

## 1. Folder structure

Everything is a Python package under `src/brakelab/`. Dependencies point **downward**: `core` knows
nothing about the GUI, so the physics can run and be tested with no display.

```
src/brakelab/
├─ core/                 THE PHYSICS — pure Python, no GUI. Fully tested.
│  ├─ models.py          VehicleConfig + sub-configs (all the inputs, typed)
│  ├─ dynamics.py        Phase 1: weight transfer, axle loads
│  ├─ tires.py           Phase 2: grip-limited force, required brake torque
│  ├─ brakes.py          Phase 3: clamp force, line pressure
│  ├─ hydraulics.py      Phase 4: master cylinder, balance bar, pedal force
│  ├─ pedal_travel.py    fluid volume, MC stroke, pedal travel, BOTS
│  ├─ thermal.py         brake-rotor heat flux + film coefficient (ANSYS inputs)
│  ├─ requirements.py    the pass/fail engineering checks
│  ├─ validation.py      input sanity checks
│  ├─ results.py         the result objects every phase fills in
│  ├─ engine.py          BrakeEngine.solve(config) -> BrakeResults  (runs all phases)
│  ├─ units.py           constants + inch↔mm helpers
│  ├─ unit_convert.py    display-unit conversion (m/mm/in, kg/lb, …)
│  └─ attrpath.py        get/set a nested field by dotted path ("mass.total_mass")
│
├─ components/catalog.py REAL parts (Tilton MCs, Wilwood calipers/pads) + match helpers
├─ optimization/         THE OPTIMIZER — separate from the physics
│  ├─ problem.py         Variable / Objective / Constraint / Settings / OptimizationProblem
│  ├─ metrics.py         catalog of optimizable quantities
│  ├─ algorithms/        pluggable search backends (random_search now; SciPy/GA/… later)
│  ├─ runner.py          runs a problem against a config + engine, ranks designs
│  ├─ sensitivity.py     which variables matter most
│  └─ report.py          optimization PDF
├─ analyses/             the "Analysis" seam (sensitivity sweep); future studies plug in here
├─ persistence/          JSON save/load (config_io) + in-program library (library)
├─ reporting/pdf_report  the design-report PDF
├─ thermal/              stub for the future rotor thermal model
│
├─ app/                  THE GUI (PySide6) — no physics lives here
│  ├─ field_spec.py      ← declarative list of Main-tab INPUTS (label, unit, range, note)
│  ├─ output_spec.py     ← declarative list of Main-tab OUTPUTS (label, formula, note, getter)
│  ├─ thermal_spec.py    ← the Thermal tab's inputs/outputs + shared read-only values
│  ├─ controller.py      holds the active config, recomputes, notifies panels
│  ├─ theme.py           light/dark palettes + fonts
│  ├─ uikit.py           shared table/combo helpers
│  ├─ widgets/           CollapsibleSection, InfoButton, popover
│  ├─ panels/            one file per panel (inputs, outputs, requirements, …)
│  └─ main.py            the window + sidebar navigation
├─ reference_configs.py  the two spreadsheet variants as code (used to seed presets & tests)
├─ cli.py                headless runner (python -m brakelab.cli)
└─ __main__.py           launches the GUI (python -m brakelab)

tests/                   golden-value + property + optimization + component tests
docs/                    this guide, the calculation audit, the architecture
configs/                 shareable vehicle JSON files
reference/               the original spreadsheet and thermal doc
```

**Key idea:** the two "spec" files (`app/field_spec.py`, `app/output_spec.py`) are declarative
lists. The GUI builds itself from them, so adding an input or output is a data edit, not widget code.

---

## 2. How to add an INPUT

1. **Store it** — add a field to the right dataclass in `core/models.py` (give it a default so old
   saved configs still load). Example: add `rotor_thickness` to `Rotor`.
2. **Show it** — add one `Field(...)` line to the matching group in `app/field_spec.py`
   (path, label, unit, kind, min, max, decimals, note). The note is the hover text.
3. **Use it** — reference it in whatever `core/` calculation needs it.

That's it. The input appears in the Design tab with a unit selector and ⓘ note automatically.

## 3. How to add an OUTPUT

1. If it's a brand-new computed quantity, add a field to the relevant result dataclass in
   `core/results.py` and set it in the matching `core/<phase>.py` module.
2. Add one `_o(label, unit, formula, description, getter)` line to `app/output_spec.py`, where
   `getter` reads it from the results, e.g. `lambda r, c: r.sizing.front.line_pressure`.

The output shows up in the Outputs table (with its formula/description in the ⓘ popover) and in the
change-highlighting — no other code needed.

## 4. How to add / change an EQUATION

The equations live in the five `core/<phase>.py` files, each a small pure function. To change one,
edit it there. To add a new phase:

1. Add a result dataclass in `core/results.py`.
2. Write `core/<newphase>.py` with a `solve_...(config-parts) -> ThatResult` function.
3. Call it in `core/engine.py` and attach the result to `BrakeResults`.
4. Expose its numbers via `app/output_spec.py`.

**Always add a test.** `tests/test_golden.py` checks outputs against known values from
`docs/calculation_audit.md`; add your expected numbers there so the physics stays verified.

## 5. How to add a real COMPONENT

Edit `src/brakelab/components/catalog.py` — it's plain data. Append a `MasterCylinderSpec`,
`CaliperSpec`, or `PadSpec` to the relevant list. It immediately appears in the Design tab dropdown
and (for master cylinders) as a discrete option the optimizer can choose from. **Verify specs against
the manufacturer datasheet** — some current entries are marked approximate.

## 6. How to add an OPTIMIZATION metric, constraint, or algorithm

- **Metric** (something to optimize or constrain): add a `Metric(...)` to `optimization/metrics.py`.
- **New search algorithm** (SciPy, genetic, CasADi, OpenMDAO): implement the `Optimizer` interface in
  `optimization/algorithms/base.py` and register it in `optimization/algorithms/__init__.py`. The UI
  reads the registry, so it appears in the "Algorithm" dropdown with no UI changes.

---

## 7. Running on another computer (macOS or Windows)

**Non-developers should not set up Python at all** — download the standalone app from the GitHub
**Releases** page (`BrakeLab-Windows.zip` / `BrakeLab-macOS-AppleSilicon.zip`) and double-click it.
See §7b for how those apps are built and released.

For development the app is standard Python + PySide6, so it runs anywhere Python does. It needs
**Python 3.9+**; all dependencies come from `pyproject.toml`.

### Any machine (recommended: a virtual environment)
```
# 1. get the code (zip or git clone) and open a terminal in the project folder
python3 -m venv .venv                 # Windows: py -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"     # app + test/dev extras
python -m brakelab                    # launches the GUI
```
On most machines the virtualenv is the cleanest option and the above is all you need.

### This particular Mac (the one it was built on)
The stock macOS *CommandLineTools* Python has a quirk where a virtualenv's PySide6 can't find its Qt
plugins. So on that machine we run against the system Python instead, and **`run.command`** (double-
click, or `./run.command`) handles it. If you set up a fresh clone the venv route above is preferred;
fall back to `run.command` only if the GUI fails to launch with a Qt-plugin error.

### Windows notes
- Use `py` / `python` instead of `python3`, and `.venv\Scripts\activate` to activate the venv.
- The Qt-plugin quirk above is macOS-specific; a normal venv on Windows works fine.
- Everything else (tests, `python -m brakelab.cli`, PDF export) is identical.

### Verifying an install
```
python -m pytest          # the whole suite should pass
python -m brakelab.cli configs/2026_baseline.json   # prints results headlessly
```

## 7b. The standalone apps (how users actually get BrakeLab)

`packaging/` holds everything needed to freeze the GUI into a double-click app with PyInstaller:

- `launcher.py` — frozen-app entry point (also gives matplotlib a persistent font-cache dir).
- `BrakeLab.spec` — one spec for both platforms; produces `dist/BrakeLab.app` on macOS and
  `dist/BrakeLab/BrakeLab.exe` on Windows. Build locally with
  `pyinstaller --noconfirm packaging/BrakeLab.spec`.
- `make_icon.py` — regenerates `icon.icns` / `icon.ico` (both are committed).

CI (`.github/workflows/build.yml`) builds **both** platforms, runs the test suite, smoke-tests the
frozen app (`BRAKELAB_SMOKE=1` auto-quits after launch), and attaches the zips to a GitHub Release.

**To publish a new release:** tag the commit and push the tag —
```
git tag v1.0.1
git push origin v1.0.1
```
A few minutes later the Release with both zips appears on GitHub. (The workflow can also be run
from the Actions tab via "Run workflow" to get test builds as artifacts without releasing.)
Release builds run only on tags because macOS runner minutes are billed 10x on private repos.

Saved configurations live in a per-user folder (`~/Library/Application Support/BrakeLab` on macOS,
`%APPDATA%\BrakeLab` on Windows). To move designs between machines, use **Export to folder…** in the
app to write a JSON file and **Import…** on the other machine.
