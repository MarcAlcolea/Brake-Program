"""Declarative description of the Thermal tab — inputs, outputs, and the shared read-only values.

Mirrors ``field_spec`` / ``output_spec`` but for the brake-rotor thermal (ANSYS-input) calculations.
Kept separate so these rows appear only on the Thermal tab, not on Main. The physics lives in
``core/thermal.py``; this file is pure presentation.

- ``INPUT_GROUPS`` — the thermal-specific editable inputs (velocities, swept area, film-coeff model…).
- ``SHARED`` — values already entered on the Main tab that drive the thermal math. They are shown
  read-only here (edit them on Main); listing them keeps the Thermal tab self-explanatory.
- ``OUTPUT_GROUPS`` — the computed heat-flux / film-coefficient / energy quantities.
"""

from __future__ import annotations

from dataclasses import dataclass

from .field_spec import Field, Group
from .output_spec import Output, OutputGroup, _o

INPUT_GROUPS: tuple[Group, ...] = (
    Group(
        "Braking Event",
        (
            Field("thermal.v_initial", "Initial speed (v(i))", "m/s", "float", 1, 60, 2,
                  "Car speed at the start of the braking event (assumed)."),
            Field("thermal.v_final", "Final speed (v(f))", "m/s", "float", 0, 60, 2,
                  "Car speed at the end of the braking event (assumed)."),
            Field("thermal.brake_time", "Braking time (t)", "s", "float", 0.1, 30, 2,
                  "Duration of the braking event; the heat-flux load step in ANSYS (assumed)."),
        ),
    ),
    Group(
        "Rotor Heat Input",
        (
            Field("thermal.swept_area", "Pad swept area on rotor, both faces (A)", "m²", "float",
                  0.0001, 0.5, 8,
                  "Area of the friction 'ring' the pad sweeps on the rotor, counting BOTH faces. "
                  "Peak heat flux = rotor power / this area."),
            Field("thermal.rotor_heat_fraction", "Rotor heat partition", "-", "float", 0.1, 1.0, 3,
                  "Fraction of braking energy that goes into the rotor rather than the pad "
                  "(audit T3). 1.0 reproduces the reference document; ~0.85–0.90 is physically "
                  "typical."),
        ),
    ),
    Group(
        "ANSYS Boundary Conditions",
        (
            Field("thermal.ambient_temp", "Ambient / initial temperature", "°C", "float", -20, 200, 1,
                  "Ambient air temperature and the rotor's initial temperature in the transient "
                  "study (assumed 22 °C)."),
            Field("thermal.cool_time", "Cooling step time (t(cool))", "s", "float", 0, 120, 1,
                  "Non-braking time simulated after the braking step, so the rotor can cool "
                  "(ANSYS step 2)."),
            Field("thermal.film_intercept", "Film coeff. intercept (a in h=a+b·v)", "W/m²·K",
                  "float", 0, 200, 2,
                  "Estimate of air convection over a flat surface: h = a + b·v. 'a' is the still-air "
                  "term."),
            Field("thermal.film_slope", "Film coeff. slope (b in h=a+b·v)", "W/m²·K per m/s",
                  "float", 0, 50, 2,
                  "Estimate of air convection over a flat surface: h = a + b·v. 'b' scales with car "
                  "speed."),
        ),
    ),
)


@dataclass(frozen=True)
class SharedValue:
    """A value entered on the Main tab, shown read-only on Thermal because it drives the math."""

    label: str
    path: str            # dotted config path (may resolve to a derived property)
    unit: str
    decimals: int = 3


SHARED: tuple[SharedValue, ...] = (
    SharedValue("Vehicle mass (M)", "mass.total_mass", "kg", 1),
    SharedValue("Front brake bias (B(f))", "pedal_box.balance_bias_front", "-", 3),
    SharedValue("Rear brake bias (B(r))", "pedal_box.balance_bias_rear", "-", 3),
    SharedValue("Front rotors (N(f))", "front_axle.n_rotors", "-", 0),
    SharedValue("Rear rotors (N(r))", "rear_axle.n_rotors", "-", 0),
)


OUTPUT_GROUPS: tuple[OutputGroup, ...] = (
    OutputGroup(
        "Heat Input",
        (
            _o("Braking energy (E)", "J", "E = 1/2 * M * (v(i)^2 - v(f)^2)",
               "Kinetic energy shed in one braking event.",
               lambda r, c: r.thermal.braking_energy),
            _o("Braking power (P)", "W", "P = E / t",
               "Average power dissipated over the braking event.",
               lambda r, c: r.thermal.braking_power),
            _o("Power into one front rotor (P(f))", "W", "P(f) = P * B(f) / N(f) * partition",
               "Front axle share of power, split over the front rotors.",
               lambda r, c: r.thermal.power_front_rotor),
            _o("Power into one rear rotor (P(r))", "W", "P(r) = P * B(r) / N(r) * partition",
               "Rear axle share of power, split over the rear rotors. A single inboard rear rotor "
               "(N(r)=1) takes the whole rear share (audit T2).",
               lambda r, c: r.thermal.power_rear_rotor),
        ),
    ),
    OutputGroup(
        "ANSYS Inputs — Heat Flux & Convection",
        (
            _o("Peak heat flux, front rotor (Q(f))", "W/m²", "Q(f) = P(f) / A",
               "Apply as the heat-flux magnitude on the front rotor's pad-contact faces.",
               lambda r, c: r.thermal.heat_flux_front),
            _o("Peak heat flux, rear rotor (Q(r))", "W/m²", "Q(r) = P(r) / A",
               "Apply as the heat-flux magnitude on the rear rotor's pad-contact faces.",
               lambda r, c: r.thermal.heat_flux_rear),
            _o("Film coefficient at brake start", "W/m²·K", "h = a + b * v(i)",
               "Convection coefficient on the non-contact faces at the start of braking (car "
               "fastest). Use as the first point of the tabular film-coefficient curve.",
               lambda r, c: r.thermal.film_coeff_start),
            _o("Film coefficient at brake end", "W/m²·K", "h = a + b * v(f)",
               "Convection coefficient at the end of braking (car slowest). The film coefficient "
               "rises back toward the start value as the car speeds up again while cooling.",
               lambda r, c: r.thermal.film_coeff_end),
        ),
    ),
)
