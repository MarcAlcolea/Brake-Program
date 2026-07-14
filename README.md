# Brake Design Studio

An FSAE brake-system design tool for our Controls team — the standard replacement for the legacy
braking spreadsheet and the by-hand rotor-thermal calculations. It has a verified calculation engine
and a desktop app (design, forward simulation, thermal, optimization, comparison, sensitivity, PDF
reports, save/load presets, a component catalog, and an ANSYS-ready rotor-temperature export).

---

## Just want to use the app? Download the Release.

**This is what almost everyone wants. No Python, no terminal, no setup.**

1. Go to the **[Releases page](https://github.com/MarcAlcolea/Brake-Program/releases/latest)**.
2. Under **Assets**, download the zip for your computer:

   | You have | Download this |
   |---|---|
   | **Windows** | `Brake-Design-Studio-Windows.zip` |
   | **Mac** (Apple Silicon — M1/M2/M3/M4) | `Brake-Design-Studio-macOS-AppleSilicon.zip` |

3. Extract the zip and open the app:
   - **Windows:** open the `Brake Design Studio` folder → double-click **`Brake Design Studio.exe`**.
   - **Mac:** double-click the zip, then **right-click `Brake Design Studio.app` → Open**.

First launch only (the app isn't signed with a paid certificate):
- **Windows** may say *"Windows protected your PC"* → click **More info → Run anyway**.
- **Mac** may block it → **right-click → Open**, or allow it under
  **System Settings → Privacy & Security → Open Anyway**.

That's it — after that it opens like any normal app. Your saved setups live in your user account, not
in the app folder, so you can replace the app with a newer version and keep all your configurations.

> ### "I downloaded it but there's no .exe / no app!"
> You almost certainly clicked the green **`Code` → Download ZIP** button on the repo's front page.
> **That gives you the source code, not the app** — it's for developers and has no ready-to-run
> program inside. The app only lives on the **[Releases](https://github.com/MarcAlcolea/Brake-Program/releases/latest)**
> page (see above). Two different downloads for two different purposes:
>
> | Download | What it is | Who it's for |
> |---|---|---|
> | **Releases → the `.zip` assets** | The finished, double-click app | **Everyone using the tool** |
> | **`Code` → Download ZIP** (or `git clone`) | The raw Python source | Developers editing the code |

---

## Repository layout (for developers)

If you cloned the source, here is what every folder is:

```
Brake Program/
├─ README.md              ← you are here
├─ run.command            ← Mac: double-click to launch from source
├─ run.bat                ← Windows: double-click to launch from source
├─ pyproject.toml         ← the one place dependencies + build config live
│
├─ src/brakelab/          ← ALL the application code (the Python package)
├─ tests/                 ← automated test suite (run with pytest)
├─ configs/               ← sample saved vehicle setups (.json)
├─ reference/             ← the original spreadsheet & thermal doc we validate against
├─ docs/                  ← engineering audit, architecture, developer guide
├─ packaging/             ← how the double-click apps get built (PyInstaller spec + icons)
└─ .github/               ← CI: runs tests on every push, builds the apps on version tags
```

### Inside `src/brakelab/` — the code, by responsibility

The app is split so that the **physics never touches the GUI**. If you want to change an equation you
work in `core/`; if you want to change how something looks you work in `app/`.

```
src/brakelab/
├─ core/          The physics engine — pure calculations, no GUI. models, the 5 solve phases,
│                 forward simulation, thermal heat-flux, validation, requirements checks.
├─ app/           The PySide6 desktop GUI. Everything you see on screen.
│   ├─ panels/    The big content areas of each tab (Main, Thermal, Optimize, Compare, Report…).
│   ├─ widgets/   Small reusable UI pieces (collapsible sections, ⓘ popovers…).
│   ├─ plots/     The matplotlib charts embedded in the GUI.
│   └─ theme.py   Fonts and light/dark colors.
├─ optimization/  The optimizer (variables, objectives, constraints, search algorithms).
├─ thermal/       Transient rotor-temperature simulation + ANSYS CSV export.
├─ components/    Catalog of real parts (master cylinders, calipers, pads).
├─ persistence/   Saving and loading configurations as JSON.
├─ reporting/     PDF report generation.
├─ analyses/      Pluggable studies over a config (e.g. sensitivity).
└─ cli.py         Headless command-line entry point (no GUI).
```

Key docs live in `docs/`:
- [`docs/calculation_audit.md`](docs/calculation_audit.md) — every spreadsheet/thermal calculation
  checked, the bugs found, and the corrected golden values the engine is tested against.
- [`docs/architecture.md`](docs/architecture.md) — the layered, extensible design.
- [`docs/developer_guide.md`](docs/developer_guide.md) — how to add inputs, outputs, equations, parts.

---

## Running from source (developers only)

Double-click **`run.command`** (Mac) or **`run.bat`** (Windows), or from a terminal:

```
python -m venv .venv                 # create a virtual environment (once)
# activate it:  Windows -> .venv\Scripts\activate    Mac/Linux -> source .venv/bin/activate
python -m pip install -e ".[dev]"    # install the app + dev/test tools (once)
python -m brakelab                   # launch the GUI
```

Headless / development commands:
```
python -m brakelab.cli configs/2026_baseline.json                    # print results, no GUI
python -m brakelab.cli configs/2026_baseline.json --report out.pdf   # + PDF report
python -m pytest                                                     # run the test suite
```

> **Mac note:** on the stock CommandLineTools Python a venv's PySide6 can fail to load its Qt plugins
> (*"Could not find the Qt platform plugin cocoa"*). If that happens, use `run.command` (it uses the
> system Python), or install a full Python from [python.org](https://www.python.org) and use a venv there.

## Releasing a new version

Tag and push — GitHub Actions builds both apps, runs the tests, smoke-tests the frozen apps, and
publishes the Release automatically:
```
git tag v1.6.0 && git push origin v1.6.0
```

## Design principles

1. **Correctness first** — the physics lives in a pure, fully-tested `core/` validated against
   `docs/calculation_audit.md`; the GUI contains no equations.
2. **One model, many configurations** — the spreadsheet's x1/x2 sheets are just two saved configs.
3. **Extensible by addition** — new capability = a new module/`Analysis`, core untouched.
4. **Written for the next student** — explicit units, typed dataclasses, docstrings that cite the
   equation, tests as executable documentation.
