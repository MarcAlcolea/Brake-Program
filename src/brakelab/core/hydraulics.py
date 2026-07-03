"""Phase 4 — master cylinder, balance bar and pedal box.

The force each master cylinder must produce is ``F_mc = P_line · A_mc``. The balance bar splits the
pedal force between the two MCs by the bias, so the pedal force needed to satisfy an axle is
``F_mc / bias``. The pedal delivers ``F_pedal = F_driver · pedal_ratio``. An axle's requirement is
met when the delivered pedal force is at least the force that axle needs:

    F_mc      = P_line · A_mc
    F_bar     = F_mc / bias                      # pedal force needed for this axle
    F_pedal   = F_driver · pedal_ratio
    met       = F_pedal >= F_bar

``optimal_bias_front`` is the front bias that makes the front and rear demands equal (the ideal
split); comparing it to the achievable balance-bar range is a useful design insight (audit **B9**).
"""

from __future__ import annotations

from .models import Hydraulics, PedalBox
from .results import HydraulicsResult, SizingResult


def solve_hydraulics(
    sizing: SizingResult, hydraulics: Hydraulics, pedal_box: PedalBox
) -> HydraulicsResult:
    """Master-cylinder forces, balance-bar demand, pedal force and feasibility."""
    mc_force_front = sizing.front.line_pressure * hydraulics.mc_area_front
    mc_force_rear = sizing.rear.line_pressure * hydraulics.mc_area_rear

    bias_front = pedal_box.balance_bias_front
    bias_rear = pedal_box.balance_bias_rear

    bar_force_front = mc_force_front / bias_front
    bar_force_rear = mc_force_rear / bias_rear

    pedal_force = pedal_box.driver_force * pedal_box.pedal_ratio

    total_mc = mc_force_front + mc_force_rear
    optimal_bias_front = mc_force_front / total_mc if total_mc > 0 else 0.5

    return HydraulicsResult(
        mc_force_front=mc_force_front,
        mc_force_rear=mc_force_rear,
        bar_force_front=bar_force_front,
        bar_force_rear=bar_force_rear,
        pedal_force=pedal_force,
        front_requirement_met=pedal_force >= bar_force_front,
        rear_requirement_met=pedal_force >= bar_force_rear,
        optimal_bias_front=optimal_bias_front,
    )
