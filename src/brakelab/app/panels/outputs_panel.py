"""OUTPUTS panel — every computed quantity, grouped by phase, in a plain table.

Columns: Quantity · Value · Unit · ⓘ. Units have their own column so they're always visible.
Clicking the ⓘ cell on a row opens that quantity's formula and description. Refreshes on every
recompute. Minimal, consistent styling from the global theme.
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
from ..widgets import show_info


class OutputsPanel(QWidget):
    """A grouped, read-only table of all outputs."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._value_items: list[tuple[Output, QTableWidgetItem]] = []
        self._row_output: dict[int, Output] = {}

        layout = QVBoxLayout(self)
        title = QLabel("OUTPUTS")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Quantity", "Value", "Unit", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

        self._build_rows()
        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def _build_rows(self) -> None:
        bold = QFont()
        bold.setBold(True)
        for group in GROUPS:
            row = self._table.rowCount()
            self._table.insertRow(row)
            header_item = QTableWidgetItem(group.title)
            header_item.setFont(bold)
            header_item.setFlags(Qt.ItemIsEnabled)
            self._table.setItem(row, 0, header_item)
            self._table.setSpan(row, 0, 1, 4)

            for output in group.outputs:
                row = self._table.rowCount()
                self._table.insertRow(row)
                name = QTableWidgetItem(output.label)
                value = QTableWidgetItem("")
                value.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                unit = QTableWidgetItem(output.unit)
                info = QTableWidgetItem("ⓘ")
                info.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 0, name)
                self._table.setItem(row, 1, value)
                self._table.setItem(row, 2, unit)
                self._table.setItem(row, 3, info)
                self._value_items.append((output, value))
                self._row_output[row] = output

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        output = self._row_output.get(row)
        if output:
            show_info(self, output.label, f"{output.formula}\n\n{output.description}")

    def refresh(self, results: BrakeResults) -> None:
        config = self._controller.config
        for output, item in self._value_items:
            val = output.getter(results, config)
            decimals = 3 if abs(val) < 100 else 1
            item.setText(f"{val:,.{decimals}f}")
