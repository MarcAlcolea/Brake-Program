"""Declarative description of the editable inputs.

Labels, symbols and notes are taken verbatim from the original "Braking Calculations" spreadsheet
so the tool matches what the team already uses. ``unit`` is the canonical unit the value is stored
in; the GUI lets each number be shown in any compatible unit (metric default). ``note`` is the
spreadsheet's own comment for that input, shown in the in-app details area when its ⓘ is clicked.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    path: str            # dotted config path, e.g. "mass.total_mass"
    label: str           # original spreadsheet variable name (with symbol)
    unit: str = ""       # canonical unit the value is stored in
    kind: str = "float"  # "float" | "int" | "bool"
    minimum: float = 0.0
    maximum: float = 1e6
    decimals: int = 3
    note: str = ""       # the spreadsheet's own comment for this input (verbatim)


@dataclass(frozen=True)
class Group:
    title: str
    fields: tuple[Field, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "Phase 1 — Vehicle Dynamics and Load Transfer",
        (
            Field("mass.total_mass", "Total Vehicle Mass (M)", "kg", "float", 50, 1000, 1,
                  "Car and driver fully equipped"),
            Field("mass.cg_height", "Height of Center of Gravity (h(cg))", "m", "float", 0.1, 1.0, 4,
                  "Center of gravity height"),
            Field("mass.wheelbase", "Wheel Base (L)", "m", "float", 1.0, 3.0, 4,
                  "Distance between axles"),
            Field("mass.front_weight_fraction", "Front weight distribution", "-", "float", 0.30, 0.70, 3,
                  "Static fraction of weight on the front axle. Derived from the b and c distances; "
                  "considering weight distrubition reccomended by Woods, doc 2. Vehicle Parameters "
                  "(suspension subteam)."),
            Field("target_decel_g", "Target Deceleration (a)", "g", "float", 0.1, 3.0, 2,
                  "e.g. 1.5 (dimensionless ratio relative to gravity)"),
        ),
    ),
    Group(
        "Phase 2 — Tire and Torque Requirements",
        (
            Field("front_axle.n_rotors", "Number of front calipers/rotors (N(f))", "-", "int", 1, 4, 0,
                  "We have two outboarded calipers on the front"),
            Field("rear_axle.n_rotors", "Number of rear calipers/rotors (N(r))", "-", "int", 1, 4, 0,
                  "We are considering ONE inboarded caliper on the rear"),
            Field("rear_axle.inboard", "Rear inboard", "", "bool", note=
                  "Program option: mark the rear as a single inboard rotor driving both wheels."),
            Field("rear_axle.driveline_ratio", "Rear driveline ratio", "-", "float", 0.1, 6.0, 3,
                  "Program option: rotor speed relative to wheel speed for an inboard rear rotor "
                  "(1.0 if the rotor turns at wheel speed)."),
            Field("tires.friction_coefficient", "Tire Friction Coeff. (mu(tire))", "-", "float", 0.5, 2.5, 2, ""),
            Field("tires.loaded_radius", "Tire Radius (Loaded) (R(tire))", "m", "float", 0.15, 0.35, 3,
                  "assumed to be 2% less than the nominal radius"),
        ),
    ),
    Group(
        "Phase 3 — Caliper and Rotor Sizing",
        (
            Field("rotor.effective_radius", "Effective Rotor Radius (R(eff))", "m", "float", 0.03, 0.2, 4,
                  "Distance from hub center to pad center. 0.177 m rotor diameter."),
            Field("pad.friction_coefficient", "Pad Friction Coeff. (mu(pad))", "-", "float", 0.2, 0.8, 3,
                  "This is the pad friction coefficient for ONE pad, not both."),
            Field("caliper.piston_area", "Area of one caliper piston (A(pc))", "mm²", "float", 100, 2000, 2,
                  "From Wilwood calipers specifications"),
            Field("caliper.n_pistons", "Number of pistons per caliper (N(pc))", "-", "int", 1, 8, 0,
                  "Wilwood calipers have two pistons per caliper"),
        ),
    ),
    Group(
        "Phase 4 — Master Cylinder and Pedal Box",
        (
            Field("hydraulics.mc_bore_front", "Master Cylinder Bore Diam (Front)", "mm", "float", 10, 30, 3,
                  "Front master-cylinder bore diameter. Switch the unit to inches to enter it as a "
                  "fraction (e.g. 5/8\" = 0.625 in)."),
            Field("hydraulics.mc_bore_rear", "Master Cylinder Bore Diam (Rear)", "mm", "float", 10, 30, 3,
                  "Rear master-cylinder bore diameter. A front/rear bore difference can be used to "
                  "perform brake bias."),
            Field("hydraulics.max_mc_stroke", "Maximum Master Cylinder Stroke", "mm", "float", 5, 60, 2,
                  "(1.1 inches), from Tilton 76 and 78 series"),
            Field("pedal_box.pedal_ratio", "Pedal Ratio (PR)", "-", "float", 2, 10, 2,
                  "Mechanical leverage (like 4:1)"),
            Field("pedal_box.balance_bias_front", "Balance Bar Bias Front (B(f))", "-", "float", 0.35, 0.65, 2,
                  "% of force directed to Front MC, it has a maximum of 65:35"),
            Field("pedal_box.driver_force", "Driver Pedal Force (F(driver))", "N", "float", 50, 1000, 1,
                  "Force exerted by the driver"),
        ),
    ),
    Group(
        "Pedal Travel",
        (
            Field("caliper.piston_travel", "Piston travel (Trav(piston))", "mm", "float", 0.05, 3.0, 3,
                  "ASSUMED"),
            Field("pedal_box.compliance", "Compliance Factor", "mm", "float", 0, 10, 2,
                  "Standard number added to MC stroke to account for brake line stretch, brake pad "
                  "compression, caliper spread, pedal box deflection, etc..."),
            Field("pedal_box.bots_margin", "BOTS margin", "mm", "float", 0, 10, 2,
                  "Eff Stroke + comp. + 3-3.5 mm"),
        ),
    ),
)
