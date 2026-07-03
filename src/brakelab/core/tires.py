"""Phase 2 — tire grip and required brake torque.

The most a wheel can brake is set by tire grip: ``F_wheel = (axle_load / 2) · μ_tire``. The brake
torque that must be produced at each rotor is that force times the tire radius, with the total
axle torque (two wheels) distributed over the axle's rotors:

    T_per_rotor = 2 · F_wheel · R_tire / (n_rotors · driveline_ratio)

- ``n_rotors = 2`` (outboard) gives the per-wheel torque.
- ``n_rotors = 1`` (inboard) gives the full axle torque on the single rotor (audit **B2** case).
- ``driveline_ratio > 1`` reduces required brake torque when the rotor spins faster than the wheel
  (mounted before the final-drive reduction) — audit **B7**; default 1.0.
"""

from __future__ import annotations

from .models import Axle, Tires
from .results import AxleTorqueResult, DynamicsResult, TorqueResult


def _axle_torque(axle_load: float, tires: Tires, axle: Axle) -> AxleTorqueResult:
    friction_force_per_wheel = (axle_load / 2.0) * tires.friction_coefficient
    torque_per_rotor = (
        2.0
        * friction_force_per_wheel
        * tires.loaded_radius
        / (axle.n_rotors * axle.driveline_ratio)
    )
    return AxleTorqueResult(
        friction_force_per_wheel=friction_force_per_wheel,
        torque_per_rotor=torque_per_rotor,
    )


def solve_torque(
    dynamics: DynamicsResult, tires: Tires, front_axle: Axle, rear_axle: Axle
) -> TorqueResult:
    """Grip-limited braking force and required per-rotor torque for both axles."""
    return TorqueResult(
        front=_axle_torque(dynamics.dynamic_front, tires, front_axle),
        rear=_axle_torque(dynamics.dynamic_rear, tires, rear_axle),
    )
