"""Compare tab — line up several saved configurations side by side.

Each of the five columns starts empty; pick a preset from the column's dropdown to fill it. The body
is three collapsible sections (click a header to fold it):

- **Inputs that differ** — only the parameters that disagree between the filled setups (small type),
  expanded by default.
- **All inputs** — every input for reference, collapsed by default.
- **Outputs** — all computed outputs, each cell tinted green when higher / red when lower than the
  first (leftmost) filled setup (the Main tab's up/down colours), expanded by default.

Everything lives in one table so the five setup columns stay aligned with the dropdowns.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.attrpath import get_by_path
from ...core.engine import BrakeEngine
from ...persistence import ConfigLibrary
from .. import theme
from ..field_spec import GROUPS as INPUT_GROUPS
from ..forward_spec import OUTPUT_GROUPS as FORWARD_GROUPS
from ..output_spec import GROUPS as OUTPUT_GROUPS
from ..uikit import muted, style_combo

_N_COLS = 5           # number of comparison columns
_EMPTY = "—"          # dropdown sentinel for "no setup in this column"
_DIFF = "Inputs that differ"
_ALL = "All inputs"
_OUT = "Backward outputs (design calc)"
_FWD = "Forward outputs (performance sim)"


def _safe_get(output, result, config):
    """Read an output value, returning None if it can't be computed (e.g. forward result absent)."""
    try:
        return output.getter(result, config)
    except Exception:  # noqa: BLE001 — a missing/None phase must never break the comparison
        return None


def _fmt_input(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return str(value)


def _fmt_output(value: float) -> str:
    v = float(value)
    decimals = 3 if abs(v) < 100 else 1
    return f"{v:,.{decimals}f}"


class CompareTab(QWidget):
    def __init__(self, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._engine = BrakeEngine()
        self._collapsed: dict[str, bool] = {_ALL: True}  # All-inputs starts folded
        self._section_rows: dict[str, list[int]] = {}
        self._header_rows: dict[int, str] = {}
        self._current_section: str | None = None

        self._small_font = QFont()
        self._small_font.setPointSize(11)
        self._small_bold_font = QFont()
        self._small_bold_font.setPointSize(11)
        self._small_bold_font.setBold(True)

        layout = QVBoxLayout(self)
        hint = QLabel("Pick a saved setup per column. For each output, green = higher and red = lower "
                      "than the first (leftmost) setup. Click a section header to fold it.")
        hint.setWordWrap(True)
        muted(hint, theme.muted_text())
        layout.addWidget(hint)

        self._table = QTableWidget(0, 1 + _N_COLS)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setShowGrid(False)
        self._table.setFrameShape(QTableWidget.NoFrame)
        self._table.cellClicked.connect(self._on_click)
        header = self._table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 1 + _N_COLS):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        layout.addWidget(self._table)

        self._combos: list[QComboBox] = []
        self._build_selector_row()
        self.reload_configs()

    # ---- selector row -----------------------------------------------------------------------
    def _build_selector_row(self) -> None:
        """Row 0 of the table holds one dropdown per column. It is kept across refreshes."""
        self._table.setRowCount(1)
        self._table.setItem(0, 0, self._bold_item("Setup"))
        for i in range(_N_COLS):
            combo = QComboBox()
            combo.setMaxVisibleItems(20)
            combo.currentIndexChanged.connect(self.refresh)
            style_combo(combo)
            self._combos.append(combo)
            self._table.setCellWidget(0, 1 + i, combo)

    def reload_configs(self) -> None:
        """Refresh the dropdowns from the library (call when presets change)."""
        names = self._library.names()
        for combo in self._combos:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(_EMPTY)
            combo.addItems(names)
            i = combo.findText(current) if current and current != _EMPTY else -1
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)
        self.refresh()

    def _selected_names(self) -> list[str]:
        return [c.currentText() if c.currentText() != _EMPTY else "" for c in self._combos]

    # ---- table body -------------------------------------------------------------------------
    def refresh(self, *_args) -> None:
        configs = [self._library.load(n) if n else None for n in self._selected_names()]
        self._table.setRowCount(1)  # keep the selector row, drop the old body
        self._section_rows = {}
        self._header_rows = {}
        self._current_section = None

        filled = [i for i, c in enumerate(configs) if c is not None]
        if not filled:
            return
        if len(filled) < 2:
            self._note("Select at least two setups to compare them.")

        # Inputs that differ (small type, expanded by default).
        self._begin_section(_DIFF)
        shown = 0
        for group in INPUT_GROUPS:
            for field in group.fields:
                values = [None if c is None else get_by_path(c, field.path) for c in configs]
                present = [v for v in values if v is not None]
                if len({_fmt_input(v) for v in present}) > 1:
                    self._plain_row(field.label, [None if v is None else _fmt_input(v) for v in values],
                                    small=True)
                    shown += 1
        if shown == 0 and len(filled) >= 2:
            self._note("All inputs are identical.", in_section=True)

        # All inputs (small type, collapsed by default). Differing rows are bold so they stand out
        # even inside the full list (the same rows appear on their own in "Inputs that differ").
        self._begin_section(_ALL)
        for group in INPUT_GROUPS:
            for field in group.fields:
                values = [None if c is None else get_by_path(c, field.path) for c in configs]
                present = [v for v in values if v is not None]
                differs = len({_fmt_input(v) for v in present}) > 1
                self._plain_row(field.label, [None if v is None else _fmt_input(v) for v in values],
                                small=True, bold=differs)

        # Outputs, tinted green/red vs. the first filled setup — split into the backward design calc
        # and the forward performance simulation so each can be read (and folded) on its own.
        results = [None if c is None else self._engine.solve(c) for c in configs]
        baseline = filled[0]
        self._add_output_section(_OUT, OUTPUT_GROUPS, results, configs, baseline)
        self._add_output_section(_FWD, FORWARD_GROUPS, results, configs, baseline)

        ok = [None if results[i] is None else results[i].ok for i in range(len(configs))]
        self._plain_row("All requirements met", [None if v is None else _fmt_input(v) for v in ok])

        self._apply_collapsed()

    def _add_output_section(self, title, groups, results, configs, baseline: int) -> None:
        """One collapsible section of output rows, each tinted green/red vs. the baseline column."""
        self._begin_section(title)
        for group in groups:
            for output in group.outputs:
                values = [None if results[i] is None else _safe_get(output, results[i], configs[i])
                          for i in range(len(configs))]
                label = output.label + (f" [{output.unit}]" if output.unit not in ("", "-") else "")
                self._output_row(label, values, baseline)

    # ---- row builders -----------------------------------------------------------------------
    def _bold_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        item.setFlags(Qt.ItemIsEnabled)
        return item

    def _begin_section(self, title: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        arrow = "▸" if self._collapsed.get(title, False) else "▾"
        self._table.setItem(row, 0, self._bold_item(f"{arrow}  {title}"))
        self._table.setSpan(row, 0, 1, 1 + _N_COLS)
        self._current_section = title
        self._section_rows[title] = []
        self._header_rows[row] = title

    def _record(self, row: int) -> None:
        if self._current_section is not None:
            self._section_rows[self._current_section].append(row)

    def _note(self, text: str, in_section: bool = False) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setForeground(QColor(theme.muted_text()))
        self._table.setItem(row, 0, item)
        self._table.setSpan(row, 0, 1, 1 + _N_COLS)
        if in_section:
            self._record(row)

    def _plain_row(self, label, shown_values, small: bool = False, bold: bool = False) -> None:
        """Label + pre-formatted string values, no colour (used for inputs and the requirements row).

        ``bold`` emphasises a whole row (used to flag inputs that differ between the compared setups)."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        cells = [QTableWidgetItem(label)]
        for text in shown_values:
            item = QTableWidgetItem("" if text is None else text)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cells.append(item)
        font = self._small_bold_font if (small and bold) else (
            self._small_font if small else None)
        for col, item in enumerate(cells):
            if font is not None:
                item.setFont(font)
            self._table.setItem(row, col, item)
        self._record(row)

    def _output_row(self, label, values, baseline: int) -> None:
        """Numeric output row; each cell tinted green if higher / red if lower than the baseline column."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(label))
        base = values[baseline]
        for i, v in enumerate(values):
            item = QTableWidgetItem("" if v is None else _fmt_output(v))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if v is not None and base is not None and i != baseline and abs(v - base) > 1e-9:
                item.setBackground(theme.increase_color() if v > base else theme.decrease_color())
            self._table.setItem(row, 1 + i, item)
        self._record(row)

    # ---- collapsing -------------------------------------------------------------------------
    def _apply_collapsed(self) -> None:
        for title, rows in self._section_rows.items():
            hidden = self._collapsed.get(title, False)
            for r in rows:
                self._table.setRowHidden(r, hidden)

    def _on_click(self, row: int, _col: int) -> None:
        title = self._header_rows.get(row)
        if title is None:
            return
        collapsed = not self._collapsed.get(title, False)
        self._collapsed[title] = collapsed
        self._table.item(row, 0).setText(f"{'▸' if collapsed else '▾'}  {title}")
        for r in self._section_rows.get(title, []):
            self._table.setRowHidden(r, collapsed)
