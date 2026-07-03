"""Round-trip tests for config save/load."""

from __future__ import annotations

from brakelab.core import BrakeEngine
from brakelab.persistence import config_from_dict, config_to_dict, load_config, save_config
from brakelab import reference_configs as rc


def test_dict_round_trip():
    original = rc.outboarded_x2()
    restored = config_from_dict(config_to_dict(original))
    assert restored == original


def test_file_round_trip(tmp_path):
    original = rc.inboarded_x1()
    path = tmp_path / "car.json"
    save_config(original, path)
    restored = load_config(path)
    assert restored == original


def test_results_stable_across_round_trip(tmp_path):
    original = rc.outboarded_x2()
    path = tmp_path / "car.json"
    save_config(original, path)
    r1 = BrakeEngine().solve(original)
    r2 = BrakeEngine().solve(load_config(path))
    assert r1.sizing.front.line_pressure == r2.sizing.front.line_pressure
    assert r1.pedal_travel.pedal_travel == r2.pedal_travel.pedal_travel
