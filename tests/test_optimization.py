"""Tests for the optimization subsystem."""

from __future__ import annotations

from brakelab.core.attrpath import get_by_path
from brakelab import reference_configs as rc
from brakelab.optimization import (
    Constraint,
    Objective,
    Op,
    OptimizationProblem,
    OptimizationRunner,
    Sense,
    Settings,
    Variable,
    sensitivity,
)
from brakelab.optimization.metrics import METRICS

VARIABLES = [
    Variable("hydraulics.mc_bore_front", "MC front", "mm", 12.0, 25.4),
    Variable("hydraulics.mc_bore_rear", "MC rear", "mm", 12.0, 25.4),
    Variable("pedal_box.pedal_ratio", "Pedal ratio", "-", 3.5, 7.0),
    Variable("pedal_box.balance_bias_front", "Bias", "-", 0.35, 0.65),
]


def _problem(**kw):
    return OptimizationProblem(
        variables=list(VARIABLES),
        objectives=[Objective("required_driver_force", Sense.MIN)],
        constraints=[
            Constraint("brake_bias_front", Op.RANGE, 0.35, 0.65),
            Constraint("pedal_travel", Op.RANGE, 30.0, 60.0),
            Constraint("mc_stroke_headroom", Op.GE, 0.0, None),
        ],
        settings=Settings(iterations=1500, alternatives=5, **kw),
    )


def test_returns_ranked_feasible_designs():
    res = OptimizationRunner(rc.outboarded_x2()).run(_problem())
    assert res.designs
    assert res.best.evaluation.feasible
    # ranked best-first: feasible first, then non-decreasing score
    feas = [1 if d.evaluation.feasible else 0 for d in res.designs]
    assert feas == sorted(feas, reverse=True)


def test_minimize_reduces_metric():
    base = rc.outboarded_x2()
    res = OptimizationRunner(base).run(_problem())
    base_val = res.base_metrics["required_driver_force"]
    best_val = res.best.evaluation.metrics["required_driver_force"]
    assert best_val < base_val


def test_designs_respect_variable_bounds():
    res = OptimizationRunner(rc.outboarded_x2()).run(_problem())
    for d in res.designs:
        for v in VARIABLES:
            value = get_by_path(d.config, v.path)
            assert v.minimum - 1e-9 <= value <= v.maximum + 1e-9


def test_constraints_are_enforced_on_best():
    res = OptimizationRunner(rc.outboarded_x2()).run(_problem())
    best = res.best
    assert 0.35 - 1e-9 <= best.config.pedal_box.balance_bias_front <= 0.65 + 1e-9
    assert 30.0 - 1e-6 <= best.evaluation.metrics["pedal_travel"] <= 60.0 + 1e-6


def test_lockup_order_constraint():
    problem = _problem()
    problem.constraints.append(Constraint("lockup_order", Op.GE, 0.0, None))
    res = OptimizationRunner(rc.outboarded_x2()).run(problem)
    # front should reach its limit before the rear: bar_rear >= bar_front
    assert res.best.evaluation.metrics["lockup_order"] >= -1e-6


def _feasibility_problem(**kw):
    """Feasibility mode: no objective, just constraints to satisfy."""
    return OptimizationProblem(
        variables=list(VARIABLES),
        objectives=[],
        constraints=[
            Constraint("brake_bias_front", Op.RANGE, 0.35, 0.65),
            Constraint("required_driver_force", Op.LE, None, 600.0),
            Constraint("pedal_travel", Op.RANGE, 20.0, 70.0),
        ],
        settings=Settings(iterations=1500, alternatives=5, **kw),
    )


def test_feasibility_mode_returns_feasible_designs_and_message():
    res = OptimizationRunner(rc.outboarded_x2()).run(_feasibility_problem())
    assert res.designs
    assert res.best.evaluation.feasible
    assert any("Feasibility mode" in m for m in res.messages)


def test_feasibility_mode_ranks_by_constraint_margin():
    # With no objective, designs are ranked by score = -(minimum constraint slack), so score is
    # non-decreasing and every feasible design (inside all limits) scores non-positive.
    res = OptimizationRunner(rc.outboarded_x2()).run(_feasibility_problem())
    scores = [d.evaluation.score for d in res.designs]
    assert scores == sorted(scores)
    for d in res.designs:
        if d.evaluation.feasible:
            assert d.evaluation.score <= 1e-9


def test_sensitivity_shares_sum_to_one():
    infl = sensitivity(rc.outboarded_x2(), VARIABLES, "required_driver_force")
    assert abs(sum(i.share for i in infl) - 1.0) < 1e-6
    assert infl[0].change >= infl[-1].change  # sorted by influence


def test_unavailable_metrics_present_but_flagged():
    assert METRICS["rotor_temperature"].available is False
    assert METRICS["required_driver_force"].available is True
