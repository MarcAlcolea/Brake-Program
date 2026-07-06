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


@dataclass(frozen=True)
class MaterialSpec:
    """A rotor material. Only the two properties the lumped-capacitance graph uses (specific heat
    and emissivity) are applied to the config; density is carried for reference only."""

    name: str
    specific_heat: float     # J/kg·K
    emissivity: float        # grey-body, smooth/unoxidised surface
    density: float           # g/cm³ (reference only — the sim uses rotor mass, entered separately)
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

# Rotor materials — properties from reference/Brake Rotors Simulations 2026.docx ("What are the
# material properties?"). 4130 is the team's preferred choice (far higher max service temperature).
MATERIALS: list[MaterialSpec] = [
    MaterialSpec("1018 Mild Steel", specific_heat=486.0, emissivity=0.28, density=7.87,
                 note="AISI 1018 (mild/low-carbon). Specific heat 0.486 J/g·K; emissivity 0.20–0.32 "
                      "smooth/unoxidised (0.28 used); density 7.87 g/cm³. Max service temp ~250 °C — "
                      "easy to machine and cheap, but may warp in Endurance."),
    MaterialSpec("4130 Chromoly", specific_heat=477.0, emissivity=0.27, density=7.85,
                 note="AISI 4130 (low-alloy). Specific heat 0.477 J/g·K; emissivity 0.27 polished; "
                      "density 7.85 g/cm³. Max service temp >500 °C — superior heat resistance, the "
                      "team's preferred rotor material."),
]

# --- lookup / matching helpers ---------------------------------------------------------------
_BORE_TOL = 0.05     # mm
_AREA_TOL = 1.0      # mm²
_MU_TOL = 0.005
_CP_TOL = 1.0        # J/kg·K
_EMISS_TOL = 0.005


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


def match_material(specific_heat: float, emissivity: float) -> MaterialSpec | None:
    for mat in MATERIALS:
        if abs(mat.specific_heat - specific_heat) <= _CP_TOL and abs(mat.emissivity - emissivity) <= _EMISS_TOL:
            return mat
    return None
