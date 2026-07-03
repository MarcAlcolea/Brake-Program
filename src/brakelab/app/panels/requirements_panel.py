"""REQUIREMENTS panel — the checks that decide pass/fail, with the numbers shown.

Each row is one engineering check: its name (hover for why it matters), the condition with the
current values filled in, and PASS/FAIL. Hard requirements must pass; soft ones are targets and are
marked as such. A one-line overall verdict sits on top. This is where you see exactly which outputs
determine acceptance and by how much each check passes or fails.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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

_GREEN = QColor(20, 120, 60)
_RED = QColor(170, 20, 30)
_AMBER = QColor(150, 110, 0)


class RequirementsPanel(QWidget):
    """Live table of engineering requirements plus an overall verdict."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("REQUIREMENTS"))

        self._verdict = QLabel()
        self._verdict.setAlignment(Qt.AlignCenter)
        vfont = self._verdict.font()
        vfont.setBold(True)
        vfont.setPointSize(vfont.pointSize() + 2)
        self._verdict.setFont(vfont)
        layout.addWidget(self._verdict)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Check", "Condition (current values)", "Status"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

        self._notes = QLabel()
        self._notes.setWordWrap(True)
        layout.addWidget(self._notes)

        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def refresh(self, results: BrakeResults) -> None:
        reqs = results.requirements
        self._table.setRowCount(len(reqs))
        for row, req in enumerate(reqs):
            name = QTableWidgetItem(req.name + ("" if req.hard else "  (target)") + "  ⓘ")
            name.setToolTip(f"{req.description}\n\nRequirement: {req.condition}")
            cond = QTableWidgetItem(req.detail)
            cond.setToolTip(req.condition)

            if req.passed:
                status_text, colour = "PASS", _GREEN
            elif req.hard:
                status_text, colour = "FAIL", _RED
            else:
                status_text, colour = "off target", _AMBER
            status = QTableWidgetItem(status_text)
            status.setForeground(colour)
            sfont = status.font()
            sfont.setBold(True)
            status.setFont(sfont)

            self._table.setItem(row, 0, name)
            self._table.setItem(row, 1, cond)
            self._table.setItem(row, 2, status)

        self._verdict.setText("ALL REQUIREMENTS MET" if results.ok else "REQUIREMENTS NOT MET")
        palette = self._verdict.palette()
        palette.setColor(self._verdict.foregroundRole(), _GREEN if results.ok else _RED)
        self._verdict.setPalette(palette)

        warnings = [m.message for m in results.messages if m.level in ("warning", "error")]
        self._notes.setText(("Notes:  " + "   •  ".join(warnings)) if warnings else "")
