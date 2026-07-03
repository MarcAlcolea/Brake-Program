"""INPUTS panel — categorized inputs as plain text fields, each with a unit and click-to-open info.

- Values are edited in text fields (not spin boxes) and commit only on Enter / focus-out, so they
  can't be nudged by accident. Bad or out-of-range entries revert.
- Each number shows its unit; where the unit is convertible (length, mass, force, pressure, area,
  volume) a small dropdown lets you view/enter that number in another unit (metric is the default).
  Switching units never changes the stored value.
- The ⓘ sends the input's original spreadsheet note to the in-window Details area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.unit_convert import compatible_units, convert
from ..controller import ProjectController
from ..field_spec import GROUPS, Field
from ..widgets import InfoButton, InfoSink


def _fmt(value: float) -> str:
    return f"{value:.6g}"


class InputPanel(QWidget):
    def __init__(self, controller: ProjectController, sink: InfoSink, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._sink = sink
        self._editors: dict[str, QWidget] = {}
        self._display_unit: dict[str, str] = {}

        layout = QVBoxLayout(self)
        title = QLabel("INPUTS")
        tf = title.font()
        tf.setBold(True)
        title.setFont(tf)
        layout.addWidget(title)

        for group in GROUPS:
            box = QGroupBox(group.title)
            grid = QGridLayout(box)
            grid.setColumnStretch(1, 1)
            for row, field in enumerate(group.fields):
                grid.addWidget(QLabel(field.label), row, 0)
                grid.addWidget(self._make_editor(field), row, 1)
                grid.addWidget(self._make_unit_widget(field), row, 2)
                if field.note:
                    grid.addWidget(InfoButton(field.label, field.note, sink), row, 3)
            layout.addWidget(box)
        layout.addStretch(1)

        controller.configReplaced.connect(self._reload_from_config)

    # --- widgets -----------------------------------------------------------------------------
    def _make_editor(self, field: Field) -> QWidget:
        value = self._controller.value(field.path)
        if field.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.toggled.connect(lambda checked, p=field.path: self._controller.set_value(p, bool(checked)))
            self._editors[field.path] = w
            return w

        self._display_unit[field.path] = field.unit
        edit = QLineEdit(self._display_text(field, value))
        edit.setAlignment(Qt.AlignRight)
        edit.editingFinished.connect(lambda e=edit, fld=field: self._commit(e, fld))
        self._editors[field.path] = edit
        return edit

    def _make_unit_widget(self, field: Field) -> QWidget:
        units = compatible_units(field.unit) if field.kind != "bool" else []
        if len(units) <= 1:
            text = "" if field.unit in ("", "-") else field.unit
            return QLabel(text)
        combo = QComboBox()
        combo.addItems(units)
        combo.setCurrentText(field.unit)
        combo.currentTextChanged.connect(lambda u, fld=field: self._change_unit(fld, u))
        return combo

    # --- value <-> display -------------------------------------------------------------------
    def _display_text(self, field: Field, canonical_value: float) -> str:
        if field.kind == "int":
            return str(int(canonical_value))
        shown = convert(float(canonical_value), field.unit, self._display_unit.get(field.path, field.unit))
        return _fmt(shown)

    def _commit(self, edit: QLineEdit, field: Field) -> None:
        try:
            entered = float(edit.text().strip())
        except ValueError:
            edit.setText(self._display_text(field, self._controller.value(field.path)))
            return
        # Convert what the user typed (in the display unit) back to the canonical unit.
        canonical = convert(entered, self._display_unit.get(field.path, field.unit), field.unit)
        if field.kind == "int":
            canonical = round(canonical)
        canonical = max(field.minimum, min(field.maximum, canonical))  # clamp in canonical units
        self._controller.set_value(field.path, canonical)
        edit.setText(self._display_text(field, canonical))

    def _change_unit(self, field: Field, new_unit: str) -> None:
        self._display_unit[field.path] = new_unit
        editor = self._editors[field.path]
        if isinstance(editor, QLineEdit):
            editor.setText(self._display_text(field, self._controller.value(field.path)))

    def _reload_from_config(self, _config) -> None:
        for path, editor in self._editors.items():
            value = self._controller.value(path)
            editor.blockSignals(True)
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QLineEdit):
                field = self._field_for(path)
                if field:
                    editor.setText(self._display_text(field, value))
            editor.blockSignals(False)

    @staticmethod
    def _field_for(path: str) -> Field | None:
        for group in GROUPS:
            for field in group.fields:
                if field.path == path:
                    return field
        return None
