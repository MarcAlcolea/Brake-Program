"""Catalog of real, off-the-shelf brake components.

Selecting a component fills the matching input variables automatically, so a user can pick "Tilton
76-Series 0.625\" master cylinder" instead of typing a bore. The same catalog lets the optimizer
choose from parts the team can actually buy (e.g. the discrete set of 76-Series bores).

This is plain, easily-editable data — students should add parts here and VERIFY specs against the
manufacturer datasheets. Values marked "approximate" in ``note`` are best-effort and should be
confirmed. The three component types the tool needs are master cylinders, calipers and brake pads.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.units import inch_to_mm

CUSTOM = "Custom"  # sentinel shown in the dropdowns for "edit variables manually"


@dataclass(frozen=True)
class MasterCylinderSpec:
    name: str
    series: str
    bore_mm: float
    stroke_mm: float
    note: str = ""


@dataclass(frozen=True)
class CaliperSpec:
    name: str
    piston_area_mm2: float   # area of ONE piston
    n_pistons: int           # total pistons (both sides)
    note: str = ""


@dataclass(frozen=True)
class PadSpec:
    name: str
    friction_coefficient: float
    note: str = ""


def _tilton_76(bore_in: float) -> MasterCylinderSpec:
    return MasterCylinderSpec(
        name=f'Tilton 76-Series {bore_in:.3f}"'.replace(".000", ".0"),
        series="Tilton 76-Series",
        bore_mm=round(inch_to_mm(bore_in), 4),
        stroke_mm=round(inch_to_mm(1.1), 2),  # 1.1" stroke
    )


# Tilton 76-Series available bores (inches). Verified sizes.
MASTER_CYLINDERS: list[MasterCylinderSpec] = [
    _tilton_76(b) for b in (0.625, 0.700, 0.750, 0.813, 0.875, 1.000)
]

CALIPERS: list[CaliperSpec] = [
    CaliperSpec("Wilwood GP200", piston_area_mm2=793.55, n_pistons=2,
                note="1.25\" pistons; from the team's spreadsheet."),
    CaliperSpec("Wilwood PS-1", piston_area_mm2=634.0, n_pistons=2,
                note="~1.12\" pistons; approximate — verify against the Wilwood datasheet."),
]

BRAKE_PADS: list[PadSpec] = [
    PadSpec("Wilwood PolyMatrix BP-10", 0.45, note="approximate; verify."),
    PadSpec("Wilwood PolyMatrix BP-20", 0.55, note="approximate; verify."),
    PadSpec("Wilwood PolyMatrix BP-28", 0.48, note="conservative average from the team's spreadsheet."),
    PadSpec("Wilwood PolyMatrix BP-40", 0.62, note="approximate; verify."),
]

# --- lookup / matching helpers ---------------------------------------------------------------
_BORE_TOL = 0.05     # mm
_AREA_TOL = 1.0      # mm²
_MU_TOL = 0.005


def master_cylinder_series() -> list[str]:
    seen: list[str] = []
    for mc in MASTER_CYLINDERS:
        if mc.series not in seen:
            seen.append(mc.series)
    return seen


def bores_for_series(series: str) -> list[float]:
    return sorted(mc.bore_mm for mc in MASTER_CYLINDERS if mc.series == series)


def all_mc_bores() -> list[float]:
    return sorted({mc.bore_mm for mc in MASTER_CYLINDERS})


def match_master_cylinder(bore_mm: float) -> MasterCylinderSpec | None:
    for mc in MASTER_CYLINDERS:
        if abs(mc.bore_mm - bore_mm) <= _BORE_TOL:
            return mc
    return None


def match_caliper(piston_area_mm2: float, n_pistons: int) -> CaliperSpec | None:
    for cal in CALIPERS:
        if cal.n_pistons == n_pistons and abs(cal.piston_area_mm2 - piston_area_mm2) <= _AREA_TOL:
            return cal
    return None


def match_pad(friction_coefficient: float) -> PadSpec | None:
    for pad in BRAKE_PADS:
        if abs(pad.friction_coefficient - friction_coefficient) <= _MU_TOL:
            return pad
    return None
