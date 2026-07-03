"""REQUIREMENTS panel — what the current inputs require vs what the setup produces.

Columns: Requirement · What the inputs require · What the setup produces · Status · ⓘ. No inequality
symbols — each side is a plain phrase. Pass/fail is shown as ✓ / ✗ (monochrome). Clicking a row's ⓘ
sends its spreadsheet comment to the in-window Details area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.results import BrakeResults, Requirement
from ..controller import ProjectController
from ..widgets import InfoSink


class RequirementsPanel(QWidget):
    def __init__(self, controller: ProjectController, sink: InfoSink, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sink = sink
        self._row_req: dict[int, Requirement] = {}

        layout = QVBoxLayout(self)
        title = QLabel("REQUIREMENTS")
        tf = title.font()
        tf.setBold(True)
        title.setFont(tf)
        layout.addWidget(title)

        self._verdict = QLabel()
        vf = self._verdict.font()
        vf.setBold(True)
        vf.setPointSize(vf.pointSize() + 1)
        self._verdict.setFont(vf)
        layout.addWidget(self._verdict)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Requirement", "The inputs require", "The setup produces", "Status", ""]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    _INFO_COL = 4

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col != self._INFO_COL:
            return  # only the ⓘ column opens details
        req = self._row_req.get(row)
        if req:
            self._sink(req.name, req.description)

    def refresh(self, results: BrakeResults) -> None:
        reqs = results.requirements
        self._row_req = dict(enumerate(reqs))
        self._table.setRowCount(len(reqs))
        for row, req in enumerate(reqs):
            name = QTableWidgetItem(req.name + ("" if req.hard else "  (target)"))
            require = QTableWidgetItem(req.requirement_text)
            produce = QTableWidgetItem(req.current_text)
            if req.passed:
                status_text = "✓ PASS"
            elif req.hard:
                status_text = "✗ FAIL"
            else:
                status_text = "✗ off target"
            status = QTableWidgetItem(status_text)
            info = QTableWidgetItem("ⓘ")
            info.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, name)
            self._table.setItem(row, 1, require)
            self._table.setItem(row, 2, produce)
            self._table.setItem(row, 3, status)
            self._table.setItem(row, 4, info)

        self._verdict.setText(
            "Status:  ALL REQUIREMENTS MET" if results.ok else "Status:  REQUIREMENTS NOT MET"
        )
