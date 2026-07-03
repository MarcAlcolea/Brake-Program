"""Built-in, dependency-free optimizer: random sampling with a coordinate-descent polish.

Robust for the small, cheap problems here (an engine solve is microseconds). Ranking prefers
feasible designs, then lower objective score. This is the default backend; heavier optimizers can be
registered alongside it without any UI change.
"""

from __future__ import annotations

import random

from ..problem import OptimizationProblem
from .base import Evaluation, Evaluator, Optimizer


def _ranked(evals: list[Evaluation]) -> list[Evaluation]:
    return sorted(evals, key=lambda e: (0 if e.feasible else 1, e.score))


class RandomSearchOptimizer(Optimizer):
    name = "Random search"

    def optimize(self, problem: OptimizationProblem, evaluate: Evaluator) -> list[Evaluation]:
        variables = problem.enabled_variables()
        if not variables:
            return []
        rng = random.Random(problem.settings.seed)
        collected: list[Evaluation] = []

        # Start from the current values, then sample the space.
        start = {v.path: (v.minimum + v.maximum) / 2 for v in variables}
        collected.append(evaluate(start))
        for _ in range(max(1, problem.settings.iterations)):
            values = {v.path: rng.uniform(v.minimum, v.maximum) for v in variables}
            collected.append(evaluate(values))

        best = _ranked(collected)[0]

        # Coordinate-descent polish around the best.
        step = 0.25
        for _ in range(60):
            improved = False
            for v in variables:
                span = v.maximum - v.minimum
                for delta in (step * span, -step * span):
                    trial = dict(best.values)
                    trial[v.path] = min(v.maximum, max(v.minimum, best.values[v.path] + delta))
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
