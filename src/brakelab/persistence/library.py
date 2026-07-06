"""In-program library of saved configurations.

Configurations live *inside the program* — in a per-user application-data folder — so they can be
browsed, renamed, compared and reused without touching the project files. From the library a config
can also be exported to any folder as JSON to share with others (see :mod:`.config_io`).

Each config is one JSON file named after its display name; the authoritative name is the ``name``
field inside the file, so renaming just rewrites the file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ..core.models import VehicleConfig
from .config_io import load_config, save_config


def app_data_dir() -> Path:
    """Per-user application-data directory for BrakeLab."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "BrakeLab"
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Roaming" / "BrakeLab"
    else:
        base = Path.home() / ".local" / "share" / "BrakeLab"
    return base


def _slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return slug or "config"


class ConfigLibrary:
    """A folder of saved :class:`VehicleConfig` files, addressed by display name."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory else app_data_dir() / "configs"
        self.directory.mkdir(parents=True, exist_ok=True)

    # --- listing / lookup --------------------------------------------------------------------
    def _index(self) -> dict[str, Path]:
        """Map display name -> file path by reading each JSON's name field."""
        index: dict[str, Path] = {}
        for path in self.directory.glob("*.json"):
            try:
                index[load_config(path).name] = path
            except Exception:  # noqa: BLE001 — skip unreadable files rather than crash the app
                continue
        return index

    def names(self) -> list[str]:
        return sorted(self._index().keys(), key=str.lower)

    def exists(self, name: str) -> bool:
        return name in self._index()

    def load(self, name: str) -> VehicleConfig:
        index = self._index()
        if name not in index:
            raise KeyError(f"No saved configuration named {name!r}.")
        return load_config(index[name])

    # --- mutation ----------------------------------------------------------------------------
    def save(self, config: VehicleConfig) -> None:
        """Save (or overwrite) ``config`` under its own ``name``."""
        save_config(config, self.directory / f"{_slug(config.name)}.json")

    def delete(self, name: str) -> None:
        index = self._index()
        if name in index:
            index[name].unlink(missing_ok=True)

    def rename(self, old: str, new: str) -> VehicleConfig:
        """Rename a saved config, returning the updated config."""
        config = self.load(old)
        config.name = new
        self.save(config)
        if _slug(old) != _slug(new):
            self.delete(old)
        return config

    # --- defaults ----------------------------------------------------------------------------
    def seed_defaults(self) -> None:
        """Populate the library on first run with presets from the original spreadsheet.

        The reference configs reproduce the spreadsheet exactly (1.5 g, 400 N) for validation; the
        seeded presets use the team's current design defaults (1.3 g target, 340 N driver force)."""
        if self.names():
            return
        from .. import reference_configs

        michigan = reference_configs.outboarded_x2()
        michigan.name = "2027 Michigan Car"
        michigan.notes = "Original spreadsheet inputs (x2 outboarded rear). Default preset."
        michigan.target_decel_g = 1.3
        michigan.pedal_box.driver_force = 340.0
        self.save(michigan)

        inboard = reference_configs.inboarded_x1()
        inboard.name = "2027 Inboard Concept"
        inboard.target_decel_g = 1.3
        inboard.pedal_box.driver_force = 340.0
        self.save(inboard)

    @property
    def default_name(self) -> str:
        """Preferred config to open on launch."""
        names = self.names()
        return "2027 Michigan Car" if "2027 Michigan Car" in names else (names[0] if names else "")
