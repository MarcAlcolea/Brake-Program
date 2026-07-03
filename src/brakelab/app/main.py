"""Main window: a simple, tabbed, light-or-dark layout.

- "Design" tab: a configuration bar (presets, save/rename, import/export) on top; INPUTS on the
  left; REQUIREMENTS (top) and OUTPUTS (bottom) on the right; a Details area along the bottom that
  shows the note/formula for whatever ⓘ you click (no external pop-ups).
- "Optimize" tab: the optimization studio.
- "Compare" tab: two saved configurations side by side.
- "Plots" tab: charts, kept separate.

A toggle button in the tab-bar corner switches light/dark; the theme is applied globally (``theme``).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
from .panels.optimization_tab import OptimizationTab
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
        self._optimize = OptimizationTab(self.controller, library)
        self._outputs = OutputsPanel(self.controller, self._details.show_details)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_design_tab(), "Design")
        self._tabs.addTab(self._optimize, "Optimize")
        self._tabs.addTab(self._compare, "Compare")
        self._tabs.addTab(PlotPanel(self.controller), "Plots")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs.setCornerWidget(self._build_corner(), Qt.TopRightCorner)
        self.setCentralWidget(self._tabs)

        self.controller.configReplaced.connect(lambda c: self._set_title(c.name))
        self._set_title(controller.config.name)

    def _on_tab_changed(self, _index: int) -> None:
        widget = self._tabs.currentWidget()
        if widget is self._compare:
            self._compare.reload_configs()
        elif widget is self._optimize:
            self._optimize.refresh_current()

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

    def _build_corner(self) -> QWidget:
        """Controls that live in the tab-bar's top-right corner (no extra top row)."""
        corner = QWidget()
        row = QHBoxLayout(corner)
        row.setContentsMargins(0, 0, 6, 0)
        row.setSpacing(6)

        export = QPushButton("Export PDF…")
        export.clicked.connect(self._report)
        row.addWidget(export)

        self._theme_btn = QPushButton()
        self._theme_btn.clicked.connect(self._toggle_dark)
        self._update_theme_button()
        row.addWidget(self._theme_btn)
        return corner

    def _update_theme_button(self) -> None:
        self._theme_btn.setText("Switch to Light Mode" if theme.is_dark() else "Switch to Dark Mode")

    def _toggle_dark(self) -> None:
        app = QApplication.instance()
        if app:
            theme.apply_theme(app, dark=not theme.is_dark())
            self._update_theme_button()
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
