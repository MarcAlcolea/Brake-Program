"""Forward performance simulator — from a driver pedal force, what does the car actually do?

The main calculation runs *backward*: pick a target deceleration and size everything to meet it.
This module runs the same physics *forward* so a driver pedal force can be turned into an actual
deceleration and, crucially, a tyre lock-up check for tuning balance-bar bias and master-cylinder
bores.

The flow is strictly one-directional so there is no circular reference (a real trap here, because
lock-up depends on weight transfer, which depends on deceleration, which depends on brake torque):

    pedal force
      → line pressure         P = (F_pedal · bias) / A_mc                       (Step A)
      → clamp force           F_clamp = P · A_one_side                          (Step B)
      → brake torque/rotor    T_rotor = F_clamp · (2 · μ_pad · R_eff)           (Step C)
      → axle brake torque     T_axle  = T_rotor · n_rotors · driveline_ratio
      → stopping force        F_stop  = (T_axle,f + T_axle,r) / R_tyre          (Step D)
      → actual deceleration   a = F_stop / (m · g)                             (Step E)
      → dynamic axle loads    ΔW = m·g·a·h/L  (uses the *actual* a, not target) (Step F)
      → grip torque           T_grip = W_dyn · μ_tyre · R_tyre                  (Step G)
      → lock-up               locked if T_axle > T_grip                         (Step H)

These reuse exactly the constants of the backward phases (``2·μ_pad·R_eff`` from
:mod:`brakes`, the ``n_rotors · driveline_ratio`` axle factor from :mod:`tires`, and the
``ΔW = m·g·a·h/L`` transfer from :mod:`dynamics`), so at the grip-limited design point the forward
axle brake torque equals the tyre grip torque exactly.
"""

from __future__ import annotations

import copy

from .models import VehicleConfig
from .results import ForwardResult
from .units import GRAVITY


def _utilization(axle_brake_torque: float, grip_torque: float) -> float:
    """Fraction of the tyre's grip torque the brakes are using (>= 1 means lock-up).

    If the axle has lifted (grip <= 0) it is fully over its limit; report a large finite number so it
    formats cleanly and sorts as 'locked'."""
    if grip_torque <= 1e-9:
        return 9.99
    return axle_brake_torque / grip_torque


def _optimal_bias_front(config: VehicleConfig, gravity: float) -> float:
    """Balance-bar front bias at which the front and rear axles reach their grip limit together.

    Found by bisection on the utilisation difference (front − rear), which is monotonic in bias, over
    the achievable balance-bar range. This is the bias that maximises deceleration before either axle
    locks — the 'optimal' the user tunes toward. If the ideal split lies outside the balance-bar's
    reach (a 65:35 hardware limit), the nearest achievable bias is returned — a signal that the MC
    bores, not the bias, need changing."""
    lo, hi = 0.35, 0.65  # achievable balance-bar range (max 65:35 either way)

    def diff(bias: float) -> float:
        trial = copy.deepcopy(config)
        trial.pedal_box.balance_bias_front = bias
        r = solve_forward(trial, gravity, with_optimal=False)
        return r.front_utilization - r.rear_utilization

    f_lo, f_hi = diff(lo), diff(hi)
    if f_lo * f_hi > 0:  # no crossing in range — return the closer-to-balanced end
        return lo if abs(f_lo) < abs(f_hi) else hi
    for _ in range(40):
        mid = (lo + hi) / 2.0
        f_mid = diff(mid)
        if abs(f_mid) < 1e-6:
            return mid
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def solve_forward(config: VehicleConfig, gravity: float = GRAVITY, with_optimal: bool = True) -> ForwardResult:
    """Run the forward performance/lock-up calculation for ``config``.

    ``with_optimal`` is set False for the internal bias sweep so the optimal-bias search does not
    recurse into itself."""
    pb = config.pedal_box
    hyd = config.hydraulics
    cal = config.caliper
    pad = config.pad
    rotor = config.rotor
    fa, ra = config.front_axle, config.rear_axle
    tyres = config.tires
    mass = config.mass

    # Step A — line pressure produced at each master cylinder [MPa = N/mm²].
    pedal_force = pb.driver_force * pb.pedal_ratio
    mc_force_front = pedal_force * pb.balance_bias_front
    mc_force_rear = pedal_force * pb.balance_bias_rear
    line_pressure_front = mc_force_front / hyd.mc_area_front
    line_pressure_rear = mc_force_rear / hyd.mc_area_rear

    # Step B — clamp force at one caliper (pressure acting on the one-side piston area) [N].
    clamp_force_front = line_pressure_front * cal.one_side_area
    clamp_force_rear = line_pressure_rear * cal.one_side_area

    # Step C — actual brake torque at one rotor; the factor of two is for both pad faces [N·m].
    two_mu_r = 2.0 * pad.friction_coefficient * rotor.effective_radius
    brake_torque_front = clamp_force_front * two_mu_r
    brake_torque_rear = clamp_force_rear * two_mu_r

    # Total brake torque delivered at the wheels of each axle (rotors × driveline reduction).
    axle_brake_torque_front = brake_torque_front * fa.n_rotors * fa.driveline_ratio
    axle_brake_torque_rear = brake_torque_rear * ra.n_rotors * ra.driveline_ratio

    # Step D — total longitudinal stopping force at the tyre contact patches [N].
    r_tyre = tyres.loaded_radius
    stopping_force = (axle_brake_torque_front + axle_brake_torque_rear) / r_tyre

    # Step E — resulting deceleration [g].
    weight = mass.total_mass * gravity
    actual_decel_g = stopping_force / weight if weight > 0 else 0.0

    # Step F — dynamic axle loads at the ACTUAL deceleration (same transfer law as the backward run).
    # Clamp the transfer so an axle never carries a negative load: under very hard braking the rear
    # can lift, but its load bottoms out at zero (all weight on the front), it does not go negative.
    static_front = weight * mass.front_weight_fraction
    static_rear = weight * (1.0 - mass.front_weight_fraction)
    raw_transfer = weight * actual_decel_g * mass.cg_height / mass.wheelbase
    transfer = max(0.0, min(raw_transfer, static_rear))
    dynamic_front = static_front + transfer
    dynamic_rear = static_rear - transfer

    # Step G — the most brake torque each axle's tyres can take before skidding [N·m].
    grip_torque_front = dynamic_front * tyres.friction_coefficient * r_tyre
    grip_torque_rear = dynamic_rear * tyres.friction_coefficient * r_tyre

    # Step H — lock-up when the axle's brake torque exceeds its grip torque.
    front_locked = axle_brake_torque_front > grip_torque_front
    rear_locked = axle_brake_torque_rear > grip_torque_rear

    front_utilization = _utilization(axle_brake_torque_front, grip_torque_front)
    rear_utilization = _utilization(axle_brake_torque_rear, grip_torque_rear)
    optimal_bias_front = _optimal_bias_front(config, gravity) if with_optimal else 0.0

    return ForwardResult(
        pedal_force=pedal_force,
        mc_force_front=mc_force_front,
        mc_force_rear=mc_force_rear,
        line_pressure_front=line_pressure_front,
        line_pressure_rear=line_pressure_rear,
        clamp_force_front=clamp_force_front,
        clamp_force_rear=clamp_force_rear,
        brake_torque_front=brake_torque_front,
        brake_torque_rear=brake_torque_rear,
        axle_brake_torque_front=axle_brake_torque_front,
        axle_brake_torque_rear=axle_brake_torque_rear,
        stopping_force=stopping_force,
        actual_decel_g=actual_decel_g,
        dynamic_front=dynamic_front,
        dynamic_rear=dynamic_rear,
        grip_torque_front=grip_torque_front,
        grip_torque_rear=grip_torque_rear,
        front_utilization=front_utilization,
        rear_utilization=rear_utilization,
        optimal_bias_front=optimal_bias_front,
        front_locked=front_locked,
        rear_locked=rear_locked,
    )
