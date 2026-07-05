"""Outputs — one collapsible table per phase, each sized to its content (no inner scroll).

After each input change, values that rose are tinted green and values that fell are tinted red
(theme-aware). Clicking a row's ⓘ opens its formula and note in a popover next to the icon.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ...core.results import BrakeResults
from .. import theme
from ..controller import ProjectController
from ..output_spec import GROUPS, Output
from ..uikit import fit_table, muted, plain_table
from ..widgets import CollapsibleSection, show_popover

_CLEAR = QColor(0, 0, 0, 0)


class OutputsPanel(QWidget):
    def __init__(self, controller: ProjectController, groups=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._value_items: list[tuple[Output, QTableWidgetItem]] = []
        self._label_items: dict[Output, QTableWidgetItem] = {}
        self._previous: dict[str, float] = {}

        if groups is None:
            groups = GROUPS
        self._outputs = [o for g in groups for o in g.outputs]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        for group in groups:
            table = plain_table(["Quantity", "Value", "Unit", ""], stretch_col=0)
            row_output: dict[int, Output] = {}
            table.setRowCount(len(group.outputs))
            for row, output in enumerate(group.outputs):
                label = QTableWidgetItem(output.label)
                table.setItem(row, 0, label)
                value = QTableWidgetItem("")
                value.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, 1, value)
                table.setItem(row, 2, QTableWidgetItem(output.unit))
                info = QTableWidgetItem("ⓘ")
                info.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 3, info)
                self._value_items.append((output, value))
                self._label_items[output] = label
                row_output[row] = output
            table.cellClicked.connect(lambda r, c, t=table, m=row_output: self._info(t, r, c, m))
            fit_table(table)
            layout.addWidget(CollapsibleSection(group.title, table, expanded=getattr(group, "expanded", True)))

        self._legend = QLabel("*  depends on a value marked as assumed")
        muted(self._legend, theme.muted_text())
        self._legend.setVisible(False)
        layout.addWidget(self._legend)
        layout.addStretch(1)

        self._assumed_affected: set[Output] = set()

        controller.resultsChanged.connect(self.refresh)
        controller.configReplaced.connect(lambda _c: self._previous.clear())
        self.refresh(controller.results)

    def _info(self, table: QTableWidget, row: int, col: int, mapping: dict[int, Output]) -> None:
        if col != 3 or row not in mapping:
            return
        output = mapping[row]
        rect = table.visualRect(table.model().index(row, col))
        pos = table.viewport().mapToGlobal(rect.bottomLeft())
        body = f"Formula:  {output.formula}"
        if output.description:
            body += f"\n{output.description}"
        if output in self._assumed_affected:
            body += "\n\n⚠ This value depends on one or more inputs you marked as assumed."
        show_popover(pos, output.label, body)

    def refresh(self, results: BrakeResults) -> None:
        config = self._controller.config
        self._assumed_affected = self._controller.assumed_affected(self._outputs)
        self._legend.setVisible(bool(self._assumed_affected))
        for output, item in self._value_items:
            val = output.getter(results, config)
            decimals = 3 if abs(val) < 100 else 1
            item.setText(f"{val:,.{decimals}f}")
            prev = self._previous.get(output.label)
            if prev is None or abs(val - prev) < 1e-9:
                item.setBackground(_CLEAR)
            else:
                item.setBackground(theme.increase_color() if val > prev else theme.decrease_color())
            self._previous[output.label] = val
            self._mark_assumed(output)

    def _mark_assumed(self, output: Output) -> None:
        """Add/remove the small 'depends on an assumed value' marker on an output's label."""
        label = self._label_items[output]
        affected = output in self._assumed_affected
        label.setText(f"{output.label} *" if affected else output.label)
        label.setToolTip(
            "Depends on one or more inputs marked as assumed." if affected else ""
        )

    def reset_highlights(self) -> None:
        for _output, item in self._value_items:
            item.setBackground(_CLEAR)
