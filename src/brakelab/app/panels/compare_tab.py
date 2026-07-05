"""Compare tab — line up several saved configurations side by side.

Each of the five columns starts empty; pick a preset from the column's dropdown to fill it. The
table then lists every input parameter (and a few key computed outputs) across whichever columns are
filled, boldfacing the rows where the filled columns disagree. Leave a column on "—" to hide it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
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
from ..field_spec import GROUPS
from ..uikit import style_combo

_N_COLS = 5           # number of comparison columns
_EMPTY = "—"          # dropdown sentinel for "no setup in this column"


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return str(value)


class CompareTab(QWidget):
    def __init__(self, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._engine = BrakeEngine()

        layout = QVBoxLayout(self)
        hint = QLabel("Pick a saved setup for each column to compare them. Leave a column on “—” to hide it.")
        from .. import theme
        from ..uikit import muted

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
        head = QTableWidgetItem("Setup")
        bold = QFont()
        bold.setBold(True)
        head.setFont(bold)
        head.setFlags(Qt.ItemIsEnabled)
        self._table.setItem(0, 0, head)
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
        names = self._selected_names()
        configs = [self._library.load(n) if n else None for n in names]
        self._table.setRowCount(1)  # keep the selector row, drop the old body

        if not any(configs):
            return

        self._section("Inputs")
        for group in GROUPS:
            for field in group.fields:
                self._row(field.label, [None if c is None else get_by_path(c, field.path) for c in configs])

        self._section("Key outputs")
        results = [None if c is None else self._engine.solve(c) for c in configs]

        def out(getter):
            return [None if r is None else getter(r) for r in results]

        self._row("Front line pressure [MPa]", out(lambda r: r.sizing.front.line_pressure))
        self._row("Rear line pressure [MPa]", out(lambda r: r.sizing.rear.line_pressure))
        self._row("Pedal travel [mm]", out(lambda r: r.pedal_travel.pedal_travel))
        self._row("Pedal force needed, front [N]", out(lambda r: r.hydraulics.bar_force_front))
        self._row("All requirements met", out(lambda r: r.ok))

    def _section(self, title: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        item = QTableWidgetItem(title)
        bold = QFont()
        bold.setBold(True)
        item.setFont(bold)
        item.setFlags(Qt.ItemIsEnabled)
        self._table.setItem(row, 0, item)
        self._table.setSpan(row, 0, 1, 1 + _N_COLS)

    def _row(self, label, values) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(label))

        shown = [None if v is None else _fmt(v) for v in values]
        filled = [s for s in shown if s is not None]
        differs = len(set(filled)) > 1

        for i, text in enumerate(shown):
            item = QTableWidgetItem("" if text is None else text)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 1 + i, item)

        if differs:
            bold = QFont()
            bold.setBold(True)
            for col in range(0, 1 + _N_COLS):
                cell = self._table.item(row, col)
                if cell is not None:
                    cell.setFont(bold)
