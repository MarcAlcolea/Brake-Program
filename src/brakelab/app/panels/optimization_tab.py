"""Optimization studio — five collapsible sections over the optimization subsystem.

Sections: Variables · Objectives · Constraints · Settings · Results. The user chooses which
parameters may change (and ranges or catalog options), sets objectives and hard constraints, hides
the algorithm behind an effort preset, then runs. Results show ranked feasible designs; any can be
loaded into the calculator or saved as a preset, with a comparison, sensitivity, before/after chart
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
    QHBoxLayout,
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

from ...components import catalog
from ...core.attrpath import get_by_path
from ...core.engine import BrakeEngine
from ...optimization import (
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
from .. import theme
from ..controller import ProjectController
from ..uikit import fit_table, muted, plain_table, style_combo
from ..widgets import CollapsibleSection, InfoButton

_LOCK_SENTINEL = 9.98  # the grip-use metrics fall back to ~9.99 when no forward result exists


def _lock_text(util: float | None) -> str:
    """Turn an axle grip-utilisation into a lock-up verdict (>1.0 means that axle locks)."""
    if util is None or util >= _LOCK_SENTINEL:
        return "—"
    return f"Locks ({util:.2f})" if util > 1.0 + 1e-6 else f"Safe ({util:.2f})"

# (path, label, unit, min, max, on-by-default, kind, note)
_VARIABLES = [
    ("hydraulics.mc_bore_front", "Master Cylinder Bore (Front)", "mm", 12.0, 25.4, True, "mc",
     "Front master-cylinder bore. A smaller bore raises front line pressure (more front braking). "
     "Use 'Search over' to draw from real catalog bores; Min/Max limit which bores are tried."),
    ("hydraulics.mc_bore_rear", "Master Cylinder Bore (Rear)", "mm", 12.0, 25.4, True, "mc",
     "Rear master-cylinder bore. A LARGER bore lowers rear line pressure (less rear braking) — the "
     "usual way to stop the rear locking. Min/Max limit which catalog bores are tried."),
    ("pedal_box.pedal_ratio", "Pedal Ratio", "-", 3.5, 7.0, True, None,
     "Pedal lever ratio. Higher multiplies the driver's force more (less effort) but adds pedal travel."),
    ("pedal_box.balance_bias_front", "Balance Bar Bias (Front)", "-", 0.35, 0.65, True, None,
     "Fraction of pedal force sent to the front master cylinder (0.35–0.65 hardware limit). More "
     "front bias = more front braking, less rear."),
    ("rotor.effective_radius", "Effective Rotor Radius", "m", 0.06, 0.12, False, None,
     "Distance from the hub centre to the pad centre. A larger radius gives more brake torque per "
     "unit clamp force."),
]
_RANGE = "Range (continuous)"
_ALL_MC = "All master cylinders"
# On by default. "rear_grip_use" (rear does not lock) is included so an out-of-the-box run targets the
# common problem of a locking rear. The pedal-travel window is OFF by default: keeping the rear from
# locking usually needs a larger rear bore, which shortens pedal travel below 30 mm — a real conflict —
# so it is left for the user to add back deliberately. Front-before-rear (lockup_stability) is also off
# by default, as it is often infeasible against the balance-bar limit.
_DEFAULT_CONSTRAINTS = {"brake_bias_front", "mc_stroke_headroom", "rear_grip_use"}

from ...optimization.metrics import CONSTRAINT_DEFAULTS  # noqa: E402


def _num(edit: QLineEdit, default: float) -> float:
    try:
        return float(edit.text())
    except (ValueError, AttributeError):
        return default


def _edit(text: str, width: int = 68) -> QLineEdit:
    e = QLineEdit(text)
    e.setFixedWidth(width)
    e.setAlignment(Qt.AlignRight)
    return e


def _cell(text: str, right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if right:
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return item


def _wrap(w: QWidget) -> QWidget:
    holder = QWidget()
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(8, 0, 0, 0)
    lay.addWidget(w)
    lay.addStretch(1)
    return holder


class OptimizationTab(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library
        self._engine = BrakeEngine()
        self._result = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        self._layout = QVBoxLayout(body)
        self._layout.setSpacing(4)

        self._add("1. Variables — what the optimizer may change", self._variables())
        self._add("2. Objectives — optional; rank designs, or leave blank to just meet the constraints",
                  self._objectives())
        self._add("3. Constraints — hard engineering limits", self._constraints())
        self._add("4. Optimization settings", self._settings())

        run = QPushButton("Optimize")
        run.clicked.connect(self._run)
        self._layout.addWidget(run)

        self._add("5. Results", self._results(), expanded=True)
        self._layout.addStretch(1)
        self.refresh_current()

    @property
    def latest_result(self):
        """The most recent optimization result, or ``None`` if none has been run yet."""
        return self._result

    def _add(self, title: str, content: QWidget, expanded: bool = True) -> None:
        self._layout.addWidget(CollapsibleSection(title, content, expanded))

    # ---- 1. Variables -----------------------------------------------------------------------
    def _variables(self) -> QWidget:
        table = plain_table(["Optimize", "Variable", "Unit", "Min", "Max", "Search over", "Current", ""],
                            stretch_col=1)
        self._var_rows = []
        table.setRowCount(len(_VARIABLES))
        for row, (path, label, unit, lo, hi, on, kind, note) in enumerate(_VARIABLES):
            check = QCheckBox()
            check.setChecked(on)
            table.setCellWidget(row, 0, _wrap(check))
            table.setItem(row, 1, _cell(label))
            table.setItem(row, 2, _cell("" if unit in ("", "-") else unit))
            mn, mx = _edit(f"{lo:g}"), _edit(f"{hi:g}")
            table.setCellWidget(row, 3, mn)
            table.setCellWidget(row, 4, mx)
            source = None
            if kind == "mc":
                source = QComboBox()
                source.addItems([_RANGE] + catalog.master_cylinder_series() + [_ALL_MC])
                source.setCurrentIndex(1)
                source.setMaxVisibleItems(8)
                style_combo(source)
                table.setCellWidget(row, 5, source)
                # Min/Max stay enabled: for a catalog series they limit which bores are tried.
            else:
                table.setItem(row, 5, _cell(_RANGE))
            cur = _cell("", right=True)
            table.setItem(row, 6, cur)
            table.setCellWidget(row, 7, _wrap(InfoButton(label, note)))
            self._var_rows.append({"path": path, "label": label, "unit": unit, "check": check,
                                   "min": mn, "max": mx, "source": source, "cur": cur})
        fit_table(table)
        return table

    # ---- 2. Objectives ----------------------------------------------------------------------
    def _objectives(self) -> QWidget:
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(14, 2, 2, 6)
        note = QLabel(
            "Optional. Leave every objective unchecked to simply find any design that satisfies the "
            "constraints below (a feasibility search — e.g. “no lock-up, under 400 N pedal force, "
            "pedal travel 30–60 mm”). Check one or more to rank the feasible designs by what "
            "they minimize, maximize or hit a target."
        )
        note.setWordWrap(True)
        muted(note, theme.muted_text())
        v.addWidget(note)

        self._feasibility = QCheckBox(
            "Find any feasible design — ignore objectives, just satisfy the constraints below")
        self._feasibility.toggled.connect(self._on_feasibility_toggled)
        v.addWidget(self._feasibility)

        table = plain_table(["Use", "Objective", "Unit", "Goal", "Target", "Weight", ""], stretch_col=1)
        self._obj_table = table
        self._obj_rows = []
        table.setRowCount(len(OBJECTIVE_KEYS))
        for row, key in enumerate(OBJECTIVE_KEYS):
            m = METRICS[key]
            check = QCheckBox()
            check.setChecked(key == "required_driver_force")
            table.setCellWidget(row, 0, _wrap(check))
            table.setItem(row, 1, _cell(m.label))
            table.setItem(row, 2, _cell("" if m.unit in ("", "-") else m.unit))
            goal = QComboBox()
            goal.addItems([s.value for s in Sense])
            goal.setMaxVisibleItems(6)
            style_combo(goal)
            table.setCellWidget(row, 3, goal)
            target = _edit("0")
            weight = _edit("1", 52)
            table.setCellWidget(row, 4, target)
            table.setCellWidget(row, 5, weight)
            table.setCellWidget(row, 6, _wrap(InfoButton(m.label, m.note or m.label)))
            self._obj_rows.append({"key": key, "check": check, "goal": goal, "target": target, "weight": weight})
        fit_table(table)
        v.addWidget(table)
        return content

    def _on_feasibility_toggled(self, on: bool) -> None:
        # In feasibility mode there is no objective, so grey out the objectives table entirely.
        self._obj_table.setEnabled(not on)

    # ---- 3. Constraints ---------------------------------------------------------------------
    def _constraints(self) -> QWidget:
        table = plain_table(["Use", "Constraint", "Limit", ""], stretch_col=1)
        self._con_rows = []
        table.setRowCount(len(CONSTRAINT_DEFAULTS))
        for row, (key, op, lo, hi) in enumerate(CONSTRAINT_DEFAULTS):
            m = METRICS[key]
            check = QCheckBox()
            check.setChecked(m.available and key in _DEFAULT_CONSTRAINTS)
            check.setEnabled(m.available)
            table.setCellWidget(row, 0, _wrap(check))
            # Keep the "unavailable" hint inline (short); the full explanation lives in the ⓘ.
            table.setItem(row, 1, _cell(m.label + ("" if m.available else "  (unavailable)")))
            limit = QWidget()
            hl = QHBoxLayout(limit)
            hl.setContentsMargins(4, 0, 4, 0)
            lo_edit = hi_edit = None
            if op == "le":
                hl.addWidget(QLabel("at most"))
                hi_edit = _edit(f"{hi:g}")
                hl.addWidget(hi_edit)
            elif op == "ge":
                hl.addWidget(QLabel("at least"))
                lo_edit = _edit(f"{lo:g}")
                hl.addWidget(lo_edit)
            else:
                lo_edit, hi_edit = _edit(f"{lo:g}", 52), _edit(f"{hi:g}", 52)
                hl.addWidget(lo_edit)
                hl.addWidget(QLabel("to"))
                hl.addWidget(hi_edit)
            hl.addWidget(QLabel("" if m.unit in ("", "-") else m.unit))
            hl.addStretch(1)
            table.setCellWidget(row, 2, limit)
            note = m.note if m.available else f"Unavailable — {m.note}"
            table.setCellWidget(row, 3, _wrap(InfoButton(m.label, note or m.label)))
            self._con_rows.append({"key": key, "op": op, "check": check, "lo": lo_edit, "hi": hi_edit})
        fit_table(table)
        return table

    # ---- 4. Settings ------------------------------------------------------------------------
    def _settings(self) -> QWidget:
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(14, 2, 2, 6)
        row = QHBoxLayout()
        row.addWidget(QLabel("Search effort"))
        self._effort = QComboBox()
        self._effort.addItems(list(EFFORT_PRESETS.keys()))
        self._effort.setCurrentText("Balanced")
        self._effort.setMaxVisibleItems(6)
        style_combo(self._effort)
        row.addWidget(self._effort)
        adv = QCheckBox("Show advanced")
        adv.toggled.connect(lambda on: self._advanced.setVisible(on))
        row.addWidget(adv)
        row.addStretch(1)
        v.addLayout(row)

        self._advanced = QWidget()
        al = QHBoxLayout(self._advanced)
        al.setContentsMargins(0, 0, 0, 0)
        al.addWidget(QLabel("Algorithm"))
        self._algorithm = QComboBox()
        self._algorithm.addItems(list(ALGORITHMS.keys()))
        self._algorithm.setMaxVisibleItems(6)
        style_combo(self._algorithm)
        al.addWidget(self._algorithm)
        al.addWidget(QLabel("Alternatives"))
        self._alternatives = _edit("5", 48)
        al.addWidget(self._alternatives)
        al.addWidget(QLabel("Seed"))
        self._seed = _edit("0", 48)
        al.addWidget(self._seed)
        al.addStretch(1)
        self._advanced.setVisible(False)
        v.addWidget(self._advanced)
        return content

    # ---- 5. Results -------------------------------------------------------------------------
    def _results(self) -> QWidget:
        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(14, 2, 2, 6)
        self._status = QLabel("Set up the sections above and click Optimize.")
        self._status.setWordWrap(True)
        v.addWidget(self._status)

        self._ranked = QTableWidget(0, 0)
        self._ranked.verticalHeader().setVisible(False)
        self._ranked.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ranked.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ranked.setSelectionMode(QAbstractItemView.SingleSelection)
        self._ranked.setShowGrid(False)
        self._ranked.setFrameShape(QTableWidget.NoFrame)
        self._ranked.horizontalHeader().setHighlightSections(False)
        self._ranked.itemSelectionChanged.connect(self._on_select)
        v.addWidget(QLabel("Ranked designs"))
        v.addWidget(self._ranked)

        buttons = QHBoxLayout()
        self._load_btn = QPushButton("Load into calculator")
        self._load_btn.clicked.connect(self._load)
        self._save_btn = QPushButton("Save as preset…")
        self._save_btn.clicked.connect(self._save)
        self._pdf_btn = QPushButton("Export report (PDF)…")
        self._pdf_btn.clicked.connect(self._export)
        for b in (self._load_btn, self._save_btn, self._pdf_btn):
            b.setEnabled(False)
            buttons.addWidget(b)
        buttons.addStretch(1)
        v.addLayout(buttons)

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Current vs selected"))
        self._compare = plain_table(["Metric", "Current", "Selected"], stretch_col=0)
        left.addWidget(self._compare)
        left.addWidget(QLabel("Most influential variables"))
        self._sens = plain_table(["Variable", "Influence"], stretch_col=0)
        left.addWidget(self._sens)
        cols.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Before / after (relative to current)"))
        self._figure = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        right.addWidget(self._canvas)
        cols.addLayout(right, 1)
        v.addLayout(cols)
        return content

    # ---- run --------------------------------------------------------------------------------
    def refresh_current(self) -> None:
        cfg = self._controller.config
        for r in self._var_rows:
            r["cur"].setText(f"{float(get_by_path(cfg, r['path'])):g}")

    def _collect(self) -> OptimizationProblem | None:
        variables = []
        for r in self._var_rows:
            if not r["check"].isChecked():
                continue
            source = r["source"].currentText() if r["source"] is not None else _RANGE
            lo, hi = _num(r["min"], 0), _num(r["max"], 0)
            if hi <= lo:
                QMessageBox.warning(self, "Optimization", f"Max must exceed Min for {r['label']}.")
                return None
            if source != _RANGE:
                # Discrete catalog bores, limited to the Min/Max window the user set.
                all_bores = catalog.all_mc_bores() if source == _ALL_MC else catalog.bores_for_series(source)
                choices = [b for b in all_bores if lo <= b <= hi]
                if not choices:
                    QMessageBox.warning(self, "Optimization",
                                        f"No {source} bores between {lo:g} and {hi:g} mm for {r['label']}. "
                                        "Widen the Min/Max, or use 'Range (continuous)'.")
                    return None
                variables.append(Variable(r["path"], r["label"], r["unit"], min(choices), max(choices), choices=choices))
            else:
                variables.append(Variable(r["path"], r["label"], r["unit"], lo, hi))
        if not variables:
            QMessageBox.information(self, "Optimization", "Enable at least one variable.")
            return None

        feasibility = self._feasibility.isChecked()
        objectives = [] if feasibility else [
            Objective(r["key"], Sense(r["goal"].currentText()), _num(r["target"], 0), _num(r["weight"], 1))
            for r in self._obj_rows if r["check"].isChecked()]
        constraints = []
        for r in self._con_rows:
            if r["check"].isChecked() and r["check"].isEnabled():
                lo = _num(r["lo"], 0) if r["lo"] is not None else None
                hi = _num(r["hi"], 0) if r["hi"] is not None else None
                constraints.append(Constraint(r["key"], Op(r["op"]), lo, hi))
        if feasibility and not constraints:
            QMessageBox.information(self, "Optimization",
                                    "Feasibility mode needs at least one constraint to satisfy. "
                                    "Enable a constraint in section 3, or set an objective instead.")
            return None
        settings = Settings(self._algorithm.currentText(), EFFORT_PRESETS.get(self._effort.currentText(), 3000),
                            int(_num(self._alternatives, 5)), int(_num(self._seed, 0)))
        return OptimizationProblem(variables, objectives, constraints, settings)

    def _run(self) -> None:
        problem = self._collect()
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
        has_obj = bool(self._result.problem.enabled_objectives())
        var_headers = [f"{v.label} [{v.unit}]" if v.unit not in ("", "-") else v.label for v in variables]
        headers = ["Rank", "Feasible", "Front axle", "Rear axle", "Score"] + var_headers
        self._ranked.setColumnCount(len(headers))
        self._ranked.setHorizontalHeaderLabels(headers)
        self._ranked.setRowCount(len(self._result.designs))
        for i, d in enumerate(self._result.designs):
            metrics = d.evaluation.metrics
            self._ranked.setItem(i, 0, _cell(str(i + 1)))
            self._ranked.setItem(i, 1, _cell("yes" if d.evaluation.feasible else "no"))
            self._ranked.setItem(i, 2, _cell(_lock_text(metrics.get("front_grip_use"))))
            self._ranked.setItem(i, 3, _cell(_lock_text(metrics.get("rear_grip_use"))))
            self._ranked.setItem(i, 4, _cell(f"{d.evaluation.score:.3f}" if has_obj else "—", right=True))
            for j, v in enumerate(variables):
                self._ranked.setItem(i, 5 + j, _cell(f"{d.evaluation.values[v.path]:g}", right=True))
        self._ranked.resizeColumnsToContents()
        fit_table(self._ranked)
        for b in (self._load_btn, self._save_btn, self._pdf_btn):
            b.setEnabled(True)

    def _selected(self):
        rows = self._ranked.selectionModel().selectedRows() if self._ranked.selectionModel() else []
        if not rows or not self._result:
            return None
        return self._result.designs[rows[0].row()]

    def _on_select(self) -> None:
        design = self._selected()
        if not design:
            return
        base = self._result.base_config
        before = self._engine.solve(base)
        keys = ["required_driver_force", "brake_bias_front", "front_line_pressure",
                "rear_line_pressure", "pedal_travel", "front_rear_balance",
                "front_grip_use", "rear_grip_use"]
        self._compare.setRowCount(len(keys))
        for i, key in enumerate(keys):
            m = METRICS[key]
            self._compare.setItem(i, 0, _cell(f"{m.label} [{m.unit}]" if m.unit not in ("", "-") else m.label))
            self._compare.setItem(i, 1, _cell(f"{m.getter(before, base):,.2f}", right=True))
            self._compare.setItem(i, 2, _cell(f"{design.evaluation.metrics[key]:,.2f}", right=True))
        fit_table(self._compare)
        self._draw_chart(before, design)

    def _update_sensitivity(self, problem: OptimizationProblem) -> None:
        # Report influence on the objective; in feasibility mode there is none, so fall back to the
        # first constraint's metric (what the search is actually trying to satisfy).
        if problem.enabled_objectives():
            primary = problem.enabled_objectives()[0].metric_key
        elif problem.enabled_constraints():
            primary = problem.enabled_constraints()[0].metric_key
        else:
            primary = "required_driver_force"
        infl = sensitivity(self._result.base_config, problem.enabled_variables(), primary, self._engine)
        self._sens.setRowCount(len(infl))
        for i, item in enumerate(infl):
            self._sens.setItem(i, 0, _cell(item.label))
            self._sens.setItem(i, 1, _cell(f"{item.share * 100:.0f}%", right=True))
        fit_table(self._sens)

    def _draw_chart(self, before, design) -> None:
        keys = ["required_driver_force", "max_line_pressure", "pedal_travel", "front_rear_balance"]
        labels = ["Driver force", "Peak pressure", "Pedal travel", "F/R imbalance"]
        cur = [METRICS[k].getter(before, self._result.base_config) for k in keys]
        sel = [design.evaluation.metrics[k] for k in keys]
        rel_sel = [(s / c) if abs(c) > 1e-9 else 0.0 for s, c in zip(sel, cur)]
        fg = "#e8e8e8" if theme.is_dark() else "#1a1a1a"
        bg = "#161616" if theme.is_dark() else "#ffffff"
        cur_color = "#666666" if theme.is_dark() else "#c0c0c0"   # "Current" — light grey
        sel_color = "#e0e0e0" if theme.is_dark() else "#333333"   # "Selected" — dark grey
        self._figure.clear()
        self._figure.set_facecolor(bg)
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(bg)
        x = range(len(keys))
        ax.bar([i - 0.2 for i in x], [1.0] * len(keys), width=0.4, label="Current", color=cur_color)
        ax.bar([i + 0.2 for i in x], rel_sel, width=0.4, label="Selected", color=sel_color)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=7, color=fg)
        ax.tick_params(colors=fg)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.set_ylabel("relative to current", color=fg, fontsize=8)
        ax.axhline(1.0, color="0.6", linewidth=0.8)
        ax.legend(fontsize=7, facecolor=bg, edgecolor=fg, labelcolor=fg)
        self._canvas.draw_idle()

    # ---- actions ----------------------------------------------------------------------------
    def _load(self) -> None:
        design = self._selected()
        if design:
            self._controller.replace_config(copy.deepcopy(design.config))
            QMessageBox.information(self, "Loaded", "Selected design loaded into the Design tab.")

    def _save(self) -> None:
        design = self._selected()
        if not design:
            return
        name, ok = QInputDialog.getText(self, "Save as preset", "Preset name:", text=f"{self._controller.config.name} (optimized)")
        name = name.strip()
        if ok and name:
            cfg = copy.deepcopy(design.config)
            cfg.name = name
            self._library.save(cfg)
            QMessageBox.information(self, "Saved", f"Saved '{name}'. It's now in the Compare tab.")

    def _export(self) -> None:
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export optimization report", "optimization_report.pdf", "PDF (*.pdf)")
        if path:
            build_optimization_report(self._result, path)
            QMessageBox.information(self, "Report exported", f"Saved to {path}")
