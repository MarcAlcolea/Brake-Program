"""Tests for the structured engineering requirements."""

from __future__ import annotations

import copy

from brakelab.core import BrakeEngine
from brakelab import reference_configs as rc


def test_baseline_meets_hard_requirements():
    r = BrakeEngine().solve(rc.outboarded_x2())
    assert all(req.passed for req in r.requirements if req.hard)
    assert r.ok is True


def test_soft_target_does_not_fail_overall():
    # Baseline pedal travel (~29.4 mm) is below the 30-60 mm target, but that is soft.
    r = BrakeEngine().solve(rc.outboarded_x2())
    pedal = next(req for req in r.requirements if "Pedal travel" in req.name)
    assert pedal.hard is False
    assert pedal.passed is False
    assert r.ok is True  # soft miss must not fail the design


def test_excess_deceleration_fails_front_authority():
    cfg = copy.deepcopy(rc.outboarded_x2())
    cfg.target_decel_g = 2.5
    r = BrakeEngine().solve(cfg)
    front = next(req for req in r.requirements if req.name == "Front braking authority")
    assert front.passed is False
    assert r.ok is False


def test_every_requirement_has_filled_detail():
    r = BrakeEngine().solve(rc.inboarded_x1())
    assert r.requirements
    for req in r.requirements:
        assert req.detail and req.condition and req.description
