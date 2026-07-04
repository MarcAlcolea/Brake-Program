"""COMPONENTS panel — pick real parts to fill the inputs automatically.

Dropdowns for the front/rear master cylinder, caliper and brake pad. Choosing a part sets the
related input variables (bore, piston area, piston count, pad μ); choosing "Custom" leaves the
values as-is so they can be edited by hand. The current selection is inferred from the values, so
editing an input directly flips the relevant dropdown back to "Custom".
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QVBoxLayout, QWidget

from ...components import catalog
from ..controller import ProjectController


def _bold_title(box: QGroupBox) -> QGroupBox:
    f = box.font()
    f.setBold(True)
    box.setFont(f)
    return box


def _normal(w: QWidget) -> QWidget:
    f = w.font()
    f.setBold(False)
    w.setFont(f)
    return w


class ComponentsPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        box = QGroupBox("Components")
        _bold_title(box)
        form = QFormLayout(box)

        self._front_mc = self._combo([mc.name for mc in catalog.MASTER_CYLINDERS], self._apply_front_mc)
        self._rear_mc = self._combo([mc.name for mc in catalog.MASTER_CYLINDERS], self._apply_rear_mc)
        self._caliper = self._combo([c.name for c in catalog.CALIPERS], self._apply_caliper)
        self._pad = self._combo([p.name for p in catalog.BRAKE_PADS], self._apply_pad)

        form.addRow(_normal_label("Front Master Cylinder"), self._front_mc)
        form.addRow(_normal_label("Rear Master Cylinder"), self._rear_mc)
        form.addRow(_normal_label("Caliper"), self._caliper)
        form.addRow(_normal_label("Brake Pad"), self._pad)
        layout.addWidget(box)

        controller.resultsChanged.connect(lambda _r: self._infer())
        controller.configReplaced.connect(lambda _c: self._infer())
        self._infer()

    def _combo(self, names: list[str], slot) -> QComboBox:
        combo = QComboBox()
        combo.addItem(catalog.CUSTOM)
        combo.addItems(names)
        combo.setMaxVisibleItems(12)
        combo.activated.connect(lambda _i, c=combo, s=slot: s(c.currentText()))
        _normal(combo)
        return combo

    # --- apply selection -> config -----------------------------------------------------------
    def _apply_front_mc(self, name: str) -> None:
        mc = _find(catalog.MASTER_CYLINDERS, name)
        if mc:
            self._controller.apply_values({"hydraulics.mc_bore_front": mc.bore_mm,
                                           "hydraulics.max_mc_stroke": mc.stroke_mm})

    def _apply_rear_mc(self, name: str) -> None:
        mc = _find(catalog.MASTER_CYLINDERS, name)
        if mc:
            self._controller.apply_values({"hydraulics.mc_bore_rear": mc.bore_mm})

    def _apply_caliper(self, name: str) -> None:
        cal = _find(catalog.CALIPERS, name)
        if cal:
            self._controller.apply_values({"caliper.piston_area": cal.piston_area_mm2,
                                           "caliper.n_pistons": cal.n_pistons})

    def _apply_pad(self, name: str) -> None:
        pad = _find(catalog.BRAKE_PADS, name)
        if pad:
            self._controller.apply_values({"pad.friction_coefficient": pad.friction_coefficient})

    # --- infer selection <- config -----------------------------------------------------------
    def _infer(self) -> None:
        c = self._controller.config
        fmc = catalog.match_master_cylinder(c.hydraulics.mc_bore_front)
        rmc = catalog.match_master_cylinder(c.hydraulics.mc_bore_rear)
        cal = catalog.match_caliper(c.caliper.piston_area, c.caliper.n_pistons)
        pad = catalog.match_pad(c.pad.friction_coefficient)
        self._set(self._front_mc, fmc.name if fmc else catalog.CUSTOM)
        self._set(self._rear_mc, rmc.name if rmc else catalog.CUSTOM)
        self._set(self._caliper, cal.name if cal else catalog.CUSTOM)
        self._set(self._pad, pad.name if pad else catalog.CUSTOM)

    @staticmethod
    def _set(combo: QComboBox, name: str) -> None:
        combo.blockSignals(True)
        i = combo.findText(name)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)


def _find(items, name):
    for item in items:
        if item.name == name:
            return item
    return None


def _normal_label(text: str):
    from PySide6.QtWidgets import QLabel

    return _normal(QLabel(text))
