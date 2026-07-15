"""Stopping-distance panel on the Simulator page — actual vs. design-target stop.

Shows, for the braking-test speeds, how far and how long the car takes to stop:

- **Actual** — at the deceleration the current driver pedal force actually produces (from the forward
  simulator). This is the real stopping performance of the setup.
- **Design target** — at the *target deceleration* set on the Main tab (the deceleration the whole
  design is sized to achieve). This is the goal; comparing it with the actual shows whether the setup
  meets its own target.

A speed-vs-distance curve draws both, so the gap is visible at a glance. Rebuilt on every edit.
"""

from __future__ import annotations

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QLabel, QTableWidgetItem, QVBoxLayout, QWidget

matplotlib.rcParams["font.family"] = ["Helvetica", "Helvetica Neue", "Arial", "DejaVu Sans"]

from ...core.performance import braking_speeds, speed_profile, stopping_distance_time
from .. import theme
from ..controller import ProjectController
from ..uikit import fit_table, muted, plain_table


class StoppingPanel(QWidget):
    """Actual vs. design-target stopping distance/time, with a speed-vs-distance chart."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._table = plain_table(["", "Distance", "Time"])
        layout.addWidget(self._table)

        self._note = QLabel("")
        self._note.setWordWrap(True)
        muted(self._note, theme.muted_text())
        layout.addWidget(self._note)

        self._figure = Figure(figsize=(6, 3.0), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(220)
        layout.addWidget(self._canvas, 1)

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    def refresh(self, *_args) -> None:
        config = self._controller.config
        results = self._controller.results
        fwd = getattr(results, "forward", None)
        vi, vf = braking_speeds(config)
        a_actual = fwd.actual_decel_g if fwd is not None else 0.0
        a_target = config.target_decel_g

        da, ta = stopping_distance_time(vi, vf, a_actual)
        dt, tt = stopping_distance_time(vi, vf, a_target)

        def cell(x: float, unit: str) -> str:
            return "—" if x == float("inf") else f"{x:.1f} {unit}" if unit == "m" else f"{x:.2f} {unit}"

        rows = [
            (f"Actual ({a_actual:.2f} g)", cell(da, "m"), cell(ta, "s")),
            (f"Design target ({a_target:.2f} g)", cell(dt, "m"), cell(tt, "s")),
        ]
        self._table.setRowCount(len(rows))
        for i, (label, dist, time) in enumerate(rows):
            for j, text in enumerate((label, dist, time)):
                self._table.setItem(i, j, QTableWidgetItem(text))
        fit_table(self._table)

        end = "to a stop" if not config.performance.custom_final_speed else f"to {vf * 3.6:.0f} km/h"
        self._note.setText(
            f"Braking from {vi * 3.6:.0f} km/h {end}. 'Actual' is what the current pedal force produces; "
            "'Design target' is the target deceleration set on the Main tab (the design goal).")
        self._draw(vi, vf, a_actual, a_target)

    def _draw(self, vi: float, vf: float, a_actual: float, a_target: float) -> None:
        fg = "#e8e8e8" if theme.is_dark() else "#1a1a1a"
        bg = "#161616" if theme.is_dark() else "#ffffff"
        self._figure.clear()
        self._figure.set_facecolor(bg)
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(bg)

        xa, va = speed_profile(vi, vf, a_actual)
        xt, vt = speed_profile(vi, vf, a_target)
        ax.plot(xa, [v * 3.6 for v in va], color=fg, linewidth=1.6, label=f"Actual ({a_actual:.2f} g)")
        ax.plot(xt, [v * 3.6 for v in vt], color=fg, linewidth=1.1, linestyle="--",
                label=f"Design target ({a_target:.2f} g)")
        ax.set_xlabel("Distance (m)", color=fg, fontsize=8)
        ax.set_ylabel("Speed (km/h)", color=fg, fontsize=8)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.grid(True, alpha=0.25)
        legend = ax.legend(fontsize=7, loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color(fg)
        self._canvas.draw_idle()
