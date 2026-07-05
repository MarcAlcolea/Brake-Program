"""Save and load a :class:`VehicleConfig` as human-readable, versioned JSON.

JSON was chosen over a binary format so configs are diff-able and reviewable in pull requests.
Every file carries a ``schema_version``; ``load_config`` routes old versions through migrations so
saved cars keep loading as the model evolves.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core.models import (
    Axle,
    Caliper,
    Hydraulics,
    MassProperties,
    Pad,
    PedalBox,
    Rotor,
    Thermal,
    Tires,
    VehicleConfig,
)

SCHEMA_VERSION = 1


def config_to_dict(config: VehicleConfig) -> dict[str, Any]:
    """Serialise a config to a plain dict with a schema version."""
    data = asdict(config)
    data["schema_version"] = SCHEMA_VERSION
    return data


def config_from_dict(data: dict[str, Any]) -> VehicleConfig:
    """Reconstruct a config from a dict, applying migrations for older schema versions."""
    data = _migrate(dict(data))
    return VehicleConfig(
        name=data["name"],
        mass=MassProperties(**data["mass"]),
        tires=Tires(**data["tires"]),
        front_axle=Axle(**data["front_axle"]),
        rear_axle=Axle(**data["rear_axle"]),
        rotor=Rotor(**data["rotor"]),
        pad=Pad(**data["pad"]),
        caliper=Caliper(**data["caliper"]),
        hydraulics=Hydraulics(**data["hydraulics"]),
        pedal_box=PedalBox(**data["pedal_box"]),
        target_decel_g=data["target_decel_g"],
        notes=data.get("notes", ""),
        thermal=Thermal(**data.get("thermal", {})),
    )


def save_config(config: VehicleConfig, path: str | Path) -> None:
    """Write a config to ``path`` as pretty-printed JSON."""
    path = Path(path)
    path.write_text(json.dumps(config_to_dict(config), indent=2), encoding="utf-8")


def load_config(path: str | Path) -> VehicleConfig:
    """Read a config from a JSON file at ``path``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return config_from_dict(data)


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade an older config dict in place to the current schema. No-op for current version."""
    version = data.get("schema_version", 1)
    # Future migrations go here, e.g.:
    #   if version < 2: ...transform...; version = 2
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"Config schema version {version} is newer than supported ({SCHEMA_VERSION}). "
            "Update brakelab to load this file."
        )
    return data
