"""Report tab — compose a customised engineering PDF.

The user chooses which saved setup the numbers come from (defaulting to the current design), fills in
cover metadata (title, author, subtitle, letterhead image, date), sets the level of detail, and ticks
which sections to include (Design, Thermal, Comparison, Optimization, Validation). For the comparison
they pick which saved setups to line up. "Generate PDF…" hands a :class:`ReportOptions` to the report
builder. Kept thin: all layout/typography lives in ``reporting.pdf_report``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.engine import BrakeEngine
from ...persistence import ConfigLibrary
from ...reporting import ReportOptions, build_report
from .. import theme
from ..controller import ProjectController
from ..uikit import muted, style_combo

_CURRENT = "current"  # sentinel userData for "the live current design"
_DETAIL = [("Extensive — every input and output", "extensive"),
           ("Simplified — key values only", "simplified")]


class ReportTab(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary,
                 optimization_result: Callable[[], object] | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library
        self._engine = BrakeEngine()
        self._opt_result = optimization_result or (lambda: None)
        self._compare_boxes: list[QCheckBox] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        self._v = QVBoxLayout(body)
        self._v.setContentsMargins(10, 8, 10, 8)
        self._v.setSpacing(6)

        self._build_setup_and_detail()
        self._build_cover_fields()
        self._build_section_choices()
        self._build_compare_choices()

        generate = QPushButton("Generate PDF…")
        generate.clicked.connect(self._generate)
        self._v.addSpacing(6)
        self._v.addWidget(generate)
        self._v.addStretch(1)

        self.reload()

    # ---- construction helpers ---------------------------------------------------------------
    def _section_h(self, text: str) -> None:
        lab = QLabel(text)
        lab.setFont(theme.heading_font(13))
        self._v.addSpacing(6)
        self._v.addWidget(lab)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {theme.border_color()};")
        self._v.addWidget(line)

    def _hint(self, text: str) -> None:
        lab = QLabel(text)
        lab.setWordWrap(True)
        muted(lab, theme.muted_text())
        self._v.addWidget(lab)

    def _build_setup_and_detail(self) -> None:
        self._section_h("Setup & detail")
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self._setup = QComboBox()
        self._setup.setMinimumWidth(280)
        self._setup.setMaxVisibleItems(20)
        style_combo(self._setup)
        grid.addWidget(QLabel("Report on setup"), 0, 0)
        grid.addWidget(self._setup, 0, 1)

        self._detail = QComboBox()
        for label, key in _DETAIL:
            self._detail.addItem(label, key)
        style_combo(self._detail)
        grid.addWidget(QLabel("Level of detail"), 1, 0)
        grid.addWidget(self._detail, 1, 1)

        holder = QWidget()
        holder.setLayout(grid)
        self._v.addWidget(holder)

    def _build_cover_fields(self) -> None:
        self._section_h("Cover")
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self._title = QLineEdit("FSAE Brake Design Report")
        self._author = QLineEdit("")
        self._author.setPlaceholderText("e.g. Marc Alcolea — Controls Subteam")
        self._subtitle = QLineEdit("")
        self._subtitle.setPlaceholderText("optional line under the car name")
        grid.addWidget(QLabel("Report title"), 0, 0)
        grid.addWidget(self._title, 0, 1)
        grid.addWidget(QLabel("Prepared by"), 1, 0)
        grid.addWidget(self._author, 1, 1)
        grid.addWidget(QLabel("Subtitle"), 2, 0)
        grid.addWidget(self._subtitle, 2, 1)

        # Letterhead / logo image.
        grid.addWidget(QLabel("Letterhead logo"), 3, 0)
        logo_row = QHBoxLayout()
        self._logo = QLineEdit("")
        self._logo.setPlaceholderText("optional image file (PNG, JPG…)")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._pick_logo)
        logo_row.addWidget(self._logo, 1)
        logo_row.addWidget(browse)
        logo_holder = QWidget()
        logo_holder.setLayout(logo_row)
        grid.addWidget(logo_holder, 3, 1)

        self._date = QCheckBox("Print today's date on the cover")
        self._date.setChecked(True)
        grid.addWidget(self._date, 4, 1)

        holder = QWidget()
        holder.setLayout(grid)
        self._v.addWidget(holder)

    def _build_section_choices(self) -> None:
        self._section_h("Sections to include")
        self._c_design = QCheckBox("Design — inputs, results and requirements (Main tab)")
        self._c_forward = QCheckBox("Performance — actual decel, lock-up and grip use (Simulator tab)")
        self._c_thermal = QCheckBox("Thermal — ANSYS heat-flux and film-coefficient inputs")
        self._c_compare = QCheckBox("Comparison — selected setups side by side")
        self._c_optimize = QCheckBox("Optimization — summary of the latest optimizer run")
        self._c_validation = QCheckBox("Validation notes — engine warnings and errors")
        self._c_toc = QCheckBox("Table of contents (when the report has several sections)")
        self._c_design.setChecked(True)
        self._c_forward.setChecked(True)
        self._c_validation.setChecked(True)
        self._c_toc.setChecked(True)
        for c in (self._c_design, self._c_forward, self._c_thermal, self._c_compare,
                  self._c_optimize, self._c_validation, self._c_toc):
            self._v.addWidget(c)
        self._c_compare.toggled.connect(self._sync_compare_enabled)
        self._opt_note = QLabel("")
        muted(self._opt_note, theme.muted_text())
        self._v.addWidget(self._opt_note)

    def _build_compare_choices(self) -> None:
        self._section_h("Comparison setups")
        self._hint("Tick the saved setups to line up in the Comparison section (needs at least two).")
        self._compare_holder = QWidget()
        self._compare_layout = QVBoxLayout(self._compare_holder)
        self._compare_layout.setContentsMargins(6, 0, 0, 0)
        self._compare_layout.setSpacing(2)
        self._v.addWidget(self._compare_holder)

    # ---- state ------------------------------------------------------------------------------
    def reload(self) -> None:
        """Refresh preset lists and optimization availability (call when the tab shows)."""
        current = self._controller.config.name

        # Setup selector: the live current design first, then every saved preset.
        prev = self._setup.currentData()
        self._setup.blockSignals(True)
        self._setup.clear()
        self._setup.addItem(f"Current design — {current}", _CURRENT)
        for name in self._library.names():
            self._setup.addItem(name, name)
        idx = self._setup.findData(prev) if prev is not None else 0
        self._setup.setCurrentIndex(idx if idx >= 0 else 0)
        self._setup.blockSignals(False)

        # Comparison preset checkboxes, preserving prior ticks.
        checked = {b.text() for b in self._compare_boxes if b.isChecked()}
        for b in self._compare_boxes:
            b.setParent(None)
        self._compare_boxes.clear()
        for name in self._library.names():
            box = QCheckBox(name)
            box.setChecked(name in checked or (not checked and name == current))
            self._compare_layout.addWidget(box)
            self._compare_boxes.append(box)

        has_opt = self._opt_result() is not None
        self._c_optimize.setEnabled(has_opt)
        if not has_opt:
            self._c_optimize.setChecked(False)
            self._opt_note.setText("Run an optimization on the Optimize tab to include its summary.")
        else:
            self._opt_note.setText("")
        self._sync_compare_enabled()
        theme.style_checkboxes(self)  # style the freshly-created comparison checkboxes

    def _sync_compare_enabled(self) -> None:
        self._compare_holder.setEnabled(self._c_compare.isChecked())

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose letterhead image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if path:
            self._logo.setText(path)

    # ---- generate ---------------------------------------------------------------------------
    def _chosen_config_and_results(self):
        data = self._setup.currentData()
        if data == _CURRENT or data is None:
            return self._controller.config, self._controller.results
        cfg = self._library.load(data)
        return cfg, self._engine.solve(cfg)

    def _compare_configs(self):
        names = [b.text() for b in self._compare_boxes if b.isChecked()]
        return [self._library.load(n) for n in names]

    def _generate(self) -> None:
        include_compare = self._c_compare.isChecked()
        compare_configs = self._compare_configs() if include_compare else []
        if include_compare and len(compare_configs) < 2:
            QMessageBox.information(self, "Report", "Pick at least two setups for the comparison section.")
            return

        config, results = self._chosen_config_and_results()
        options = ReportOptions(
            title=self._title.text().strip() or "FSAE Brake Design Report",
            author=self._author.text().strip(),
            subtitle=self._subtitle.text().strip(),
            include_date=self._date.isChecked(),
            logo_path=self._logo.text().strip(),
            detail=self._detail.currentData(),
            include_design=self._c_design.isChecked(),
            include_forward=self._c_forward.isChecked(),
            include_thermal=self._c_thermal.isChecked(),
            include_compare=include_compare,
            include_optimization=self._c_optimize.isChecked() and self._c_optimize.isEnabled(),
            include_validation=self._c_validation.isChecked(),
            include_toc=self._c_toc.isChecked(),
            compare_configs=compare_configs,
            optimization_result=self._opt_result() if self._c_optimize.isChecked() else None,
        )

        default = f"{config.name}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Generate PDF report", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            build_report(config, results, path, options=options, engine=self._engine)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Report failed", str(exc))
            return
        QMessageBox.information(self, "Report generated", f"Saved to {path}")
