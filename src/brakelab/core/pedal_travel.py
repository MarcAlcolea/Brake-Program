"""Pedal travel — fluid volume, master-cylinder stroke and pedal movement.

Taking up pad clearance requires displacing a fluid volume ``V = A_pistons · piston_travel`` for
each axle (all pistons on all of that axle's calipers). The master cylinder must sweep that volume,
so its stroke is ``V / A_mc``. Averaging the two axles, adding a compliance allowance, and
multiplying by the pedal ratio gives pedal travel:

    V_axle   = n_rotors · A_displacing · piston_travel
    stroke   = V_axle / A_mc
    eff      = mean(stroke_front, stroke_rear) + compliance
    travel   = eff · pedal_ratio
    bots     = eff + bots_margin

The compliance term is always applied (the spreadsheet applied it on one sheet but not the other;
the engine is consistent). Pedal travel of ~30–60 mm is generally desirable.
"""

from __future__ import annotations

from .models import Axle, Caliper, Hydraulics, PedalBox
from .results import PedalTravelResult


def solve_pedal_travel(
    caliper: Caliper,
    front_axle: Axle,
    rear_axle: Axle,
    hydraulics: Hydraulics,
    pedal_box: PedalBox,
) -> PedalTravelResult:
    """Fluid volume, MC stroke, and pedal travel."""
    total_area_front = front_axle.n_rotors * caliper.displacing_area
    total_area_rear = rear_axle.n_rotors * caliper.displacing_area
    volume_front = total_area_front * caliper.piston_travel
    volume_rear = total_area_rear * caliper.piston_travel

    stroke_front = volume_front / hydraulics.mc_area_front
    stroke_rear = volume_rear / hydraulics.mc_area_rear

    theoretical_effective_stroke = (stroke_front + stroke_rear) / 2.0
    effective_stroke = theoretical_effective_stroke + pedal_box.compliance
    pedal_travel = effective_stroke * pedal_box.pedal_ratio
    bots_trigger = effective_stroke + pedal_box.bots_margin

    return PedalTravelResult(
        total_piston_area_front=total_area_front,
        total_piston_area_rear=total_area_rear,
        volume_front=volume_front,
        volume_rear=volume_rear,
        mc_stroke_front=stroke_front,
        mc_stroke_rear=stroke_rear,
        theoretical_effective_stroke=theoretical_effective_stroke,
        effective_stroke=effective_stroke,
        pedal_travel=pedal_travel,
        bots_trigger=bots_trigger,
    )
