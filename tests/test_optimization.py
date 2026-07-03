"""Tests for the optimization search."""

from __future__ import annotations

from brakelab.core import BrakeEngine
from brakelab.core.attrpath import get_by_path
from brakelab.analyses import GOALS, OptVariable, optimize
from brakelab import reference_configs as rc

VARIABLES = [
    OptVariable("hydraulics.mc_bore_front", "MC front", "mm", 12.0, 25.4),
    OptVariable("hydraulics.mc_bore_rear", "MC rear", "mm", 12.0, 25.4),
    OptVariable("pedal_box.pedal_ratio", "Pedal ratio", "-", 3.5, 7.0),
    OptVariable("pedal_box.balance_bias_front", "Bias", "-", 0.35, 0.65),
]


def _required_force(engine, cfg):
    r = engine.solve(cfg)
    return max(r.hydraulics.bar_force_front, r.hydraulics.bar_force_rear) / cfg.pedal_box.pedal_ratio


def test_least_effort_reduces_required_force():
    engine = BrakeEngine()
    base = rc.outboarded_x2()
    before = _required_force(engine, base)
    res = optimize(base, VARIABLES, "Least driver effort", engine, iterations=2000)
    after = _required_force(engine, res.config)
    assert after < before
    assert res.improved


def test_result_respects_bounds():
    engine = BrakeEngine()
    res = optimize(rc.outboarded_x2(), VARIABLES, "Least driver effort", engine, iterations=1500)
    for var in VARIABLES:
        value = get_by_path(res.config, var.path)
        assert var.minimum - 1e-9 <= value <= var.maximum + 1e-9


def test_balanced_goal_equalizes_axles():
    engine = BrakeEngine()
    res = optimize(rc.outboarded_x2(), VARIABLES, "Balanced front/rear braking", engine, iterations=2000)
    r = engine.solve(res.config)
    assert abs(r.hydraulics.bar_force_front - r.hydraulics.bar_force_rear) < 25.0


def test_no_variables_is_graceful():
    res = optimize(rc.outboarded_x2(), [], "Least driver effort", BrakeEngine())
    assert res.values == {}
    assert res.messages


def test_all_goals_run():
    engine = BrakeEngine()
    for goal in GOALS:
        res = optimize(rc.outboarded_x2(), VARIABLES, goal, engine, iterations=800)
        assert res.config is not None
