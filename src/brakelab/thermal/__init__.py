"""Brake-rotor thermal analysis.

- :mod:`.simulation` — the transient lumped-capacitance duty-cycle simulation (rotor temperature
  vs time over repeated stops) and ANSYS-ready CSV export.
- :mod:`.base` — the original design notes for this package.

The algebraic ANSYS-input values (peak flux, film coefficients) live in :mod:`brakelab.core.thermal`.
"""

from .simulation import ThermalSimResult, simulate_temperature, write_ansys_csv

__all__ = ["ThermalSimResult", "simulate_temperature", "write_ansys_csv"]
