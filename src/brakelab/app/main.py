"""Main window: assembles the input, results and plot panels and the file actions.

Layout is a three-pane splitter — inputs (left, scrollable) · results (centre) · plot (right).
Editing any input recomputes live via the controller. Toolbar actions handle open/save/report.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QToolBar,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .. import reference_configs
from ..core.models import VehicleConfig
from .controller import ProjectController
from .panels.input_panel import InputPanel
from .panels.results_panel import ResultsPanel
from .plots.plot_panel import PlotPanel

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"


class MainWindow(QMainWindow):
    def __init__(self, config: VehicleConfig) -> None:
        super().__init__()
        self.setWindowTitle("BrakeLab — FSAE Brake Design Tool")
        self.resize(1280, 800)

        self.controller = ProjectController(config)

        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)
        input_scroll.setWidget(InputPanel(self.controller))
        input_scroll.setMinimumWidth(340)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(input_scroll)
        splitter.addWidget(ResultsPanel(self.controller))
        splitter.addWidget(PlotPanel(self.controller))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        self.setCentralWidget(splitter)

        self._build_toolbar()
        self.controller.configReplaced.connect(lambda c: self.setWindowTitle(f"BrakeLab — {c.name}"))
        self.setWindowTitle(f"BrakeLab — {config.name}")

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main")
        self.addToolBar(bar)
        for text, slot in (("Open…", self._open), ("Save…", self._save), ("Export PDF…", self._report)):
            action = QAction(text, self)
            action.triggered.connect(slot)
            bar.addAction(action)

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
