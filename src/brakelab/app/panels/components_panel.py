"""Component selection, a shared custom-part library and portable setup snapshots."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from ...components.library import SLOTS, current_values
from ..controller import ProjectController
from ..uikit import style_combo
from ..widgets import CollapsibleSection
from .component_manager import ComponentEditor, ComponentManager


class ComponentsPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._combos = {}
        content = QWidget()
        form = QFormLayout(content)
        form.setContentsMargins(14, 2, 2, 6)
        form.setVerticalSpacing(5)
        for slot, label in (("front_mc", "Front master cylinder"), ("rear_mc", "Rear master cylinder"),
                            ("caliper", "Caliper"), ("pad", "Brake pad")):
            combo = style_combo(QComboBox())
            combo.setMaxVisibleItems(15)
            combo.activated.connect(lambda _i, s=slot: self._apply(s))
            self._combos[slot] = combo
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(combo, 1)
            more = QToolButton()
            more.setText("\u22ef")
            more.setPopupMode(QToolButton.InstantPopup)
            menu = QMenu(more)
            menu.addAction("Save current values as component…", lambda s=slot: self._save_current(s))
            more.setMenu(menu)
            layout.addWidget(more)
            form.addRow(QLabel(label), row)
        manage = QPushButton("Manage components…")
        manage.clicked.connect(self._manage)
        form.addRow(manage)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(CollapsibleSection("Components", content, expanded=True))
        controller.resultsChanged.connect(self._refresh)
        controller.configReplaced.connect(self._refresh)
        controller.componentsChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self, *_):
        for slot, combo in self._combos.items():
            parts = self._controller.component_library.all(SLOTS[slot])
            selected = self._controller.selected_component(slot)
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Custom", None)
            index = 0
            for part in parts:
                combo.addItem(part.name, part)
                if part == selected:
                    index = combo.count() - 1
            if selected is not None and index == 0:
                combo.addItem(f"{selected.name} (saved values)", selected)
                index = combo.count() - 1
            combo.setCurrentIndex(index)
            combo.setToolTip(selected.note if selected else "Custom — edit the numeric inputs manually.")
            combo.blockSignals(False)

    def _apply(self, slot):
        self._controller.select_component(slot, self._combos[slot].currentData())

    def _manage(self):
        ComponentManager(self._controller, self).exec()

    def _save_current(self, slot):
        editor = ComponentEditor(self, kind=SLOTS[slot], values=current_values(self._controller.config, slot))
        while editor.exec() == QDialog.Accepted:
            try:
                part = self._controller.component_library.save(editor.component)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "Cannot save component", str(exc))
                continue
            self._controller.componentsChanged.emit()
            self._controller.select_component(slot, part)
            return
