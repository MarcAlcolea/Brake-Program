"""OPTIMIZATION tab — tune chosen variables to best meet a goal, then save the result to compare.

Workflow (kept deliberately simple):
1. Pick a goal (plain-language dropdown with a description).
2. Tick the variables to optimize and adjust their allowed ranges (bias defaults to a 0.65 max).
3. Optionally set the pedal-travel window the result must stay within.
4. Run — the before/after table shows what changed and how the key outputs moved.
5. Apply the result to the Design tab, or save it as a new preset so it appears in Compare.
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...analyses import GOALS, OptVariable, optimize
from ...core.engine import BrakeEngine
from ...core.results import BrakeResults
from ...persistence import ConfigLibrary
from ..controller import ProjectController

# (path, label, unit, default min, default max, enabled by default)
_CANDIDATES = [
    ("hydraulics.mc_bore_front", "Master Cylinder Bore (Front)", "mm", 12.0, 25.4, True),
    ("hydraulics.mc_bore_rear", "Master Cylinder Bore (Rear)", "mm", 12.0, 25.4, True),
    ("pedal_box.pedal_ratio", "Pedal Ratio", "-", 3.5, 7.0, True),
    ("pedal_box.balance_bias_front", "Balance Bar Bias (Front)", "-", 0.35, 0.65, True),
    ("rotor.effective_radius", "Effective Rotor Radius", "m", 0.06, 0.12, False),
]


class OptimizationTab(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library
        self._engine = BrakeEngine()
        self._result = None
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Search for the best values of the selected variables. Pick a goal, choose which "
            "variables to tune and their limits, then Run. You can apply the result or save it as a "
            "new preset to compare."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Goal
        goal_row = QHBoxLayout()
        goal_row.addWidget(self._bold(QLabel("Goal:")))
        self._goal = QComboBox()
        self._goal.addItems(list(GOALS.keys()))
        self._goal.currentTextChanged.connect(self._update_goal_desc)
        goal_row.addWidget(self._goal)
        goal_row.addStretch(1)
        layout.addLayout(goal_row)
        self._goal_desc = QLabel()
        self._goal_desc.setWordWrap(True)
        layout.addWidget(self._goal_desc)

        # Variables
        var_box = QGroupBox("Variables to optimize")
        var_box.setStyleSheet("QGroupBox::title { font-weight: bold; }")
        vb = QVBoxLayout(var_box)
        self._var_table = QTableWidget(len(_CANDIDATES), 6)
        self._var_table.setHorizontalHeaderLabels(["Optimize", "Variable", "Unit", "Min", "Max", "Current"])
        self._var_table.verticalHeader().setVisible(False)
        self._var_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._var_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._var_table.setShowGrid(False)
        hh = self._var_table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (0, 2, 3, 4, 5):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self._build_var_rows()
        vb.addWidget(self._var_table)
        layout.addWidget(var_box)

        # Pedal-travel constraint
        cons = QHBoxLayout()
        cons.addWidget(QLabel("Keep pedal travel between"))
        self._travel_min = QLineEdit("30")
        self._travel_max = QLineEdit("60")
        for e in (self._travel_min, self._travel_max):
            e.setFixedWidth(60)
            e.setAlignment(Qt.AlignRight)
        cons.addWidget(self._travel_min)
        cons.addWidget(QLabel("and"))
        cons.addWidget(self._travel_max)
        cons.addWidget(QLabel("mm"))
        cons.addStretch(1)
        run = QPushButton("Run optimization")
        run.clicked.connect(self._run)
        cons.addWidget(run)
        layout.addLayout(cons)

        # Results
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._results = QTableWidget(0, 3)
        self._results.setHorizontalHeaderLabels(["Item", "Current", "Optimized"])
        self._results.verticalHeader().setVisible(False)
        self._results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._results.setSelectionMode(QAbstractItemView.NoSelection)
        self._results.setShowGrid(False)
        rh = self._results.horizontalHeader()
        rh.setSectionResizeMode(0, QHeaderView.Stretch)
        rh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        rh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._results, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._apply_btn = QPushButton("Apply to Design")
        self._apply_btn.clicked.connect(self._apply)
        self._save_btn = QPushButton("Save as new preset…")
        self._save_btn.clicked.connect(self._save_as)
        self._apply_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        actions.addWidget(self._apply_btn)
        actions.addWidget(self._save_btn)
        layout.addLayout(actions)

        self._update_goal_desc(self._goal.currentText())
        self.refresh_current()

    # --- construction helpers ----------------------------------------------------------------
    @staticmethod
    def _bold(label: QLabel) -> QLabel:
        f = label.font()
        f.setBold(True)
        label.setFont(f)
        return label

    def _build_var_rows(self) -> None:
        for row, (path, label, unit, lo, hi, enabled) in enumerate(_CANDIDATES):
            check = QCheckBox()
            check.setChecked(enabled)
            wrap = QWidget()
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(6, 0, 6, 0)
            wl.addWidget(check)
            self._var_table.setCellWidget(row, 0, wrap)
            self._var_table.setItem(row, 1, QTableWidgetItem(label))
            self._var_table.setItem(row, 2, QTableWidgetItem("" if unit in ("", "-") else unit))
            min_edit = QLineEdit(f"{lo:g}")
            max_edit = QLineEdit(f"{hi:g}")
            for e in (min_edit, max_edit):
                e.setFixedWidth(70)
                e.setAlignment(Qt.AlignRight)
            self._var_table.setCellWidget(row, 3, min_edit)
            self._var_table.setCellWidget(row, 4, max_edit)
            current = QTableWidgetItem("")
            current.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._var_table.setItem(row, 5, current)
            self._rows.append({"path": path, "label": label, "unit": unit,
                               "check": check, "min": min_edit, "max": max_edit, "current": current})

    # --- updates -----------------------------------------------------------------------------
    def _update_goal_desc(self, goal: str) -> None:
        self._goal_desc.setText(GOALS[goal][0] if goal in GOALS else "")

    def refresh_current(self) -> None:
        """Update the Current column from the active config (call when the tab is shown)."""
        cfg = self._controller.config
        for r in self._rows:
            r["current"].setText(f"{float(_get(cfg, r['path'])):g}")

    # --- run ---------------------------------------------------------------------------------
    def _run(self) -> None:
        variables = []
        for r in self._rows:
            if not r["check"].isChecked():
                continue
            try:
                lo, hi = float(r["min"].text()), float(r["max"].text())
            except ValueError:
                QMessageBox.warning(self, "Optimization", f"Invalid limits for {r['label']}.")
                return
            if hi <= lo:
                QMessageBox.warning(self, "Optimization", f"Max must exceed Min for {r['label']}.")
                return
            variables.append(OptVariable(r["path"], r["label"], r["unit"], lo, hi))
        if not variables:
            QMessageBox.information(self, "Optimization", "Select at least one variable to optimize.")
            return
        try:
            tmin, tmax = float(self._travel_min.text()), float(self._travel_max.text())
        except ValueError:
            QMessageBox.warning(self, "Optimization", "Invalid pedal-travel limits.")
            return

        base = copy.deepcopy(self._controller.config)
        self._result = optimize(base, variables, self._goal.currentText(), self._engine, travel_range=(tmin, tmax))
        self._populate_results(base, variables)
        self._apply_btn.setEnabled(True)
        self._save_btn.setEnabled(True)

    def _populate_results(self, base, variables) -> None:
        res = self._result
        before = self._engine.solve(base)
        after = self._engine.solve(res.config)

        rows: list[tuple[str, str, str]] = []
        rows.append(("— Variables —", "", ""))
        for var in variables:
            rows.append((f"{var.label} [{var.unit}]" if var.unit not in ("", "-") else var.label,
                         f"{float(_get(base, var.path)):g}", f"{res.values[var.path]:g}"))
        rows.append(("— Key outputs —", "", ""))
        rows.append(("Required driver force [N]", _fmt(_req_force(before, base)), _fmt(_req_force(after, res.config))))
        rows.append(("Front line pressure [MPa]", _fmt(before.sizing.front.line_pressure, 3), _fmt(after.sizing.front.line_pressure, 3)))
        rows.append(("Rear line pressure [MPa]", _fmt(before.sizing.rear.line_pressure, 3), _fmt(after.sizing.rear.line_pressure, 3)))
        rows.append(("Pedal travel [mm]", _fmt(before.pedal_travel.pedal_travel, 1), _fmt(after.pedal_travel.pedal_travel, 1)))
        rows.append(("Balance bias front", _fmt(base.pedal_box.balance_bias_front, 3), _fmt(res.config.pedal_box.balance_bias_front, 3)))
        rows.append(("All requirements met", "yes" if before.ok else "no", "yes" if after.ok else "no"))

        self._results.setRowCount(len(rows))
        for i, (item, cur, opt) in enumerate(rows):
            name = QTableWidgetItem(item)
            if item.startswith("—"):
                f = name.font()
                f.setBold(True)
                name.setFont(f)
            self._results.setItem(i, 0, name)
            c = QTableWidgetItem(cur)
            o = QTableWidgetItem(opt)
            c.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            o.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._results.setItem(i, 1, c)
            self._results.setItem(i, 2, o)

        status = f"Goal: {res.goal}.  " + ("Feasible — all requirements met." if res.feasible else "Not feasible within bounds.")
        if res.messages:
            status += "  " + " ".join(res.messages)
        self._status.setText(status)

    def _apply(self) -> None:
        if self._result:
            self._controller.replace_config(copy.deepcopy(self._result.config))
            QMessageBox.information(self, "Applied", "Optimized values applied to the Design tab.")

    def _save_as(self) -> None:
        if not self._result:
            return
        default = f"{self._controller.config.name} (optimized)"
        name, ok = QInputDialog.getText(self, "Save as new preset", "Preset name:", text=default)
        name = name.strip()
        if not ok or not name:
            return
        cfg = copy.deepcopy(self._result.config)
        cfg.name = name
        self._library.save(cfg)
        QMessageBox.information(self, "Saved", f"Saved '{name}'. It's now available in the Compare tab.")


def _get(cfg, path):
    from ...core.attrpath import get_by_path
    return get_by_path(cfg, path)


def _req_force(r: BrakeResults, c) -> float:
    return max(r.hydraulics.bar_force_front, r.hydraulics.bar_force_rear) / c.pedal_box.pedal_ratio


def _fmt(v: float, decimals: int = 1) -> str:
    return f"{v:,.{decimals}f}"
