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


def _slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return slug or "config"


class ConfigLibrary:
    """A folder of saved :class:`VehicleConfig` files, addressed by display name.

    An optional **shared (team) folder** — typically a synced location (Dropbox, Google Drive, a Git
    clone…) — is merged in transparently: its presets appear in :meth:`names` alongside the personal
    ones, so the whole subteam sees the same saved setups. Personal presets shadow a team preset of
    the same name (your local copy wins). :meth:`save` always writes to the personal folder;
    :meth:`publish` writes to the shared folder to share a setup with the team.
    """

    def __init__(self, directory: str | Path | None = None,
                 shared_dir: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory else app_data_dir() / "configs"
        self.directory.mkdir(parents=True, exist_ok=True)
        if shared_dir is None:
            from .settings import get_team_dir

            shared_dir = get_team_dir()
        self.shared_dir = Path(shared_dir) if shared_dir else None

    # --- listing / lookup --------------------------------------------------------------------
    def _index_dir(self, directory: Path | None) -> dict[str, Path]:
        """Map display name -> file path for one folder (by reading each JSON's name field)."""
        index: dict[str, Path] = {}
        if directory is None or not directory.is_dir():
            return index
        for path in directory.glob("*.json"):
            try:
                index[load_config(path).name] = path
            except Exception:  # noqa: BLE001 — skip unreadable files rather than crash the app
                continue
        return index

    def _personal_index(self) -> dict[str, Path]:
        return self._index_dir(self.directory)

    def _shared_index(self) -> dict[str, Path]:
        return self._index_dir(self.shared_dir)

    def _index(self) -> dict[str, Path]:
        """Merged name -> path; personal presets shadow a team preset of the same name."""
        index = self._shared_index()
        index.update(self._personal_index())
        return index

    def names(self) -> list[str]:
        return sorted(self._index().keys(), key=str.lower)

    def exists(self, name: str) -> bool:
        return name in self._index()

    def is_shared(self, name: str) -> bool:
        """True if ``name`` comes only from the team folder (no personal copy shadows it)."""
        return name in self._shared_index() and name not in self._personal_index()

    def load(self, name: str) -> VehicleConfig:
        index = self._index()
        if name not in index:
            raise KeyError(f"No saved configuration named {name!r}.")
        return load_config(index[name])

    # --- shared / team folder ----------------------------------------------------------------
    @property
    def shared_configured(self) -> bool:
        return self.shared_dir is not None and self.shared_dir.is_dir()

    def set_shared_dir(self, path: str | Path | None) -> None:
        """Point the library at a team folder (or clear it with None) and remember it in settings."""
        from .settings import set_team_dir

        self.shared_dir = Path(path) if path else None
        set_team_dir(str(self.shared_dir) if self.shared_dir else None)

    def publish(self, config: VehicleConfig) -> None:
        """Copy ``config`` into the shared team folder so teammates see it."""
        if self.shared_dir is None:
            raise RuntimeError("No team folder is set.")
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        save_config(config, self.shared_dir / f"{_slug(config.name)}.json")

    # --- mutation ----------------------------------------------------------------------------
    def save(self, config: VehicleConfig) -> None:
        """Save (or overwrite) ``config`` under its own ``name`` in the PERSONAL folder."""
        save_config(config, self.directory / f"{_slug(config.name)}.json")

    def delete(self, name: str) -> bool:
        """Delete a PERSONAL preset. Team presets are left untouched (delete them from the shared
        folder to remove them for everyone). Returns True if a personal file was removed."""
        personal = self._personal_index()
        if name in personal:
            personal[name].unlink(missing_ok=True)
            return True
        return False

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
