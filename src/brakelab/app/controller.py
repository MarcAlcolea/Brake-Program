"""Application state and mediation between the GUI and the core.

The ``ProjectController`` owns the active config and the engine. When any input changes it re-runs
the engine and emits ``resultsChanged`` so panels and plots refresh (Observer pattern). The GUI
never touches the physics directly — it only reads/writes the config through this controller.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..core.attrpath import get_by_path, set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
from ..persistence import load_config, save_config
from ..reporting import build_report


class ProjectController(QObject):
    """Holds the current config/results and recomputes on change."""

    resultsChanged = Signal(object)  # BrakeResults
    configReplaced = Signal(object)  # VehicleConfig — a whole new config was loaded

    def __init__(self, config: VehicleConfig) -> None:
        super().__init__()
        self._engine = BrakeEngine()
        self._config = config
        self._results: BrakeResults = self._engine.solve(config)

    # --- accessors ---------------------------------------------------------------------------
    @property
    def config(self) -> VehicleConfig:
        return self._config

    @property
    def results(self) -> BrakeResults:
        return self._results

    def value(self, path: str) -> float:
        return get_by_path(self._config, path)

    # --- mutation ----------------------------------------------------------------------------
    def set_value(self, path: str, value) -> None:
        """Update one config field by dotted path and recompute."""
        set_by_path(self._config, path, value)
        self.recompute()

    def apply_values(self, values: dict[str, float]) -> None:
        """Update several config fields at once (e.g. from a catalog part) and recompute once."""
        for path, value in values.items():
            set_by_path(self._config, path, value)
        self.recompute()

    def replace_config(self, config: VehicleConfig) -> None:
        self._config = config
        self.configReplaced.emit(config)
        self.recompute()

    def recompute(self) -> None:
        self._results = self._engine.solve(self._config)
        self.resultsChanged.emit(self._results)

    # --- IO ----------------------------------------------------------------------------------
    def load(self, path: str | Path) -> None:
        self.replace_config(load_config(path))

    def save(self, path: str | Path) -> None:
        save_config(self._config, path)

    def export_report(self, path: str | Path) -> None:
        build_report(self._config, self._results, path)
