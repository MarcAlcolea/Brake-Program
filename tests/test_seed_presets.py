"""Seeding the library from the bundled preset files."""

from __future__ import annotations

from brakelab.persistence import ConfigLibrary
from brakelab.persistence.library import bundled_presets_dir


def test_bundled_presets_exist():
    files = list(bundled_presets_dir().glob("*.json"))
    assert files, "no bundled preset files found in brakelab/presets/"


def test_seed_populates_and_is_idempotent(tmp_path):
    lib = ConfigLibrary(directory=tmp_path)
    assert lib.names() == []
    lib.seed_defaults()
    seeded = lib.names()
    assert "2027 Michigan Car" in seeded
    # seeding again must not duplicate or overwrite
    lib.seed_defaults()
    assert lib.names() == seeded


def test_seed_keeps_user_edits_but_adds_new_defaults(tmp_path):
    lib = ConfigLibrary(directory=tmp_path)
    lib.seed_defaults()
    # user edits an existing default
    car = lib.load("2027 Michigan Car")
    car.target_decel_g = 0.7
    lib.save(car)
    # re-seeding does not clobber the user's edit
    lib.seed_defaults()
    assert lib.load("2027 Michigan Car").target_decel_g == 0.7


def test_michigan_default_is_4130_chromoly(tmp_path):
    from brakelab.components.catalog import match_material

    lib = ConfigLibrary(directory=tmp_path)
    lib.seed_defaults()
    c = lib.load("2027 Michigan Car")
    mat = match_material(c.thermal.rotor_specific_heat, c.thermal.emissivity)
    assert mat is not None and "4130" in mat.name
