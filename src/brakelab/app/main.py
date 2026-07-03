"""Main window: a simple, tabbed, light-or-dark layout.

- "Design" tab: a configuration bar (presets, save/rename, import/export) on top; INPUTS on the
  left; REQUIREMENTS (top) and OUTPUTS (bottom) on the right; a Details area along the bottom that
  shows the note/formula for whatever ⓘ you click (no external pop-ups).
- "Compare" tab: two saved configurations side by side.
- "Plots" tab: charts, kept separate.

A View menu toggles light/dark. The theme is applied globally (see ``theme``).
"""

from __future__ import annotations

import sys

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
    QVBoxLayout,
    QWidget,
)

from ..core.models import VehicleConfig
from ..persistence import ConfigLibrary
from . import theme
from .controller import ProjectController
from .panels.compare_tab import CompareTab
from .panels.config_bar import ConfigBar
from .panels.input_panel import InputPanel
from .panels.outputs_panel import OutputsPanel
from .panels.requirements_panel import RequirementsPanel
from .plots.plot_panel import PlotPanel
from .widgets import DetailsPanel


class MainWindow(QMainWindow):
    def __init__(self, controller: ProjectController, library: ConfigLibrary) -> None:
        super().__init__()
        self.resize(1280, 860)
        self.controller = controller
        self.library = library
        self._details = DetailsPanel()

        self._compare = CompareTab(library)
        self._outputs = OutputsPanel(self.controller, self._details.show_details)

        tabs = QTabWidget()
        tabs.addTab(self._build_design_tab(), "Design")
        tabs.addTab(self._compare, "Compare")
        tabs.addTab(PlotPanel(self.controller), "Plots")
        tabs.currentChanged.connect(lambda _i: self._compare.reload_configs())
        self.setCentralWidget(tabs)

        self._build_menu()
        self.controller.configReplaced.connect(lambda c: self._set_title(c.name))
        self._set_title(controller.config.name)

    def _build_design_tab(self) -> QWidget:
        inputs = QScrollArea()
        inputs.setWidgetResizable(True)
        inputs.setWidget(InputPanel(self.controller, self._details.show_details))
        inputs.setMinimumWidth(420)

        right = QSplitter(Qt.Vertical)
        right.addWidget(RequirementsPanel(self.controller, self._details.show_details))
        right.addWidget(self._outputs)
        right.setStretchFactor(0, 0)
        right.setStretchFactor(1, 1)

        body = QSplitter(Qt.Horizontal)
        body.addWidget(inputs)
        body.addWidget(right)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(ConfigBar(self.controller, self.library))
        layout.addWidget(body, 1)
        layout.addWidget(self._details)
        return wrapper

    def _build_menu(self) -> None:
        view = self.menuBar().addMenu("View")
        self._dark_action = QAction("Dark mode", self, checkable=True, checked=theme.is_dark())
        self._dark_action.triggered.connect(self._toggle_dark)
        view.addAction(self._dark_action)

        file_menu = self.menuBar().addMenu("File")
        report = QAction("Export PDF report…", self)
        report.triggered.connect(self._report)
        file_menu.addAction(report)

    def _toggle_dark(self, checked: bool) -> None:
        app = QApplication.instance()
        if app:
            theme.apply_theme(app, dark=checked)
            self._outputs.reset_highlights()

    def _set_title(self, name: str) -> None:
        self.setWindowTitle(f"BrakeLab — {name}")

    def _report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF report", f"{self.controller.config.name}.pdf", "PDF (*.pdf)")
        if path:
            self.controller.export_report(path)
            QMessageBox.information(self, "Report exported", f"Saved to {path}")


def run(config: VehicleConfig | None = None) -> int:
    """Launch the GUI. Seeds the library on first run and opens the default preset."""
    app = QApplication.instance() or QApplication(sys.argv)
    theme.apply_theme(app, dark=False)

    library = ConfigLibrary()
    library.seed_defaults()
    if config is None:
        config = library.load(library.default_name)

    controller = ProjectController(config)
    window = MainWindow(controller, library)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
