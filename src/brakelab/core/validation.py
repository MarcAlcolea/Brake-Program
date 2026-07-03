"""Engineering validation of inputs and results.

Produces a list of messages (error / warning / info) that both the headless engine and the GUI
consume. Errors indicate a physically invalid or infeasible configuration; warnings flag values
outside typical/comfortable ranges.
"""

from __future__ import annotations

from .models import VehicleConfig
from .results import (
    HydraulicsResult,
    PedalTravelResult,
    SizingResult,
    ValidationMessage,
)

#: Balance-bar hardware limit (front bias). Bias beyond this is usually not achievable.
MAX_BALANCE_BIAS_FRONT: float = 0.65
MIN_BALANCE_BIAS_FRONT: float = 0.35

#: Desirable pedal-travel window [mm].
PEDAL_TRAVEL_MIN: float = 30.0
PEDAL_TRAVEL_MAX: float = 60.0


def validate_config(config: VehicleConfig) -> list[ValidationMessage]:
    """Check inputs for physical validity and sensible ranges (independent of results)."""
    msgs: list[ValidationMessage] = []

    f = config.mass.front_weight_fraction
    if not 0.0 < f < 1.0:
        msgs.append(ValidationMessage("error", f"Front weight fraction {f:.3f} must be between 0 and 1."))

    bias = config.pedal_box.balance_bias_front
    if not 0.0 < bias < 1.0:
        msgs.append(ValidationMessage("error", f"Front balance bias {bias:.3f} must be between 0 and 1."))
    elif not MIN_BALANCE_BIAS_FRONT <= bias <= MAX_BALANCE_BIAS_FRONT:
        msgs.append(
            ValidationMessage(
                "warning",
                f"Front balance bias {bias:.2f} is outside the typical "
                f"{MIN_BALANCE_BIAS_FRONT:g}–{MAX_BALANCE_BIAS_FRONT:g} hardware range.",
            )
        )

    for name, value in (
        ("total mass", config.mass.total_mass),
        ("wheelbase", config.mass.wheelbase),
        ("cg height", config.mass.cg_height),
        ("tire radius", config.tires.loaded_radius),
        ("rotor effective radius", config.rotor.effective_radius),
        ("caliper piston area", config.caliper.piston_area),
        ("target deceleration", config.target_decel_g),
    ):
        if value <= 0:
            msgs.append(ValidationMessage("error", f"{name.capitalize()} must be positive (got {value})."))

    for axle_name, axle in (("front", config.front_axle), ("rear", config.rear_axle)):
        if axle.n_rotors < 1:
            msgs.append(ValidationMessage("error", f"{axle_name.capitalize()} axle needs at least 1 rotor."))

    return msgs


def validate_results(
    sizing: SizingResult,
    hydraulics: HydraulicsResult,
    pedal_travel: PedalTravelResult,
) -> list[ValidationMessage]:
    """Check computed results against feasibility and comfort thresholds."""
    msgs: list[ValidationMessage] = []

    if not hydraulics.front_requirement_met:
        msgs.append(
            ValidationMessage(
                "error",
                f"Front braking requirement NOT met: pedal delivers "
                f"{hydraulics.pedal_force:.0f} N but {hydraulics.bar_force_front:.0f} N is required.",
            )
        )
    if not hydraulics.rear_requirement_met:
        msgs.append(
            ValidationMessage(
                "error",
                f"Rear braking requirement NOT met: pedal delivers "
                f"{hydraulics.pedal_force:.0f} N but {hydraulics.bar_force_rear:.0f} N is required.",
            )
        )

    travel = pedal_travel.pedal_travel
    if travel < PEDAL_TRAVEL_MIN:
        msgs.append(
            ValidationMessage("warning", f"Pedal travel {travel:.1f} mm is below the desirable {PEDAL_TRAVEL_MIN:g} mm.")
        )
    elif travel > PEDAL_TRAVEL_MAX:
        msgs.append(
            ValidationMessage("warning", f"Pedal travel {travel:.1f} mm exceeds the desirable {PEDAL_TRAVEL_MAX:g} mm.")
        )

    return msgs
