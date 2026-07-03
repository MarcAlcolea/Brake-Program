"""Optimizer registry — map an algorithm name to its implementation.

Register new backends here (SciPy, genetic, CasADi, OpenMDAO); the UI reads ``ALGORITHMS`` so new
entries appear automatically.
"""

from __future__ import annotations

from .base import Evaluation, Evaluator, Optimizer
from .random_search import RandomSearchOptimizer

ALGORITHMS: dict[str, type[Optimizer]] = {
    RandomSearchOptimizer.name: RandomSearchOptimizer,
}


def get_optimizer(name: str) -> Optimizer:
    if name not in ALGORITHMS:
        raise ValueError(f"Unknown optimizer {name!r}. Available: {list(ALGORITHMS)}")
    return ALGORITHMS[name]()


__all__ = ["Optimizer", "Evaluation", "Evaluator", "RandomSearchOptimizer", "ALGORITHMS", "get_optimizer"]
