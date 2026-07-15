"""Declarative description of every output, grouped by the spreadsheet's phases.

Names, symbols, formulas and notes are taken from the original "Braking Calculations" spreadsheet
(its variable, formula and notes columns) so the outputs match what the team already reads. Each row
has a getter that reads the value from ``(results, config)``. The ⓘ shows the formula and the
spreadsheet's own note in the in-app details area.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.models import VehicleConfig
from ..core.performance import stopping_from_config
from ..core.results import BrakeResults


@dataclass(frozen=True)
class Output:
    label: str
    unit: str
    formula: str
    description: str
    getter: Callable[[BrakeResults, VehicleConfig], float]


@dataclass(frozen=True)
class OutputGroup:
    title: str
    outputs: tuple[Output, ...]
    expanded: bool = True   # whether this section starts open in the Outputs panel


def _o(label, unit, formula, description, getter) -> Output:
    return Output(label, unit, formula, description, getter)


GROUPS: tuple[OutputGroup, ...] = (
    OutputGroup(
        "Phase 1 — Vehicle Dynamics and Load Transfer",
        (
            _o("Total Vehicle Weight (W)", "N", "W = M * g", "",
               lambda r, c: r.dynamics.weight),
            _o("Dynamic Weight Transfer (Delta W)", "N", "Delta W = (W * a * h(cg)) / L", "",
               lambda r, c: r.dynamics.weight_transfer),
            _o("Horizontal distance from front axle to CG (b)", "m", "b = L * (1 - front fraction)", "",
               lambda r, c: r.dynamics.front_axle_to_cg),
            _o("Horizontal distance from rear axle to CG (c)", "m", "c = L * front fraction", "",
               lambda r, c: r.dynamics.rear_axle_to_cg),
            _o("Static Front Axle Load", "N", "W * (b / L)", "",
               lambda r, c: r.dynamics.static_front),
            _o("Static Rear Axle Load", "N", "W * (c / L)", "",
               lambda r, c: r.dynamics.static_rear),
            _o("Dynamic Front Axle Load During Braking (W(f,dyn))", "N", "Static Front + Delta W", "",
               lambda r, c: r.dynamics.dynamic_front),
            _o("Dynamic Rear Axle Load During Braking (W(r,dyn))", "N", "Static Rear - Delta W", "",
               lambda r, c: r.dynamics.dynamic_rear),
        ),
        expanded=False,
    ),
    OutputGroup(
        "Phase 2 — Tire and Torque Requirements",
        (
            _o("Max Friction Force (Front) (F(f,tire))", "N", "F(f,tire) = (W(f,dyn) / 2) * mu(tire)",
               "Max friction force for ONE front wheel", lambda r, c: r.torque.front.friction_force_per_wheel),
            _o("Required Torque (Front) (T(f,req))", "N·m", "T(f,req) = F(f,tire) * R(tire) * (2 / N(f))",
               "Required torque for each front caliper to produce for wheel",
               lambda r, c: r.torque.front.torque_per_rotor),
            _o("Max Friction Force (Rear) (F(r,tire))", "N", "F(r,tire) = (W(r,dyn) / 2) * mu(tire)",
               "Max friction force for ONE rear wheel", lambda r, c: r.torque.rear.friction_force_per_wheel),
            _o("Required Torque (Rear) (T(r,req))", "N·m", "T(r,req) = F(r,tire) * R(tire) * (2 / N(r))",
               "Required torque for each rear caliper to produce for wheel",
               lambda r, c: r.torque.rear.torque_per_rotor),
        ),
        expanded=False,
    ),
    OutputGroup(
        "Phase 3 — Caliper and Rotor Sizing",
        (
            _o("Caliper Piston Area (A(cal))", "mm²", "A(cal) = A(pc) * N(pc) / 2",
               "Total piston area on ONE SIDE of the caliper", lambda r, c: c.caliper.one_side_area),
            _o("Required Clamp Force (Front) (F(f,clamp))", "N", "F(f,clamp) = T(f,req) / (2 * mu(pad) * R(eff))",
               "This uses the pad friction coefficient of ONE pad, multiplied by two for both pads. "
               "Required clamp force for each front caliper.", lambda r, c: r.sizing.front.clamp_force),
            _o("Required Line Pressure (Front) (P(f,line))", "MPa", "P(f,line) = F(f,clamp) / A(cal)",
               "Important: components in hydraulic circuit have maximum rated pressure that must not be exceeded",
               lambda r, c: r.sizing.front.line_pressure),
            _o("Required Clamp Force (Rear) (F(r,clamp))", "N", "F(r,clamp) = T(r,req) / (2 * mu(pad) * R(eff))",
               "Required clamp force for each rear caliper.", lambda r, c: r.sizing.rear.clamp_force),
            _o("Required Line Pressure (Rear) (P(r,line))", "MPa", "P(r,line) = F(r,clamp) / A(cal)",
               "Important: components in hydraulic circuit have maximum rated pressure that must not be exceeded",
               lambda r, c: r.sizing.rear.line_pressure),
        ),
        expanded=False,
    ),
    OutputGroup(
        "Phase 4 — Master Cylinder and Pedal Box",
        (
            _o("Master Cylinder Area (Front) (A(f,mc))", "mm²", "A(f,mc) = PI * (d(f) / 2)^2",
               "Area of the cylinder bore (pi * r^2). Difference in MC area between front and rear MC "
               "cylinders can be used to perform brake bias", lambda r, c: c.hydraulics.mc_area_front),
            _o("Master Cylinder Area (Rear) (A(r,mc))", "mm²", "A(r,mc) = PI * (d(r) / 2)^2",
               "Area of the cylinder bore (pi * r^2).", lambda r, c: c.hydraulics.mc_area_rear),
            _o("Master Cylinder Force Required (Front) (F(f,mc))", "N", "F(f,mc) = P(f,line) * A(f,mc)",
               "Force needed at front master cylinder to meet pressure requirements.",
               lambda r, c: r.hydraulics.mc_force_front),
            _o("Master Cylinder Force Required (Rear) (F(r,mc))", "N", "F(r,mc) = P(r,line) * A(r,mc)",
               "Force needed at rear master cylinder to meet pressure requirements.",
               lambda r, c: r.hydraulics.mc_force_rear),
            _o("Force required into Balance Bar (Front) (F(f,bar))", "N", "F(f,bar) = F(f,mc) / B(f)",
               "Force needed from the pedal into the balance bar to meet Front braking requirements "
               "(before balance bar distribution)", lambda r, c: r.hydraulics.bar_force_front),
            _o("Force required into Balance Bar (Rear) (F(r,bar))", "N", "F(r,bar) = F(r,mc) / B(r)",
               "Force needed from the pedal into the balance bar to meet rear braking requirements "
               "(before balance bar distribution)", lambda r, c: r.hydraulics.bar_force_rear),
            _o("Force produced from pedal (F(pedal))", "N", "F(pedal) = F(driver) * PR",
               "Amount of force going into the balance bar", lambda r, c: r.hydraulics.pedal_force),
        ),
        expanded=False,
    ),
    OutputGroup(
        "Pedal Travel",
        (
            _o("Total area of caliper pistons FRONT (A(f,c))", "mm²", "A(f,c) = N(f) * N(pc) * A(pc)", "",
               lambda r, c: r.pedal_travel.total_piston_area_front),
            _o("Total area of caliper pistons REAR (A(r,c))", "mm²", "A(r,c) = N(r) * N(pc) * A(pc)", "",
               lambda r, c: r.pedal_travel.total_piston_area_rear),
            _o("Volume Required FRONT (V(f))", "mm³", "V(f) = A(f,c) * Trav(piston)", "",
               lambda r, c: r.pedal_travel.volume_front),
            _o("Volume Required REAR (V(r))", "mm³", "V(r) = A(r,c) * Trav(piston)", "",
               lambda r, c: r.pedal_travel.volume_rear),
            _o("Theoretical Master Cylinder Stroke FRONT (St(f,mc))", "mm", "St(f,mc) = V(f) / A(f,mc)",
               "Volume required / MC area", lambda r, c: r.pedal_travel.mc_stroke_front),
            _o("Theoretical Master Cylinder Stroke REAR (St(r,mc))", "mm", "St(r,mc) = V(r) / A(r,mc)",
               "Volume required / MC area", lambda r, c: r.pedal_travel.mc_stroke_rear),
            _o("Theoretical Effective Stroke (St(Teff))", "mm", "St(Teff) = (St(f,mc) + St(r,mc)) / 2", "",
               lambda r, c: r.pedal_travel.theoretical_effective_stroke),
            _o("Effective Stroke with Compliance (St(Ceff))", "mm", "St(Ceff) = St(Teff) + Compliance Factor",
               "Theoretical MC stroke + compliance factor. This is the actual master-cylinder stroke "
               "consumed, and what the operational / hard-stop / mechanical limits are checked against.",
               lambda r, c: r.pedal_travel.effective_stroke),
            _o("Max Operational Stroke (St(op))", "mm", "St(op) = 40% of Max MC Stroke",
               "Largest stroke we want to use in normal operation. The healthy operating window is "
               "20–40% of the mechanical limit; this is shown at the 40% upper bound. Staying under it "
               "is a target, not a hard requirement.",
               lambda r, c: c.hydraulics.max_operational_stroke),
            _o("Hard-stop / Failure Stroke (St(hs))", "mm", "St(hs) = 50% of Max MC Stroke",
               "Stroke at which a hard stop / failure condition is reached — a fixed 50% of the "
               "mechanical limit. The effective stroke must stay below this.",
               lambda r, c: c.hydraulics.hardstop_stroke),
            _o("Absolute Mechanical Stroke Limit", "mm", "Maximum Master Cylinder Stroke (input)",
               "The master cylinder's absolute mechanical stroke limit. The effective stroke must never "
               "reach it; the operational and hard-stop limits are fractions of it.",
               lambda r, c: c.hydraulics.max_mc_stroke),
            _o("Pedal Travel (Trav(pedal))", "mm", "Trav(pedal) = St(Ceff) * PR",
               "Pedal travel between 30 and 60 mm is desirable", lambda r, c: r.pedal_travel.pedal_travel),
            _o("BOTS Trigger Point", "mm", "BOTS = St(Ceff) + BOTS margin",
               "Target value at which BOTS should trigger (also a hardstop)",
               lambda r, c: r.pedal_travel.bots_trigger),
        ),
    ),
    OutputGroup(
        "Stopping Performance (at target decel)",
        (
            _o("Stopping Distance (target)", "m", "d = (v_i^2 - v_f^2) / (2 * a),  a = target decel * g",
               "How far the car travels braking from the Initial Speed at the DESIGN target "
               "deceleration (constant-decel model). The forward Simulator shows the same figure at the "
               "actual achievable deceleration.",
               lambda r, c: stopping_from_config(c, c.target_decel_g)[0]),
            _o("Stopping Time (target)", "s", "t = (v_i - v_f) / a,  a = target decel * g",
               "How long the stop takes at the design target deceleration.",
               lambda r, c: stopping_from_config(c, c.target_decel_g)[1]),
        ),
        expanded=False,
    ),
)
