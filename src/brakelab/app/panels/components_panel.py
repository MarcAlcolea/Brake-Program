"""Components — pick real parts to fill the inputs, shown as a collapsible section.

Dropdowns for front/rear master cylinder, caliper and brake pad. Choosing a part sets the related
inputs; "Custom" leaves them for manual editing. The selection is inferred from the current values.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from ...components import catalog
from ..controller import ProjectController
from ..widgets import CollapsibleSection


class ComponentsPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller

        content = QWidget()
        form = QFormLayout(content)
        form.setContentsMargins(14, 2, 2, 6)
        form.setVerticalSpacing(5)

        self._front_mc = self._combo([mc.name for mc in catalog.MASTER_CYLINDERS], self._apply_front_mc)
        self._rear_mc = self._combo([mc.name for mc in catalog.MASTER_CYLINDERS], self._apply_rear_mc)
        self._caliper = self._combo([c.name for c in catalog.CALIPERS], self._apply_caliper)
        self._pad = self._combo([p.name for p in catalog.BRAKE_PADS], self._apply_pad)
        form.addRow(QLabel("Front master cylinder"), self._front_mc)
        form.addRow(QLabel("Rear master cylinder"), self._rear_mc)
        form.addRow(QLabel("Caliper"), self._caliper)
        form.addRow(QLabel("Brake pad"), self._pad)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(CollapsibleSection("Components", content, expanded=True))

        controller.resultsChanged.connect(lambda _r: self._infer())
        controller.configReplaced.connect(lambda _c: self._infer())
        self._infer()

    def _combo(self, names: list[str], slot) -> QComboBox:
        combo = QComboBox()
        combo.addItem(catalog.CUSTOM)
        combo.addItems(names)
        combo.setMaxVisibleItems(len(names) + 1)
        combo.activated.connect(lambda _i, c=combo, s=slot: s(c.currentText()))
        return combo

    def _apply_front_mc(self, name: str) -> None:
        mc = _find(catalog.MASTER_CYLINDERS, name)
        if mc:
            self._controller.apply_values({"hydraulics.mc_bore_front": mc.bore_mm, "hydraulics.max_mc_stroke": mc.stroke_mm})

    def _apply_rear_mc(self, name: str) -> None:
        mc = _find(catalog.MASTER_CYLINDERS, name)
        if mc:
            self._controller.apply_values({"hydraulics.mc_bore_rear": mc.bore_mm})

    def _apply_caliper(self, name: str) -> None:
        cal = _find(catalog.CALIPERS, name)
        if cal:
            self._controller.apply_values({"caliper.piston_area": cal.piston_area_mm2, "caliper.n_pistons": cal.n_pistons})

    def _apply_pad(self, name: str) -> None:
        pad = _find(catalog.BRAKE_PADS, name)
        if pad:
            self._controller.apply_values({"pad.friction_coefficient": pad.friction_coefficient})

    def _infer(self) -> None:
        c = self._controller.config
        self._set(self._front_mc, catalog.match_master_cylinder(c.hydraulics.mc_bore_front))
        self._set(self._rear_mc, catalog.match_master_cylinder(c.hydraulics.mc_bore_rear))
        self._set(self._caliper, catalog.match_caliper(c.caliper.piston_area, c.caliper.n_pistons))
        self._set(self._pad, catalog.match_pad(c.pad.friction_coefficient))

    @staticmethod
    def _set(combo: QComboBox, spec) -> None:
        combo.blockSignals(True)
        i = combo.findText(spec.name if spec else catalog.CUSTOM)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)


def _find(items, name):
    for item in items:
        if item.name == name:
            return item
    return None
