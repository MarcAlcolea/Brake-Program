"""Stopping distance/time model + persistence of the new Performance inputs."""

from __future__ import annotations

import math

from brakelab.core.performance import stopping_distance_time, stopping_from_config
from brakelab.persistence.config_io import config_from_dict, config_to_dict
from brakelab import reference_configs


def test_stopping_distance_time_full_stop():
    # 28 m/s, 1.3 g, to rest: a = 1.3*9.81 = 12.753 m/s²
    d, t = stopping_distance_time(28.0, 0.0, 1.3)
    assert math.isclose(d, 28.0**2 / (2 * 1.3 * 9.81), rel_tol=1e-9)
    assert math.isclose(t, 28.0 / (1.3 * 9.81), rel_tol=1e-9)


def test_stopping_to_a_final_speed():
    d, t = stopping_distance_time(30.0, 10.0, 1.0)
    a = 1.0 * 9.81
    assert math.isclose(d, (30.0**2 - 10.0**2) / (2 * a), rel_tol=1e-9)
    assert math.isclose(t, (30.0 - 10.0) / a, rel_tol=1e-9)


def test_non_positive_decel_never_stops():
    d, t = stopping_distance_time(28.0, 0.0, 0.0)
    assert math.isinf(d) and math.isinf(t)


def test_final_speed_clamped_to_initial():
    # asking to "slow" to a higher speed yields zero distance/time, never negative
    d, t = stopping_distance_time(10.0, 20.0, 1.0)
    assert d == 0.0 and t == 0.0


def test_stopping_from_config_uses_toggle():
    c = reference_configs.outboarded_x2()
    c.performance.initial_speed = 30.0
    c.performance.stop_to_rest = False
    c.performance.final_speed = 12.0
    d, _ = stopping_from_config(c, 1.2)
    d_ref, _ = stopping_distance_time(30.0, 12.0, 1.2)
    assert math.isclose(d, d_ref, rel_tol=1e-12)


def test_performance_round_trips_through_json():
    c = reference_configs.outboarded_x2()
    c.performance.initial_speed = 33.3
    c.performance.stop_to_rest = False
    c.performance.final_speed = 8.0
    back = config_from_dict(config_to_dict(c))
    assert back.performance.initial_speed == 33.3
    assert back.performance.stop_to_rest is False
    assert back.performance.final_speed == 8.0


def test_old_config_without_performance_still_loads():
    c = reference_configs.outboarded_x2()
    data = config_to_dict(c)
    del data["performance"]  # simulate a config saved before the feature existed
    back = config_from_dict(data)
    assert back.performance.initial_speed == 28.0  # default
    assert back.performance.stop_to_rest is True
