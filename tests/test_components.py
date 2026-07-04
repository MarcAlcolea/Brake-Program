"""Tests for the component catalog and discrete (catalog-based) optimization."""

from __future__ import annotations

from brakelab.components import catalog
from brakelab.core import BrakeEngine
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
)


def test_baseline_matches_real_components():
    # The 2027 Michigan Car inputs should resolve to real catalog parts.
    cfg = rc.outboarded_x2()
    mc = catalog.match_master_cylinder(cfg.hydraulics.mc_bore_front)
    cal = catalog.match_caliper(cfg.caliper.piston_area, cfg.caliper.n_pistons)
    pad = catalog.match_pad(cfg.pad.friction_coefficient)
    assert mc is not None and "0.625" in mc.name
    assert cal is not None and cal.name == "Wilwood GP200"
    assert pad is not None and "BP-28" in pad.name


def test_series_bores_are_discrete_and_sorted():
    bores = catalog.bores_for_series("Tilton 76-Series")
    assert bores == sorted(bores)
    assert len(bores) >= 4
    # 5/8" should be present (15.875 mm)
    assert any(abs(b - 15.875) < 0.01 for b in bores)


def test_optimization_picks_catalog_bore():
    bores = catalog.bores_for_series("Tilton 76-Series")
    problem = OptimizationProblem(
        variables=[
            Variable("hydraulics.mc_bore_front", "MC front", "mm", min(bores), max(bores), choices=bores),
            Variable("hydraulics.mc_bore_rear", "MC rear", "mm", min(bores), max(bores), choices=bores),
            Variable("pedal_box.pedal_ratio", "Pedal ratio", "-", 3.5, 7.0),
        ],
        objectives=[Objective("required_driver_force", Sense.MIN)],
        constraints=[Constraint("pedal_travel", Op.RANGE, 30.0, 60.0)],
        settings=Settings(iterations=1200, alternatives=5),
    )
    res = OptimizationRunner(rc.outboarded_x2()).run(problem)
    best = res.best
    # The recommended bores must be actual catalog sizes the team can buy.
    for path in ("hydraulics.mc_bore_front", "hydraulics.mc_bore_rear"):
        value = get_by_path(best.config, path)
        assert any(abs(value - b) < 1e-6 for b in bores)
