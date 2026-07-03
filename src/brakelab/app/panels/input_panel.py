"""INPUTS panel — categorized input forms built from the declarative field spec.

Each field is a labelled editor bound to the controller (edit → recompute → everyone refreshes).
The label carries an "ⓘ" and a hover tooltip showing that input's note, so the meaning of every
parameter is one hover away. Plain default Qt widgets throughout — no custom styling.
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
    """A vertical stack of grouped input forms bound to the controller."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._editors: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        heading = QLabel("INPUTS")
        heading.setToolTip("Design parameters. Hover the ⓘ on any label to see what it means.")
        layout.addWidget(heading)

        for group in GROUPS:
            box = QGroupBox(group.title)
            form = QFormLayout(box)
            for field in group.fields:
                editor = self._make_editor(field)
                self._editors[field.path] = editor
                label = QLabel(f"{field.label}  ⓘ" if field.note else field.label)
                if field.note:
                    label.setToolTip(field.note)
                    editor.setToolTip(field.note)
                form.addRow(label, editor)
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
        if field.unit and field.unit != "-":
            w.setSuffix(f" {field.unit}")
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
