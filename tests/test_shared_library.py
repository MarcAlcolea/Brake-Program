"""Shared (team) library folder: merge, publish, personal-shadowing, and safe delete."""

from __future__ import annotations

from brakelab.persistence import ConfigLibrary
from brakelab import reference_configs


def test_merge_publish_shadow_and_delete(tmp_path):
    personal = tmp_path / "personal"
    team = tmp_path / "team"
    lib = ConfigLibrary(directory=personal, shared_dir=team)

    # a personal preset
    local = reference_configs.outboarded_x2()
    local.name = "MyLocal"
    lib.save(local)
    assert "MyLocal" in lib.names()
    assert lib.is_shared("MyLocal") is False

    # publish a preset to the team folder
    shared = reference_configs.inboarded_x1()
    shared.name = "TeamCar"
    lib.publish(shared)
    assert "TeamCar" in lib.names()
    assert lib.is_shared("TeamCar") is True

    # a different personal library pointed at the same team folder sees the team preset
    other = ConfigLibrary(directory=tmp_path / "other", shared_dir=team)
    assert "TeamCar" in other.names()

    # a personal preset of the same name shadows the team copy (local wins)
    clash = reference_configs.outboarded_x2()
    clash.name = "TeamCar"
    clash.target_decel_g = 0.9
    lib.save(clash)
    assert lib.is_shared("TeamCar") is False
    assert lib.load("TeamCar").target_decel_g == 0.9

    # deleting removes only the personal copy; the team copy survives and can't be deleted locally
    assert lib.delete("TeamCar") is True
    assert "TeamCar" in lib.names() and lib.is_shared("TeamCar") is True
    assert lib.delete("TeamCar") is False


def test_no_team_folder_behaves_like_before(tmp_path):
    lib = ConfigLibrary(directory=tmp_path / "p", shared_dir=None)
    assert lib.shared_configured is False
    c = reference_configs.outboarded_x2()
    c.name = "Solo"
    lib.save(c)
    assert lib.names() == ["Solo"]
