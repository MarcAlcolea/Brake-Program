"""Brake balance diagram: geometry invariants + cross-check against the forward simulator."""

from __future__ import annotations

import copy
import math

from brakelab.core.balance import brake_balance
from brakelab.core.forward import solve_forward
from brakelab import reference_configs


def test_ideal_parabola_starts_at_origin_and_sums_to_total_force():
    c = reference_configs.outboarded_x2()
    bd = brake_balance(c, points=40)
    assert bd.ideal_front[0] == 0.0 and bd.ideal_rear[0] == 0.0
    # Along the ideal curve, front+rear brake force equals a·W; recover a at a mid point and check the
    # sum equals that deceleration's total force. Use the known parametrisation to get a at index i.
    i = 20
    a = ((1.0 - c.mass.front_weight_fraction) * c.mass.wheelbase / c.mass.cg_height) * i / 40
    assert math.isclose(bd.ideal_front[i] + bd.ideal_rear[i], a * bd.weight, rel_tol=1e-9)


def test_actual_line_is_straight_through_origin():
    c = reference_configs.outboarded_x2()
    bd = brake_balance(c, points=30)
    assert bd.actual_front[0] == 0.0 and bd.actual_rear[0] == 0.0
    # constant slope
    slopes = [r / f for f, r in zip(bd.actual_front[1:], bd.actual_rear[1:])]
    assert max(slopes) - min(slopes) < 1e-9


def _first_axle_to_lock(config):
    """Sweep pedal force upward and return ('front'|'rear') for whichever axle locks first."""
    base = config.pedal_box.driver_force
    scale = 0.2
    while scale < 60.0:
        c = copy.deepcopy(config)
        c.pedal_box.driver_force = base * scale
        r = solve_forward(c, with_optimal=False)
        if r.front_locked or r.rear_locked:
            return "front" if r.front_locked and (not r.rear_locked or r.front_utilization >= r.rear_utilization) else "rear"
        scale += 0.2
    return None


def test_lock_order_matches_forward_simulator():
    # front-biased outboarded car — start from a low pedal force so nothing is locked yet
    c = reference_configs.outboarded_x2()
    c.pedal_box.driver_force = 40.0
    bd = brake_balance(c)               # lock ORDER is independent of pedal-force magnitude
    first = _first_axle_to_lock(c)
    assert first is not None
    assert bd.front_locks_first == (first == "front")
    # the usable (first-lock) deceleration is finite and positive
    assert 0.0 < bd.usable_decel < 5.0
