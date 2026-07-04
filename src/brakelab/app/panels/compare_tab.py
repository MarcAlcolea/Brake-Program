"""Compare tab — view two saved configurations side by side.

Pick any two presets from the library; the table lists every input parameter with both values and
marks the rows that differ, followed by a few key computed outputs. This makes it easy to see how
two designs differ and how those differences affect the results.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.attrpath import get_by_path
from ...core.engine import BrakeEngine
from ...core.models import VehicleConfig
from ...persistence import ConfigLibrary
from ..field_spec import GROUPS


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
        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Compare"))
        self._combo_a = QComboBox()
        self._combo_b = QComboBox()
        for combo in (self._combo_a, self._combo_b):
            combo.setMinimumWidth(240)
            combo.setMaxVisibleItems(20)
            combo.currentTextChanged.connect(self.refresh)
        selectors.addWidget(self._combo_a)
        selectors.addWidget(QLabel("with"))
        selectors.addWidget(self._combo_b)
        selectors.addStretch(1)
        layout.addLayout(selectors)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Parameter", "A", "B", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QTableWidget.NoFrame)
        header = self._table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

        self.reload_configs()

    def reload_configs(self) -> None:
        """Refresh the dropdowns from the library (call when presets change)."""
        names = self._library.names()
        for i, combo in enumerate((self._combo_a, self._combo_b)):
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names)
            target = current if current in names else (names[min(i, len(names) - 1)] if names else "")
            if target:
                combo.setCurrentIndex(combo.findText(target))
            combo.blockSignals(False)
        self.refresh()

    def refresh(self, *_args) -> None:
        name_a, name_b = self._combo_a.currentText(), self._combo_b.currentText()
        if not name_a or not name_b:
            self._table.setRowCount(0)
            return
        cfg_a, cfg_b = self._library.load(name_a), self._library.load(name_b)
        self._table.setRowCount(0)

        self._section("Inputs")
        for group in GROUPS:
            for field in group.fields:
                self._row(field.label, get_by_path(cfg_a, field.path), get_by_path(cfg_b, field.path))

        self._section("Key outputs")
        ra, rb = self._engine.solve(cfg_a), self._engine.solve(cfg_b)
        self._row("Front line pressure [MPa]", ra.sizing.front.line_pressure, rb.sizing.front.line_pressure)
        self._row("Rear line pressure [MPa]", ra.sizing.rear.line_pressure, rb.sizing.rear.line_pressure)
        self._row("Pedal travel [mm]", ra.pedal_travel.pedal_travel, rb.pedal_travel.pedal_travel)
        self._row("Pedal force needed, front [N]", ra.hydraulics.bar_force_front, rb.hydraulics.bar_force_front)
        self._row("All requirements met", ra.ok, rb.ok)

    def _section(self, title: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        item = QTableWidgetItem(title)
        bold = QFont()
        bold.setBold(True)
        item.setFont(bold)
        item.setFlags(Qt.ItemIsEnabled)
        self._table.setItem(row, 0, item)
        self._table.setSpan(row, 0, 1, 4)

    def _row(self, label, a, b) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(label))
        self._table.setItem(row, 1, QTableWidgetItem(_fmt(a)))
        self._table.setItem(row, 2, QTableWidgetItem(_fmt(b)))
        differs = _fmt(a) != _fmt(b)
        marker = QTableWidgetItem("≠" if differs else "")
        marker.setTextAlignment(Qt.AlignCenter)
        if differs:
            bold = QFont()
            bold.setBold(True)
            for col in (0, 1, 2):
                self._table.item(row, col).setFont(bold)
            marker.setFont(bold)
        self._table.setItem(row, 3, marker)
