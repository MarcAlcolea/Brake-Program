"""Transient rotor-temperature simulation — physics sanity + export tests.

The lumped-capacitance model has exact limiting cases we can test:
- with no cooling at all, one stop must raise the rotor by exactly E_rotor / (m·c);
- with cooling and no heating, temperature must decay monotonically toward ambient;
- repeated stops must never cool below ambient and must peak above a single stop.
"""

from __future__ import annotations

import csv

import pytest

from brakelab import reference_configs
from brakelab.thermal import simulate_temperature, write_ansys_csv


@pytest.fixture()
def config():
    return reference_configs.outboarded_x2()


def _no_cooling(cfg):
    cfg.thermal.film_intercept = 0.0
    cfg.thermal.film_slope = 0.0
    cfg.thermal.emissivity = 0.0
    return cfg


def test_adiabatic_single_stop_matches_energy_balance(config):
    """No losses, one stop: ΔT == P_rotor·t / (m·c) on both axles (energy conservation)."""
    _no_cooling(config)
    config.thermal.n_stops = 1
    config.thermal.cool_time = 0.0
    r = simulate_temperature(config)
    ambient = config.thermal.ambient_temp
    assert r.final_front - ambient == pytest.approx(r.adiabatic_rise_front, rel=1e-6)
    assert r.final_rear - ambient == pytest.approx(r.adiabatic_rise_rear, rel=1e-6)
    # Front rotors take more energy than rear at front-biased hydraulics (x2 config).
    assert r.adiabatic_rise_front > r.adiabatic_rise_rear > 0


def test_adiabatic_stops_accumulate_linearly(config):
    """No losses: N stops = N × the single-stop rise."""
    _no_cooling(config)
    config.thermal.cool_time = 0.0
    config.thermal.n_stops = 5
    r = simulate_temperature(config)
    ambient = config.thermal.ambient_temp
    assert r.final_front - ambient == pytest.approx(5 * r.adiabatic_rise_front, rel=1e-6)


def test_cooling_decays_toward_ambient_and_never_below(config):
    """With convection on and a long cool phase, the rotor ends colder than its peak, is
    monotonically non-increasing while coasting, and never drops below ambient."""
    config.thermal.n_stops = 1
    config.thermal.cool_time = 600.0
    r = simulate_temperature(config)
    ambient = config.thermal.ambient_temp
    assert r.final_front < r.peak_front
    assert min(r.temp_front) >= ambient - 1e-9
    # after the peak the trace must not rise again (heating is over)
    i_peak = r.temp_front.index(max(r.temp_front))
    tail = r.temp_front[i_peak:]
    assert all(a >= b - 1e-9 for a, b in zip(tail, tail[1:]))
    # long cooldown should get most of the way back to ambient
    assert r.final_front - ambient < 0.35 * (r.peak_front - ambient)


def test_repeated_stops_run_hotter_than_one(config):
    config.thermal.n_stops = 1
    one = simulate_temperature(config)
    config.thermal.n_stops = 10
    ten = simulate_temperature(config)
    assert ten.peak_front > one.peak_front
    assert ten.peak_rear > one.peak_rear


def test_radiation_lowers_peak_temperature(config):
    config.thermal.emissivity = 0.0
    no_rad = simulate_temperature(config)
    config.thermal.emissivity = 0.9
    rad = simulate_temperature(config)
    assert rad.peak_front < no_rad.peak_front


def test_csv_export_round_trip(config, tmp_path):
    r = simulate_temperature(config)
    path = tmp_path / "sim.csv"
    write_ansys_csv(r, path)
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["time_s", "temp_front_C", "temp_rear_C", "film_coeff_W_m2K",
                       "heat_flux_front_W_m2", "heat_flux_rear_W_m2"]
    assert len(rows) == len(r.time) + 1
    assert float(rows[1][1]) == pytest.approx(config.thermal.ambient_temp)


def test_old_configs_without_sim_fields_still_load(config):
    """The new Thermal fields have defaults, so JSON saved before this feature must round-trip."""
    from brakelab.persistence import config_from_dict, config_to_dict

    d = config_to_dict(config)
    for key in ("rotor_mass", "rotor_specific_heat", "emissivity", "n_stops", "cool_speed"):
        d["thermal"].pop(key, None)
    loaded = config_from_dict(d)
    assert loaded.thermal.rotor_mass == 1.3
    assert loaded.thermal.n_stops == 10
