"""Application state and mediation between the GUI and the core.

The ``ProjectController`` owns the active config and the engine. When any input changes it re-runs
the engine and emits ``resultsChanged`` so panels and plots refresh (Observer pattern). The GUI
never touches the physics directly — it only reads/writes the config through this controller.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..core.attrpath import get_by_path, set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
from ..persistence import load_config, save_config
from ..reporting import build_report


def _perturb(value):
    """Nudge a value so a dependent output changes, respecting its type."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    return value * 1.0001 + 1e-6


def _close(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)


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

    # --- assumptions -------------------------------------------------------------------------
    def is_assumed(self, path: str) -> bool:
        return path in self._config.assumed_inputs

    def set_assumed(self, path: str, assumed: bool) -> None:
        """Flag/unflag an input path as an assumed value and refresh the assumption markers."""
        flagged = self._config.assumed_inputs
        if assumed and path not in flagged:
            flagged.append(path)
        elif not assumed and path in flagged:
            flagged.remove(path)
        else:
            return
        # The numbers don't change, but outputs' assumed-dependency markers might — re-emit so the
        # panels re-evaluate them.
        self.resultsChanged.emit(self._results)

    def assumed_affected(self, getters) -> set:
        """Return the subset of ``getters`` whose value depends on any currently-assumed input.

        Dependency is detected empirically: for each assumed input we solve a perturbed copy of the
        config and see which outputs move. This keeps the warning correct without hand-maintaining a
        dependency map, and it costs only one extra solve per assumed input. Purely advisory — any
        failure to perturb/solve is swallowed (that input simply contributes no markers).
        """
        assumed = list(self._config.assumed_inputs)
        if not assumed:
            return set()
        getters = list(getters)
        base = self._results
        affected: set = set()
        for path in assumed:
            try:
                cfg = copy.deepcopy(self._config)
                set_by_path(cfg, path, _perturb(get_by_path(cfg, path)))
                perturbed = self._engine.solve(cfg)
            except Exception:  # noqa: BLE001 — advisory only
                continue
            for key in getters:
                if key in affected:
                    continue
                try:
                    if not _close(key.getter(base, self._config), key.getter(perturbed, cfg)):
                        affected.add(key)
                except Exception:  # noqa: BLE001
                    continue
        return affected

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

    def export_report(self, path: str | Path, options=None) -> None:
        build_report(self._config, self._results, path, options=options)
