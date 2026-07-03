"""Engineering requirements — the pass/fail checks that decide if a design is acceptable.

These are separate from :mod:`brakelab.core.validation` (which flags nonsensical *inputs*). A
requirement is a design check with a clear condition and the current numbers filled in, so it is
obvious *what* must hold, *why*, and *by how much* it passes or fails.

Hard requirements must pass for the design to be acceptable; soft ones are desirable targets.
"""

from __future__ import annotations

from .models import VehicleConfig
from .results import HydraulicsResult, PedalTravelResult, Requirement, SizingResult

#: Desirable pedal-travel window [mm].
PEDAL_TRAVEL_MIN = 30.0
PEDAL_TRAVEL_MAX = 60.0


def evaluate_requirements(
    config: VehicleConfig,
    hydraulics: HydraulicsResult,
    pedal_travel: PedalTravelResult,
) -> list[Requirement]:
    """Build the list of engineering checks for the current results."""
    h, p = hydraulics, pedal_travel
    reqs: list[Requirement] = []

    # --- Hard: the driver must be able to reach each axle's grip limit --------------------------
    reqs.append(
        Requirement(
            name="Front braking authority",
            description="The pedal must deliver enough force to lock the front tires at the target "
            "deceleration. This is the force the front axle needs, routed through the balance bar.",
            condition="F_pedal ≥ F_bar,front",
            detail=f"delivered {h.pedal_force:,.0f} N  ≥  required {h.bar_force_front:,.0f} N",
            passed=h.front_requirement_met,
            hard=True,
        )
    )
    reqs.append(
        Requirement(
            name="Rear braking authority",
            description="The pedal must deliver enough force to lock the rear tires at the target "
            "deceleration.",
            condition="F_pedal ≥ F_bar,rear",
            detail=f"delivered {h.pedal_force:,.0f} N  ≥  required {h.bar_force_rear:,.0f} N",
            passed=h.rear_requirement_met,
            hard=True,
        )
    )

    # --- Hard: master-cylinder stroke must fit within the available stroke ----------------------
    max_stroke = config.hydraulics.max_mc_stroke
    reqs.append(
        Requirement(
            name="Front MC stroke available",
            description="The required front master-cylinder stroke must fit within the cylinder's "
            "maximum available stroke.",
            condition="stroke_front ≤ stroke_max",
            detail=f"needed {p.mc_stroke_front:,.2f} mm  ≤  available {max_stroke:,.2f} mm",
            passed=p.mc_stroke_front <= max_stroke,
            hard=True,
        )
    )
    reqs.append(
        Requirement(
            name="Rear MC stroke available",
            description="The required rear master-cylinder stroke must fit within the cylinder's "
            "maximum available stroke.",
            condition="stroke_rear ≤ stroke_max",
            detail=f"needed {p.mc_stroke_rear:,.2f} mm  ≤  available {max_stroke:,.2f} mm",
            passed=p.mc_stroke_rear <= max_stroke,
            hard=True,
        )
    )

    # --- Soft: pedal travel should sit in a comfortable window ----------------------------------
    reqs.append(
        Requirement(
            name="Pedal travel in comfortable range",
            description=f"Pedal travel between {PEDAL_TRAVEL_MIN:g} and {PEDAL_TRAVEL_MAX:g} mm gives "
            "good feel without excessive movement. Outside this range is a target miss, not a failure.",
            condition=f"{PEDAL_TRAVEL_MIN:g} mm ≤ pedal travel ≤ {PEDAL_TRAVEL_MAX:g} mm",
            detail=f"{p.pedal_travel:,.1f} mm",
            passed=PEDAL_TRAVEL_MIN <= p.pedal_travel <= PEDAL_TRAVEL_MAX,
            hard=False,
        )
    )

    return reqs
