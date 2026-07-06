"""Transient simulation panel on the Thermal page — rotor temperature vs time over the duty cycle.

Runs :func:`brakelab.thermal.simulate_temperature` on the current config and shows a monochrome
temperature/time chart (front rotor solid, rear dashed, ambient dotted), the scalar takeaways in a
small table, and an "Export ANSYS CSV…" button that writes the tabular boundary-condition data.
Rebuilt on every input change like the rest of the app.
"""

from __future__ import annotations

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

matplotlib.rcParams["font.family"] = ["Helvetica", "Helvetica Neue", "Arial", "DejaVu Sans"]

from ...thermal import ThermalSimResult, simulate_temperature, write_ansys_csv
from .. import theme
from ..controller import ProjectController
from ..uikit import fit_table, plain_table


class ThermalSimPanel(QWidget):
    """Chart + takeaways for the lumped-capacitance rotor-temperature simulation."""

    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._result: ThermalSimResult | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._table = plain_table(["", "Front rotor", "Rear rotor"])
        layout.addWidget(self._table)

        self._figure = Figure(figsize=(6, 3.4), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(240)
        layout.addWidget(self._canvas, 1)

        buttons = QHBoxLayout()
        self._export = QPushButton("Export ANSYS CSV…")
        self._export.clicked.connect(self._export_csv)
        buttons.addWidget(self._export)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        controller.resultsChanged.connect(lambda _r: self.refresh())
        controller.configReplaced.connect(lambda _c: self.refresh())
        self.refresh()

    # ---- computation / display ----------------------------------------------------------------
    def refresh(self, *_args) -> None:
        try:
            self._result = simulate_temperature(self._controller.config)
        except Exception:  # noqa: BLE001 — never let a bad input crash the page
            self._result = None

        self._fill_table()
        self._draw()

    def _fill_table(self) -> None:
        r = self._result
        rows = [
            ("Peak temperature (°C)", r and f"{r.peak_front:.1f}", r and f"{r.peak_rear:.1f}"),
            ("End of duty cycle (°C)", r and f"{r.final_front:.1f}", r and f"{r.final_rear:.1f}"),
            ("Rise per stop, no cooling (°C)",
             r and f"{r.adiabatic_rise_front:.1f}", r and f"{r.adiabatic_rise_rear:.1f}"),
        ]
        self._table.setRowCount(len(rows))
        for i, (label, front, rear) in enumerate(rows):
            for j, text in enumerate((label, front or "—", rear or "—")):
                self._table.setItem(i, j, QTableWidgetItem(text))
        fit_table(self._table)

    def _draw(self) -> None:
        fg = "#e8e8e8" if theme.is_dark() else "#1a1a1a"
        bg = "#161616" if theme.is_dark() else "#ffffff"
        soft = "#9a9a9a" if theme.is_dark() else "#7a7a7a"
        self._figure.clear()
        self._figure.set_facecolor(bg)
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(bg)

        r = self._result
        if r is None:
            ax.text(0.5, 0.5, "Simulation unavailable for these inputs.", ha="center", va="center",
                    color=fg, fontsize=9, transform=ax.transAxes)
            ax.axis("off")
            self._canvas.draw_idle()
            return

        ambient = self._controller.config.thermal.ambient_temp
        ax.plot(r.time, r.temp_front, color=fg, linewidth=1.4, label="Front rotor")
        ax.plot(r.time, r.temp_rear, color=fg, linewidth=1.1, linestyle="--", label="Rear rotor")
        ax.axhline(ambient, color=soft, linewidth=0.8, linestyle=":", label="Ambient")
        ax.set_xlabel("Time (s)", color=fg, fontsize=8)
        ax.set_ylabel("Rotor temperature (°C)", color=fg, fontsize=8)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(fg)
        ax.grid(True, alpha=0.25)
        legend = ax.legend(fontsize=7, loc="upper left", frameon=False)
        for text in legend.get_texts():
            text.set_color(fg)
        self._canvas.draw_idle()

    # ---- export ---------------------------------------------------------------------------------
    def _export_csv(self) -> None:
        if self._result is None:
            QMessageBox.warning(self, "Brake Design Studio", "Nothing to export — fix the inputs first.")
            return
        name = self._controller.config.name.replace(" ", "_") or "config"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export ANSYS CSV", f"{name}_thermal_sim.csv", "CSV files (*.csv)")
        if path:
            write_ansys_csv(self._result, path)
