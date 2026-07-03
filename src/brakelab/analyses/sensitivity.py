"""Sensitivity sweep — vary one numeric input and track chosen outputs.

A small, general analysis that proves the seam works and is genuinely useful: e.g. "how does pedal
travel change with piston travel?" or "how does front line pressure change with target g?".

The swept parameter is addressed by a dotted path into the config (``"mass.front_weight_fraction"``,
``"caliper.piston_travel"``, ``"target_decel_g"``). Outputs are addressed by a callable that reads
a :class:`BrakeResults`. A few ready-made output getters are provided.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from ..core.attrpath import set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
from .base import Analysis, AnalysisResult

#: Ready-made output getters keyed by label.
OUTPUTS: dict[str, Callable[[BrakeResults], float]] = {
    "Front line pressure [MPa]": lambda r: r.sizing.front.line_pressure,
    "Rear line pressure [MPa]": lambda r: r.sizing.rear.line_pressure,
    "Pedal travel [mm]": lambda r: r.pedal_travel.pedal_travel,
    "Pedal force required, front [N]": lambda r: r.hydraulics.bar_force_front,
    "Dynamic front load [N]": lambda r: r.dynamics.dynamic_front,
}


@dataclass
class SensitivityAnalysis(Analysis):
    """Sweep ``parameter`` from ``start`` to ``stop`` over ``steps`` points, tracking ``outputs``."""

    parameter: str
    start: float
    stop: float
    steps: int = 25
    outputs: tuple[str, ...] = ("Front line pressure [MPa]", "Pedal travel [mm]")
    name: str = "Sensitivity sweep"

    def run(self, config: VehicleConfig, engine: BrakeEngine) -> AnalysisResult:
        xs = [self.start + (self.stop - self.start) * i / (self.steps - 1) for i in range(self.steps)]
        series: dict[str, tuple[list[float], list[float]]] = {label: (xs, []) for label in self.outputs}

        for x in xs:
            trial = copy.deepcopy(config)
            set_by_path(trial, self.parameter, x)
            result = engine.solve(trial)
            for label in self.outputs:
                series[label][1].append(OUTPUTS[label](result))

        return AnalysisResult(
            title=f"Sensitivity of outputs to '{self.parameter}'",
            series=series,
            summary={"parameter": self.parameter, "range": (self.start, self.stop), "steps": self.steps},
        )
