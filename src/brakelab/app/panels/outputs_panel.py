"""OUTPUTS panel — every computed quantity, grouped by phase, in a plain table.

Columns are Quantity · Value · Unit, so units are always visible in their own column. Each quantity
carries an "ⓘ" and a hover tooltip showing its formula and a description, so any number can be
traced to its equation. Refreshes on every recompute. No custom styling.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.results import BrakeResults
from ..controller import ProjectController
from ..output_spec import GROUPS, Output


class OutputsPanel(QWidget):
    """A grouped, read-only table of all outputs."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._value_items: list[tuple[Output, QTableWidgetItem]] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("OUTPUTS"))

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Quantity", "Value", "Unit"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

        self._build_rows()
        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def _build_rows(self) -> None:
        bold = QFont()
        bold.setBold(True)
        for group in GROUPS:
            # Group header row spanning all columns.
            row = self._table.rowCount()
            self._table.insertRow(row)
            header_item = QTableWidgetItem(group.title)
            header_item.setFont(bold)
            header_item.setFlags(Qt.ItemIsEnabled)
            self._table.setItem(row, 0, header_item)
            self._table.setSpan(row, 0, 1, 3)

            for output in group.outputs:
                row = self._table.rowCount()
                self._table.insertRow(row)
                tip = f"{output.formula}\n\n{output.description}"

                name = QTableWidgetItem(f"{output.label}  ⓘ")
                name.setToolTip(tip)
                value = QTableWidgetItem("")
                value.setToolTip(tip)
                value.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                unit = QTableWidgetItem(output.unit)
                unit.setToolTip(tip)

                self._table.setItem(row, 0, name)
                self._table.setItem(row, 1, value)
                self._table.setItem(row, 2, unit)
                self._value_items.append((output, value))

    def refresh(self, results: BrakeResults) -> None:
        config = self._controller.config
        for output, item in self._value_items:
            val = output.getter(results, config)
            decimals = 3 if abs(val) < 100 else 1
            item.setText(f"{val:,.{decimals}f}")
