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
    volume_front: float             # mm³
    volume_rear: float              # mm³
    mc_stroke_front: float          # mm
    mc_stroke_rear: float           # mm
    effective_stroke: float         # mm — average, with compliance
    pedal_travel: float             # mm — at the pedal
    bots_trigger: float             # mm — effective stroke + margin


@dataclass(frozen=True)
class ValidationMessage:
    level: str                      # "error" | "warning" | "info"
    message: str


@dataclass(frozen=True)
class BrakeResults:
    dynamics: DynamicsResult
    torque: TorqueResult
    sizing: SizingResult
    hydraulics: HydraulicsResult
    pedal_travel: PedalTravelResult
    messages: tuple[ValidationMessage, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True if no validation errors and both axle braking requirements are met."""
        no_errors = all(m.level != "error" for m in self.messages)
        return no_errors and self.hydraulics.front_requirement_met and self.hydraulics.rear_requirement_met
