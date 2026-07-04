"""Algorithm-independent definition of an optimization problem.

A problem is *what* to optimize (variables, objectives, constraints, settings) with no reference to
*how* (the search algorithm). This separation lets new algorithms (SciPy, genetic, CasADi,
OpenMDAO) be added without touching the UI or these definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Sense(str, Enum):
    MIN = "Minimize"
    MAX = "Maximize"
    TARGET = "Target"


class Op(str, Enum):
    LE = "le"        # value <= upper
    GE = "ge"        # value >= lower
    RANGE = "range"  # lower <= value <= upper


@dataclass
class Variable:
    path: str          # dotted config path the optimizer may change
    label: str
    unit: str
    minimum: float
    maximum: float
    enabled: bool = True
    choices: list[float] | None = None  # if set, a DISCRETE variable (e.g. real catalog bore sizes)

    @property
    def discrete(self) -> bool:
        return bool(self.choices)


@dataclass
class Objective:
    metric_key: str
    sense: Sense = Sense.MIN
    target: float = 0.0     # used when sense is TARGET
    weight: float = 1.0
    enabled: bool = True


@dataclass
class Constraint:
    metric_key: str
    op: Op = Op.LE
    lower: float | None = None
    upper: float | None = None
    enabled: bool = True


@dataclass
class Settings:
    algorithm: str = "Random search"
    iterations: int = 3000     # search budget (hidden behind an "effort" preset in the UI)
    alternatives: int = 5      # how many ranked feasible designs to keep
    seed: int = 0


#: Effort presets map a friendly label to a search budget (algorithm details stay hidden).
EFFORT_PRESETS = {"Quick": 800, "Balanced": 3000, "Thorough": 12000}


@dataclass
class OptimizationProblem:
    variables: list[Variable] = field(default_factory=list)
    objectives: list[Objective] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def enabled_variables(self) -> list[Variable]:
        return [v for v in self.variables if v.enabled]

    def enabled_objectives(self) -> list[Objective]:
        return [o for o in self.objectives if o.enabled]

    def enabled_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.enabled]
