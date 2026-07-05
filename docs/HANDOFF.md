# Handoff — context for a new Claude Code session

Paste the block below into a new Claude Code chat started in `/Users/marc/Desktop/Brake Program`.
(This project also has persistent memory, so a fresh session in this folder auto-loads the key
facts — this doc is a thorough backup and a way to set the immediate focus.)

---

```
I'm continuing work on an existing project — a professional Python desktop tool for my
university FSAE team's Controls subteam that replaces our brake-system Google Spreadsheet.
It's a long-term, multi-year team tool: correctness, maintainability, and extensibility
matter more than speed. Please read docs/architecture.md, docs/calculation_audit.md, and
docs/developer_guide.md first, then confirm you understand the state before making changes.

PROJECT LOCATION: /Users/marc/Desktop/Brake Program  (git repo; commit as we go, modular commits)

HOW TO RUN (this Mac has a quirk):
- Launch the GUI: double-click run.command, or  PYTHONPATH=src python3 -m brakelab
- There is NO `python` or `pip` on PATH — always use `python3` and `python3 -m pip`.
- A venv's PySide6 is BROKEN on this machine (can't find Qt "cocoa" plugin). We use the SYSTEM
  python3 (/Library/Developer/CommandLineTools/usr/bin/python3, Python 3.9.6) with a brakelab.pth
  in its user site-packages pointing at src/. Do NOT recreate a venv here.
- Tests: python3 -m pytest   (34 passing). Headless: python3 -m brakelab.cli configs/2026_baseline.json
- Headless GUI smoke: QT_QPA_PLATFORM=offscreen AND patch QMessageBox/QInputDialog/QFileDialog,
  or modal dialogs hang the run.

WHAT IT IS (all built and working):
- core/ = the physics (pure Python, no GUI, fully tested): 5 phases (dynamics, tires, brakes,
  hydraulics, pedal_travel) + requirements + validation + engine.solve(config)->BrakeResults.
- app/ = PySide6 GUI. Inputs/outputs are DECLARATIVE lists in app/field_spec.py and
  app/output_spec.py (the UI builds itself from them). Left SIDEBAR nav + 4 pages: Design,
  Optimize, Compare, Plots. Config library (presets), per-field unit switching, component catalog,
  optimization studio (5 sections), PDF reports, light/dark themes.
- optimization/ = SEPARATE pluggable subsystem (problem/metrics/algorithms/runner/sensitivity/
  report). Random-search backend now; SciPy/GA/CasADi/OpenMDAO add via the Optimizer interface with
  no UI changes. Supports discrete "catalog" variables (e.g. MC bore from Tilton 76-Series).
- components/catalog.py = real parts (Tilton MCs, Wilwood GP200/PS-1 calipers, BP-10/20/28/40 pads).
  Some specs approximate/flagged — verify against datasheets.
- persistence/ (JSON + in-program library), reporting/ (PDF), analyses/ (Analysis seam),
  thermal/ (documented STUB — NOT implemented yet).

CALC FIXES ALREADY MADE (see docs/calculation_audit.md):
- B1: front weight fraction is one input; default 0.52 (front-biased 52F/48R) reproduces the sheet.
  OPEN: confirm true front/rear weight distribution with the suspension team.
- B2: inboard rear clamp force now includes the factor of 2 (sheet dropped it).
- B4: one unified caliper piston area. Piston travel 0.15mm confirmed correct by Marc.
- OPEN engineering questions: inboard rear driveline ratio (B7); verify PS-1 / pad specs.

GUI CONVENTIONS (follow these):
- NEVER setStyleSheet on normal widgets — it makes them ignore the QPalette (caused black boxes in
  light mode). Bold via font instead. (The popover is an isolated frame, so its stylesheet is OK.)
- Bold SPARINGLY: only section headers / titles / the active sidebar tab / a dropdown's chosen
  option (Helvetica Bold); body is Helvetica Light. No ALL CAPS. No grey selection boxes — the
  sidebar and collapsible section headers are plain ClickableLabels (bold when active/expanded).
- Light theme = truly white (#ffffff, minimal grey); dark = near-black (#141414).
- Collapsible sections (widgets/section.py) instead of nested group boxes. Tables size to content
  (uikit.fit_table) so a page scrolls once — avoid scroll-inside-scroll.
- ⓘ opens a popover next to the icon (widgets/popover.py), not a bottom panel.
- Every QComboBox: setMaxVisibleItems, and pass it through uikit.style_combo (bold chosen option).

EXTENDING (see docs/developer_guide.md): add input = dataclass field in core/models.py + one line in
app/field_spec.py. Add output = compute in core + one _o(...) line in app/output_spec.py. Add
component = one line in components/catalog.py. Add optimizer algorithm = implement Optimizer +
register in optimization/algorithms/__init__.py.

POSSIBLE NEXT STEPS (Marc will direct): implement the thermal module (energy->heat flux->transient
temp->ANSYS export; notes in thermal/base.py and docs/calculation_audit.md); add rotors to the
catalog; make caliper/pad discrete optimization variables; a SETUP.md / install script for teammates.

Please start by confirming the app runs (tests pass, GUI launches) and summarizing the current state
back to me before we pick the next task.
```
