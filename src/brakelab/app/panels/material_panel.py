"""Rotor-material chooser for the Thermal tab.

Mirrors the Components panel: pick 1018 Mild Steel or 4130 Chromoly to fill the graph's specific
heat and emissivity, or "Custom" to edit them by hand. Material affects only the preview graph, not
the ANSYS boundary-condition values. Properties come from the reference rotor-simulation document
(see :data:`brakelab.components.catalog.MATERIALS`). The selection is inferred from the current
values, so hand-editing the fields back to a material's numbers re-selects it.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QWidget

from ...components import catalog
from ..controller import ProjectController
from ..uikit import style_combo

_CUSTOM_TIP = "Custom — set specific heat and emissivity by hand in Graph inputs below."


class ThermalMaterialPanel(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller

        form = QFormLayout(self)
        form.setContentsMargins(14, 2, 2, 2)
        form.setVerticalSpacing(5)

        self._combo = QComboBox()
        self._combo.addItem(catalog.CUSTOM)
        self._combo.addItems([m.name for m in catalog.MATERIALS])
        self._combo.setMaxVisibleItems(len(catalog.MATERIALS) + 1)
        self._combo.activated.connect(lambda _i: self._apply(self._combo.currentText()))
        style_combo(self._combo)
        form.addRow(QLabel("Rotor material"), self._combo)

        controller.resultsChanged.connect(lambda _r: self._infer())
        controller.configReplaced.connect(lambda _c: self._infer())
        self._infer()

    def _apply(self, name: str) -> None:
        mat = next((m for m in catalog.MATERIALS if m.name == name), None)
        if mat:
            self._controller.apply_values({
                "thermal.rotor_specific_heat": mat.specific_heat,
                "thermal.emissivity": mat.emissivity,
            })
            self._combo.setToolTip(mat.note)
        else:
            self._combo.setToolTip(_CUSTOM_TIP)

    def _infer(self) -> None:
        t = self._controller.config.thermal
        mat = catalog.match_material(t.rotor_specific_heat, t.emissivity)
        self._combo.blockSignals(True)
        i = self._combo.findText(mat.name if mat else catalog.CUSTOM)
        self._combo.setCurrentIndex(i if i >= 0 else 0)
        self._combo.blockSignals(False)
        self._combo.setToolTip(mat.note if mat else _CUSTOM_TIP)
