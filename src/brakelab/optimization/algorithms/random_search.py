"""Built-in, dependency-free optimizer: random sampling with a coordinate-descent polish.

Robust for the small, cheap problems here (an engine solve is microseconds). Ranking prefers
feasible designs, then lower objective score. This is the default backend; heavier optimizers can be
registered alongside it without any UI change.
"""

from __future__ import annotations

import random

from ..problem import OptimizationProblem, Variable
from .base import Evaluation, Evaluator, Optimizer


def _ranked(evals: list[Evaluation]) -> list[Evaluation]:
    return sorted(evals, key=lambda e: (0 if e.feasible else 1, e.score))


def _sample(var: Variable, rng: random.Random) -> float:
    if var.discrete:
        return rng.choice(var.choices)
    return rng.uniform(var.minimum, var.maximum)


def _start_value(var: Variable) -> float:
    mid = (var.minimum + var.maximum) / 2
    if var.discrete:
        return min(var.choices, key=lambda c: abs(c - mid))
    return mid


def _neighbors(var: Variable, current: float, step: float) -> list[float]:
    """Candidate moves for the polish pass — adjacent choices for discrete, +/- step for continuous."""
    if var.discrete:
        ordered = sorted(var.choices)
        idx = min(range(len(ordered)), key=lambda i: abs(ordered[i] - current))
        return [ordered[i] for i in (idx - 1, idx + 1) if 0 <= i < len(ordered)]
    span = var.maximum - var.minimum
    return [min(var.maximum, current + step * span), max(var.minimum, current - step * span)]


class RandomSearchOptimizer(Optimizer):
    name = "Random search"

    def optimize(self, problem: OptimizationProblem, evaluate: Evaluator) -> list[Evaluation]:
        variables = problem.enabled_variables()
        if not variables:
            return []
        rng = random.Random(problem.settings.seed)
        collected: list[Evaluation] = []

        # Start from a central value, then sample the space (discrete vars draw from their choices).
        collected.append(evaluate({v.path: _start_value(v) for v in variables}))
        for _ in range(max(1, problem.settings.iterations)):
            collected.append(evaluate({v.path: _sample(v, rng) for v in variables}))

        best = _ranked(collected)[0]

        # Coordinate-descent polish around the best.
        step = 0.25
        for _ in range(60):
            improved = False
            for v in variables:
                for value in _neighbors(v, best.values[v.path], step):
                    trial = dict(best.values)
                    trial[v.path] = value
                    cand = evaluate(trial)
                    collected.append(cand)
                    if _ranked([cand, best])[0] is cand and cand is not best:
                        best, improved = cand, True
            if not improved:
                step *= 0.5
                if step < 1e-4:
                    break

        # Rank all, de-duplicate near-identical designs, return the requested number of alternatives.
        ranked = _ranked(collected)
        unique: list[Evaluation] = []
        seen: set[tuple] = set()
        for e in ranked:
            key = tuple(round(e.values[v.path], 4) for v in variables)
            if key not in seen:
                seen.add(key)
                unique.append(e)
            if len(unique) >= max(1, problem.settings.alternatives):
                break
        return unique
