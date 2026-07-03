"""Main window: a tabbed layout with a bare-bones, consistent look.

- "Design" tab: INPUTS on the left; REQUIREMENTS (top) and OUTPUTS (bottom) on the right. Editing
  any input recomputes live and refreshes the outputs and requirements.
- "Plots" tab: charts, kept separate so they never crowd the numbers (more plots to come).

No custom stylesheets — default Qt widgets throughout.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import reference_configs
from ..core.models import VehicleConfig
from .controller import ProjectController
from .panels.input_panel import InputPanel
from .panels.outputs_panel import OutputsPanel
from .panels.requirements_panel import RequirementsPanel
from .plots.plot_panel import PlotPanel

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"


class MainWindow(QMainWindow):
    def __init__(self, config: VehicleConfig) -> None:
        super().__init__()
        self.resize(1200, 820)
        self.controller = ProjectController(config)

        tabs = QTabWidget()
        tabs.addTab(self._build_design_tab(), "Design")
        tabs.addTab(self._build_plots_tab(), "Plots")
        self.setCentralWidget(tabs)

        self._build_toolbar()
        self.controller.configReplaced.connect(lambda c: self._set_title(c.name))
        self._set_title(config.name)

    def _build_design_tab(self) -> QWidget:
        inputs = QScrollArea()
        inputs.setWidgetResizable(True)
        inputs.setWidget(InputPanel(self.controller))
        inputs.setMinimumWidth(360)

        right = QSplitter(Qt.Vertical)
        right.addWidget(RequirementsPanel(self.controller))
        right.addWidget(OutputsPanel(self.controller))
        right.setStretchFactor(0, 0)
        right.setStretchFactor(1, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(inputs)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        return wrapper

    def _build_plots_tab(self) -> QWidget:
        return PlotPanel(self.controller)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main")
        self.addToolBar(bar)
        for text, slot in (("Open…", self._open), ("Save…", self._save), ("Export PDF…", self._report)):
            action = QAction(text, self)
            action.triggered.connect(slot)
            bar.addAction(action)

    def _set_title(self, name: str) -> None:
        self.setWindowTitle(f"BrakeLab — {name}")

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open configuration", str(_CONFIG_DIR), "JSON (*.json)")
        if path:
            try:
                self.controller.load(path)
            except Exception as exc:  # noqa: BLE001 — surface any load error to the user
                QMessageBox.critical(self, "Open failed", str(exc))

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save configuration", str(_CONFIG_DIR), "JSON (*.json)")
        if path:
            self.controller.save(path)

    def _report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF report", str(_CONFIG_DIR), "PDF (*.pdf)")
        if path:
            self.controller.export_report(path)
            QMessageBox.information(self, "Report exported", f"Saved to {path}")


def run(config: VehicleConfig | None = None) -> int:
    """Launch the GUI. Defaults to the 2026 baseline configuration."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(config or reference_configs.outboarded_x2())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
