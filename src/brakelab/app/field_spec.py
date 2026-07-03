"""Declarative description of the editable inputs, grouped into panels.

Adding an input to the GUI is a one-line edit here — no widget code. Each field names the config
path it binds to, a label, unit, widget kind, range, and a ``note`` shown on hover (mirroring the
"Notes/Assumptions" columns of the original spreadsheet).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    path: str            # dotted config path, e.g. "mass.total_mass"
    label: str
    unit: str = ""
    kind: str = "float"  # "float" | "int" | "bool"
    minimum: float = 0.0
    maximum: float = 1e6
    step: float = 1.0
    decimals: int = 3
    note: str = ""       # shown on hover (the spreadsheet's note for this input)


@dataclass(frozen=True)
class Group:
    title: str
    fields: tuple[Field, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "Phase 1 — Vehicle Dynamics",
        (
            Field("mass.total_mass", "Total vehicle mass", "kg", "float", 50, 1000, 1, 1,
                  "Car and driver, fully equipped."),
            Field("mass.cg_height", "CG height", "m", "float", 0.1, 1.0, 0.005, 4,
                  "Height of the centre of gravity above the ground."),
            Field("mass.wheelbase", "Wheelbase", "m", "float", 1.0, 3.0, 0.005, 4,
                  "Distance between the front and rear axles."),
            Field("mass.front_weight_fraction", "Front weight fraction", "-", "float", 0.30, 0.70, 0.01, 3,
                  "Static fraction of the car's weight on the front axle (0.52 = 52% front). "
                  "Confirm with the suspension team; the CG distances b and c are derived from this."),
            Field("target_decel_g", "Target deceleration", "g", "float", 0.1, 3.0, 0.05, 2,
                  "Design deceleration as a multiple of g (e.g. 1.5). With tire μ = 1.5 this is the "
                  "theoretical all-tires-locked limit."),
        ),
    ),
    Group(
        "Phase 2 — Tires & Axles",
        (
            Field("tires.friction_coefficient", "Tire friction coeff. (μ)", "-", "float", 0.5, 2.5, 0.05, 2,
                  "Tire–road friction coefficient."),
            Field("tires.loaded_radius", "Tire loaded radius", "m", "float", 0.15, 0.35, 0.002, 3,
                  "Loaded rolling radius (assumed ~2% less than the nominal radius)."),
            Field("front_axle.n_rotors", "Front rotors / calipers", "-", "int", 1, 4, 1, 0,
                  "Number of rotors (calipers) on the front axle. Two outboard = one per wheel."),
            Field("rear_axle.n_rotors", "Rear rotors / calipers", "-", "int", 1, 4, 1, 0,
                  "Number of rotors on the rear axle. 2 = outboard (one per wheel); 1 = a single "
                  "inboard rotor that brakes both rear wheels."),
            Field("rear_axle.inboard", "Rear inboard", "", "bool", note=
                  "Tick if the rear uses a single inboard rotor on the driveline (informational)."),
            Field("rear_axle.driveline_ratio", "Rear driveline ratio", "-", "float", 0.1, 6.0, 0.1, 3,
                  "Rotor speed : wheel speed for an inboard rear rotor. 1.0 if the rotor turns at "
                  "wheel speed; >1 if it sits before the final-drive reduction."),
        ),
    ),
    Group(
        "Phase 3 — Rotor, Pad & Caliper",
        (
            Field("rotor.effective_radius", "Effective rotor radius (R_eff)", "m", "float", 0.03, 0.2, 0.001, 4,
                  "Distance from the hub centre to the pad centre (≈ rotor OD / 2 minus pad half-height)."),
            Field("pad.friction_coefficient", "Pad friction coeff. (μ, one pad)", "-", "float", 0.2, 0.8, 0.01, 3,
                  "Friction coefficient of ONE pad. The rotor's effective friction is 2·μ (both faces)."),
            Field("caliper.piston_area", "Caliper piston area (one piston)", "mm²", "float", 100, 2000, 1, 2,
                  "Area of ONE caliper piston, from the caliper spec."),
            Field("caliper.n_pistons", "Pistons per caliper", "-", "int", 1, 8, 1, 0,
                  "Total pistons in the caliper, counting both sides (e.g. 2 for a Wilwood GP200)."),
            Field("caliper.piston_travel", "Piston travel", "mm", "float", 0.05, 3.0, 0.05, 3,
                  "Pad-clearance take-up per application (assumed). Dominates pedal travel."),
        ),
    ),
    Group(
        "Phase 4 — Master Cylinders & Pedal",
        (
            Field("hydraulics.mc_bore_front", "Front MC bore", "mm", "float", 10, 30, 0.1, 3,
                  "Front master-cylinder bore diameter. Common sizes: 5/8\" = 15.875 mm, "
                  "0.7\" = 17.78 mm, 3/4\" = 19.05 mm."),
            Field("hydraulics.mc_bore_rear", "Rear MC bore", "mm", "float", 10, 30, 0.1, 3,
                  "Rear master-cylinder bore diameter. A front/rear bore difference is one way to set bias."),
            Field("hydraulics.max_mc_stroke", "Max MC stroke", "mm", "float", 5, 60, 0.5, 2,
                  "Maximum available master-cylinder stroke (e.g. Tilton 76/78 series = 1.1\" = 27.94 mm)."),
            Field("pedal_box.pedal_ratio", "Pedal ratio", "-", "float", 2, 10, 0.1, 2,
                  "Mechanical leverage of the pedal (e.g. 6 means 6:1)."),
            Field("pedal_box.balance_bias_front", "Front balance bias", "-", "float", 0.35, 0.65, 0.01, 2,
                  "Fraction of pedal force sent to the FRONT master cylinder. Hardware max is about 65:35."),
            Field("pedal_box.driver_force", "Driver pedal force", "N", "float", 50, 1000, 10, 1,
                  "Force applied by the driver at the pedal."),
            Field("pedal_box.compliance", "Compliance allowance", "mm", "float", 0, 10, 0.5, 2,
                  "Extra MC stroke for line stretch, pad compression, caliper spread and pedal-box "
                  "deflection. Standard allowance ≈ 2.5 mm."),
            Field("pedal_box.bots_margin", "BOTS margin", "mm", "float", 0, 10, 0.5, 2,
                  "Travel beyond the effective stroke at which the brake-over-travel switch / hardstop "
                  "should trip (≈ 3–3.5 mm)."),
        ),
    ),
)
