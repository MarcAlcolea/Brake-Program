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
from .. import theme
from ..controller import ProjectController
from ..uikit import muted, style_combo
from ..widgets import CollapsibleSection, InfoButton


def _fmt(value: float) -> str:
    return f"{value:.6g}"


class InputPanel(QWidget):
    def __init__(self, controller: ProjectController, groups=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._editors: dict[str, QWidget] = {}
        self._assumed_boxes: dict[str, QCheckBox] = {}
        self._display_unit: dict[str, str] = {}

        if groups is None:
            from ..field_spec import GROUPS
            groups = GROUPS
        self._groups = groups

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        for group in groups:
            content = QWidget()
            grid = QGridLayout(content)
            grid.setContentsMargins(14, 2, 2, 6)
            grid.setColumnStretch(1, 1)
            grid.setVerticalSpacing(5)
            header = QLabel("Assumed")
            muted(header, theme.muted_text())
            hf = header.font()
            hf.setPointSize(max(8, hf.pointSize() - 2))
            header.setFont(hf)
            header.setToolTip("Tick to mark a value as assumed; results that depend on it are flagged with *")
            grid.addWidget(header, 0, 3, Qt.AlignHCenter)
            for row, field in enumerate(group.fields, start=1):
                grid.addWidget(QLabel(field.label), row, 0)
                grid.addWidget(self._make_editor(field), row, 1)
                grid.addWidget(self._make_unit_widget(field), row, 2)
                grid.addWidget(self._make_assumed_box(field), row, 3, Qt.AlignHCenter)
                if field.note:
                    grid.addWidget(InfoButton(field.label, field.note), row, 4)
            layout.addWidget(CollapsibleSection(group.title, content, expanded=True))
        layout.addStretch(1)

        controller.configReplaced.connect(self._reload_from_config)
        # Also refresh when values change without a whole new config — e.g. picking a Component fills
        # the bore/area inputs, and the optimizer can load a design. Editors must reflect that live.
        controller.resultsChanged.connect(self._reload_from_config)

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

    def _make_assumed_box(self, field) -> QWidget:
        """A tiny checkbox marking this value as 'assumed'. Saved with the preset; when checked, the
        outputs that depend on this input show a small warning."""
        box = QCheckBox()
        box.setChecked(self._controller.is_assumed(field.path))
        box.setToolTip("Assumed value — flag outputs that depend on it with a small warning (*)")
        box.setFocusPolicy(Qt.NoFocus)
        box.toggled.connect(lambda checked, p=field.path: self._controller.set_assumed(p, bool(checked)))
        self._assumed_boxes[field.path] = box
        return box

    def _make_unit_widget(self, field) -> QWidget:
        units = compatible_units(field.unit) if field.kind != "bool" else []
        if getattr(field, "fixed_unit", False) or len(units) <= 1:
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
        specs = {f.path: f for g in self._groups for f in g.fields}
        for path, editor in self._editors.items():
            value = self._controller.value(path)
            editor.blockSignals(True)
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QLineEdit) and path in specs:
                editor.setText(self._display_text(specs[path], value))
            editor.blockSignals(False)
        for path, box in self._assumed_boxes.items():
            box.blockSignals(True)
            box.setChecked(self._controller.is_assumed(path))
            box.blockSignals(False)
