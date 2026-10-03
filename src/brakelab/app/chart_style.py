"""Use installed chart fonts without repeated missing-font warnings."""

import sys

import matplotlib
from matplotlib import font_manager


def apply_chart_fonts():
    installed = {font.name for font in font_manager.fontManager.ttflist}
    preferred = (["Segoe UI", "Arial", "DejaVu Sans"] if sys.platform.startswith("win")
                 else ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"])
    matplotlib.rcParams["font.family"] = [name for name in preferred if name in installed] or ["DejaVu Sans"]
