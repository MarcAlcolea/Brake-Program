"""Interactive plot: line pressure & required pedal force vs target deceleration.

Sweeps the deceleration target using the same engine and marks the current operating point, so the
driver/designer can see headroom at a glance. Rebuilt whenever the config changes.
"""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...analyses import SensitivityAnalysis
from ...core.engine import BrakeEngine
from ..controller import ProjectController


class PlotPanel(QWidget):
    """A matplotlib canvas showing a deceleration sweep of key outputs."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._engine = BrakeEngine()

        self._figure = Figure(figsize=(5, 4), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        config = self._controller.config
        sweep = SensitivityAnalysis(
            parameter="target_decel_g",
            start=0.5,
            stop=max(2.0, config.target_decel_g),
            steps=30,
            outputs=("Front line pressure [MPa]", "Rear line pressure [MPa]"),
        )
        result = sweep.run(config, self._engine)

        self._figure.clear()
        ax = self._figure.add_subplot(111)
        for label, (xs, ys) in result.series.items():
            ax.plot(xs, ys, label=label)
        ax.axvline(config.target_decel_g, color="0.5", linestyle="--", linewidth=1, label="Current target")
        ax.set_xlabel("Target deceleration [g]")
        ax.set_ylabel("Required line pressure [MPa]")
        ax.set_title("Line pressure vs deceleration")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        self._canvas.draw_idle()
