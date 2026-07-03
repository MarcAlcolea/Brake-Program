"""Reference configurations matching the original spreadsheet sheets.

These reproduce the inputs of the two design variants in ``reference/Braking Calculations.xlsx``
so the engine can be validated against known numbers (see ``tests/`` and ``docs/calculation_audit.md``).

- :func:`outboarded_x2` — the "x2 Outboarded" sheet (2 rear rotors). Self-consistent; the engine
  reproduces its numbers.
- :func:`inboarded_x1` — the "x1 Inboarded" sheet (1 rear rotor). The engine reproduces it *except*
  the rear clamp/pressure, which use the corrected factor-of-two (audit **B2**).

Caliper piston area is unified to 793.55 mm² (audit **B4**); the sheet used 792 mm² only in its
pedal-travel section, so pedal travel differs from the sheet by ~0.1 %.
"""

from __future__ import annotations

from .core.models import (
    Axle,
    Caliper,
    Hydraulics,
    MassProperties,
    Pad,
    PedalBox,
    Rotor,
    Tires,
    VehicleConfig,
)
from .core.units import inch_to_mm

# Values shared by both sheets.
_MASS = dict(total_mass=320.0, cg_height=0.3556, wheelbase=1.625, front_weight_fraction=0.52)
_TIRES = dict(friction_coefficient=1.5, loaded_radius=0.224)
_ROTOR = dict(effective_radius=0.0885)
_PAD = dict(friction_coefficient=0.48)
_CALIPER_AREA = 793.55  # mm², area of one piston (unified, audit B4)


def outboarded_x2() -> VehicleConfig:
    """"x2 Outboarded" variant: two rear rotors, equal 5/8" master cylinders, 65/35 bias."""
    return VehicleConfig(
        name="2026 Baseline (x2 Outboarded)",
        mass=MassProperties(**_MASS),
        tires=Tires(**_TIRES),
        front_axle=Axle(n_rotors=2),
        rear_axle=Axle(n_rotors=2),
        rotor=Rotor(**_ROTOR),
        pad=Pad(**_PAD),
        caliper=Caliper(piston_area=_CALIPER_AREA, n_pistons=2, piston_travel=0.15),
        hydraulics=Hydraulics(mc_bore_front=inch_to_mm(0.625), mc_bore_rear=inch_to_mm(0.625)),
        pedal_box=PedalBox(pedal_ratio=6.0, balance_bias_front=0.65, driver_force=400.0),
        target_decel_g=1.5,
        notes="Reproduces the x2 Outboarded spreadsheet sheet.",
    )


def inboarded_x1() -> VehicleConfig:
    """"x1 Inboarded" variant: single rear rotor, 0.7"/0.625" master cylinders, 64/36 bias."""
    return VehicleConfig(
        name="2026 Inboard (x1 Inboarded)",
        mass=MassProperties(**_MASS),
        tires=Tires(**_TIRES),
        front_axle=Axle(n_rotors=2),
        rear_axle=Axle(n_rotors=1, inboard=True),
        rotor=Rotor(**_ROTOR),
        pad=Pad(**_PAD),
        caliper=Caliper(piston_area=_CALIPER_AREA, n_pistons=2, piston_travel=1.2),
        hydraulics=Hydraulics(mc_bore_front=inch_to_mm(0.7), mc_bore_rear=inch_to_mm(0.625)),
        pedal_box=PedalBox(pedal_ratio=6.0, balance_bias_front=0.64, driver_force=400.0),
        target_decel_g=1.5,
        notes="Reproduces the x1 Inboarded sheet; rear sizing uses the corrected factor-of-two (B2).",
    )
