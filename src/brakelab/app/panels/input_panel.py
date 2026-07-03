"""Categorized input panels built from the declarative field spec.

Each :class:`~brakelab.app.field_spec.Group` becomes a titled form; each field becomes a bound
widget that writes back to the controller (which recomputes and notifies everyone else).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..controller import ProjectController
from ..field_spec import GROUPS, Field


class InputPanel(QWidget):
    """A scrollable stack of grouped input forms bound to the controller."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._editors: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        for group in GROUPS:
            box = QGroupBox(group.title)
            form = QFormLayout(box)
            for field in group.fields:
                editor = self._make_editor(field)
                self._editors[field.path] = editor
                label = field.label + (f"  [{field.unit}]" if field.unit else "")
                form.addRow(QLabel(label), editor)
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
        if field.kind == "int":
            w = QSpinBox()
            w.setRange(int(field.minimum), int(field.maximum))
            w.setSingleStep(int(field.step))
            w.setValue(int(value))
            w.valueChanged.connect(lambda v, p=field.path: self._controller.set_value(p, int(v)))
            return w
        w = QDoubleSpinBox()
        w.setRange(field.minimum, field.maximum)
        w.setSingleStep(field.step)
        w.setDecimals(field.decimals)
        w.setSuffix(f" {field.unit}" if field.unit and field.unit != "-" else "")
        w.setValue(float(value))
        w.valueChanged.connect(lambda v, p=field.path: self._controller.set_value(p, float(v)))
        return w

    def _reload_from_config(self, _config) -> None:
        """Refresh every editor after a new config is loaded, without triggering recompute loops."""
        for path, editor in self._editors.items():
            value = self._controller.value(path)
            editor.blockSignals(True)
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QSpinBox):
                editor.setValue(int(value))
            elif isinstance(editor, QDoubleSpinBox):
                editor.setValue(float(value))
            editor.blockSignals(False)
