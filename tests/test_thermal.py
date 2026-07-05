"""Golden-value tests for the brake-rotor thermal phase.

Expected numbers come from the "Peak Heat Flux Calculation" in
``reference/Brake Rotors Simulations 2026.docx`` (m=320 kg, v_i=28, v_f=10 m/s, t=3 s, 65/35 bias,
A=0.02343522 m², two rotors per axle). Also checks the audit **T2** coupling: a single inboard rear
rotor absorbs the whole rear energy, so its heat flux doubles.
"""

from __future__ import annotations

import dataclasses

import pytest

from brakelab.core import BrakeEngine
from brakelab import reference_configs as rc


@pytest.fixture(scope="module")
def x2():
    return BrakeEngine().solve(rc.outboarded_x2())


def approx(value):
    return pytest.approx(value, rel=1e-5)


def test_energy_and_power(x2):
    t = x2.thermal
    assert t.braking_energy == approx(109_440.0)      # 1/2 * 320 * (28^2 - 10^2)
    assert t.braking_power == approx(36_480.0)         # E / 3 s


def test_per_rotor_power(x2):
    t = x2.thermal
    assert t.power_front_rotor == approx(11_856.0)     # 36480 * 0.65 / 2
    assert t.power_rear_rotor == approx(6_384.0)       # 36480 * 0.35 / 2


def test_peak_heat_flux(x2):
    t = x2.thermal
    assert t.heat_flux_front == approx(505_905.0)      # 11856 / 0.02343522
    assert t.heat_flux_rear == approx(272_411.0)       # 6384 / 0.02343522


def test_film_coefficient(x2):
    t = x2.thermal
    assert t.film_coeff_start == approx(94.0)          # 10 + 3 * 28
    assert t.film_coeff_end == approx(40.0)            # 10 + 3 * 10


def test_inboard_single_rear_rotor_doubles_rear_flux():
    """Audit T2: with one inboard rear rotor it takes the full rear energy, not half."""
    x1 = BrakeEngine().solve(rc.inboarded_x1())
    x2 = BrakeEngine().solve(rc.outboarded_x2())
    # x1 has n_rotors_rear = 1 vs 2; rear bias differs slightly (0.64 vs 0.65), so compare the ratio.
    ratio = x1.thermal.heat_flux_rear / x2.thermal.heat_flux_rear
    expected = (0.36 / 1) / (0.35 / 2)
    assert ratio == approx(expected)


def test_rotor_heat_partition_scales_flux():
    """Audit T3: the rotor/pad energy split scales heat flux linearly; 1.0 reproduces the doc."""
    config = rc.outboarded_x2()
    config.thermal = dataclasses.replace(config.thermal, rotor_heat_fraction=0.85)
    t = BrakeEngine().solve(config).thermal
    assert t.heat_flux_front == approx(505_905.0 * 0.85)
