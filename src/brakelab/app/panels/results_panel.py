"""Results panel: a live status banner, a results table, and validation messages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.results import BrakeResults
from ..controller import ProjectController


class ResultsPanel(QWidget):
    """Shows the current results; refreshes whenever the controller recomputes."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("font-size: 15px; font-weight: bold; padding: 6px; border-radius: 4px;")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Quantity", "Front", "Rear", "Unit"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table, 1)

        self._messages = QTextEdit()
        self._messages.setReadOnly(True)
        self._messages.setFixedHeight(120)
        layout.addWidget(self._messages)

        controller.resultsChanged.connect(self.update_results)
        self.update_results(controller.results)

    def update_results(self, r: BrakeResults) -> None:
        d, tq, s, h, p = r.dynamics, r.torque, r.sizing, r.hydraulics, r.pedal_travel
        rows = [
            ("Dynamic axle load", d.dynamic_front, d.dynamic_rear, "N", 1),
            ("Required torque / rotor", tq.front.torque_per_rotor, tq.rear.torque_per_rotor, "N·m", 2),
            ("Required clamp force", s.front.clamp_force, s.rear.clamp_force, "N", 1),
            ("Required line pressure", s.front.line_pressure, s.rear.line_pressure, "MPa", 3),
            ("MC force required", h.mc_force_front, h.mc_force_rear, "N", 1),
            ("Pedal force required", h.bar_force_front, h.bar_force_rear, "N", 1),
        ]
        scalars = [
            ("Vehicle weight", d.weight, "", "N", 1),
            ("Weight transfer", d.weight_transfer, "", "N", 1),
            ("Pedal force delivered", h.pedal_force, "", "N", 1),
            ("Optimal front bias", h.optimal_bias_front, "", "-", 3),
            ("Pedal travel", p.pedal_travel, "", "mm", 1),
        ]
        self._table.setRowCount(len(rows) + len(scalars))
        for i, (name, f, rr, unit, dec) in enumerate(rows + scalars):
            self._table.setItem(i, 0, QTableWidgetItem(name))
            self._table.setItem(i, 1, QTableWidgetItem(f"{f:,.{dec}f}"))
            self._table.setItem(i, 2, QTableWidgetItem("" if rr == "" else f"{rr:,.{dec}f}"))
            self._table.setItem(i, 3, QTableWidgetItem(unit))

        if r.ok:
            self._status.setText("PASS — requirements met")
            self._status.setStyleSheet(self._status.styleSheet() + "background:#1b7a3d; color:white;")
        else:
            self._status.setText("REVIEW REQUIRED")
            self._status.setStyleSheet(self._status.styleSheet() + "background:#b00020; color:white;")

        if r.messages:
            html = []
            for m in r.messages:
                colour = {"error": "#b00020", "warning": "#8a6d00"}.get(m.level, "#333")
                html.append(f'<div style="color:{colour}">[{m.level.upper()}] {m.message}</div>')
            self._messages.setHtml("".join(html))
        else:
            self._messages.setHtml('<div style="color:#1b7a3d">No issues.</div>')
