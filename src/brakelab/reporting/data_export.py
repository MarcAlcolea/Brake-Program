"""Export a configuration and its results to CSV for teammates (opens directly in Excel).

A flat, readable dump — every input, every design (backward) and performance (forward) output, the
requirements check, and the selected components — one row each, with a Section column so it can be
filtered or pivoted. Uses only the standard-library ``csv`` module, so it works in the frozen app
(where openpyxl is deliberately not bundled).
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..app.field_spec import GROUPS as INPUT_GROUPS
from ..app.forward_spec import OUTPUT_GROUPS as FORWARD_GROUPS
from ..app.output_spec import GROUPS as OUTPUT_GROUPS
from ..core.attrpath import get_by_path
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
from .pdf_report import _selected_components


def _input_value(config: VehicleConfig, field_spec) -> str:
    v = get_by_path(config, field_spec.path)
    if field_spec.kind == "bool":
        return "yes" if v else "no"
    if field_spec.kind == "int":
        return str(int(v))
    return f"{float(v):.{field_spec.decimals}f}"


def _output_value(output, results: BrakeResults, config: VehicleConfig) -> str:
    try:
        return f"{output.getter(results, config):.4f}"
    except Exception:  # noqa: BLE001 — a missing phase should leave the cell blank, not crash
        return ""


def export_csv(config: VehicleConfig, results: BrakeResults, path: str | Path) -> Path:
    """Write a full inputs+outputs+requirements+components dump for ``config`` to ``path``."""
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Section", "Quantity", "Value", "Unit"])
        w.writerow(["Configuration", "Name", config.name, ""])

        for comp, part in _selected_components(config):
            w.writerow(["Components", comp, part, ""])

        for group in INPUT_GROUPS:
            for fld in group.fields:
                w.writerow([f"Input — {group.title}", fld.label, _input_value(config, fld), fld.unit])

        for group in OUTPUT_GROUPS:
            for out in group.outputs:
                w.writerow([f"Output (design) — {group.title}", out.label,
                            _output_value(out, results, config), out.unit])

        if getattr(results, "forward", None) is not None:
            for group in FORWARD_GROUPS:
                for out in group.outputs:
                    w.writerow([f"Output (performance) — {group.title}", out.label,
                                _output_value(out, results, config), out.unit])
            from ..core.performance import stopping_from_config

            da, ta = stopping_from_config(config, results.forward.actual_decel_g)
            dt, tt = stopping_from_config(config, config.target_decel_g)
            w.writerow(["Stopping — actual", "Stopping distance", f"{da:.2f}", "m"])
            w.writerow(["Stopping — actual", "Stopping time", f"{ta:.3f}", "s"])
            w.writerow(["Stopping — design target", "Stopping distance", f"{dt:.2f}", "m"])
            w.writerow(["Stopping — design target", "Stopping time", f"{tt:.3f}", "s"])

        for req in getattr(results, "requirements", ()) or ():
            status = "PASS" if req.passed else ("FAIL" if req.hard else "OFF TARGET")
            w.writerow(["Requirement", req.name,
                        f"needs {req.requirement_text}; produces {req.current_text}", status])
    return path
