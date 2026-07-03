"""Property tests: physical invariants that must hold for any valid configuration."""

from __future__ import annotations

import pytest

from brakelab.core import BrakeEngine
from brakelab import reference_configs as rc

CONFIGS = [rc.outboarded_x2(), rc.inboarded_x1()]


@pytest.mark.parametrize("config", CONFIGS, ids=lambda c: c.name)
def test_static_loads_sum_to_weight(config):
    d = BrakeEngine().solve(config).dynamics
    assert d.static_front + d.static_rear == pytest.approx(d.weight)


@pytest.mark.parametrize("config", CONFIGS, ids=lambda c: c.name)
def test_dynamic_loads_sum_to_weight(config):
    # Load transfer moves weight between axles but conserves the total.
    d = BrakeEngine().solve(config).dynamics
    assert d.dynamic_front + d.dynamic_rear == pytest.approx(d.weight)


@pytest.mark.parametrize("config", CONFIGS, ids=lambda c: c.name)
def test_front_gains_load_under_braking(config):
    d = BrakeEngine().solve(config).dynamics
    assert d.dynamic_front > d.static_front
    assert d.dynamic_rear < d.static_rear


@pytest.mark.parametrize("config", CONFIGS, ids=lambda c: c.name)
def test_bias_complement(config):
    assert config.pedal_box.balance_bias_front + config.pedal_box.balance_bias_rear == pytest.approx(1.0)


def test_higher_decel_increases_transfer():
    base = rc.outboarded_x2()
    hi = rc.outboarded_x2()
    hi.target_decel_g = 2.0
    dw_base = BrakeEngine().solve(base).dynamics.weight_transfer
    dw_hi = BrakeEngine().solve(hi).dynamics.weight_transfer
    assert dw_hi > dw_base
