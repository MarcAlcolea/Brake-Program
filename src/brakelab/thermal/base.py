"""Brake-rotor thermal analysis — deferred module (design stub).

Planned as an :class:`~brakelab.analyses.base.Analysis` subclass so it plugs in without touching
the core. It will reproduce and replace the hand calculations in
``reference/Brake Rotors Simulations 2026.docx``:

1. Braking energy per event ``E = 1/2 m (v_i^2 - v_f^2)`` and power ``P = E / t``.
2. Split energy to each rotor. The document splits by hydraulic bias; the engine can instead use
   the actual braking-force distribution from :mod:`brakelab.core.dynamics` (audit **T1**), and it
   must use the same ``n_rotors`` as the mechanical model so an inboard single rear rotor gets the
   full rear energy (audit **T2**).
3. Peak heat flux ``q = P_rotor / A_swept`` and a speed-dependent film coefficient ``h = 10 + 3v``.
4. A lumped-capacitance transient temperature model over a duty cycle, and export of ANSYS-ready
   heat-flux / film-coefficient tabular data.

A ``materials`` library (1018 steel, 4130 chromoly: density, conductivity, specific heat,
emissivity, E, yield, CTE) will seed step 4 — values are captured in ``docs/calculation_audit.md``.
"""

from __future__ import annotations

# Intentionally not implemented in v1. See module docstring and docs/implementation_plan.md.
