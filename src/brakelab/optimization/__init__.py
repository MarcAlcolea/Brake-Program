"""Optimization subsystem — separate from the calculation engine.

Public pieces:
- :mod:`.metrics` — the catalog of optimizable quantities.
- :mod:`.problem` — Variable / Objective / Constraint / Settings / OptimizationProblem.
- :mod:`.algorithms` — pluggable optimizers (default: random search).
- :class:`.runner.OptimizationRunner` — runs a problem against a config + brake engine, returns
  ranked :class:`.runner.Design` objects.
- :func:`.sensitivity.sensitivity` — which variables matter most.
- :func:`.report.build_optimization_report` — PDF summary.
"""

from .metrics import CONSTRAINT_DEFAULTS, METRICS, OBJECTIVE_KEYS, Metric
from .problem import (
    EFFORT_PRESETS,
    Constraint,
    Objective,
    Op,
    OptimizationProblem,
    Sense,
    Settings,
    Variable,
)
from .runner import Design, OptimizationResult, OptimizationRunner
from .sensitivity import Influence, sensitivity

__all__ = [
    "METRICS", "Metric", "OBJECTIVE_KEYS", "CONSTRAINT_DEFAULTS",
    "Variable", "Objective", "Constraint", "Settings", "OptimizationProblem", "Sense", "Op",
    "EFFORT_PRESETS", "OptimizationRunner", "OptimizationResult", "Design",
    "sensitivity", "Influence",
]
