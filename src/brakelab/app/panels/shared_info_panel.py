"""Read-only display of Main-tab values that drive the thermal math.

Shown at the top of the Thermal tab so it is self-explanatory: these numbers are entered on the Main
tab and shared, not re-entered here. The table refreshes whenever the config changes so it always
mirrors Main. Uses a plain content-sized table (no inner scroll), matching the Outputs panel.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem, QVBoxLayout, QWidget

from ...core.attrpath import get_by_path
from ..controller import ProjectController
from ..thermal_spec import SHARED
from ..uikit import fit_table, plain_table
from ..widgets import CollapsibleSection


class SharedInfoPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller

        table = plain_table(["From Main tab", "Value", "Unit"], stretch_col=0)
        table.setRowCount(len(SHARED))
        self._value_items: list[QTableWidgetItem] = []
        for row, ref in enumerate(SHARED):
            table.setItem(row, 0, QTableWidgetItem(ref.label))
            value = QTableWidgetItem("")
            value.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 1, value)
            table.setItem(row, 2, QTableWidgetItem("" if ref.unit in ("", "-") else ref.unit))
            self._value_items.append(value)
        self._table = table

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(CollapsibleSection("Shared inputs (from Main)", table, expanded=True))

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        for ref, item in zip(SHARED, self._value_items):
            value = float(get_by_path(self._controller.config, ref.path))
            item.setText(f"{value:,.{ref.decimals}f}")
        fit_table(self._table)
