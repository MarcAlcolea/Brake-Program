"""Configuration bar — choose a preset and save; extra actions live behind a compact menu.

The dropdown lists the in-program library. Save / Save As are one click; Rename, Delete, Import and
Export-to-folder are grouped under a "⋯" menu to keep the row uncluttered.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QWidget,
)

from ...persistence import ConfigLibrary, load_config, save_config
from ..controller import ProjectController


class ConfigBar(QWidget):
    def __init__(self, controller: ProjectController, library: ConfigLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._library = library

        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 2)
        row.addWidget(QLabel("Configuration"))

        self._combo = QComboBox()
        self._combo.setMinimumWidth(240)
        self._combo.setMaxVisibleItems(20)
        self._combo.currentTextChanged.connect(self._on_selected)
        row.addWidget(self._combo)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        save_as = QPushButton("Save As…")
        save_as.clicked.connect(self._save_as)
        row.addWidget(save)
        row.addWidget(save_as)

        more = QToolButton()
        more.setText("⋯")
        more.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(more)
        menu.addAction("Rename…", self._rename)
        menu.addAction("Delete", self._delete)
        menu.addSeparator()
        menu.addAction("Import…", self._import)
        menu.addAction("Export to folder…", self._export)
        more.setMenu(menu)
        row.addWidget(more)
        row.addStretch(1)

        self._reload_combo(select=controller.config.name)

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

    def _save(self) -> None:
        self._library.save(self._controller.config)
        self._reload_combo(select=self._controller.config.name)

    def _save_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save As", "New preset name:", text=self._controller.config.name)
        name = name.strip()
        if not ok or not name:
            return
        if self._library.exists(name) and not self._confirm(name):
            return
        self._controller.config.name = name
        self._library.save(self._controller.config)
        self._controller.configReplaced.emit(self._controller.config)
        self._reload_combo(select=name)

    def _rename(self) -> None:
        current = self._controller.config.name
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current)
        name = name.strip()
        if not ok or not name or name == current:
            return
        if self._library.exists(name) and not self._confirm(name):
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

    def _confirm(self, name: str) -> bool:
        return QMessageBox.question(self, "Overwrite", f"'{name}' already exists. Overwrite?") == QMessageBox.Yes
