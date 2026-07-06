"""Simulator status — the lock-up and target-deceleration checks, framed as pass/fail.

Mirrors the Main tab's Requirements panel (same look, ⓘ for the meaning of each check) rather than
big coloured banners: each row states the limit, what the setup produces, and a plain ✓/✗ verdict.
The numeric forward quantities live in the adjacent Outputs panel (``forward_spec.OUTPUT_GROUPS``).
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from ...core.results import BrakeResults
from .. import theme
from ..controller import ProjectController
from ..uikit import fit_table, muted, plain_table
from ..widgets import show_popover


class ForwardStatusPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._row_info: dict[int, tuple[str, str]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        heading = QLabel("Lock-Up & Performance")
        heading.setFont(theme.heading_font())
        layout.addWidget(heading)

        # Green/red verdict line, mirroring the Main tab's "All requirements met" banner.
        self._verdict = QLabel()
        layout.addWidget(self._verdict)

        self._table = plain_table(["Check", "Limit", "Produces", "Status", ""], stretch_col=0)
        self._table.cellClicked.connect(self._info)
        layout.addWidget(self._table)

        # Detailed monochrome summary (optimal balance-bar bias etc.) below the table.
        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        controller.resultsChanged.connect(self.refresh)
        self.refresh(controller.results)

    def _info(self, row: int, col: int) -> None:
        if col != 4 or row not in self._row_info:
            return
        name, desc = self._row_info[row]
        rect = self._table.visualRect(self._table.model().index(row, col))
        pos = self._table.viewport().mapToGlobal(rect.bottomLeft())
        show_popover(pos, name, desc)

    def refresh(self, results: BrakeResults) -> None:
        f = results.forward
        if f is None:
            return
        target = self._controller.config.target_decel_g

        checks = [
            (
                "Front lock-up",
                "Lock-up means the front tyres break traction (skid): the brake torque at the front "
                "axle has exceeded what the tyres' grip can hold. Compares front axle brake torque "
                "(Produces) against the front grip torque (Limit) at the current deceleration.",
                f"{f.grip_torque_front:,.0f} N·m",
                f"{f.axle_brake_torque_front:,.0f} N·m",
                not f.front_locked, "Safe", "Locks up",
            ),
            (
                "Rear lock-up",
                "Lock-up means the rear tyres break traction (skid): the rear axle brake torque has "
                "exceeded the rear grip torque. A rear lock-up is especially bad — it makes the car "
                "unstable. Tune the balance-bar bias toward the optimal value to avoid it.",
                f"{f.grip_torque_rear:,.0f} N·m",
                f"{f.axle_brake_torque_rear:,.0f} N·m",
                not f.rear_locked, "Safe", "Locks up",
            ),
            (
                "Target decel",
                "The Target Deceleration set on the Main tab is the design goal. The forward math does "
                "NOT use it (to avoid a circular reference); this row simply compares the deceleration "
                "this pedal force actually produces (Produces) against that target (Limit) so you can "
                "see how close you are.",
                f"{target:,.2f} g",
                f"{f.actual_decel_g:,.2f} g",
                f.actual_decel_g >= target, "Meets", "Below",
            ),
        ]

        self._row_info = {}
        self._table.setRowCount(len(checks))
        all_passed = True
        for row, (name, desc, limit, produces, passed, ok_word, bad_word) in enumerate(checks):
            self._table.setItem(row, 0, QTableWidgetItem(name))
            self._table.setItem(row, 1, QTableWidgetItem(limit))
            self._table.setItem(row, 2, QTableWidgetItem(produces))
            self._table.setItem(row, 3, QTableWidgetItem(f"{'✓' if passed else '✗'} {ok_word if passed else bad_word}"))
            self._table.setItem(row, 4, QTableWidgetItem("ⓘ"))
            self._row_info[row] = (name, desc)
            all_passed = all_passed and passed
        fit_table(self._table)

        # Green when neither axle locks up and the target deceleration is met; red otherwise.
        # Same colours as the Main tab's requirements banner.
        self._verdict.setText("All requirements met" if all_passed else "Requirements not met")
        muted(self._verdict, "#3aa564" if all_passed else "#d05a5a")

        # Plain, monochrome summary line (no coloured banner).
        verdicts = []
        verdicts.append("front locks up" if f.front_locked else "front safe")
        verdicts.append("rear locks up" if f.rear_locked else "rear safe")
        summary = (f"At {f.actual_decel_g:,.2f} g: " + ", ".join(verdicts)
                   + f".  Optimal balance-bar bias (front) ≈ {f.optimal_bias_front:,.2f}"
                   + f" (currently {self._controller.config.pedal_box.balance_bias_front:,.2f}).")
        muted(self._status, theme.muted_text())
        self._status.setText(summary)
