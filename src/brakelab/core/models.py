"""Configuration data model for a vehicle's brake system.

These typed dataclasses are the single source of truth for every input. They are grouped the same
way the GUI panels and the spreadsheet phases are grouped, so a student can map one to the other.

Design notes (why this shape prevents the audited bugs)
------------------------------------------------------
- ``MassProperties.front_weight_fraction`` is the *only* place the weight split is defined; the
  axle loads are derived from it consistently (audit **B1** — the spreadsheet's static loads were
  inconsistent with its stated CG location).
- ``PedalBox.balance_bias_front`` is the *only* bias input; the rear complement is derived and the
  value is range-checked (audit **B6**).
- One ``Caliper.piston_area`` feeds both line-pressure and pedal-travel math (audit **B4**).
- ``Axle`` carries ``n_rotors`` / ``inboard`` / ``driveline_ratio`` as data, so the spreadsheet's
  "x1 inboarded" and "x2 outboarded" variants are just two configurations of one engine
  (audit **B2**/**B7**).

v1 simplification: a single ``Rotor``/``Pad``/``Caliper`` spec is shared by both axles (as the
spreadsheet does). Splitting into independent front/rear corners later is an additive change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import units


@dataclass
class MassProperties:
    """Vehicle mass and weight distribution."""

    total_mass: float               # kg — car + driver, fully equipped
    cg_height: float                # m — height of centre of gravity
    wheelbase: float                # m — distance between axles
    front_weight_fraction: float    # — static fraction of weight on the front axle (0..1)


@dataclass
class Tires:
    """Tire grip and geometry (shared front/rear in v1)."""

    friction_coefficient: float     # — tire-road μ
    loaded_radius: float            # m — loaded rolling radius


@dataclass
class Axle:
    """Per-axle brake layout."""

    n_rotors: int                   # — rotors/calipers on this axle (2 outboard, 1 inboard, ...)
    inboard: bool = False           # — True if a single inboard rotor drives both wheels
    driveline_ratio: float = 1.0    # — rotor speed : wheel speed (>1 if rotor is before the
    #                                   final-drive reduction). Scales required brake torque.


@dataclass
class Rotor:
    """Brake rotor sizing (shared front/rear in v1)."""

    effective_radius: float         # m — hub-centre to pad-centre (R_eff)


@dataclass
class Pad:
    """Brake pad friction (per pad / one side)."""

    friction_coefficient: float     # — μ of ONE pad. Effective rotor friction is 2·μ (both faces).


@dataclass
class Caliper:
    """Caliper piston geometry (shared front/rear in v1)."""

    piston_area: float              # mm² — area of ONE piston
    n_pistons: int                  # — total pistons in the caliper (both sides)
    piston_travel: float            # mm — pad clearance take-up per application

    @property
    def one_side_area(self) -> float:
        """Total piston area on ONE side — the area that generates clamp force from pressure."""
        return self.piston_area * self.n_pistons / 2.0

    @property
    def displacing_area(self) -> float:
        """Total piston face area fed by fluid (both sides) — sets fluid volume for pedal travel."""
        return self.piston_area * self.n_pistons


@dataclass
class Hydraulics:
    """Master cylinders. Difference in bore between front/rear is one way to set brake bias."""

    mc_bore_front: float            # mm — front master-cylinder bore diameter
    mc_bore_rear: float             # mm — rear master-cylinder bore diameter
    max_mc_stroke: float = 27.94    # mm — maximum available MC stroke (e.g. Tilton 76/78 = 1.1")

    @property
    def mc_area_front(self) -> float:
        """Front master-cylinder bore area [mm²]."""
        return units.circle_area_mm2(self.mc_bore_front)

    @property
    def mc_area_rear(self) -> float:
        """Rear master-cylinder bore area [mm²]."""
        return units.circle_area_mm2(self.mc_bore_rear)


@dataclass
class PedalBox:
    """Pedal, balance bar and driver input."""

    pedal_ratio: float              # — mechanical advantage (e.g. 6 for 6:1)
    balance_bias_front: float       # — fraction of pedal force sent to the FRONT MC (0..1)
    driver_force: float             # N — force applied by the driver at the pedal
    compliance: float = 2.5         # mm — extra MC stroke for line stretch, pad compression, etc.
    bots_margin: float = 3.5        # mm — travel beyond effective stroke at which BOTS/hardstop trips

    @property
    def balance_bias_rear(self) -> float:
        """Fraction of pedal force sent to the REAR MC (complement of the front bias)."""
        return 1.0 - self.balance_bias_front


@dataclass
class VehicleConfig:
    """Complete brake-system configuration for one vehicle."""

    name: str
    mass: MassProperties
    tires: Tires
    front_axle: Axle
    rear_axle: Axle
    rotor: Rotor
    pad: Pad
    caliper: Caliper
    hydraulics: Hydraulics
    pedal_box: PedalBox
    target_decel_g: float           # — design deceleration target [g]
    notes: str = ""
