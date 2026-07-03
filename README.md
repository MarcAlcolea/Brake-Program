# FSAE Brake Design Tool

A maintainable, extensible desktop application for Formula SAE brake system design — the
standard engineering tool for our Controls team, replacing the legacy braking spreadsheet and
the hand calculations for brake-rotor thermal analysis.

## Status
Project scaffolding + engineering audit. **No calculation code implemented yet** — the physics
is being specified and verified first (correctness before UI). See:

- [`docs/calculation_audit.md`](docs/calculation_audit.md) — every spreadsheet/thermal
  calculation checked, with the bugs found (B1 static-load swap, B2 missing ×2 on inboard rear,
  etc.) and the corrected golden values.
- [`docs/architecture.md`](docs/architecture.md) — layered, OOP, extensible design and build order.

## Layout
```
docs/        engineering audit + architecture
reference/   original spreadsheet & thermal document (validation source of truth)
configs/     saved vehicle configurations (JSON)
src/brakelab/  core engine · analyses · thermal · persistence · reporting · app (GUI)
tests/       golden-value + property tests
```

## Priorities
1. **Correctness** — verified against `docs/calculation_audit.md` before any UI.
2. **Maintainability & extensibility** — future students can read and extend it.
3. GUI, save/load, PDF reports, then optimization / Monte Carlo / telemetry / thermal as plug-in
   analyses.

## Getting started (once implementation begins)
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
