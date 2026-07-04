"""Inputs — one collapsible section per phase, each a simple grid of fields.

Values are plain text fields (no spin boxes) that commit on Enter / focus-out and revert on bad
input. Each number shows its unit; convertible units get a small dropdown (metric default). The ⓘ
opens the field's note in a popover next to the icon. No group-box borders, no bold except the
section headers.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.unit_convert import compatible_units, convert
from ..controller import ProjectController
from ..uikit import style_combo
from ..widgets import CollapsibleSection, InfoButton


def _fmt(value: float) -> str:
    return f"{value:.6g}"


class InputPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._editors: dict[str, QWidget] = {}
        self._display_unit: dict[str, str] = {}

        from ..field_spec import GROUPS

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        for group in GROUPS:
            content = QWidget()
            grid = QGridLayout(content)
            grid.setContentsMargins(14, 2, 2, 6)
            grid.setColumnStretch(1, 1)
            grid.setVerticalSpacing(5)
            for row, field in enumerate(group.fields):
                grid.addWidget(QLabel(field.label), row, 0)
                grid.addWidget(self._make_editor(field), row, 1)
                grid.addWidget(self._make_unit_widget(field), row, 2)
                if field.note:
                    grid.addWidget(InfoButton(field.label, field.note), row, 3)
            layout.addWidget(CollapsibleSection(group.title, content, expanded=True))
        layout.addStretch(1)

        controller.configReplaced.connect(self._reload_from_config)

    def _make_editor(self, field) -> QWidget:
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
        edit.setMaximumWidth(130)
        edit.editingFinished.connect(lambda e=edit, fld=field: self._commit(e, fld))
        self._editors[field.path] = edit
        return edit

    def _make_unit_widget(self, field) -> QWidget:
        units = compatible_units(field.unit) if field.kind != "bool" else []
        if len(units) <= 1:
            return QLabel("" if field.unit in ("", "-") else field.unit)
        combo = QComboBox()
        combo.addItems(units)
        combo.setCurrentText(field.unit)
        combo.setMaxVisibleItems(len(units))
        combo.currentTextChanged.connect(lambda u, fld=field: self._change_unit(fld, u))
        return style_combo(combo)

    def _display_text(self, field, canonical_value: float) -> str:
        if field.kind == "int":
            return str(int(canonical_value))
        shown = convert(float(canonical_value), field.unit, self._display_unit.get(field.path, field.unit))
        return _fmt(shown)

    def _commit(self, edit: QLineEdit, field) -> None:
        try:
            entered = float(edit.text().strip())
        except ValueError:
            edit.setText(self._display_text(field, self._controller.value(field.path)))
            return
        canonical = convert(entered, self._display_unit.get(field.path, field.unit), field.unit)
        if field.kind == "int":
            canonical = round(canonical)
        canonical = max(field.minimum, min(field.maximum, canonical))
        self._controller.set_value(field.path, canonical)
        edit.setText(self._display_text(field, canonical))

    def _change_unit(self, field, new_unit: str) -> None:
        self._display_unit[field.path] = new_unit
        editor = self._editors[field.path]
        if isinstance(editor, QLineEdit):
            editor.setText(self._display_text(field, self._controller.value(field.path)))

    def _reload_from_config(self, _config) -> None:
        from ..field_spec import GROUPS

        specs = {f.path: f for g in GROUPS for f in g.fields}
        for path, editor in self._editors.items():
            value = self._controller.value(path)
            editor.blockSignals(True)
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QLineEdit) and path in specs:
                editor.setText(self._display_text(specs[path], value))
            editor.blockSignals(False)
