"""INPUTS panel — categorized inputs as plain text fields with click-to-open info.

Values are edited in normal text fields (not spin boxes, so they can't be nudged by accident) and
only committed when you press Enter or leave the field. Out-of-range or non-numeric entries are
rejected and the field reverts. Each row has an "ⓘ" button that opens the input's note on click.
Bare, consistent widgets — the theme is applied globally.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..controller import ProjectController
from ..field_spec import GROUPS, Field
from ..widgets import InfoButton


class InputPanel(QWidget):
    """A vertical stack of grouped input rows bound to the controller."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._editors: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        title = QLabel("INPUTS")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        for group in GROUPS:
            box = QGroupBox(group.title)
            grid = QGridLayout(box)
            grid.setColumnStretch(1, 1)
            for row, field in enumerate(group.fields):
                label = QLabel(field.label)
                editor = self._make_editor(field)
                self._editors[field.path] = editor
                grid.addWidget(label, row, 0)
                grid.addWidget(editor, row, 1)
                if field.note:
                    grid.addWidget(InfoButton(field.label, field.note), row, 2)
            layout.addWidget(box)
        layout.addStretch(1)

        controller.configReplaced.connect(self._reload_from_config)

    def _make_editor(self, field: Field) -> QWidget:
        value = self._controller.value(field.path)
        if field.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            w.toggled.connect(lambda checked, p=field.path: self._controller.set_value(p, bool(checked)))
            return w

        edit = QLineEdit(self._format(field, value))
        edit.setAlignment(Qt.AlignRight)
        if field.unit and field.unit != "-":
            edit.setPlaceholderText(field.unit)
        edit.editingFinished.connect(lambda e=edit, fld=field: self._commit(e, fld))
        return edit

    @staticmethod
    def _format(field: Field, value) -> str:
        if field.kind == "int":
            return str(int(value))
        return f"{float(value):.{field.decimals}f}"

    def _commit(self, edit: QLineEdit, field: Field) -> None:
        text = edit.text().strip()
        try:
            value = int(round(float(text))) if field.kind == "int" else float(text)
        except ValueError:
            edit.setText(self._format(field, self._controller.value(field.path)))
            return
        value = max(field.minimum, min(field.maximum, value))  # clamp to the field's range
        self._controller.set_value(field.path, value)
        edit.setText(self._format(field, value))

    def _reload_from_config(self, _config) -> None:
        """Refresh every editor after a new config is loaded."""
        for path, editor in self._editors.items():
            value = self._controller.value(path)
            editor.blockSignals(True)
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QLineEdit):
                # Recover the field to format correctly.
                field = self._field_for(path)
                editor.setText(self._format(field, value) if field else str(value))
            editor.blockSignals(False)

    @staticmethod
    def _field_for(path: str) -> Field | None:
        for group in GROUPS:
            for field in group.fields:
                if field.path == path:
                    return field
        return None
