"""Sensitivity tab — which inputs most affect a chosen output.

Pick any output; the panel perturbs every numeric input a little, re-solves, and draws a tornado
chart of each input's *elasticity* (percent change in the output per percent change in the input).
Sorted longest-first, it answers "what should I focus on to move this number?" — bars to the right
push the output up, bars to the left push it down. Monochrome, theme-aware, rebuilt on any change.
"""

from __future__ import annotations

import copy

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Match the app's Helvetica typography in the charts too (falls back gracefully if unavailable).
matplotlib.rcParams["font.family"] = ["Helvetica", "Helvetica Neue", "Arial", "DejaVu Sans"]

from ...core.attrpath import get_by_path, set_by_path
from ...core.engine import BrakeEngine
from .. import theme
from ..controller import ProjectController
from ..field_spec import GROUPS as INPUT_GROUPS
from ..output_spec import GROUPS as OUTPUT_GROUPS
from ..uikit import style_combo

# Outputs to surface first in the picker (most-used design targets), by label. Anything not listed
# follows in spec order.
_KEY_OUTPUTS = (
    "Pedal Travel (Trav(pedal))",
    "Required Line Pressure (Front) (P(f,line))",
    "Required Line Pressure (Rear) (P(r,line))",
    "Force required into Balance Bar (Front) (F(f,bar))",
    "Required Clamp Force (Front) (F(f,clamp))",
    "Dynamic Front Axle Load During Braking (W(f,dyn))",
)
_MAX_BARS = 12


class SensitivityPanel(QWidget):
    """Tornado chart of input influence on a selected output."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._engine = BrakeEngine()

        self._outputs = self._ordered_outputs()
        self._inputs = [f for g in INPUT_GROUPS for f in g.fields if f.kind in ("float", "int")]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        hint = QLabel("Longer bars = focus there to move this number; bars to the right raise it, to "
                      "the left lower it.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.muted_text()};")
        layout.addWidget(hint)

        picker = QHBoxLayout()
        picker.addWidget(QLabel("Output:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(320)
        self._combo.setMaxVisibleItems(20)
        self._combo.addItems([o.label for o in self._outputs])
        style_combo(self._combo)
        self._combo.currentIndexChanged.connect(self.refresh)
        picker.addWidget(self._combo)
        picker.addStretch(1)
        layout.addLayout(picker)

        self._figure = Figure(figsize=(6, 4.6), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout.addWidget(self._canvas, 1)

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    def _ordered_outputs(self):
        flat = [o for g in OUTPUT_GROUPS for o in g.outputs]
        by_label = {o.label: o for o in flat}
        head = [by_label[l] for l in _KEY_OUTPUTS if l in by_label]
        rest = [o for o in flat if o.label not in set(_KEY_OUTPUTS)]
        return head + rest

    # ---- computation ------------------------------------------------------------------------
    def _elasticity(self, output, field, config, base_out: float) -> float | None:
        """Central-difference elasticity of ``output`` w.r.t. ``field``: (%Δout)/(%Δin)."""
        v = float(get_by_path(config, field.path))
        step = 1.0 if field.kind == "int" else max(abs(v) * 0.01, 1e-4)
        try:
            hi = copy.deepcopy(config)
            set_by_path(hi, field.path, round(v + step) if field.kind == "int" else v + step)
            lo = copy.deepcopy(config)
            set_by_path(lo, field.path, round(v - step) if field.kind == "int" else v - step)
            o_hi = output.getter(self._engine.solve(hi), hi)
            o_lo = output.getter(self._engine.solve(lo), lo)
        except Exception:  # noqa: BLE001
            return None
        d_out = (o_hi - o_lo) / 2.0
        if abs(base_out) < 1e-12 or abs(v) < 1e-12:
            return None
        return (d_out / base_out) / (step / v)

    def refresh(self, *_args) -> None:
        output = self._outputs[max(0, self._combo.currentIndex())]
        config = self._controller.config
        try:
            base_out = output.getter(self._controller.results, config)
        except Exception:  # noqa: BLE001
            base_out = 0.0

        scored = []
        for field in self._inputs:
            e = self._elasticity(output, field, config, base_out)
            if e is not None and abs(e) > 1e-6:
                scored.append((field.label, e))
        scored.sort(key=lambda t: abs(t[1]), reverse=True)
        scored = scored[:_MAX_BARS]

        fg = "#e8e8e8" if theme.is_dark() else "#1a1a1a"
        bg = "#161616" if theme.is_dark() else "#ffffff"
        bar = "#b0b0b0" if theme.is_dark() else "#333333"
        self._figure.clear()
        self._figure.set_facecolor(bg)
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(bg)

        if not scored:
            ax.text(0.5, 0.5, "No measurable sensitivity for this output.", ha="center", va="center",
                    color=fg, fontsize=9, transform=ax.transAxes)
            ax.axis("off")
            self._canvas.draw_idle()
            return

        labels = [lbl for lbl, _ in scored][::-1]   # largest at top
        values = [e for _, e in scored][::-1]
        y = range(len(labels))
        ax.barh(list(y), values, color=bar, edgecolor=fg, linewidth=0.4)
        ax.axvline(0, color=fg, linewidth=0.8)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=7, color=fg)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.set_xlabel("Elasticity  (% change in output per % change in input)", color=fg, fontsize=8)
        ax.set_title(f"What moves: {output.label}", color=fg, fontsize=9)
        ax.grid(True, axis="x", alpha=0.25)
        self._canvas.draw_idle()


# Backwards-compatible alias (older imports referred to PlotPanel).
PlotPanel = SensitivityPanel
