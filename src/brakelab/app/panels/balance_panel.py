"""Brake balance diagram panel on the Simulator page — front vs. rear brake force.

Draws the classic brake-balance chart for the current config: the ideal-distribution parabola (both
axles locking together), the design's actual fixed front:rear split as a straight line, iso-
deceleration lines, and the operating point at the design pedal force. A one-line verdict states which
axle locks first and at what deceleration. Rebuilt on every input change, like the rest of the app.
"""

from __future__ import annotations

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

matplotlib.rcParams["font.family"] = ["Helvetica", "Helvetica Neue", "Arial", "DejaVu Sans"]

from ...core.balance import BalanceDiagram, brake_balance
from .. import theme
from ..controller import ProjectController
from ..uikit import muted


class BalancePanel(QWidget):
    """The brake balance diagram for the current configuration."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._result: BalanceDiagram | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._verdict = QLabel("")
        self._verdict.setWordWrap(True)
        muted(self._verdict, theme.muted_text())
        layout.addWidget(self._verdict)

        self._figure = Figure(figsize=(5.2, 4.4), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(320)
        layout.addWidget(self._canvas, 1)

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    def refresh(self, *_args) -> None:
        try:
            self._result = brake_balance(self._controller.config)
        except Exception:  # noqa: BLE001 — never let a bad input crash the page
            self._result = None
        self._update_verdict()
        self._draw()

    def _update_verdict(self) -> None:
        bd = self._result
        if bd is None:
            self._verdict.setText("Brake balance unavailable for these inputs.")
            return
        who = "Front" if bd.front_locks_first else "Rear"
        if bd.usable_decel != float("inf"):
            self._verdict.setText(
                f"{who} axle locks first, at about {bd.usable_decel:.2f} g. "
                "Below the ideal curve the front locks first (stable); above it the rear locks first.")
        else:
            self._verdict.setText(f"{who} axle is the first toward its grip limit.")

    def _draw(self) -> None:
        fg = "#e8e8e8" if theme.is_dark() else "#1a1a1a"
        bg = "#161616" if theme.is_dark() else "#ffffff"
        ideal_c = "#8a8a8a"
        iso_c = "#6f6f6f" if theme.is_dark() else "#c2c2c2"
        self._figure.clear()
        self._figure.set_facecolor(bg)
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(bg)

        bd = self._result
        if bd is None:
            ax.axis("off")
            self._canvas.draw_idle()
            return

        ax.plot(bd.ideal_front, bd.ideal_rear, color=ideal_c, linewidth=1.4, label="Ideal distribution")
        ax.plot(bd.actual_front, bd.actual_rear, color=fg, linewidth=1.6, label="Actual (this design)")
        for a in bd.iso_decels:
            total = a * bd.weight
            ax.plot([0, total], [total, 0], color=iso_c, linewidth=0.8, linestyle=":")
            ax.annotate(f"{a:g} g", xy=(total * 0.02, total * 0.98), fontsize=6.5, color=ideal_c)
        ax.plot([bd.op_front], [bd.op_rear], marker="o", color=fg, markersize=5,
                label="Design pedal force")

        top = max(max(bd.ideal_front, default=1), max(bd.ideal_rear, default=1),
                  bd.op_front, bd.op_rear) * 1.05
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
        ax.set_xlabel("Front brake force (N)", color=fg, fontsize=8)
        ax.set_ylabel("Rear brake force (N)", color=fg, fontsize=8)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.grid(True, alpha=0.25)
        legend = ax.legend(fontsize=7, loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color(fg)
        self._canvas.draw_idle()
