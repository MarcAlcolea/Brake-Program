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

from ...persistence import ConfigLibrary, config_to_dict, load_config, save_config
from ..controller import ProjectController
from ..uikit import style_combo

_CUSTOM = "Custom"  # shown when the live config no longer matches its saved preset


def _config_equal(a, b) -> bool:
    """Two configs are 'the same preset' if everything but the display name matches."""
    da, db = config_to_dict(a), config_to_dict(b)
    da.pop("name", None)
    db.pop("name", None)
    return da == db


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
        style_combo(self._combo)
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
        menu.addSeparator()
        team = menu.addMenu("Team library")
        team.addAction("Set team folder…", self._set_team_folder)
        team.addAction("Publish current setup to team", self._publish)
        more.setMenu(menu)
        row.addWidget(more)
        row.addStretch(1)

        self._reload_combo(select=controller.config.name)
        # Keep the dropdown in sync when the config is replaced elsewhere (e.g. the other tab's bar).
        controller.configReplaced.connect(lambda c: self._reload_combo(select=c.name))
        # Editing any input diverges the config from its saved preset — reflect that as "Custom".
        controller.resultsChanged.connect(lambda _r: self._sync_selection())

    def _reload_combo(self, select: str | None = None) -> None:
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(self._library.names())
        self._combo.addItem(_CUSTOM)
        if select:
            i = self._combo.findText(select)
            if i >= 0:
                self._combo.setCurrentIndex(i)
        self._combo.blockSignals(False)

    def _sync_selection(self) -> None:
        """Show the preset name while the config matches it; switch to 'Custom' once it's edited."""
        name = self._controller.config.name
        target = name if self._matches_saved(name) else _CUSTOM
        self._combo.blockSignals(True)
        i = self._combo.findText(target)
        self._combo.setCurrentIndex(i if i >= 0 else self._combo.findText(_CUSTOM))
        self._combo.blockSignals(False)

    def _matches_saved(self, name: str) -> bool:
        if not name or not self._library.exists(name):
            return False
        try:
            return _config_equal(self._controller.config, self._library.load(name))
        except Exception:  # noqa: BLE001 — a bad/missing file just means "not matching"
            return False

    def _on_selected(self, name: str) -> None:
        if not name or name == _CUSTOM:
            return  # "Custom" is a status, not a loadable preset
        # Load when switching presets, or when re-picking the current one to discard unsaved edits.
        if name != self._controller.config.name or not self._matches_saved(name):
            self._controller.replace_config(self._library.load(name))

    def _save(self) -> None:
        self._library.save(self._controller.config)
        # Notify both tabs' bars so they refresh their list and drop the "Custom" state together.
        self._controller.configReplaced.emit(self._controller.config)

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
        if self._library.is_shared(name):
            QMessageBox.information(
                self, "Delete",
                "This is a team preset. Delete it from the shared folder to remove it for everyone.")
            return
        if len(self._library.names()) <= 1:
            QMessageBox.information(self, "Delete", "Keep at least one saved configuration.")
            return
        if QMessageBox.question(self, "Delete", f"Delete preset '{name}'?") != QMessageBox.Yes:
            return
        self._library.delete(name)
        remaining = self._library.names()
        self._controller.replace_config(self._library.load(remaining[0]))
        self._reload_combo(select=remaining[0])

    # --- team library ------------------------------------------------------------------------
    def _set_team_folder(self) -> None:
        start = str(self._library.shared_dir) if self._library.shared_dir else str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self, "Choose the shared team folder (synced via Dropbox, Google Drive, Git…)", start)
        if not path:
            return
        self._library.set_shared_dir(path)
        self._reload_combo(select=self._controller.config.name)
        QMessageBox.information(
            self, "Team library",
            f"Team folder set to:\n{path}\n\nSaved setups in that folder now appear in the list. "
            "Use 'Publish current setup to team' to share the current one.")

    def _publish(self) -> None:
        if not self._library.shared_configured:
            if QMessageBox.question(
                    self, "Team library",
                    "No team folder is set yet. Choose one now?") != QMessageBox.Yes:
                return
            self._set_team_folder()
            if not self._library.shared_configured:
                return
        try:
            self._library.publish(self._controller.config)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Publish failed", str(exc))
            return
        self._reload_combo(select=self._controller.config.name)
        QMessageBox.information(
            self, "Team library",
            f"Published '{self._controller.config.name}' to the team folder. Teammates who point at "
            "the same folder will see it.")

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
