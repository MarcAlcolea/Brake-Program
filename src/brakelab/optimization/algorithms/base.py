"""Optimizer interface — the seam for plugging in new search algorithms.

An optimizer only samples variable values and calls an ``evaluate`` callback that hides all the
domain detail (building a config, solving it, scoring objectives, checking constraints). Because the
optimizer never touches the brake model directly, SciPy / genetic / CasADi / OpenMDAO backends can be
added later by implementing this one method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from ..problem import OptimizationProblem


@dataclass
class Evaluation:
    """The outcome of evaluating one set of variable values."""

    values: dict[str, float]
    metrics: dict[str, float]
    score: float
    feasible: bool
    violations: list[str] = field(default_factory=list)


#: Callback signature: given variable values, return a full Evaluation.
Evaluator = Callable[[dict[str, float]], Evaluation]


class Optimizer(ABC):
    name: str = "optimizer"

    @abstractmethod
    def optimize(self, problem: OptimizationProblem, evaluate: Evaluator) -> list[Evaluation]:
        """Search the variable space and return evaluations ranked best-first."""
        raise NotImplementedError
