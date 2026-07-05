"""Main window: a left sidebar selects pages shown in a stacked area.

- Design: configuration bar on top; components + inputs on the left, requirements + outputs on the
  right (one scroll per column). Clicking any ⓘ opens a popover next to it.
- Optimize / Compare / Plots: the optimization studio, side-by-side comparison, and charts.

The sidebar footer holds the light/dark toggle and PDF export. One simple, flat theme (see ``theme``).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.models import VehicleConfig
from ..persistence import ConfigLibrary
from . import theme
from .controller import ProjectController
from .panels.compare_tab import CompareTab
from .panels.components_panel import ComponentsPanel
from .panels.config_bar import ConfigBar
from .panels.input_panel import InputPanel
from .panels.optimization_tab import OptimizationTab
from .panels.outputs_panel import OutputsPanel
from .panels.requirements_panel import RequirementsPanel
from .plots.plot_panel import PlotPanel
from .widgets import ClickableLabel

_PAGES = ["Design", "Optimize", "Compare", "Plots"]


class MainWindow(QMainWindow):
    def __init__(self, controller: ProjectController, library: ConfigLibrary) -> None:
        super().__init__()
        self.resize(1240, 840)
        self.controller = controller
        self.library = library

        self._outputs = OutputsPanel(self.controller)
        self._compare = CompareTab(library)
        self._optimize = OptimizationTab(self.controller, library)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._design_page())
        self._stack.addWidget(self._optimize)
        self._stack.addWidget(self._compare)
        self._stack.addWidget(PlotPanel(self.controller))

        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._sidebar())
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet(f"color: {theme.border_color()};")
        row.addWidget(divider)
        row.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self.controller.configReplaced.connect(lambda c: self._set_title(c.name))
        self._set_title(controller.config.name)
        self._select_page(0)

    # ---- sidebar ----------------------------------------------------------------------------
    def _sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(168)
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 14, 8, 12)
        v.setSpacing(10)

        self._nav_labels: list[ClickableLabel] = []
        for i, name in enumerate(_PAGES):
            label = ClickableLabel(name)
            label.setFont(theme.heading_font(14, bold=False))
            label.clicked.connect(lambda idx=i: self._select_page(idx))
            self._nav_labels.append(label)
            v.addWidget(label)
        v.addStretch(1)

        self._theme_btn = QPushButton()
        self._theme_btn.clicked.connect(self._toggle_dark)
        self._update_theme_button()
        v.addWidget(self._theme_btn)

        export = QPushButton("Export PDF…")
        export.clicked.connect(self._report)
        v.addWidget(export)
        return panel

    def _select_page(self, index: int) -> None:
        for j, label in enumerate(self._nav_labels):
            label.setFont(theme.heading_font(14, bold=(j == index)))
        self._stack.setCurrentIndex(index)
        if self._stack.currentWidget() is self._compare:
            self._compare.reload_configs()
        elif self._stack.currentWidget() is self._optimize:
            self._optimize.refresh_current()

    # ---- design page ------------------------------------------------------------------------
    def _design_page(self) -> QWidget:
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)
        lv.addWidget(ComponentsPanel(self.controller))
        lv.addWidget(InputPanel(self.controller))
        lv.addStretch(1)
        left_scroll = _scroll(left)
        left_scroll.setMinimumWidth(430)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 4, 4, 4)
        rv.addWidget(RequirementsPanel(self.controller))
        rv.addWidget(self._outputs)
        rv.addStretch(1)
        right_scroll = _scroll(right)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(6, 6, 6, 2)
        v.addWidget(ConfigBar(self.controller, self.library))
        v.addWidget(splitter, 1)
        return page

    # ---- theme / actions --------------------------------------------------------------------
    def _update_theme_button(self) -> None:
        self._theme_btn.setText("Switch to light" if theme.is_dark() else "Switch to dark")

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


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setWidget(widget)
    return area


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
