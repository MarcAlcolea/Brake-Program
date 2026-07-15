"""Stopping distance and time from a deceleration — a constant-deceleration (flat-profile) model.

Given a braking deceleration (either the *design target* from the backward calc or the *actual*
achievable value from the forward simulator) and a start/end speed, this returns how far the car
travels and how long it takes to slow down:

    distance = (v_i² − v_f²) / (2·a)        time = (v_i − v_f) / a        a = decel_g · g

The deceleration is assumed constant over the stop (a good first approximation; real decel builds up
and tails off). Pure — no Qt, no IO — so it is reused by the outputs, the report graph and tests.
"""

from __future__ import annotations

from .models import VehicleConfig
from .units import GRAVITY


def braking_speeds(config: VehicleConfig) -> tuple[float, float]:
    """(initial, final) speed [m/s] for the stopping estimate; final is 0 when stopping to rest."""
    p = config.performance
    return p.initial_speed, (p.final_speed if p.custom_final_speed else 0.0)


def stopping_distance_time(initial_speed: float, final_speed: float, decel_g: float,
                           gravity: float = GRAVITY) -> tuple[float, float]:
    """Distance [m] and time [s] to slow from ``initial_speed`` to ``final_speed`` at ``decel_g`` g.

    Returns ``(inf, inf)`` if the deceleration is non-positive (the car never stops)."""
    a = decel_g * gravity
    if a <= 0.0:
        return float("inf"), float("inf")
    vi = max(initial_speed, 0.0)
    vf = min(max(final_speed, 0.0), vi)
    distance = (vi * vi - vf * vf) / (2.0 * a)
    time = (vi - vf) / a
    return distance, time


def stopping_from_config(config: VehicleConfig, decel_g: float,
                         gravity: float = GRAVITY) -> tuple[float, float]:
    """Stopping distance [m] and time [s] for ``config``'s braking-test speeds at ``decel_g`` g."""
    vi, vf = braking_speeds(config)
    return stopping_distance_time(vi, vf, decel_g, gravity)


def speed_profile(initial_speed: float, final_speed: float, decel_g: float,
                  gravity: float = GRAVITY, n: int = 60) -> tuple[list[float], list[float]]:
    """(distance[m], speed[m/s]) points along a constant-decel stop, for a speed-vs-distance plot."""
    a = decel_g * gravity
    if a <= 0:
        return [0.0], [max(initial_speed, 0.0)]
    vi = max(initial_speed, 0.0)
    vf = min(max(final_speed, 0.0), vi)
    total = (vi * vi - vf * vf) / (2.0 * a)
    xs, vs = [], []
    for i in range(n + 1):
        x = total * i / n
        v2 = max(vi * vi - 2.0 * a * x, 0.0)
        xs.append(x)
        vs.append(v2 ** 0.5)
    return xs, vs
