"""Brake-rotor thermal phase — heat flux and film coefficient for ANSYS transient studies.

Pure functions, like the other phases. This reproduces the hand calculations in
``reference/Brake Rotors Simulations 2026.docx`` (the "Peak Heat Flux Calculation" section), which
produce the boundary-condition values typed into an ANSYS transient thermal simulation. The tool
does not run the simulation; it computes the numbers the simulation needs.

Energy → power → per-rotor power → peak heat flux::

    E = 1/2 m (v_i^2 - v_f^2)            kinetic energy shed in one braking event
    P = E / t                            average braking power over the event
    P_rotor = P * bias_axle / N_rotors   power into one rotor on that axle  (audit T2)
    q = P_rotor / A_swept                peak heat flux on the rotor face

The per-axle rotor count ``N`` is read from the shared :class:`~brakelab.core.models.Axle`, so a
single inboard rear rotor (``N_r = 1``) correctly absorbs the whole rear axle's energy instead of
half (audit **T2**). ``rotor_heat_fraction`` exposes the rotor/pad energy split (audit **T3**); it
defaults to 1.0, which reproduces the document.

The convection boundary condition uses the document's speed-dependent estimate for air blowing over
a flat plate, ``h = a + b·v`` (defaults a=10, b=3), evaluated at the start and end of the braking
event — the two ends of the tabular curve the film coefficient follows as the car slows.
"""

from __future__ import annotations

from .models import Axle, MassProperties, PedalBox, Thermal
from .results import ThermalResult


def solve_thermal(
    mass: MassProperties,
    pedal_box: PedalBox,
    front_axle: Axle,
    rear_axle: Axle,
    thermal: Thermal,
) -> ThermalResult:
    """Compute the thermal quantities for one braking event."""
    v_i, v_f, t = thermal.v_initial, thermal.v_final, thermal.brake_time

    energy = 0.5 * mass.total_mass * (v_i * v_i - v_f * v_f)
    power = energy / t if t > 0 else 0.0

    n_front = max(front_axle.n_rotors, 1)
    n_rear = max(rear_axle.n_rotors, 1)
    fraction = thermal.rotor_heat_fraction

    power_front = power * pedal_box.balance_bias_front / n_front * fraction
    power_rear = power * pedal_box.balance_bias_rear / n_rear * fraction

    area = thermal.swept_area
    flux_front = power_front / area if area > 0 else 0.0
    flux_rear = power_rear / area if area > 0 else 0.0

    film_start = thermal.film_intercept + thermal.film_slope * v_i
    film_end = thermal.film_intercept + thermal.film_slope * v_f

    return ThermalResult(
        braking_energy=energy,
        braking_power=power,
        power_front_rotor=power_front,
        power_rear_rotor=power_rear,
        heat_flux_front=flux_front,
        heat_flux_rear=flux_rear,
        film_coeff_start=film_start,
        film_coeff_end=film_end,
    )
