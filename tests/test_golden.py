"""Golden-value tests: engine output vs the (corrected) spreadsheet numbers.

Every expected value here traces to a row in ``docs/calculation_audit.md``. The x2 Outboarded
sheet is self-consistent and is reproduced to the digit for Phases 1-4. The x1 Inboarded rear
sizing asserts the *corrected* values (audit B2 — the sheet dropped the factor of two).
"""

from __future__ import annotations

import math

import pytest

from brakelab.core import BrakeEngine
from brakelab import reference_configs as rc


@pytest.fixture(scope="module")
def x2():
    return BrakeEngine().solve(rc.outboarded_x2())


@pytest.fixture(scope="module")
def x1():
    return BrakeEngine().solve(rc.inboarded_x1())


def approx(value):
    return pytest.approx(value, rel=1e-6)


# --- x2 Outboarded: matches the spreadsheet exactly (Phases 1-4) --------------------------------

def test_x2_dynamics(x2):
    d = x2.dynamics
    assert d.weight == approx(3139.2)
    assert d.weight_transfer == approx(1030.4303261538464)
    assert d.static_front == approx(1632.384)
    assert d.static_rear == approx(1506.816)
    assert d.dynamic_front == approx(2662.8143261538467)
    assert d.dynamic_rear == approx(476.38567384615385)


def test_x2_torque(x2):
    assert x2.torque.front.friction_force_per_wheel == approx(1997.1107446153852)
    assert x2.torque.front.torque_per_rotor == approx(447.35280679384627)
    assert x2.torque.rear.friction_force_per_wheel == approx(357.28925538461536)
    assert x2.torque.rear.torque_per_rotor == approx(80.03279320615384)


def test_x2_sizing(x2):
    assert x2.sizing.front.clamp_force == approx(5265.452056751933)
    assert x2.sizing.front.line_pressure == approx(6.635312276913923)
    assert x2.sizing.rear.clamp_force == approx(942.0055697841628)
    assert x2.sizing.rear.line_pressure == approx(1.1870774893004573)


def test_x2_hydraulics(x2):
    h = x2.hydraulics
    assert h.mc_force_front == approx(1313.344671316663)
    assert h.mc_force_rear == approx(234.96140148919776)
    assert h.bar_force_front == approx(2020.5302635641)
    assert h.bar_force_rear == approx(671.3182899691365)
    assert h.pedal_force == approx(2400.0)
    assert h.front_requirement_met is True
    assert h.rear_requirement_met is True


def test_x2_pedal_travel(x2):
    p = x2.pedal_travel
    # Pedal travel is ~29.43 mm; the sheet reported 29.40 mm. The ~0.1 % difference is the audit
    # B4 fix (one unified piston area instead of the sheet's 793.55 / 792 mix).
    assert p.pedal_travel == pytest.approx(29.40, rel=2e-3)
    assert p.mc_stroke_front == approx(p.mc_stroke_rear)


# --- x1 Inboarded: front/dynamics match; rear sizing uses the corrected factor of two -----------

def test_x1_rear_torque_uses_full_axle(x1):
    # One inboard rotor carries both rear wheels' torque -> twice the per-rotor torque of x2.
    assert x1.torque.rear.torque_per_rotor == approx(160.06558641230768)


def test_x1_rear_sizing_is_corrected(x1):
    # Audit B2: corrected clamp = T/(2*mu*Reff) = 1884 N, NOT the sheet's 3768 N.
    assert x1.sizing.rear.clamp_force == approx(1884.0111395683257)
    assert x1.sizing.rear.line_pressure == approx(2.374154978600915)


def test_x1_rear_requirement_now_met(x1):
    # With B2 fixed the rear demand halves, so the rear requirement is met (the buggy sheet said no).
    assert x1.hydraulics.rear_requirement_met is True
    # Front remains the binding constraint on this variant.
    assert x1.hydraulics.front_requirement_met is False
