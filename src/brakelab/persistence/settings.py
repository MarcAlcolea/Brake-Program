"""Small persisted application settings (a JSON file in the app-data directory).

Currently holds only the optional *team library* folder — a path the user points at a shared/synced
location (Dropbox, Google Drive, OneDrive, a Git clone…). Kept tiny and forgiving: a missing or
unreadable file just means "no settings yet".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .library import app_data_dir

_TEAM_KEY = "team_library_dir"


def _settings_path() -> Path:
    return app_data_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    path = _settings_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — a corrupt settings file must never block the app
            return {}
    return {}


def save_settings(data: dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_team_dir() -> str | None:
    """The configured team-library folder path, or None if not set."""
    return load_settings().get(_TEAM_KEY) or None


def set_team_dir(path: str | None) -> None:
    """Set (or clear, with None) the team-library folder path."""
    data = load_settings()
    if path:
        data[_TEAM_KEY] = str(path)
    else:
        data.pop(_TEAM_KEY, None)
    save_settings(data)
