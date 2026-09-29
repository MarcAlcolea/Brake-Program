"""Create, edit and share parts without changing the installed program."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from ...components.library import Component, FIELDS, KINDS, load_component, new_component, save_component
from ..uikit import style_combo


class ComponentEditor(QDialog):
    def __init__(self, parent=None, component: Component | None = None,
                 kind: str = "pad", values: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit component" if component else "New component")
        self.resize(470, 380)
        self.component = None
        self._identifier = component.id if component else None
        self._initial = dict(component.values if component else values or {})
        self._fields = {}
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self._kind = QComboBox()
        for key, label in KINDS.items():
            self._kind.addItem(label, key)
        self._kind.setCurrentIndex(self._kind.findData(component.kind if component else kind))
        self._kind.setEnabled(component is None and values is None)
        style_combo(self._kind)
        form.addRow("Type", self._kind)
        self._name = QLineEdit(component.name if component else "")
        form.addRow("Name", self._name)
        outer.addLayout(form)
        self._values_form = QFormLayout()
        outer.addLayout(self._values_form)
        self._stroke_note = QLabel("The current car model has one stroke limit: front selection sets it; "
                                  "rear selection applies the bore only.")
        self._stroke_note.setWordWrap(True)
        outer.addWidget(self._stroke_note)
        self._note = QTextEdit()
        self._note.setPlainText(component.note if component else "")
        self._note.setPlaceholderText("Optional notes, source or assumptions")
        self._note.setMaximumHeight(85)
        outer.addWidget(self._note)
        self._error = QLabel()
        self._error.setWordWrap(True)
        outer.addWidget(self._error)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self._kind.currentIndexChanged.connect(self._rebuild)
        self._rebuild()

    def _rebuild(self) -> None:
        while self._values_form.rowCount():
            self._values_form.removeRow(0)
        self._fields = {}
        kind = self._kind.currentData()
        for key, label, lo, hi in FIELDS[kind]:
            edit = QLineEdit(str(self._initial.get(key, "")))
            edit.setPlaceholderText(f"{lo:g} to {hi:g}")
            self._values_form.addRow(label, edit)
            self._fields[key] = edit
        if kind == "master_cylinder":
            edit = QLineEdit(self._initial.get("series", ""))
            self._values_form.addRow("Series", edit)
            self._fields["series"] = edit
        self._stroke_note.setVisible(kind == "master_cylinder")

    def _save(self) -> None:
        try:
            values = {key: edit.text().strip() if key == "series" else float(edit.text().strip())
                      for key, edit in self._fields.items()}
            self.component = new_component(self._kind.currentData(), self._name.text(), values,
                                           self._note.toPlainText(), self._identifier)
        except ValueError as exc:
            self._error.setText(f"Cannot save: {exc}")
            return
        self.accept()


class ComponentManager(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage components")
        self.resize(720, 510)
        self._controller = controller
        self._library = controller.component_library
        outer = QVBoxLayout(self)
        info = QLabel("Create parts for your library, or import/export a component file to share. "
                      "Duplicate a built-in part to customise it. Saved setups keep their own values.")
        info.setWordWrap(True)
        outer.addWidget(info)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._selected)
        outer.addWidget(self._list, 1)
        self._detail = QLabel()
        self._detail.setTextFormat(Qt.PlainText)
        self._detail.setWordWrap(True)
        outer.addWidget(self._detail)
        row = QHBoxLayout()
        self._buttons = {}
        for title, callback in (("New…", self._new), ("Edit…", self._edit),
                                ("Duplicate…", self._duplicate), ("Delete", self._delete),
                                ("Import…", self._import), ("Export…", self._export)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            self._buttons[title] = button
            row.addWidget(button)
        outer.addLayout(row)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        outer.addWidget(close)
        self._reload()

    def _part(self):
        row = self._list.currentRow()
        return self._parts[row] if 0 <= row < len(self._parts) else None

    def _reload(self, identifier=None):
        self._parts = self._library.all()
        self._list.blockSignals(True)
        self._list.clear()
        builtins = self._library.builtin_ids()
        for part in self._parts:
            origin = "Built-in" if part.id in builtins else "Custom"
            self._list.addItem(f"{KINDS[part.kind]} — {part.name} ({origin})")
        selected = next((i for i, p in enumerate(self._parts) if p.id == identifier), 0)
        self._list.setCurrentRow(selected if self._parts else -1)
        self._list.blockSignals(False)
        self._selected()

    def _selected(self, *_):
        part = self._part()
        custom = part is not None and part.id not in self._library.builtin_ids()
        for title in ("Edit…", "Delete"):
            self._buttons[title].setEnabled(custom)
        for title in ("Duplicate…", "Export…"):
            self._buttons[title].setEnabled(part is not None)
        if part:
            details = [f"{label}: {part.values[key]:g}" for key, label, *_ in FIELDS[part.kind]]
            if part.kind == "master_cylinder":
                details.append(f"Series: {part.values['series']}")
            self._detail.setText("\n".join(details + ([part.note] if part.note else [])))
        else:
            self._detail.clear()

    def _changed(self, part=None):
        self._controller.componentsChanged.emit()
        self._reload(part.id if part else None)

    def _edit_part(self, part=None, replace_existing=False):
        editor = ComponentEditor(self, component=part)
        while editor.exec() == QDialog.Accepted:
            try:
                saved = self._library.save(editor.component, replace=replace_existing)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "Cannot save component", str(exc))
                continue
            self._changed(saved)
            return

    def _new(self):
        self._edit_part()

    def _edit(self):
        part = self._part()
        if part and part.id not in self._library.builtin_ids():
            self._edit_part(part, replace_existing=True)

    def _duplicate(self):
        part = self._part()
        if part:
            self._edit_part(replace(part, id=str(uuid4()), name=f"{part.name} copy"))

    def _delete(self):
        part = self._part()
        if part and QMessageBox.question(self, "Delete component", f"Delete '{part.name}' from your library?") == QMessageBox.Yes:
            try:
                self._library.delete(part)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "Cannot delete", str(exc))
                return
            self._changed()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import component", "", "Component files (*.component.json *.json)")
        if not path:
            return
        try:
            part = load_component(path)
            conflict = self._library.conflict(part)
            replace_existing = False
            if conflict and conflict != part:
                box = QMessageBox(self)
                box.setWindowTitle("Component already exists")
                box.setText(f"'{conflict.name}' already exists. Replace it or save a separate copy?")
                overwrite = box.addButton("Replace", QMessageBox.AcceptRole)
                overwrite.setEnabled(conflict.id not in self._library.builtin_ids())
                copy = box.addButton("Save as copy…", QMessageBox.ActionRole)
                box.addButton(QMessageBox.Cancel)
                box.exec()
                if box.clickedButton() == copy:
                    self._edit_part(replace(part, id=str(uuid4()), name=f"{part.name} copy"))
                    return
                if box.clickedButton() != overwrite:
                    return
                replace_existing = True
            part = self._library.save(part, replace=replace_existing)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self._changed(part)

    def _export(self):
        part = self._part()
        if not part:
            return
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", part.name).strip("._") or "component"
        path, _ = QFileDialog.getSaveFileName(self, "Export component to share", f"{filename}.component.json",
                                             "Component files (*.component.json)")
        if path:
            try:
                save_component(part, path)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "Export failed", str(exc))
                return
            QMessageBox.information(self, "Exported", "Send this file to a teammate. They can add it with Manage components → Import.")
