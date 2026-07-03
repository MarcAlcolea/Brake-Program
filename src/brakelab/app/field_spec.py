"""Declarative description of the editable inputs, grouped into panels.

Adding an input to the GUI is a one-line edit here — no widget code. Each field names the config
path it binds to, a label, unit, widget kind, and range. Panels build themselves from this spec.
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


@dataclass(frozen=True)
class Group:
    title: str
    fields: tuple[Field, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "Mass & Dynamics",
        (
            Field("mass.total_mass", "Total mass", "kg", "float", 50, 1000, 1, 1),
            Field("mass.cg_height", "CG height", "m", "float", 0.1, 1.0, 0.005, 4),
            Field("mass.wheelbase", "Wheelbase", "m", "float", 1.0, 3.0, 0.005, 4),
            Field("mass.front_weight_fraction", "Front weight fraction", "-", "float", 0.3, 0.7, 0.01, 3),
            Field("target_decel_g", "Target deceleration", "g", "float", 0.1, 3.0, 0.05, 2),
        ),
    ),
    Group(
        "Tires",
        (
            Field("tires.friction_coefficient", "Tire friction coeff.", "-", "float", 0.5, 2.5, 0.05, 2),
            Field("tires.loaded_radius", "Loaded radius", "m", "float", 0.15, 0.35, 0.002, 3),
        ),
    ),
    Group(
        "Axles",
        (
            Field("front_axle.n_rotors", "Front rotors", "-", "int", 1, 4, 1),
            Field("rear_axle.n_rotors", "Rear rotors", "-", "int", 1, 4, 1),
            Field("rear_axle.inboard", "Rear inboard", "", "bool"),
            Field("rear_axle.driveline_ratio", "Rear driveline ratio", "-", "float", 0.1, 6.0, 0.1, 3),
        ),
    ),
    Group(
        "Rotor, Pad & Caliper",
        (
            Field("rotor.effective_radius", "Rotor effective radius", "m", "float", 0.03, 0.2, 0.001, 4),
            Field("pad.friction_coefficient", "Pad friction coeff. (one pad)", "-", "float", 0.2, 0.8, 0.01, 3),
            Field("caliper.piston_area", "Caliper piston area", "mm²", "float", 100, 2000, 1, 2),
            Field("caliper.n_pistons", "Pistons per caliper", "-", "int", 1, 8, 1),
            Field("caliper.piston_travel", "Piston travel", "mm", "float", 0.05, 3.0, 0.05, 3),
        ),
    ),
    Group(
        "Master Cylinders & Pedal",
        (
            Field("hydraulics.mc_bore_front", "Front MC bore", "mm", "float", 10, 30, 0.1, 3),
            Field("hydraulics.mc_bore_rear", "Rear MC bore", "mm", "float", 10, 30, 0.1, 3),
            Field("pedal_box.pedal_ratio", "Pedal ratio", "-", "float", 2, 10, 0.1, 2),
            Field("pedal_box.balance_bias_front", "Front balance bias", "-", "float", 0.35, 0.65, 0.01, 2),
            Field("pedal_box.driver_force", "Driver force", "N", "float", 50, 1000, 10, 1),
            Field("pedal_box.compliance", "Compliance allowance", "mm", "float", 0, 10, 0.5, 2),
        ),
    ),
)
