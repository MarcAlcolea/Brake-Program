"""Optimization — search for the best values of chosen design variables.

The user picks which variables to tune (master-cylinder bores, pedal ratio, balance bias, …) and
their allowed ranges, plus a plain-language goal. A lightweight search (random sampling followed by
a coordinate-descent polish) finds values that best meet the goal while keeping pedal travel in range
and satisfying the hard braking requirements. The engine solve is cheap, so this needs no external
optimizer library.

Goals (all minimise a simple, explainable quantity):
- "Least driver effort": minimise the pedal force the driver must apply to meet both axles.
- "Balanced front/rear braking": make the front and rear reach their limits together.
- "Centre the pedal travel": bring pedal travel to the middle of the desirable range.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Callable

from ..core.attrpath import get_by_path, set_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults

_PENALTY = 1e6


@dataclass
class OptVariable:
    """A design variable to optimise, with its inclusive search bounds."""

    path: str
    label: str
    unit: str
    minimum: float
    maximum: float


def _required_driver_force(r: BrakeResults, c: VehicleConfig) -> float:
    """Pedal force the driver must apply for both axles to meet their requirement."""
    return max(r.hydraulics.bar_force_front, r.hydraulics.bar_force_rear) / c.pedal_box.pedal_ratio


#: goal key -> (description, cost function to minimise)
GOALS: dict[str, tuple[str, Callable[[BrakeResults, VehicleConfig], float]]] = {
    "Least driver effort": (
        "Minimise the pedal force the driver must apply to lock both axles. Lower is easier to "
        "modulate and leaves more braking margin.",
        _required_driver_force,
    ),
    "Balanced front/rear braking": (
        "Make the front and rear need the same pedal force, so neither axle is the sole limit.",
        lambda r, c: abs(r.hydraulics.bar_force_front - r.hydraulics.bar_force_rear),
    ),
    "Centre the pedal travel": (
        "Bring pedal travel to the middle of the desirable range for good feel.",
        lambda r, c: abs(r.pedal_travel.pedal_travel - 45.0),
    ),
}


@dataclass
class OptResult:
    config: VehicleConfig                 # optimized configuration
    values: dict[str, float]              # optimized value per variable path
    goal: str
    objective_value: float                # the goal cost at the optimum (excludes penalties)
    feasible: bool                        # all hard requirements met at the optimum
    improved: bool                        # better than the starting point
    messages: list[str] = field(default_factory=list)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def optimize(
    base: VehicleConfig,
    variables: list[OptVariable],
    goal: str,
    engine: BrakeEngine,
    travel_range: tuple[float, float] = (30.0, 60.0),
    iterations: int = 4000,
    seed: int = 0,
) -> OptResult:
    """Find variable values that best meet ``goal`` within bounds and constraints."""
    if not variables:
        return OptResult(copy.deepcopy(base), {}, goal, 0.0, False, False, ["No variables selected to optimize."])
    if goal not in GOALS:
        raise ValueError(f"Unknown goal {goal!r}")

    _, cost_fn = GOALS[goal]
    tmin, tmax = travel_range
    rng = random.Random(seed)

    def total_cost(values: list[float]) -> tuple[float, float, bool]:
        cfg = copy.deepcopy(base)
        for var, val in zip(variables, values):
            set_by_path(cfg, var.path, val)
        r = engine.solve(cfg)
        goal_cost = cost_fn(r, cfg)

        penalty = 0.0
        travel = r.pedal_travel.pedal_travel
        if travel < tmin:
            penalty += _PENALTY * (tmin - travel)
        elif travel > tmax:
            penalty += _PENALTY * (travel - tmax)
        for req in r.requirements:
            if req.hard and not req.passed:
                penalty += _PENALTY
        feasible = all(req.passed for req in r.requirements if req.hard)
        return goal_cost + penalty, goal_cost, feasible

    start = [_clamp(get_by_path(base, v.path), v.minimum, v.maximum) for v in variables]
    best = list(start)
    best_total, best_goal, best_feasible = total_cost(best)
    start_total = best_total

    # Global random sampling.
    for _ in range(iterations):
        cand = [rng.uniform(v.minimum, v.maximum) for v in variables]
        total, goal_cost, feasible = total_cost(cand)
        if total < best_total:
            best, best_total, best_goal, best_feasible = cand, total, goal_cost, feasible

    # Local coordinate-descent polish.
    step = 0.25  # fraction of each variable's range
    for _ in range(60):
        improved = False
        for j, var in enumerate(variables):
            span = var.maximum - var.minimum
            for delta in (step * span, -step * span):
                cand = list(best)
                cand[j] = _clamp(best[j] + delta, var.minimum, var.maximum)
                total, goal_cost, feasible = total_cost(cand)
                if total < best_total - 1e-12:
                    best, best_total, best_goal, best_feasible = cand, total, goal_cost, feasible
                    improved = True
        if not improved:
            step *= 0.5
            if step < 1e-4:
                break

    optimized = copy.deepcopy(base)
    for var, val in zip(variables, best):
        set_by_path(optimized, var.path, val)
    values = {var.path: val for var, val in zip(variables, best)}

    messages: list[str] = []
    if not best_feasible:
        messages.append("No feasible solution found within the given bounds — try widening the ranges.")
    return OptResult(
        config=optimized,
        values=values,
        goal=goal,
        objective_value=best_goal,
        feasible=best_feasible,
        improved=best_total < start_total - 1e-9,
        messages=messages,
    )
