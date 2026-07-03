"""OPTIMIZATION studio — a professional, five-section workflow over the optimization subsystem.

Sections: 1) Variables  2) Objectives  3) Constraints  4) Optimization Settings  5) Results.
The user chooses which parameters may change and their ranges, defines objectives (minimize /
maximize / target) and hard constraints, hides the algorithm behind an effort preset, then runs.
Results show the best design plus ranked feasible alternatives; any can be loaded into the
calculator or saved as a preset, with a comparison table, a sensitivity list, a before/after chart
and a PDF report. All optimization logic lives in ``brakelab.optimization`` — this file is only UI.
"""

from __future__ import annotations

import copy

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.attrpath import get_by_path
from ...core.engine import BrakeEngine
from ...optimization import (
    CONSTRAINT_DEFAULTS,
    EFFORT_PRESETS,
    METRICS,
    OBJECTIVE_KEYS,
    Constraint,
    Objective,
    Op,
    OptimizationProblem,
    OptimizationRunner,
    Sense,
    Settings,
    Variable,
    sensitivity,
)
from ...optimization.algorithms import ALGORITHMS
from ...optimization.report import build_optimization_report
from ...persistence import ConfigLibrary
from ..controller import ProjectController

# Design variables the optimizer may tune: (path, label, unit, min, max, enabled-by-default)
_VARIABLES = [
    ("hydraulics.mc_bore_front", "Master Cylinder Bore (Front)", "mm", 12.0, 25.4, True),
    ("hydraulics.mc_bore_rear", "Master Cylinder Bore (Rear)", "mm", 12.0, 25.4, True),
    ("pedal_box.pedal_ratio", "Pedal Ratio", "-", 3.5, 7.0, True),
    ("pedal_box.balance_bias_front", "Balance Bar Bias (Front)", "-", 0.35, 0.65, True),
    ("rotor.effective_radius", "Effective Rotor Radius", "m", 0.06, 0.12, False),
]
_DEFAULT_CONSTRAINTS = {"brake_bias_front", "lockup_order", "pedal_travel", "mc_stroke_headroom"}


def _bold(w):
    f = w.font()
    f.setBold(True)
    w.setFont(f)
    return w


def _num(edit: QLineEdit, default: float) -> float:
    try:
        return float(edit.text())
    except (ValueError, AttributeError):
        return default


class OptimizationTab(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library
        self._engine = BrakeEngine()
        self._result = None

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        self._layout = QVBoxLayout(body)

        self._build_variables()
        self._build_objectives()
        self._build_constraints()
        self._build_settings()

        run = QPushButton("Optimize")
        run.clicked.connect(self._run)
        self._layout.addWidget(run)

        self._build_results()
        self._layout.addStretch(1)
        self.refresh_current()

    # ---- section helpers --------------------------------------------------------------------
    def _section(self, title: str) -> QVBoxLayout:
        box = QGroupBox(title)
        _bold(box)
        inner = QVBoxLayout(box)
        # children should not inherit the bold title font
        self._layout.addWidget(box)
        return inner

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.setShowGrid(False)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        return t

    @staticmethod
    def _edit(text: str, width: int = 70) -> QLineEdit:
        e = QLineEdit(text)
        e.setFixedWidth(width)
        e.setAlignment(Qt.AlignRight)
        _bold_off(e)
        return e

    # ---- 1. Variables -----------------------------------------------------------------------
    def _build_variables(self) -> None:
        lay = self._section("1. Variables — what the optimizer may change")
        self._var_table = self._table(["Optimize", "Variable", "Unit", "Min", "Max", "Current"])
        self._var_rows = []
        self._var_table.setRowCount(len(_VARIABLES))
        for row, (path, label, unit, lo, hi, on) in enumerate(_VARIABLES):
            check = QCheckBox()
            check.setChecked(on)
            self._var_table.setCellWidget(row, 0, _wrap(check))
            self._var_table.setItem(row, 1, _cell(label))
            self._var_table.setItem(row, 2, _cell("" if unit in ("", "-") else unit))
            mn, mx = self._edit(f"{lo:g}"), self._edit(f"{hi:g}")
            self._var_table.setCellWidget(row, 3, mn)
            self._var_table.setCellWidget(row, 4, mx)
            cur = _cell("", right=True)
            self._var_table.setItem(row, 5, cur)
            self._var_rows.append({"path": path, "label": label, "unit": unit, "check": check, "min": mn, "max": mx, "cur": cur})
        _fit(self._var_table)
        lay.addWidget(self._var_table)

    # ---- 2. Objectives ----------------------------------------------------------------------
    def _build_objectives(self) -> None:
        lay = self._section("2. Objectives — what a good design maximizes / minimizes / targets")
        self._obj_table = self._table(["Use", "Objective", "Unit", "Goal", "Target", "Weight"])
        self._obj_rows = []
        self._obj_table.setRowCount(len(OBJECTIVE_KEYS))
        for row, key in enumerate(OBJECTIVE_KEYS):
            m = METRICS[key]
            check = QCheckBox()
            check.setChecked(key == "required_driver_force")
            self._obj_table.setCellWidget(row, 0, _wrap(check))
            self._obj_table.setItem(row, 1, _cell(m.label))
            self._obj_table.setItem(row, 2, _cell("" if m.unit in ("", "-") else m.unit))
            goal = QComboBox()
            goal.addItems([s.value for s in Sense])
            goal.setMaxVisibleItems(6)
            _bold_off(goal)
            self._obj_table.setCellWidget(row, 3, goal)
            target = self._edit("0")
            self._obj_table.setCellWidget(row, 4, target)
            weight = self._edit("1", 55)
            self._obj_table.setCellWidget(row, 5, weight)
            self._obj_rows.append({"key": key, "check": check, "goal": goal, "target": target, "weight": weight})
        _fit(self._obj_table)
        lay.addWidget(self._obj_table)

    # ---- 3. Constraints ---------------------------------------------------------------------
    def _build_constraints(self) -> None:
        lay = self._section("3. Constraints — hard engineering limits the design must respect")
        self._con_table = self._table(["Use", "Constraint", "Limit", "Note"])
        self._con_rows = []
        self._con_table.setRowCount(len(CONSTRAINT_DEFAULTS))
        for row, (key, op, lo, hi) in enumerate(CONSTRAINT_DEFAULTS):
            m = METRICS[key]
            check = QCheckBox()
            check.setChecked(m.available and key in _DEFAULT_CONSTRAINTS)
            check.setEnabled(m.available)
            self._con_table.setCellWidget(row, 0, _wrap(check))
            self._con_table.setItem(row, 1, _cell(m.label))

            limit_widget = QWidget()
            hl = QHBoxLayout(limit_widget)
            hl.setContentsMargins(4, 0, 4, 0)
            lo_edit = hi_edit = None
            if op == "le":
                hl.addWidget(QLabel("at most"))
                hi_edit = self._edit(f"{hi:g}")
                hl.addWidget(hi_edit)
            elif op == "ge":
                hl.addWidget(QLabel("at least"))
                lo_edit = self._edit(f"{lo:g}")
                hl.addWidget(lo_edit)
            else:  # range
                lo_edit = self._edit(f"{lo:g}", 55)
                hi_edit = self._edit(f"{hi:g}", 55)
                hl.addWidget(lo_edit)
                hl.addWidget(QLabel("to"))
                hl.addWidget(hi_edit)
            hl.addWidget(QLabel("" if m.unit in ("", "-") else m.unit))
            hl.addStretch(1)
            self._con_table.setCellWidget(row, 2, limit_widget)
            self._con_table.setItem(row, 3, _cell("" if m.available else "unavailable — " + m.note))
            self._con_rows.append({"key": key, "op": op, "check": check, "lo": lo_edit, "hi": hi_edit})
        _fit(self._con_table)
        lay.addWidget(self._con_table)

    # ---- 4. Settings ------------------------------------------------------------------------
    def _build_settings(self) -> None:
        lay = self._section("4. Optimization Settings")
        row = QHBoxLayout()
        row.addWidget(QLabel("Search effort:"))
        self._effort = QComboBox()
        self._effort.addItems(list(EFFORT_PRESETS.keys()))
        self._effort.setCurrentText("Balanced")
        self._effort.setMaxVisibleItems(6)
        row.addWidget(self._effort)
        adv = QCheckBox("Show advanced")
        adv.toggled.connect(self._toggle_advanced)
        row.addWidget(adv)
        row.addStretch(1)
        lay.addLayout(row)

        self._advanced = QWidget()
        al = QHBoxLayout(self._advanced)
        al.setContentsMargins(0, 0, 0, 0)
        al.addWidget(QLabel("Algorithm:"))
        self._algorithm = QComboBox()
        self._algorithm.addItems(list(ALGORITHMS.keys()))
        self._algorithm.setMaxVisibleItems(6)
        al.addWidget(self._algorithm)
        al.addWidget(QLabel("Alternatives:"))
        self._alternatives = self._edit("5", 50)
        al.addWidget(self._alternatives)
        al.addWidget(QLabel("Random seed:"))
        self._seed = self._edit("0", 50)
        al.addWidget(self._seed)
        al.addStretch(1)
        self._advanced.setVisible(False)
        lay.addWidget(self._advanced)

    def _toggle_advanced(self, on: bool) -> None:
        self._advanced.setVisible(on)

    # ---- 5. Results -------------------------------------------------------------------------
    def _build_results(self) -> None:
        lay = self._section("5. Results")
        self._status = QLabel("Set up the sections above and click Optimize.")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._ranked = QTableWidget(0, 0)
        self._ranked.verticalHeader().setVisible(False)
        self._ranked.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ranked.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ranked.setSelectionMode(QAbstractItemView.SingleSelection)
        self._ranked.itemSelectionChanged.connect(self._on_select_design)
        lay.addWidget(_bold(QLabel("Ranked designs")))
        lay.addWidget(self._ranked)

        buttons = QHBoxLayout()
        self._load_btn = QPushButton("Load selected into calculator")
        self._load_btn.clicked.connect(self._load_selected)
        self._save_btn = QPushButton("Save selected as preset…")
        self._save_btn.clicked.connect(self._save_selected)
        self._pdf_btn = QPushButton("Export optimization report (PDF)…")
        self._pdf_btn.clicked.connect(self._export_report)
        for b in (self._load_btn, self._save_btn, self._pdf_btn):
            b.setEnabled(False)
            buttons.addWidget(b)
        buttons.addStretch(1)
        lay.addLayout(buttons)

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(_bold(QLabel("Current vs selected design")))
        self._compare = QTableWidget(0, 3)
        self._compare.setHorizontalHeaderLabels(["Metric", "Current", "Selected"])
        self._compare.verticalHeader().setVisible(False)
        self._compare.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._compare.setSelectionMode(QAbstractItemView.NoSelection)
        self._compare.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        left.addWidget(self._compare)
        left.addWidget(_bold(QLabel("Most influential variables")))
        self._sens = QTableWidget(0, 2)
        self._sens.setHorizontalHeaderLabels(["Variable", "Influence"])
        self._sens.verticalHeader().setVisible(False)
        self._sens.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sens.setSelectionMode(QAbstractItemView.NoSelection)
        self._sens.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        left.addWidget(self._sens)
        cols.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(_bold(QLabel("Before / after (relative to current)")))
        self._figure = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        right.addWidget(self._canvas)
        cols.addLayout(right, 1)
        lay.addLayout(cols)

    # ---- run --------------------------------------------------------------------------------
    def refresh_current(self) -> None:
        cfg = self._controller.config
        for r in self._var_rows:
            r["cur"].setText(f"{float(get_by_path(cfg, r['path'])):g}")

    def _collect_problem(self) -> OptimizationProblem | None:
        variables = []
        for r in self._var_rows:
            if not r["check"].isChecked():
                continue
            lo, hi = _num(r["min"], 0), _num(r["max"], 0)
            if hi <= lo:
                QMessageBox.warning(self, "Optimization", f"Max must exceed Min for {r['label']}.")
                return None
            variables.append(Variable(r["path"], r["label"], r["unit"], lo, hi))
        if not variables:
            QMessageBox.information(self, "Optimization", "Enable at least one variable.")
            return None

        objectives = []
        for r in self._obj_rows:
            if r["check"].isChecked():
                objectives.append(Objective(r["key"], Sense(r["goal"].currentText()),
                                            _num(r["target"], 0), _num(r["weight"], 1)))

        constraints = []
        for r in self._con_rows:
            if r["check"].isChecked() and r["check"].isEnabled():
                op = Op(r["op"])
                lo = _num(r["lo"], 0) if r["lo"] is not None else None
                hi = _num(r["hi"], 0) if r["hi"] is not None else None
                constraints.append(Constraint(r["key"], op, lo, hi))

        settings = Settings(
            algorithm=self._algorithm.currentText(),
            iterations=EFFORT_PRESETS.get(self._effort.currentText(), 3000),
            alternatives=int(_num(self._alternatives, 5)),
            seed=int(_num(self._seed, 0)),
        )
        return OptimizationProblem(variables, objectives, constraints, settings)

    def _run(self) -> None:
        problem = self._collect_problem()
        if problem is None:
            return
        base = copy.deepcopy(self._controller.config)
        self._result = OptimizationRunner(base, self._engine).run(problem)
        self._populate_ranked()
        feasible = sum(1 for d in self._result.designs if d.evaluation.feasible)
        msg = f"Found {len(self._result.designs)} design(s); {feasible} feasible."
        if self._result.messages:
            msg += "  " + " ".join(self._result.messages)
        self._status.setText(msg)
        self._update_sensitivity(problem)
        if self._result.designs:
            self._ranked.selectRow(0)

    def _populate_ranked(self) -> None:
        variables = self._result.problem.enabled_variables()
        headers = ["Rank", "Feasible", "Score"] + [f"{v.label} [{v.unit}]" if v.unit not in ("", "-") else v.label for v in variables]
        self._ranked.setColumnCount(len(headers))
        self._ranked.setHorizontalHeaderLabels(headers)
        self._ranked.setRowCount(len(self._result.designs))
        for i, d in enumerate(self._result.designs):
            self._ranked.setItem(i, 0, _cell(str(i + 1)))
            self._ranked.setItem(i, 1, _cell("yes" if d.evaluation.feasible else "no"))
            self._ranked.setItem(i, 2, _cell(f"{d.evaluation.score:.3f}", right=True))
            for j, v in enumerate(variables):
                self._ranked.setItem(i, 3 + j, _cell(f"{d.evaluation.values[v.path]:g}", right=True))
        self._ranked.resizeColumnsToContents()
        for b in (self._load_btn, self._save_btn, self._pdf_btn):
            b.setEnabled(True)

    def _selected_design(self):
        rows = self._ranked.selectionModel().selectedRows() if self._ranked.selectionModel() else []
        if not rows or not self._result:
            return None
        return self._result.designs[rows[0].row()]

    def _on_select_design(self) -> None:
        design = self._selected_design()
        if not design:
            return
        base = self._result.base_config
        before = self._engine.solve(base)
        keys = ["required_driver_force", "brake_bias_front", "front_line_pressure",
                "rear_line_pressure", "pedal_travel", "front_rear_balance"]
        self._compare.setRowCount(len(keys))
        for i, key in enumerate(keys):
            m = METRICS[key]
            cur = m.getter(before, base)
            sel = design.evaluation.metrics[key]
            self._compare.setItem(i, 0, _cell(f"{m.label} [{m.unit}]" if m.unit not in ("", "-") else m.label))
            self._compare.setItem(i, 1, _cell(f"{cur:,.2f}", right=True))
            self._compare.setItem(i, 2, _cell(f"{sel:,.2f}", right=True))
        self._draw_chart(before, design)

    def _update_sensitivity(self, problem: OptimizationProblem) -> None:
        primary = problem.enabled_objectives()[0].metric_key if problem.enabled_objectives() else "required_driver_force"
        infl = sensitivity(self._result.base_config, problem.enabled_variables(), primary, self._engine)
        self._sens.setRowCount(len(infl))
        for i, item in enumerate(infl):
            self._sens.setItem(i, 0, _cell(item.label))
            self._sens.setItem(i, 1, _cell(f"{item.share * 100:.0f}%", right=True))

    def _draw_chart(self, before, design) -> None:
        keys = ["required_driver_force", "max_line_pressure", "pedal_travel", "front_rear_balance"]
        labels = ["Driver force", "Peak pressure", "Pedal travel", "F/R imbalance"]
        cur = [METRICS[k].getter(before, self._result.base_config) for k in keys]
        sel = [design.evaluation.metrics[k] for k in keys]
        rel_cur = [1.0 for _ in keys]
        rel_sel = [(s / c) if abs(c) > 1e-9 else 0.0 for s, c in zip(sel, cur)]
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        x = range(len(keys))
        ax.bar([i - 0.2 for i in x], rel_cur, width=0.4, label="Current")
        ax.bar([i + 0.2 for i in x], rel_sel, width=0.4, label="Selected")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=7)
        ax.set_ylabel("relative to current")
        ax.axhline(1.0, color="0.6", linewidth=0.8)
        ax.legend(fontsize=7)
        self._canvas.draw_idle()

    # ---- actions ----------------------------------------------------------------------------
    def _load_selected(self) -> None:
        design = self._selected_design()
        if design:
            self._controller.replace_config(copy.deepcopy(design.config))
            QMessageBox.information(self, "Loaded", "Selected design loaded into the Design tab.")

    def _save_selected(self) -> None:
        design = self._selected_design()
        if not design:
            return
        default = f"{self._controller.config.name} (optimized)"
        name, ok = QInputDialog.getText(self, "Save as preset", "Preset name:", text=default)
        name = name.strip()
        if ok and name:
            cfg = copy.deepcopy(design.config)
            cfg.name = name
            self._library.save(cfg)
            QMessageBox.information(self, "Saved", f"Saved '{name}'. It's now in the Compare tab.")

    def _export_report(self) -> None:
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export optimization report", "optimization_report.pdf", "PDF (*.pdf)")
        if path:
            build_optimization_report(self._result, path)
            QMessageBox.information(self, "Report exported", f"Saved to {path}")


# --- small widget helpers ---------------------------------------------------------------------
def _bold_off(w):
    f = w.font()
    f.setBold(False)
    w.setFont(f)
    return w


def _cell(text: str, right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if right:
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return item


def _wrap(widget: QWidget) -> QWidget:
    holder = QWidget()
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(8, 0, 0, 0)
    lay.addWidget(widget)
    lay.addStretch(1)
    return holder


def _fit(table: QTableWidget) -> None:
    table.resizeColumnsToContents()
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    height = table.horizontalHeader().height() + 8
    for r in range(table.rowCount()):
        height += table.rowHeight(r)
    table.setMaximumHeight(height + 8)
