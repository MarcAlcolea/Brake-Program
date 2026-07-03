"""OUTPUTS panel — every computed quantity, grouped by phase, in a plain table.

Columns: Quantity · Value · Unit · ⓘ. After each input change, values that went up are tinted green
and values that went down are tinted red (theme-aware), so it's easy to see what a change affected.
Clicking a row's ⓘ sends its formula and note to the in-window Details area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
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
from .. import theme
from ..controller import ProjectController
from ..output_spec import GROUPS, Output
from ..widgets import InfoSink

_TRANSPARENT = QColor(0, 0, 0, 0)


class OutputsPanel(QWidget):
    def __init__(self, controller: ProjectController, sink: InfoSink, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._sink = sink
        self._value_items: list[tuple[Output, QTableWidgetItem]] = []
        self._row_output: dict[int, Output] = {}
        self._previous: dict[str, float] = {}

        layout = QVBoxLayout(self)
        title = QLabel("OUTPUTS")
        tf = title.font()
        tf.setBold(True)
        title.setFont(tf)
        layout.addWidget(title)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Quantity", "Value", "Unit", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
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
        controller.configReplaced.connect(lambda _c: self._previous.clear())
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
                value = QTableWidgetItem("")
                value.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                info = QTableWidgetItem("ⓘ")
                info.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 0, QTableWidgetItem(output.label))
                self._table.setItem(row, 1, value)
                self._table.setItem(row, 2, QTableWidgetItem(output.unit))
                self._table.setItem(row, 3, info)
                self._value_items.append((output, value))
                self._row_output[row] = output

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        output = self._row_output.get(row)
        if output:
            note = f"Formula:  {output.formula}"
            if output.description:
                note += f"\n\n{output.description}"
            self._sink(output.label, note)

    def refresh(self, results: BrakeResults) -> None:
        config = self._controller.config
        for output, item in self._value_items:
            val = output.getter(results, config)
            decimals = 3 if abs(val) < 100 else 1
            item.setText(f"{val:,.{decimals}f}")

            prev = self._previous.get(output.label)
            if prev is None or abs(val - prev) < 1e-9:
                item.setBackground(_TRANSPARENT)
            elif val > prev:
                item.setBackground(theme.increase_color())
            else:
                item.setBackground(theme.decrease_color())
            self._previous[output.label] = val

    def reset_highlights(self) -> None:
        """Re-clear/re-evaluate highlight colours (e.g. after a theme change)."""
        for _output, item in self._value_items:
            item.setBackground(_TRANSPARENT)
