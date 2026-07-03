"""The extensibility seam: an ``Analysis`` runs a study over a config and the engine.

Everything beyond the base calculation — sensitivity sweeps, optimization, Monte Carlo, telemetry
comparison, thermal duty cycles — is an :class:`Analysis`. New capability is a new subclass plus
(optionally) one GUI panel; the core never changes. This is what keeps the project extensible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig


@dataclass
class AnalysisResult:
    """Generic result container. ``series`` holds named x/y data for plotting; ``summary`` holds
    scalar takeaways; ``table`` holds row dicts for tabular display/report."""

    title: str
    series: dict[str, tuple[list[float], list[float]]] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    table: list[dict[str, Any]] = field(default_factory=list)


class Analysis(ABC):
    """Base class for all analyses."""

    #: Human-readable name shown in the UI / registry.
    name: str = "analysis"

    @abstractmethod
    def run(self, config: VehicleConfig, engine: BrakeEngine) -> AnalysisResult:
        """Run the analysis and return its result."""
        raise NotImplementedError
