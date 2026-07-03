"""Phase 1 — vehicle dynamics and longitudinal load transfer.

Under braking, load transfers from the rear axle to the front. The static split is set by the
CG position; the transfer is ``ΔW = W·a·h/L`` (with ``a`` in g, ``W = m·g`` gives ``ΔW = m·a·h/L``).

Audit **B1**: axle loads are derived from a single ``front_weight_fraction`` so the loads can never
disagree with the CG geometry. Front axle load is the fraction of weight on the front (by
definition), and the CG distances are back-derived for reporting:

    static_front = W · f_front
    static_rear  = W · (1 - f_front)
    b (front-axle → CG) = L · (1 - f_front)     # CG sits closer to the heavier axle
    c (rear-axle  → CG) = L · f_front
"""

from __future__ import annotations

from .models import MassProperties, Tires
from .results import DynamicsResult
from .units import GRAVITY


def solve_dynamics(
    mass: MassProperties, target_decel_g: float, gravity: float = GRAVITY
) -> DynamicsResult:
    """Compute weight, load transfer, and static/dynamic axle loads."""
    weight = mass.total_mass * gravity
    weight_transfer = weight * target_decel_g * mass.cg_height / mass.wheelbase

    f_front = mass.front_weight_fraction
    static_front = weight * f_front
    static_rear = weight * (1.0 - f_front)

    # Distances back-derived from the weight split so geometry and loads stay consistent.
    front_axle_to_cg = mass.wheelbase * (1.0 - f_front)
    rear_axle_to_cg = mass.wheelbase * f_front

    return DynamicsResult(
        weight=weight,
        weight_transfer=weight_transfer,
        front_axle_to_cg=front_axle_to_cg,
        rear_axle_to_cg=rear_axle_to_cg,
        static_front=static_front,
        static_rear=static_rear,
        dynamic_front=static_front + weight_transfer,
        dynamic_rear=static_rear - weight_transfer,
    )
