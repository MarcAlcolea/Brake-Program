"""Optimization runner — turns an OptimizationProblem into ranked designs.

The runner builds the ``evaluate`` callback (apply values → solve with the brake engine → read
metrics → score objectives → check constraints), hands it to the chosen optimizer, and packages the
ranked evaluations into concrete :class:`Design` objects (each a real ``VehicleConfig``).

Objective scaling: each objective is normalised by the metric's value at the starting design so that
objectives with different magnitudes combine fairly in the weighted score (lower score is better).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..core.attrpath import set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from .algorithms import Evaluation, get_optimizer
from .metrics import METRICS, all_available_keys
from .problem import Constraint, Objective, Op, OptimizationProblem, Sense


@dataclass
class Design:
    config: VehicleConfig
    evaluation: Evaluation


@dataclass
class OptimizationResult:
    designs: list[Design]                 # ranked, best first
    problem: OptimizationProblem
    base_metrics: dict[str, float]
    base_config: VehicleConfig
    messages: list[str] = field(default_factory=list)

    @property
    def best(self) -> Design | None:
        return self.designs[0] if self.designs else None


def _constraint_ok(con: Constraint, value: float) -> bool:
    if con.op is Op.LE:
        return con.upper is None or value <= con.upper + 1e-9
    if con.op is Op.GE:
        return con.lower is None or value >= con.lower - 1e-9
    lo = con.lower if con.lower is not None else float("-inf")
    hi = con.upper if con.upper is not None else float("inf")
    return lo - 1e-9 <= value <= hi + 1e-9


class OptimizationRunner:
    def __init__(self, base_config: VehicleConfig, engine: BrakeEngine | None = None) -> None:
        self.base_config = base_config
        self.engine = engine or BrakeEngine()

    def _metrics_for(self, config: VehicleConfig) -> dict[str, float]:
        results = self.engine.solve(config)
        return {k: METRICS[k].getter(results, config) for k in all_available_keys()}

    def _apply(self, values: dict[str, float]) -> VehicleConfig:
        config = copy.deepcopy(self.base_config)
        for path, value in values.items():
            set_by_path(config, path, value)
        return config

    def run(self, problem: OptimizationProblem) -> OptimizationResult:
        base_metrics = self._metrics_for(self.base_config)
        objectives = [o for o in problem.enabled_objectives() if METRICS[o.metric_key].available]
        constraints = [c for c in problem.enabled_constraints() if METRICS[c.metric_key].available]

        def score(metrics: dict[str, float]) -> float:
            total = 0.0
            for obj in objectives:
                value = metrics[obj.metric_key]
                scale = abs(base_metrics[obj.metric_key]) or 1.0
                if obj.sense is Sense.MIN:
                    term = value / scale
                elif obj.sense is Sense.MAX:
                    term = -value / scale
                else:  # TARGET
                    term = abs(value - obj.target) / scale
                total += obj.weight * term
            return total

        def evaluate(values: dict[str, float]) -> Evaluation:
            config = self._apply(values)
            metrics = self._metrics_for(config)
            violations = [
                METRICS[c.metric_key].label
                for c in constraints
                if not _constraint_ok(c, metrics[c.metric_key])
            ]
            return Evaluation(values, metrics, score(metrics), not violations, violations)

        optimizer = get_optimizer(problem.settings.algorithm)
        evaluations = optimizer.optimize(problem, evaluate)
        designs = [Design(self._apply(ev.values), ev) for ev in evaluations]

        messages: list[str] = []
        if not objectives:
            messages.append("No objectives selected — designs are ranked only by constraint feasibility.")
        if designs and not designs[0].evaluation.feasible:
            messages.append("No fully feasible design found — try relaxing constraints or widening variable ranges.")
        return OptimizationResult(designs, problem, base_metrics, copy.deepcopy(self.base_config), messages)
