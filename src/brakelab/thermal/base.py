"""Brake-rotor thermal analysis — future full-simulation module (design stub).

The *algebraic ANSYS-input* calculations from ``reference/Brake Rotors Simulations 2026.docx`` are
already implemented as a core phase in :mod:`brakelab.core.thermal` and shown on the GUI's Thermal
tab (steps 1–3 below). This package is reserved for the heavier, later work — a self-contained
transient temperature *simulation* that plugs in as an :class:`~brakelab.analyses.base.Analysis`
without touching the core:

1. [done, core] Braking energy ``E = 1/2 m (v_i^2 - v_f^2)`` and power ``P = E / t``.
2. [done, core] Split energy to each rotor, coupled to the mechanical model's ``n_rotors`` so an
   inboard single rear rotor gets the full rear energy (audit **T2**), with an explicit rotor/pad
   partition (audit **T3**). The document's hydraulic-bias split is used; using the actual
   braking-force distribution from :mod:`brakelab.core.dynamics` instead (audit **T1**) is a
   possible refinement.
3. [done, core] Peak heat flux ``q = P_rotor / A_swept`` and a speed-dependent film coefficient
   ``h = a + b v``.
4. [done, simulation.py] A lumped-capacitance transient temperature model over a duty cycle, and
   export of ANSYS-ready heat-flux / film-coefficient tabular data as CSV.

Possible next step: a ``materials`` library (1018 steel, 4130 chromoly: density, conductivity,
specific heat, emissivity, E, yield, CTE) so rotor material is a dropdown — values are captured in
``docs/calculation_audit.md``.
"""

from __future__ import annotations
