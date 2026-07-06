"""Transient rotor-temperature simulation — a lumped-capacitance duty cycle.

Answers "how hot do the rotors actually get after N stops?" without leaving the tool, and exports
the time-tabular data an ANSYS transient study wants. One representative rotor per axle is
simulated as a single thermal mass (lumped capacitance — valid while conduction through the rotor
is fast compared to surface exchange, which holds for thin FSAE rotors):

    m·c · dT/dt = P_in(t) − h(v)·A·(T − T_amb) − ε·σ·A·(T_K⁴ − T_amb,K⁴)

- **Heat in**: during each braking event (duration ``brake_time``) the rotor absorbs the same
  per-rotor power the ANSYS-input phase computes (:mod:`brakelab.core.thermal`, audits T2/T3
  included) — constant over the event, since that power is already the event average.
- **Convection**: the document's film model ``h = a + b·v`` with the car slowing ``v_i → v_f``
  linearly while braking, then travelling at ``cool_speed`` for ``cool_time`` between stops.
- **Radiation**: grey-body with ``emissivity``; negligible cold, significant near fade temperatures.
- **Areas**: the pad swept area (both faces) is used for both heat input and surface exchange —
  a deliberate simplification; hat/vane surfaces would add cooling area, so results are slightly
  conservative (hot).

The duty cycle is ``n_stops`` × (brake + cool). Explicit Euler integration; the thermal time
constant m·c/(h·A) is hundreds of seconds, so the default step is far inside stability.

Assumption defaults (rotor mass 1.3 kg, c_p 486 J/kg·K for 1018 steel, ε 0.28 machined steel) are
stated in the UI and should be replaced with measured/actual values.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ..core.models import VehicleConfig
from ..core.thermal import solve_thermal

STEFAN_BOLTZMANN = 5.670374419e-8  # W/m²·K⁴
_KELVIN = 273.15


@dataclass(frozen=True)
class ThermalSimResult:
    """Time histories (equal-length lists) plus the scalar takeaways."""

    time: list[float]          # s
    temp_front: list[float]    # °C — one front rotor
    temp_rear: list[float]     # °C — one rear rotor
    film_coeff: list[float]    # W/m²·K — h(v(t)), same for both axles
    flux_front: list[float]    # W/m² — applied heat flux on the front rotor
    flux_rear: list[float]     # W/m²
    peak_front: float          # °C
    peak_rear: float           # °C
    final_front: float         # °C — at the end of the duty cycle
    final_rear: float          # °C
    adiabatic_rise_front: float  # °C — one stop with zero cooling: E_rotor / (m·c)
    adiabatic_rise_rear: float   # °C


def simulate_temperature(config: VehicleConfig, dt: float = 0.02) -> ThermalSimResult:
    """Run the duty-cycle simulation for ``config``. Pure; no Qt, no files."""
    th = config.thermal
    steady = solve_thermal(config.mass, config.pedal_box, config.front_axle, config.rear_axle, th)

    m_c = max(th.rotor_mass, 1e-9) * max(th.rotor_specific_heat, 1e-9)
    area = max(th.swept_area, 0.0)
    t_amb = th.ambient_temp
    brake_t = max(th.brake_time, 0.0)
    cool_t = max(th.cool_time, 0.0)
    n_stops = max(int(th.n_stops), 1)

    def film(v: float) -> float:
        return max(th.film_intercept + th.film_slope * v, 0.0)

    def losses(temp: float, h: float) -> float:
        conv = h * area * (temp - t_amb)
        rad = th.emissivity * STEFAN_BOLTZMANN * area * (
            (temp + _KELVIN) ** 4 - (t_amb + _KELVIN) ** 4
        )
        return conv + rad

    time = [0.0]
    tf = [t_amb]
    tr = [t_amb]
    hs = [film(th.v_initial)]
    qf = [0.0]
    qr = [0.0]

    now = 0.0
    temp_f = temp_r = t_amb
    for _ in range(n_stops):
        for braking, duration in ((True, brake_t), (False, cool_t)):
            steps = max(int(round(duration / dt)), 1) if duration > 0 else 0
            for i in range(steps):
                if braking:
                    frac = (i + 0.5) / steps
                    v = th.v_initial + (th.v_final - th.v_initial) * frac
                    p_f, p_r = steady.power_front_rotor, steady.power_rear_rotor
                else:
                    v = th.cool_speed
                    p_f = p_r = 0.0
                h = film(v)
                temp_f += (p_f - losses(temp_f, h)) * dt / m_c
                temp_r += (p_r - losses(temp_r, h)) * dt / m_c
                temp_f = max(temp_f, t_amb) if temp_f < t_amb else temp_f
                temp_r = max(temp_r, t_amb) if temp_r < t_amb else temp_r
                now += dt
                time.append(now)
                tf.append(temp_f)
                tr.append(temp_r)
                hs.append(h)
                qf.append(steady.heat_flux_front if braking else 0.0)
                qr.append(steady.heat_flux_rear if braking else 0.0)

    return ThermalSimResult(
        time=time,
        temp_front=tf,
        temp_rear=tr,
        film_coeff=hs,
        flux_front=qf,
        flux_rear=qr,
        peak_front=max(tf),
        peak_rear=max(tr),
        final_front=tf[-1],
        final_rear=tr[-1],
        adiabatic_rise_front=steady.power_front_rotor * brake_t / m_c,
        adiabatic_rise_rear=steady.power_rear_rotor * brake_t / m_c,
    )


def write_ansys_csv(result: ThermalSimResult, path: str | Path) -> None:
    """Export the time histories as CSV — the tabular heat-flux / film-coefficient / temperature
    data an ANSYS transient thermal study takes as boundary conditions (and a validation trace)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "time_s",
            "temp_front_C",
            "temp_rear_C",
            "film_coeff_W_m2K",
            "heat_flux_front_W_m2",
            "heat_flux_rear_W_m2",
        ])
        for row in zip(
            result.time, result.temp_front, result.temp_rear,
            result.film_coeff, result.flux_front, result.flux_rear,
        ):
            w.writerow([f"{x:.6g}" for x in row])
