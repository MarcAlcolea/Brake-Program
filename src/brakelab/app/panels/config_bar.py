"""Configuration bar — pick, save, rename and share saved configurations.

The dropdown lists everything in the in-program library. From here you can save the current inputs
as a preset, rename or delete presets, and import/export JSON files to share a configuration with
others. Editing inputs changes the working copy; use Save (or Save As) to store it in the library.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ...persistence import ConfigLibrary, load_config, save_config
from ..controller import ProjectController


class ConfigBar(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("Configuration:"))

        self._combo = QComboBox()
        self._combo.setMinimumWidth(220)
        self._combo.currentTextChanged.connect(self._on_selected)
        layout.addWidget(self._combo)

        for text, slot in (
            ("Save", self._save),
            ("Save As…", self._save_as),
            ("Rename…", self._rename),
            ("Delete", self._delete),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            layout.addWidget(b)

        layout.addSpacing(16)
        for text, slot in (("Import…", self._import), ("Export to folder…", self._export)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            layout.addWidget(b)
        layout.addStretch(1)

        self._reload_combo(select=controller.config.name)

    # --- combo management --------------------------------------------------------------------
    def _reload_combo(self, select: str | None = None) -> None:
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(self._library.names())
        if select:
            i = self._combo.findText(select)
            if i >= 0:
                self._combo.setCurrentIndex(i)
        self._combo.blockSignals(False)

    def _on_selected(self, name: str) -> None:
        if name and name != self._controller.config.name:
            self._controller.replace_config(self._library.load(name))

    # --- actions -----------------------------------------------------------------------------
    def _save(self) -> None:
        self._library.save(self._controller.config)
        self._reload_combo(select=self._controller.config.name)

    def _save_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save As", "New preset name:", text=self._controller.config.name)
        name = name.strip()
        if not ok or not name:
            return
        if self._library.exists(name) and not self._confirm_overwrite(name):
            return
        self._controller.config.name = name
        self._library.save(self._controller.config)
        self._controller.configReplaced.emit(self._controller.config)  # refresh title/inputs
        self._reload_combo(select=name)

    def _rename(self) -> None:
        current = self._controller.config.name
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current)
        name = name.strip()
        if not ok or not name or name == current:
            return
        if self._library.exists(name) and not self._confirm_overwrite(name):
            return
        if self._library.exists(current):
            self._library.rename(current, name)
        self._controller.config.name = name
        self._controller.configReplaced.emit(self._controller.config)
        self._reload_combo(select=name)

    def _delete(self) -> None:
        name = self._controller.config.name
        if len(self._library.names()) <= 1:
            QMessageBox.information(self, "Delete", "Keep at least one saved configuration.")
            return
        if QMessageBox.question(self, "Delete", f"Delete preset '{name}'?") != QMessageBox.Yes:
            return
        self._library.delete(name)
        remaining = self._library.names()
        self._controller.replace_config(self._library.load(remaining[0]))
        self._reload_combo(select=remaining[0])

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import configuration", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            config = load_config(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self._library.save(config)
        self._controller.replace_config(config)
        self._reload_combo(select=config.name)

    def _export(self) -> None:
        default = f"{self._controller.config.name}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export configuration", str(Path.home() / default), "JSON (*.json)")
        if path:
            save_config(self._controller.config, path)
            QMessageBox.information(self, "Exported", f"Saved to {path}")

    def _confirm_overwrite(self, name: str) -> bool:
        return QMessageBox.question(self, "Overwrite", f"'{name}' already exists. Overwrite?") == QMessageBox.Yes
