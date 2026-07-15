"""Main window: a left sidebar selects pages shown in a stacked area.

- Design: configuration bar on top; components + inputs on the left, requirements + outputs on the
  right (one scroll per column). Clicking any ⓘ opens a popover next to it.
- Optimize / Compare / Plots: the optimization studio, side-by-side comparison, and charts.

The sidebar footer holds the light/dark toggle and PDF export. One simple, flat theme (see ``theme``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
from .panels.forward_panel import ForwardStatusPanel
from .panels.input_panel import InputPanel
from .panels.optimization_tab import OptimizationTab
from .panels.outputs_panel import OutputsPanel
from .panels.report_tab import ReportTab
from .panels.requirements_panel import RequirementsPanel
from .panels.shared_info_panel import SharedInfoPanel
from .plots.plot_panel import SensitivityPanel
from .panels.material_panel import ThermalMaterialPanel
from .panels.thermal_sim_panel import ThermalSimPanel
from .panels.balance_panel import BalancePanel
from .uikit import muted
from .widgets import ClickableLabel, CollapsibleSection
from . import forward_spec, thermal_spec

_PAGES = ["Main", "Simulator", "Thermal", "Optimize", "Compare", "Sensitivity", "Report"]


class MainWindow(QMainWindow):
    def __init__(self, controller: ProjectController, library: ConfigLibrary) -> None:
        super().__init__()
        self.resize(1240, 840)
        self.controller = controller
        self.library = library

        self._outputs = OutputsPanel(self.controller)
        self._compare = CompareTab(library)
        self._optimize = OptimizationTab(self.controller, library)
        self._report = ReportTab(self.controller, library, optimization_result=lambda: self._optimize.latest_result)

        self._desc_labels: list[QLabel] = []
        self._stack = QStackedWidget()
        self._stack.addWidget(self._framed(
            "Design the brake system — choose components and check the pedal force and sizing needed "
            "to hit a target deceleration.", self._design_page()))
        self._stack.addWidget(self._framed(
            "Simulate real braking — from a driver pedal force, see the actual deceleration and "
            "whether either axle locks up.", self._simulator_page()))
        self._stack.addWidget(self._framed(
            "Rotor thermal — compute the ANSYS heat-flux and film-coefficient inputs, and simulate "
            "rotor temperature over repeated stops.", self._thermal_page()))
        self._stack.addWidget(self._framed(
            "Optimize the setup — search component and tuning values that best meet your objectives "
            "and constraints.", self._optimize))
        self._stack.addWidget(self._framed(
            "Compare setups — line up saved configurations side by side to see how they differ.",
            self._compare))
        self._stack.addWidget(self._framed(
            "Sensitivity — see which inputs most affect a chosen output, so you know what to tune.",
            SensitivityPanel(self.controller)))
        self._stack.addWidget(self._framed(
            "Report — build a customised PDF engineering report of the design.", self._report))

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
        theme.style_checkboxes(self)  # visible tick boxes, per-widget (no app stylesheet — see theme)

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

        export = QPushButton("Report…")
        export.clicked.connect(lambda: self._select_page(_PAGES.index("Report")))
        v.addWidget(export)
        return panel

    def _framed(self, description: str, widget: QWidget) -> QWidget:
        """Wrap a page with a small muted one-line description of the tab's purpose at the top."""
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(10, 8, 10, 0)
        v.setSpacing(3)
        label = QLabel(description)
        label.setWordWrap(True)
        label.setFont(theme.body_font())     # keep Helvetica-Light explicitly
        muted(label, theme.muted_text())     # colour via palette, so a theme toggle won't drop the font
        self._desc_labels.append(label)
        v.addWidget(label)
        v.addWidget(widget, 1)
        return holder

    def _select_page(self, index: int) -> None:
        for j, label in enumerate(self._nav_labels):
            label.setFont(theme.heading_font(14, bold=(j == index)))
        self._stack.setCurrentIndex(index)
        # Pages are wrapped in a description frame, so refresh by page name rather than widget identity.
        name = _PAGES[index]
        if name == "Compare":
            self._compare.reload_configs()
        elif name == "Optimize":
            self._optimize.refresh_current()
        elif name == "Report":
            self._report.reload()

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

    # ---- simulator page ---------------------------------------------------------------------
    def _simulator_page(self) -> QWidget:
        """Forward performance / lock-up simulator. Same layout as Main (components + inputs left,
        status + outputs right), sharing the one config so tuning here also updates the Main tab."""
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)
        lv.addWidget(ComponentsPanel(self.controller))
        lv.addWidget(InputPanel(self.controller, groups=forward_spec.INPUT_GROUPS))
        lv.addStretch(1)
        left_scroll = _scroll(left)
        left_scroll.setMinimumWidth(430)

        self._forward_status = ForwardStatusPanel(self.controller)
        self._forward_outputs = OutputsPanel(self.controller, groups=forward_spec.OUTPUT_GROUPS)
        self._balance = BalancePanel(self.controller)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 4, 4, 4)
        rv.addWidget(self._forward_status)
        rv.addWidget(self._forward_outputs)
        rv.addWidget(CollapsibleSection("Brake balance diagram", self._balance, expanded=False))
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

    # ---- thermal page -----------------------------------------------------------------------
    def _thermal_page(self) -> QWidget:
        """Brake-rotor thermal for ANSYS. Inputs always on the left (required ones expanded, the
        preview-graph inputs a collapsed dropdown below a divider); outputs on the right (ANSYS
        values, then the optional temperature graph as a matching collapsed dropdown)."""
        def note(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            muted(lbl, theme.muted_text())
            self._desc_labels.append(lbl)  # keep muted colour correct on theme toggle
            return lbl

        def hline() -> QFrame:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet(f"color: {theme.border_color()};")
            return line

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)
        lv.addWidget(SharedInfoPanel(self.controller))
        lv.addWidget(note("Required inputs — these produce the ANSYS boundary-condition values on "
                          "the right."))
        lv.addWidget(InputPanel(self.controller, groups=thermal_spec.INPUT_GROUPS))
        lv.addWidget(hline())
        lv.addWidget(note("Optional — these only shape the preview graph, not the ANSYS values. "
                          "Pick a rotor material to fill the specific heat and emissivity."))
        lv.addWidget(ThermalMaterialPanel(self.controller))
        lv.addWidget(InputPanel(self.controller, groups=thermal_spec.SIM_INPUT_GROUPS, expanded=False))
        lv.addStretch(1)
        left_scroll = _scroll(left)
        left_scroll.setMinimumWidth(430)

        self._thermal_outputs = OutputsPanel(self.controller, groups=thermal_spec.OUTPUT_GROUPS)
        self._thermal_sim = ThermalSimPanel(self.controller)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 4, 4, 4)
        rv.addWidget(self._thermal_outputs)
        rv.addWidget(hline())
        rv.addWidget(note("Preview — not a substitute for ANSYS or similar simulation software."))
        rv.addWidget(CollapsibleSection("Rotor temperature graph", self._thermal_sim, expanded=False))
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
            self._thermal_outputs.reset_highlights()
            self._forward_outputs.reset_highlights()
            self._thermal_sim.refresh()  # redraw the chart in the new theme's colours
            self._balance.refresh()
            theme.style_checkboxes(self)  # re-apply the theme-aware indicator fill
            for lbl in self._desc_labels:  # refresh the muted colour for the new theme (palette-based)
                muted(lbl, theme.muted_text())

    def _set_title(self, name: str) -> None:
        self.setWindowTitle(f"Brake Design Studio — {name}")


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setWidget(widget)
    return area


def run(config: VehicleConfig | None = None) -> int:
    """Launch the GUI. Seeds the library on first run and opens the default preset."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Brake Design Studio")
    app.setOrganizationName("Brake Design Studio")
    icon_file = Path(__file__).resolve().parent / "assets" / "icon.png"
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))
    theme.apply_theme(app, dark=False)

    library = ConfigLibrary()
    library.seed_defaults()
    if config is None:
        config = library.load(library.default_name)

    controller = ProjectController(config)
    window = MainWindow(controller, library)
    window.show()

    # CI smoke test: BRAKELAB_SMOKE=1 quits shortly after the window is up, so the packaged
    # app can be verified headless (exit 0 = launched, solved, and rendered without crashing).
    if os.environ.get("BRAKELAB_SMOKE"):
        QTimer.singleShot(2000, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
