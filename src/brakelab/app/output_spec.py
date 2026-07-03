"""Declarative description of every output, grouped by the spreadsheet's phases.

Each row knows its label, unit, the formula it comes from, a plain-English description, and a getter
that reads the value from ``(results, config)``. The outputs panel renders these uniformly with a
hover tooltip (formula + description), so nothing the engine computes is hidden and every number is
traceable to its equation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.models import VehicleConfig
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


def _o(label, unit, formula, description, getter) -> Output:
    return Output(label, unit, formula, description, getter)


GROUPS: tuple[OutputGroup, ...] = (
    OutputGroup(
        "Phase 1 — Vehicle Dynamics & Load Transfer",
        (
            _o("Vehicle weight (W)", "N", "W = M · g",
               "Total weight of the car.", lambda r, c: r.dynamics.weight),
            _o("Dynamic weight transfer (ΔW)", "N", "ΔW = W · a · h_cg / L",
               "Load shifted from the rear to the front axle under braking.", lambda r, c: r.dynamics.weight_transfer),
            _o("Front axle → CG (b)", "m", "b = L · (1 − f_front)",
               "Horizontal distance from the front axle to the CG.", lambda r, c: r.dynamics.front_axle_to_cg),
            _o("Rear axle → CG (c)", "m", "c = L · f_front",
               "Horizontal distance from the rear axle to the CG.", lambda r, c: r.dynamics.rear_axle_to_cg),
            _o("Static front axle load", "N", "W · f_front",
               "Weight on the front axle at rest.", lambda r, c: r.dynamics.static_front),
            _o("Static rear axle load", "N", "W · (1 − f_front)",
               "Weight on the rear axle at rest.", lambda r, c: r.dynamics.static_rear),
            _o("Dynamic front axle load", "N", "static_front + ΔW",
               "Front axle load during braking (gains load).", lambda r, c: r.dynamics.dynamic_front),
            _o("Dynamic rear axle load", "N", "static_rear − ΔW",
               "Rear axle load during braking (loses load).", lambda r, c: r.dynamics.dynamic_rear),
        ),
    ),
    OutputGroup(
        "Phase 2 — Tire & Torque Requirements",
        (
            _o("Max friction force, front (per wheel)", "N", "F_f,tire = (W_f,dyn / 2) · μ_tire",
               "Grip-limited braking force at one front wheel.", lambda r, c: r.torque.front.friction_force_per_wheel),
            _o("Required torque, front (per rotor)", "N·m", "T_f = 2 · F_f,tire · R_tire / (N_f · ratio)",
               "Brake torque each front rotor must produce.", lambda r, c: r.torque.front.torque_per_rotor),
            _o("Max friction force, rear (per wheel)", "N", "F_r,tire = (W_r,dyn / 2) · μ_tire",
               "Grip-limited braking force at one rear wheel.", lambda r, c: r.torque.rear.friction_force_per_wheel),
            _o("Required torque, rear (per rotor)", "N·m", "T_r = 2 · F_r,tire · R_tire / (N_r · ratio)",
               "Brake torque each rear rotor must produce (a single inboard rotor carries both wheels).",
               lambda r, c: r.torque.rear.torque_per_rotor),
        ),
    ),
    OutputGroup(
        "Phase 3 — Caliper & Rotor Sizing",
        (
            _o("Caliper clamp area (one side)", "mm²", "A_side = A_piston · n_pistons / 2",
               "Piston area on one side that generates clamp force from line pressure.",
               lambda r, c: c.caliper.one_side_area),
            _o("Required clamp force, front", "N", "F_f,clamp = T_f / (2 · μ_pad · R_eff)",
               "Clamp force each front caliper must apply.", lambda r, c: r.sizing.front.clamp_force),
            _o("Required line pressure, front", "MPa", "P_f = F_f,clamp / A_side",
               "Hydraulic pressure needed in the front circuit.", lambda r, c: r.sizing.front.line_pressure),
            _o("Required clamp force, rear", "N", "F_r,clamp = T_r / (2 · μ_pad · R_eff)",
               "Clamp force each rear caliper must apply.", lambda r, c: r.sizing.rear.clamp_force),
            _o("Required line pressure, rear", "MPa", "P_r = F_r,clamp / A_side",
               "Hydraulic pressure needed in the rear circuit.", lambda r, c: r.sizing.rear.line_pressure),
        ),
    ),
    OutputGroup(
        "Phase 4 — Master Cylinder & Pedal Box",
        (
            _o("MC area, front", "mm²", "A_f,mc = π · (d_f / 2)²",
               "Bore area of the front master cylinder.", lambda r, c: c.hydraulics.mc_area_front),
            _o("MC area, rear", "mm²", "A_r,mc = π · (d_r / 2)²",
               "Bore area of the rear master cylinder.", lambda r, c: c.hydraulics.mc_area_rear),
            _o("MC force required, front", "N", "F_f,mc = P_f · A_f,mc",
               "Force needed at the front master cylinder.", lambda r, c: r.hydraulics.mc_force_front),
            _o("MC force required, rear", "N", "F_r,mc = P_r · A_r,mc",
               "Force needed at the rear master cylinder.", lambda r, c: r.hydraulics.mc_force_rear),
            _o("Pedal force needed for front", "N", "F_bar,front = F_f,mc / bias_front",
               "Total pedal force whose front share meets the front requirement.",
               lambda r, c: r.hydraulics.bar_force_front),
            _o("Pedal force needed for rear", "N", "F_bar,rear = F_r,mc / bias_rear",
               "Total pedal force whose rear share meets the rear requirement.",
               lambda r, c: r.hydraulics.bar_force_rear),
            _o("Pedal force delivered", "N", "F_pedal = F_driver · pedal_ratio",
               "Force the driver's input actually delivers to the balance bar.",
               lambda r, c: r.hydraulics.pedal_force),
            _o("Optimal front bias", "-", "bias* = F_f,mc / (F_f,mc + F_r,mc)",
               "Front bias that balances the front/rear demands exactly (compare to the 65:35 limit).",
               lambda r, c: r.hydraulics.optimal_bias_front),
        ),
    ),
    OutputGroup(
        "Phase 5 — Pedal Travel",
        (
            _o("Total piston area, front", "mm²", "N_f · A_piston · n_pistons",
               "Total front caliper piston area fed by fluid (both sides).",
               lambda r, c: r.pedal_travel.total_piston_area_front),
            _o("Total piston area, rear", "mm²", "N_r · A_piston · n_pistons",
               "Total rear caliper piston area fed by fluid (both sides).",
               lambda r, c: r.pedal_travel.total_piston_area_rear),
            _o("Fluid volume, front", "mm³", "V_f = A_pistons,front · piston_travel",
               "Fluid the front circuit must displace to take up pad clearance.",
               lambda r, c: r.pedal_travel.volume_front),
            _o("Fluid volume, rear", "mm³", "V_r = A_pistons,rear · piston_travel",
               "Fluid the rear circuit must displace.", lambda r, c: r.pedal_travel.volume_rear),
            _o("MC stroke, front", "mm", "stroke_f = V_f / A_f,mc",
               "Front master-cylinder stroke required.", lambda r, c: r.pedal_travel.mc_stroke_front),
            _o("MC stroke, rear", "mm", "stroke_r = V_r / A_r,mc",
               "Rear master-cylinder stroke required.", lambda r, c: r.pedal_travel.mc_stroke_rear),
            _o("Theoretical effective stroke", "mm", "(stroke_f + stroke_r) / 2",
               "Average MC stroke before the compliance allowance.",
               lambda r, c: r.pedal_travel.theoretical_effective_stroke),
            _o("Effective stroke (with compliance)", "mm", "effective + compliance",
               "Effective stroke after adding the compliance allowance.",
               lambda r, c: r.pedal_travel.effective_stroke),
            _o("Pedal travel", "mm", "travel = effective_stroke · pedal_ratio",
               "Movement at the pedal. Comfortable range ≈ 30–60 mm.",
               lambda r, c: r.pedal_travel.pedal_travel),
            _o("BOTS trigger (MC stroke)", "mm", "effective_stroke + BOTS margin",
               "MC stroke at which the brake-over-travel switch / hardstop should trip.",
               lambda r, c: r.pedal_travel.bots_trigger),
        ),
    ),
)
