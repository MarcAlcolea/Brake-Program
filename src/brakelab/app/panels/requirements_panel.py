"""REQUIREMENTS panel — the checks that decide pass/fail, with the numbers shown.

Each row is one engineering check: its name, the condition with current values filled in, and a
plain ✓ PASS / ✗ FAIL (monochrome, no colour). Clicking the ⓘ cell explains why the check matters.
Hard requirements must pass; soft ones are targets. A one-line overall verdict sits on top.
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
from ..widgets import show_info


class RequirementsPanel(QWidget):
    """Live table of engineering requirements plus an overall verdict."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Check", "Condition (current values)", "Status", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

        self._notes = QLabel()
        self._notes.setWordWrap(True)
        layout.addWidget(self._notes)

        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        req = self._row_req.get(row)
        if req:
            show_info(self, req.name, f"{req.description}\n\nRequirement: {req.condition}")

    def refresh(self, results: BrakeResults) -> None:
        reqs = results.requirements
        self._row_req = dict(enumerate(reqs))
        self._table.setRowCount(len(reqs))
        for row, req in enumerate(reqs):
            name = QTableWidgetItem(req.name + ("" if req.hard else "  (target)"))
            cond = QTableWidgetItem(req.detail)
            if req.passed:
                status_text = "✓ PASS"
            elif req.hard:
                status_text = "✗ FAIL"
            else:
                status_text = "– off target"
            status = QTableWidgetItem(status_text)
            info = QTableWidgetItem("ⓘ")
            info.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, name)
            self._table.setItem(row, 1, cond)
            self._table.setItem(row, 2, status)
            self._table.setItem(row, 3, info)

        self._verdict.setText("Status:  ALL REQUIREMENTS MET" if results.ok else "Status:  REQUIREMENTS NOT MET")

        warnings = [m.message for m in results.messages if m.level in ("warning", "error")]
        self._notes.setText(("Notes:  " + "   •  ".join(warnings)) if warnings else "")
