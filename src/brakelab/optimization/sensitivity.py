"""Sensitivity analysis — which variables most influence a chosen metric.

Perturbs each variable one at a time by a small fraction of its range and measures the resulting
change in the target metric. Returns a ranked, normalised influence (share of total) so the UI can
show "what matters most" as a simple bar list.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from ..core.attrpath import get_by_path, set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from .metrics import METRICS
from .problem import Variable


@dataclass
class Influence:
    label: str
    unit: str
    change: float        # absolute change in the metric across the perturbation
    share: float         # fraction of total influence (0..1)


def sensitivity(
    base: VehicleConfig,
    variables: list[Variable],
    metric_key: str,
    engine: BrakeEngine | None = None,
    fraction: float = 0.1,
) -> list[Influence]:
    """Rank ``variables`` by their influence on ``metric_key`` around ``base``."""
    engine = engine or BrakeEngine()
    metric = METRICS[metric_key]

    def metric_at(config: VehicleConfig) -> float:
        return metric.getter(engine.solve(config), config)

    raw: list[tuple[Variable, float]] = []
    for var in variables:
        span = var.maximum - var.minimum
        if span <= 0:
            raw.append((var, 0.0))
            continue
        delta = span * fraction
        base_val = get_by_path(base, var.path)
        hi = copy.deepcopy(base)
        lo = copy.deepcopy(base)
        set_by_path(hi, var.path, min(var.maximum, base_val + delta))
        set_by_path(lo, var.path, max(var.minimum, base_val - delta))
        raw.append((var, abs(metric_at(hi) - metric_at(lo))))

    total = sum(change for _v, change in raw) or 1.0
    influences = [
        Influence(var.label, var.unit, change, change / total)
        for var, change in raw
    ]
    return sorted(influences, key=lambda i: i.change, reverse=True)
