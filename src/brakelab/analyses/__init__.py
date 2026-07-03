"""Pluggable analyses that consume a config + engine (the extensibility seam)."""

from .base import Analysis, AnalysisResult
from .sensitivity import SensitivityAnalysis

__all__ = ["Analysis", "AnalysisResult", "SensitivityAnalysis"]
