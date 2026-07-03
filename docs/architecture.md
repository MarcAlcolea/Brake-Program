# Architecture — FSAE Brake Design Tool

**Status:** proposed (for discussion before implementation)

> **Decisions (2026-07-03):** GUI framework = **PySide6/Qt** (§7). B1 default =
> `front_weight_fraction = 0.52` / front-biased 52F/48R (see `calculation_audit.md`).
**Goal:** replace the braking spreadsheet with a maintainable, extensible desktop engineering
tool that becomes the Controls team's standard brake-design environment.

---

## 1. Design principles

1. **Correctness is a first-class, testable property.** The physics lives in a pure-Python core
   with zero GUI/IO dependencies, validated against the golden values in
   [`calculation_audit.md`](calculation_audit.md).
2. **The GUI never contains physics.** Any equation in a widget is a bug. Panels read/write a
   config object and display results; nothing more.
3. **One model, many configurations.** The spreadsheet's x1/x2 sheets become *configurations* of
   one parameterised engine. No copy-paste variants.
4. **Extensible by addition, not modification (Open/Closed).** Optimization, Monte Carlo,
   telemetry, and thermal all plug in as `Analysis` implementations against stable interfaces —
   no core rewrite.
5. **Written for the next student.** Explicit units, dataclasses over dicts, docstrings that cite
   the equation and its source, and tests as executable documentation.

---

## 2. Layered structure

```
┌──────────────────────────────────────────────────────────┐
│  app/        GUI (PySide6): panels, plots, validation UI  │  ← no physics
├──────────────────────────────────────────────────────────┤
│  controller  AppState / ProjectController (Observer)      │  ← mediates GUI ↔ core
├───────────────┬──────────────────┬───────────────────────┤
│  reporting/   │  persistence/    │  analyses/  thermal/   │  ← consume the core
│  (PDF)        │  (JSON save/load)│  (optimize, MC, …)     │
├───────────────┴──────────────────┴───────────────────────┤
│  core/   VehicleConfig → engine → BrakeResults  +units    │  ← pure, fully tested
└──────────────────────────────────────────────────────────┘
```

Dependencies point **downward only**. `core/` imports nothing above it and no GUI/plot/IO
libraries, so it can run headless (CI, scripts, batch studies) and is trivial to unit-test.

---

## 3. The core (`src/brakelab/core/`)

### 3.1 Configuration model (`models.py`)
Nested, typed dataclasses grouped the way the GUI panels are grouped:

```
VehicleConfig
├─ MassProperties   (mass, cg_height, front_weight_fraction, wheelbase)
├─ Tires            (mu, loaded_radius)
├─ Axle × 2 (front/rear): n_rotors, inboard: bool, driveline_ratio
├─ Rotor            (effective_radius, geometry, material→MaterialLibrary)
├─ Pad              (mu, swept_area)
├─ Caliper          (piston_area, n_pistons, piston_travel)
├─ Hydraulics       (mc_bore_front, mc_bore_rear, compliance)
├─ PedalBox         (pedal_ratio, balance_bias_front, driver_force)
└─ TargetDecel      (g)
```

Design choices that directly kill the audited bugs:
- **One** `front_weight_fraction` → axle loads derived consistently (**B1** impossible).
- **One** `balance_bias_front`; rear = `1 − front`, range-validated (**B6**).
- **One** `Caliper.piston_area` read by both pressure and pedal-travel math (**B4**).
- Axle carries `inboard`/`n_rotors`/`driveline_ratio` so x1/x2 and inboard scaling are just data
  (**B2**, **B7**).

### 3.2 Calculation modules (one per physics phase)
Each is a pure function/class: `config → phase result`. Mirrors the spreadsheet phases so a
student can map sheet ↔ code 1:1:

| Module | Responsibility (spreadsheet phase) |
|---|---|
| `dynamics.py` | Weight transfer, static & dynamic axle loads (Phase 1) |
| `tires.py` | Grip-limited force & required brake torque (Phase 2) |
| `brakes.py` | Clamp force, line pressure — `clamp_from_torque()` (Phase 3) |
| `hydraulics.py` | MC force, balance bar, pedal force, feasibility (Phase 4) |
| `pedal_travel.py` | Fluid volume, MC stroke, pedal travel, BOTS |
| `validation.py` | Engineering-limit checks → warnings/errors |
| `units.py` | Explicit SI internals + conversion helpers (in↔m, etc.) |

### 3.3 Orchestrator (`engine.py` → `results.py`)
`BrakeEngine.solve(config) -> BrakeResults`. `BrakeResults` is an immutable dataclass holding
every intermediate + final quantity (so reports/plots/tests read one object). The engine is a
thin pipeline; each stage is independently testable.

### 3.4 Units
Internally **SI everywhere**; convert only at the GUI/report boundary. Start with a small typed
conversion helper; `pint` can be adopted later behind the same boundary if we want full
dimensional safety. (Recommendation: begin lightweight to keep the core dependency-free.)

---

## 4. Extensibility seam — the `Analysis` interface (`analyses/base.py`)

The key to "add features later without redesign." Everything beyond the base calculation is an
Analysis over `(config, engine)`:

```python
class Analysis(ABC):
    name: str
    @abstractmethod
    def run(self, config: VehicleConfig, engine: BrakeEngine) -> AnalysisResult: ...
```

Planned implementations (each self-contained, GUI discovers them via a registry):
- **Sensitivity / sweep** — vary one input, plot an output (e.g. pedal travel vs piston travel).
- **Optimization** — solve for bias / bore / `R_eff` to hit targets (later: CasADi/OpenMDAO,
  as the spreadsheet's own notes anticipate).
- **Monte Carlo** — propagate input tolerances → output distributions & confidence.
- **Thermal** (`thermal/`) — duty-cycle → energy → heat flux + film-coefficient tables →
  lumped-capacitance transient temperature; **exports ANSYS-ready tabular data**, replacing the
  doc's hand calcs. Couples to the same `n_rotors`/bias so **T2** can't drift.
- **Telemetry ingest** — real deceleration/pressure logs → back out effective μ, validate model.

New feature = new `Analysis` subclass + one panel. Core untouched.

---

## 5. Persistence (`persistence/config_io.py`)
- `VehicleConfig` ⇄ **JSON** (human-readable, git-diffable, review-friendly).
- Every file carries a `schema_version`; a small migration path keeps old configs loadable.
- `configs/` holds versioned car definitions (e.g. `2026_baseline.json`). This is the
  "save/load complete vehicle configuration" requirement, and it makes configs reviewable in PRs.

## 6. Reporting (`reporting/pdf_report.py`)
- Consumes `BrakeResults` + config → a professional PDF (inputs, results tables, plots,
  pass/fail with margins, assumptions/citations). Kept fully separate from GUI so reports can be
  generated headless/batch. Likely `reportlab` (or matplotlib PDF pages) — decide at build time.

## 7. GUI (`app/`, PySide6/Qt — recommended)
- **Why Qt/PySide6:** mature, professional, native look, strong plotting integration
  (pyqtgraph for live/interactive, matplotlib for report-quality), LGPL, the de-facto choice for
  desktop engineering tools — good longevity for a multi-year student project.
- **Structure:** `panels/` (one categorized input panel per config group), `plots/`, `widgets/`
  (validated numeric fields that show inline errors from `validation.py`).
- **Live updates:** `ProjectController` holds the active config; on any edit it re-runs the
  engine and notifies subscribers (Observer pattern) → results and plots refresh instantly.
- **Validation UX:** invalid/out-of-range inputs highlight the field and explain why, driven by
  the same `validation.py` used headlessly.

---

## 8. Testing (`tests/`)
- `pytest`. **Golden-value tests** assert engine outputs equal the *corrected* values in
  `calculation_audit.md`, each traceable to an audit row.
- **Property tests** for physical invariants: `static_front + static_rear == W`;
  `dynamic_front + dynamic_rear == W`; energy conservation in thermal; bias sums to 1.
- Core has no GUI deps, so tests run fast in CI with no display.

---

## 9. Proposed layout

```
Brake Program/
├─ README.md · pyproject.toml · requirements.txt · .gitignore
├─ docs/            calculation_audit.md · architecture.md · (physics_reference.md)
├─ reference/       original xlsx + thermal docx (source of truth for validation)
├─ configs/         saved VehicleConfig JSON (e.g. 2026_baseline.json)
├─ src/brakelab/
│  ├─ core/         models · units · dynamics · tires · brakes · hydraulics ·
│  │                pedal_travel · validation · engine · results
│  ├─ analyses/     base (+ sensitivity, optimization, montecarlo …)
│  ├─ thermal/      base (+ heat flux, film coeff, transient, ANSYS export)
│  ├─ persistence/  config_io
│  ├─ reporting/    pdf_report
│  └─ app/          main · controller · panels/ · widgets/ · plots/
└─ tests/           golden + property tests
```

(`brakelab` is a placeholder package name — open to a team-preferred name.)

---

## 10. Proposed build order (each a modular commit, after we agree)

1. `core/models.py` + `units.py` — the config schema.
2. `core/dynamics/tires/brakes/hydraulics/pedal_travel` + `engine` — **with the B1/B2 fixes**.
3. `tests/` — golden values from the audit. **Gate: outputs match corrected numbers before any UI.**
4. `persistence` (JSON save/load) + a `2026_baseline.json`.
5. `validation` + a headless CLI/`__main__` to run a config and print results.
6. `reporting` (PDF).
7. `app/` GUI (PySide6): panels → live recompute → plots → validation UX.
8. First `Analysis` (sensitivity sweep) to prove the extensibility seam.
9. `thermal/` module (energy → flux → transient → ANSYS export).

Steps 1–3 deliver a **trustworthy, verified calculator** before a single pixel of UI — matching
the stated priority: *correctness first, then everything else*.
