"""In-program library of saved configurations.

Configurations live *inside the program* — in a per-user application-data folder — so they can be
browsed, renamed, compared and reused without touching the project files. From the library a config
can be exported to a file to share with others (e.g. by email), and a file someone sends you can be
imported straight back in (see :mod:`.config_io` and the config bar's Import/Export actions).

Each config is one JSON file named after its display name; the authoritative name is the ``name``
field inside the file, so renaming just rewrites the file.

The library is **seeded** from the preset files bundled with the app (``brakelab/presets/*.json``).
To ship a new default preset with a release, drop its ``.json`` in that folder — it then appears for
everyone on a fresh install, and is added for existing users on upgrade (without touching their own
saved setups).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ..core.models import VehicleConfig
from .config_io import load_config, save_config


def app_data_dir() -> Path:
    """Per-user application-data directory for Brake Design Studio.

    Renamed from the old "BrakeLab" product name; if a folder under the old name exists and the new
    one doesn't yet, it is migrated once so saved configurations carry over silently.
    """
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        root = Path.home() / "AppData" / "Roaming"
    else:
        root = Path.home() / ".local" / "share"
    base = root / "Brake Design Studio"
    legacy = root / "BrakeLab"
    if not base.exists() and legacy.exists():
        try:
            legacy.rename(base)
        except OSError:
            pass
    return base


def bundled_presets_dir() -> Path:
    """Folder of preset ``.json`` files shipped with the app (``brakelab/presets``).

    Resolves both in a source checkout and in the frozen app (PyInstaller mirrors the package path)."""
    return Path(__file__).resolve().parent.parent / "presets"


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

    def import_file(self, path: str | Path) -> VehicleConfig:
        """Load a config file someone shared and add it to the library, returning the config."""
        config = load_config(path)
        self.save(config)
        return config

    # --- defaults ----------------------------------------------------------------------------
    def seed_defaults(self) -> None:
        """Ensure the presets bundled with the app are present in the library.

        On a fresh install this populates the library; on a later version it adds any *new* bundled
        preset (matched by name) without overwriting the user's own saved setups. Ship a new default
        by dropping its ``.json`` into ``brakelab/presets/``."""
        existing = set(self.names())
        for path in sorted(bundled_presets_dir().glob("*.json")):
            try:
                config = load_config(path)
            except Exception:  # noqa: BLE001 — skip an unreadable bundled preset
                continue
            if config.name not in existing:
                self.save(config)
                existing.add(config.name)

    @property
    def default_name(self) -> str:
        """Preferred config to open on launch."""
        names = self.names()
        return "2027 Michigan Car" if "2027 Michigan Car" in names else (names[0] if names else "")
