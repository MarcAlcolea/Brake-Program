"""Result value objects produced by the engine.

Each phase returns a small immutable dataclass; ``BrakeResults`` aggregates them. Reports, plots
and tests all read these objects, so there is one place to look for every computed quantity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DynamicsResult:
    weight: float                   # N
    weight_transfer: float          # N — longitudinal load transfer under braking
    front_axle_to_cg: float         # m — b
    rear_axle_to_cg: float          # m — c
    static_front: float             # N
    static_rear: float              # N
    dynamic_front: float            # N — during braking
    dynamic_rear: float             # N


@dataclass(frozen=True)
class AxleTorqueResult:
    friction_force_per_wheel: float  # N — grip-limited braking force at one wheel
    torque_per_rotor: float          # N·m — required brake torque at one rotor/caliper


@dataclass(frozen=True)
class TorqueResult:
    front: AxleTorqueResult
    rear: AxleTorqueResult


@dataclass(frozen=True)
class AxleSizingResult:
    clamp_force: float              # N — required clamp force at one caliper
    line_pressure: float            # MPa — required hydraulic line pressure


@dataclass(frozen=True)
class SizingResult:
    front: AxleSizingResult
    rear: AxleSizingResult


@dataclass(frozen=True)
class HydraulicsResult:
    mc_force_front: float           # N — force required at the front master cylinder
    mc_force_rear: float            # N
    bar_force_front: float          # N — pedal force required (via bias) to satisfy the front
    bar_force_rear: float           # N
    pedal_force: float              # N — force delivered at the balance bar (driver × pedal ratio)
    front_requirement_met: bool
    rear_requirement_met: bool
    optimal_bias_front: float       # — bias that balances front/rear demand exactly


@dataclass(frozen=True)
class PedalTravelResult:
    total_piston_area_front: float      # mm² — all front caliper pistons (both sides)
    total_piston_area_rear: float       # mm²
    volume_front: float                 # mm³
    volume_rear: float                  # mm³
    mc_stroke_front: float              # mm
    mc_stroke_rear: float               # mm
    theoretical_effective_stroke: float  # mm — average of the two MC strokes (no compliance)
    effective_stroke: float             # mm — theoretical + compliance
    pedal_travel: float                 # mm — at the pedal
    bots_trigger: float                 # mm — effective stroke + margin


@dataclass(frozen=True)
class ThermalResult:
    """Brake-rotor thermal quantities that seed an ANSYS transient thermal study."""

    braking_energy: float           # J — kinetic energy shed in one braking event
    braking_power: float            # W — energy / braking time
    power_front_rotor: float        # W — power into ONE front rotor
    power_rear_rotor: float         # W — power into ONE rear rotor
    heat_flux_front: float          # W/m² — peak heat flux on a front rotor face
    heat_flux_rear: float           # W/m² — peak heat flux on a rear rotor face
    film_coeff_start: float         # W/m²·K — convection coefficient at the start of braking (v_i)
    film_coeff_end: float           # W/m²·K — convection coefficient at the end of braking (v_f)


@dataclass(frozen=True)
class ForwardResult:
    """Forward ("performance simulator") calculation: from a driver pedal force, what the car does.

    Unlike the main backward calculation (which starts from a *target* deceleration), this flows
    strictly forward — pedal force → line pressure → clamp force → brake torque → deceleration →
    dynamic load transfer → tyre lock-up — so it never depends on the target deceleration and there
    is no circular reference. Torques marked "axle" are the total at the wheels (per-rotor × rotor
    count × driveline ratio), directly comparable to the tyre grip torque.
    """

    pedal_force: float              # N — force into the balance bar (driver force × pedal ratio)
    mc_force_front: float           # N — force into the front master cylinder (pedal force × bias)
    mc_force_rear: float            # N
    line_pressure_front: float      # MPa — produced front line pressure
    line_pressure_rear: float       # MPa
    clamp_force_front: float        # N — clamp force at one front caliper (one side)
    clamp_force_rear: float         # N
    brake_torque_front: float       # N·m — actual brake torque at ONE front rotor
    brake_torque_rear: float        # N·m — actual brake torque at ONE rear rotor
    axle_brake_torque_front: float  # N·m — total front-axle brake torque at the wheels
    axle_brake_torque_rear: float   # N·m
    stopping_force: float           # N — total longitudinal braking force at the tyres
    actual_decel_g: float           # g — resulting deceleration
    dynamic_front: float            # N — front axle load at the actual deceleration
    dynamic_rear: float             # N
    grip_torque_front: float        # N·m — max front-axle brake torque before the tyres skid
    grip_torque_rear: float         # N·m
    front_utilization: float        # — front axle brake torque / grip torque (1.0 = on the limit)
    rear_utilization: float         # —
    optimal_bias_front: float       # — balance-bar bias that makes both axles reach the limit together
    front_locked: bool              # True if the front axle exceeds its grip (lock-up)
    rear_locked: bool               # True if the rear axle exceeds its grip (lock-up)


@dataclass(frozen=True)
class ValidationMessage:
    level: str                      # "error" | "warning" | "info"
    message: str


@dataclass(frozen=True)
class Requirement:
    """A single engineering check, framed as "what the inputs require" vs "what the setup produces".

    Both sides are pre-formatted strings (no inequality symbols) so the panel can show the
    requirement and the current result plainly, side by side.
    """

    name: str                       # spreadsheet-style label, e.g. "Are front braking requirements met?"
    description: str                # the spreadsheet's own comment for this check
    requirement_text: str           # what the current inputs require, e.g. "at least 2,021 N of pedal force"
    current_text: str               # what the current setup produces, e.g. "2,400 N delivered"
    passed: bool
    hard: bool = True               # True = must pass; False = a desirable target (soft)


@dataclass(frozen=True)
class BrakeResults:
    dynamics: DynamicsResult
    torque: TorqueResult
    sizing: SizingResult
    hydraulics: HydraulicsResult
    pedal_travel: PedalTravelResult
    thermal: ThermalResult
    forward: ForwardResult | None = None
    requirements: tuple[Requirement, ...] = field(default_factory=tuple)
    messages: tuple[ValidationMessage, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True if no validation errors and every hard requirement passes."""
        no_errors = all(m.level != "error" for m in self.messages)
        hard_ok = all(r.passed for r in self.requirements if r.hard)
        return no_errors and hard_ok
