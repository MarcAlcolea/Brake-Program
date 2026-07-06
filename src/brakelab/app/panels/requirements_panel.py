"""Requirements — what the inputs require vs what the setup produces, in one compact table.

No inequality symbols; pass/fail as ✓ / ✗. A short status line sits on top. Clicking a row's ⓘ
opens its note in a popover next to the icon.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from ...core.results import BrakeResults, Requirement
from .. import theme
from ..controller import ProjectController
from ..uikit import fit_table, muted, plain_table
from ..widgets import show_popover


class RequirementsPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row_req: dict[int, Requirement] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        heading = QLabel("Requirements")
        heading.setFont(theme.heading_font())
        layout.addWidget(heading)
        self._status = QLabel()
        layout.addWidget(self._status)

        self._table = plain_table(["Requirement", "The inputs require", "The setup produces", "Status", ""], stretch_col=0)
        self._table.cellClicked.connect(self._info)
        layout.addWidget(self._table)

        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def _info(self, row: int, col: int) -> None:
        if col != 4 or row not in self._row_req:
            return
        req = self._row_req[row]
        rect = self._table.visualRect(self._table.model().index(row, col))
        pos = self._table.viewport().mapToGlobal(rect.bottomLeft())
        show_popover(pos, req.name, req.description)

    def refresh(self, results: BrakeResults) -> None:
        reqs = results.requirements
        self._row_req = dict(enumerate(reqs))
        self._table.setRowCount(len(reqs))
        for row, req in enumerate(reqs):
            self._table.setItem(row, 0, QTableWidgetItem(req.name + ("" if req.hard else "  (target)")))
            self._table.setItem(row, 1, QTableWidgetItem(req.requirement_text))
            self._table.setItem(row, 2, QTableWidgetItem(req.current_text))
            status = "✓ Pass" if req.passed else ("✗ Fail" if req.hard else "✗ Off target")
            self._table.setItem(row, 3, QTableWidgetItem(status))
            info = QTableWidgetItem("ⓘ")
            self._table.setItem(row, 4, info)
        fit_table(self._table)

        ok = results.ok
        self._status.setText("All requirements met" if ok else "Requirements not met")
        muted(self._status, "#3aa564" if ok else "#d05a5a")
