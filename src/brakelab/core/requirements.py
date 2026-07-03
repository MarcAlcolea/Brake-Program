"""Engineering requirements — what the current inputs demand vs what the setup produces.

Each requirement states, in plain words, what the design must achieve given the current inputs
(mass, target deceleration, geometry, …) and, alongside it, what the current setup actually
produces. No inequality symbols are used. The two braking checks and their comments come straight
from the spreadsheet ("Are front/rear braking requirements met?").

Hard requirements must pass for the design to be acceptable; soft ones are desirable targets.
"""

from __future__ import annotations

from .models import VehicleConfig
from .results import HydraulicsResult, PedalTravelResult, Requirement

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

    reqs.append(
        Requirement(
            name="Are front braking requirements met?",
            description="Is the force from the pedal greater than the force required to go into the "
            "balance bar (for the front tires)?",
            requirement_text=f"at least {h.bar_force_front:,.0f} N of pedal force",
            current_text=f"{h.pedal_force:,.0f} N produced",
            passed=h.front_requirement_met,
            hard=True,
        )
    )
    reqs.append(
        Requirement(
            name="Are rear braking requirements met?",
            description="Is the force from the pedal greater than the force required to go into the "
            "balance bar (for the rear tires)?",
            requirement_text=f"at least {h.bar_force_rear:,.0f} N of pedal force",
            current_text=f"{h.pedal_force:,.0f} N produced",
            passed=h.rear_requirement_met,
            hard=True,
        )
    )

    max_stroke = config.hydraulics.max_mc_stroke
    reqs.append(
        Requirement(
            name="Front master cylinder stroke fits",
            description="The required front master-cylinder stroke must fit within the maximum "
            "available stroke of the cylinder.",
            requirement_text=f"at most {max_stroke:,.2f} mm of stroke",
            current_text=f"{p.mc_stroke_front:,.2f} mm needed",
            passed=p.mc_stroke_front <= max_stroke,
            hard=True,
        )
    )
    reqs.append(
        Requirement(
            name="Rear master cylinder stroke fits",
            description="The required rear master-cylinder stroke must fit within the maximum "
            "available stroke of the cylinder.",
            requirement_text=f"at most {max_stroke:,.2f} mm of stroke",
            current_text=f"{p.mc_stroke_rear:,.2f} mm needed",
            passed=p.mc_stroke_rear <= max_stroke,
            hard=True,
        )
    )

    reqs.append(
        Requirement(
            name="Pedal travel in desirable range",
            description="Pedal travel between 30 and 60 mm is desirable. Outside this range is a "
            "target miss, not a failure.",
            requirement_text=f"between {PEDAL_TRAVEL_MIN:g} and {PEDAL_TRAVEL_MAX:g} mm",
            current_text=f"{p.pedal_travel:,.1f} mm",
            passed=PEDAL_TRAVEL_MIN <= p.pedal_travel <= PEDAL_TRAVEL_MAX,
            hard=False,
        )
    )

    return reqs
