"""Compare tab — line up several saved configurations side by side.

Each of the five columns starts empty; pick a preset from the column's dropdown to fill it. The table
then shows only the **inputs that differ** between the filled setups, followed by **all outputs**. For
each output, cells are tinted green when higher and red when lower than the first (leftmost) filled
setup — the same up/down colours as the Main tab — so you can see at a glance how a change moved every
result. Leave a column on "—" to hide it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.attrpath import get_by_path
from ...core.engine import BrakeEngine
from ...persistence import ConfigLibrary
from .. import theme
from ..field_spec import GROUPS as INPUT_GROUPS
from ..output_spec import GROUPS as OUTPUT_GROUPS
from ..uikit import muted, style_combo

_N_COLS = 5           # number of comparison columns
_EMPTY = "—"          # dropdown sentinel for "no setup in this column"


def _fmt_input(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return str(value)


def _fmt_output(value: float) -> str:
    v = float(value)
    decimals = 3 if abs(v) < 100 else 1
    return f"{v:,.{decimals}f}"


class CompareTab(QWidget):
    def __init__(self, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._engine = BrakeEngine()

        layout = QVBoxLayout(self)
        hint = QLabel("Pick a saved setup per column. Shows the inputs that differ and all outputs; "
                      "for each output, green = higher and red = lower than the first (leftmost) setup.")
        hint.setWordWrap(True)
        muted(hint, theme.muted_text())
        layout.addWidget(hint)

        self._table = QTableWidget(0, 1 + _N_COLS)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QTableWidget.NoFrame)
        header = self._table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 1 + _N_COLS):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        layout.addWidget(self._table)

        self._combos: list[QComboBox] = []
        self._build_selector_row()
        self.reload_configs()

    # ---- selector row -----------------------------------------------------------------------
    def _build_selector_row(self) -> None:
        """Row 0 of the table holds one dropdown per column. It is kept across refreshes."""
        self._table.setRowCount(1)
        self._table.setItem(0, 0, self._bold_item("Setup"))
        for i in range(_N_COLS):
            combo = QComboBox()
            combo.setMaxVisibleItems(20)
            combo.currentIndexChanged.connect(self.refresh)
            style_combo(combo)
            self._combos.append(combo)
            self._table.setCellWidget(0, 1 + i, combo)

    def reload_configs(self) -> None:
        """Refresh the dropdowns from the library (call when presets change)."""
        names = self._library.names()
        for combo in self._combos:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(_EMPTY)
            combo.addItems(names)
            i = combo.findText(current) if current and current != _EMPTY else -1
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)
        self.refresh()

    def _selected_names(self) -> list[str]:
        return [c.currentText() if c.currentText() != _EMPTY else "" for c in self._combos]

    # ---- table body -------------------------------------------------------------------------
    def refresh(self, *_args) -> None:
        configs = [self._library.load(n) if n else None for n in self._selected_names()]
        self._table.setRowCount(1)  # keep the selector row, drop the old body

        filled = [i for i, c in enumerate(configs) if c is not None]
        if not filled:
            return
        if len(filled) < 2:
            self._note("Select at least two setups to compare them.")

        # Inputs — only the ones that differ across the filled setups.
        self._section("Inputs that differ")
        shown = 0
        for group in INPUT_GROUPS:
            for field in group.fields:
                values = [None if c is None else get_by_path(c, field.path) for c in configs]
                present = [v for v in values if v is not None]
                if len({_fmt_input(v) for v in present}) > 1:
                    self._plain_row(field.label, [None if v is None else _fmt_input(v) for v in values])
                    shown += 1
        if shown == 0 and len(filled) >= 2:
            self._note("All inputs are identical.")

        # Outputs — all of them, tinted green/red vs. the first filled setup.
        results = [None if c is None else self._engine.solve(c) for c in configs]
        baseline = filled[0]
        self._section("Outputs")
        for group in OUTPUT_GROUPS:
            for output in group.outputs:
                values = [None if results[i] is None else output.getter(results[i], configs[i])
                          for i in range(len(configs))]
                label = output.label + (f" [{output.unit}]" if output.unit not in ("", "-") else "")
                self._output_row(label, values, baseline)

        ok = [None if results[i] is None else results[i].ok for i in range(len(configs))]
        self._plain_row("All requirements met", [None if v is None else _fmt_input(v) for v in ok])

    # ---- row builders -----------------------------------------------------------------------
    def _bold_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        item.setFlags(Qt.ItemIsEnabled)
        return item

    def _section(self, title: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, self._bold_item(title))
        self._table.setSpan(row, 0, 1, 1 + _N_COLS)

    def _note(self, text: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setForeground(QColor(theme.muted_text()))
        self._table.setItem(row, 0, item)
        self._table.setSpan(row, 0, 1, 1 + _N_COLS)

    def _plain_row(self, label, shown_values) -> None:
        """Label + pre-formatted string values, no colour (used for inputs and the requirements row)."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(label))
        for i, text in enumerate(shown_values):
            item = QTableWidgetItem("" if text is None else text)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 1 + i, item)

    def _output_row(self, label, values, baseline: int) -> None:
        """Numeric output row; each cell tinted green if higher / red if lower than the baseline column."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(label))
        base = values[baseline]
        for i, v in enumerate(values):
            item = QTableWidgetItem("" if v is None else _fmt_output(v))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if v is not None and base is not None and i != baseline and abs(v - base) > 1e-9:
                item.setBackground(theme.increase_color() if v > base else theme.decrease_color())
            self._table.setItem(row, 1 + i, item)
