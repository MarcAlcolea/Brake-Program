"""Brake balance diagram — front vs. rear brake force, the classic brake-design chart.

Everything is expressed as brake force at the tyre contact patch [N], front on the x-axis and rear on
the y-axis.

- **Ideal distribution (parabola):** the locus of (F_front, F_rear) that puts *both* axles exactly at
  their grip limit at the same deceleration ``a`` (in g). At deceleration ``a`` the dynamic axle loads
  are ``W_f = W(χ + a·h/L)`` and ``W_r = W((1−χ) − a·h/L)``, and the force that uses each axle's grip
  is ``a·W_f`` / ``a·W_r``. Eliminating ``a`` traces the parabola. Above it the rear is over-braked
  (rear locks first, unstable); below it the front locks first (stable understeer).
- **Actual line:** the real brake system produces a *fixed* front:rear force ratio (set by bias, MC
  bores, rotors, pads, caliper, driveline), so as pedal force rises you travel out a straight line
  through the origin. Its slope is the forward simulator's rear/front axle-torque ratio.
- **Lock-up:** walking out the actual line, whichever axle reaches its grip limit first is the one
  that locks; the deceleration there is the usable limit. Front-locks-first is the safe outcome.

Pure — no Qt, no IO — so the GUI chart, the report chart and tests all share it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .forward import solve_forward
from .models import VehicleConfig
from .units import GRAVITY


@dataclass(frozen=True)
class BalanceDiagram:
    ideal_front: list[float]      # N — ideal-distribution parabola
    ideal_rear: list[float]
    actual_front: list[float]     # N — actual fixed-ratio line (origin outward)
    actual_rear: list[float]
    op_front: float               # N — operating point at the design pedal force
    op_rear: float
    weight: float                 # N — total vehicle weight (for the iso-deceleration lines)
    iso_decels: tuple[float, ...]  # g — deceleration lines to draw (F_f + F_r = a·W)
    front_locks_first: bool
    lock_decel_front: float       # g at which the front axle locks along the actual line (inf if never)
    lock_decel_rear: float        # g at which the rear axle locks along the actual line
    usable_decel: float           # g at the first axle to lock — the balanced limit


def _axle_lock_decel(mu: float, weight: float, chi: float, h: float, L: float,
                     k: float, front: bool) -> float:
    """Deceleration [g] at which one axle reaches its grip limit while travelling the actual line.

    ``k`` is the rear:front force ratio (slope of the actual line). ``front`` selects the axle.
    Returns ``inf`` when that axle cannot become the limiting one (its lock never occurs first)."""
    slope_term = mu * h * (1.0 + k) / L
    if front:
        denom = 1.0 - slope_term
        if denom <= 0.0:
            return float("inf")  # front is never grip-limited before the rear lifts
        f_front = mu * weight * chi / denom
        return f_front * (1.0 + k) / weight
    # rear
    denom = k + slope_term
    if denom <= 0.0:
        return float("inf")
    f_front = mu * weight * (1.0 - chi) / denom
    return f_front * (1.0 + k) / weight


def brake_balance(config: VehicleConfig, gravity: float = GRAVITY, points: int = 60) -> BalanceDiagram:
    """Build the brake-balance diagram data for ``config``."""
    m = config.mass
    weight = m.total_mass * gravity
    chi = m.front_weight_fraction
    h = m.cg_height
    L = m.wheelbase
    mu = config.tires.friction_coefficient

    # Ideal-distribution parabola, from a = 0 up to the rear lift-off decel (W_r = 0).
    a_lift = (1.0 - chi) * L / h if h > 0 else 2.0
    a_max = max(a_lift, 0.05)
    ideal_front, ideal_rear = [], []
    for i in range(points + 1):
        a = a_max * i / points
        ideal_front.append(a * weight * (chi + a * h / L))
        ideal_rear.append(a * weight * ((1.0 - chi) - a * h / L))

    # Actual fixed-ratio line from the forward simulator's axle brake torques at the design pedal force.
    fwd = solve_forward(config, gravity)
    r_tyre = config.tires.loaded_radius
    op_front = fwd.axle_brake_torque_front / r_tyre if r_tyre > 0 else 0.0
    op_rear = fwd.axle_brake_torque_rear / r_tyre if r_tyre > 0 else 0.0
    k = op_rear / op_front if op_front > 1e-9 else 0.0

    lock_front = _axle_lock_decel(mu, weight, chi, h, L, k, front=True)
    lock_rear = _axle_lock_decel(mu, weight, chi, h, L, k, front=False)
    front_first = lock_front <= lock_rear
    usable = min(lock_front, lock_rear)

    # Draw the actual line a little past whichever comes first: the operating point or the lock point.
    f_at_lock = usable * weight / (1.0 + k) if usable != float("inf") else op_front
    f_extent = max(op_front, f_at_lock) * 1.15 + 1e-6
    actual_front = [f_extent * i / points for i in range(points + 1)]
    actual_rear = [k * f for f in actual_front]

    # Iso-deceleration lines to overlay (skip any at/above rear lift-off, and de-duplicate).
    candidates = sorted({round(a, 3) for a in (0.5, 1.0, config.target_decel_g) if 0 < a < a_max})

    return BalanceDiagram(
        ideal_front=ideal_front,
        ideal_rear=ideal_rear,
        actual_front=actual_front,
        actual_rear=actual_rear,
        op_front=op_front,
        op_rear=op_rear,
        weight=weight,
        iso_decels=tuple(candidates),
        front_locks_first=front_first,
        lock_decel_front=lock_front,
        lock_decel_rear=lock_rear,
        usable_decel=usable,
    )
