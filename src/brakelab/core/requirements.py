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

    # Master-cylinder stroke: only the operational target is a requirement. The hard-stop and absolute
    # mechanical limits are shown as outputs (Pedal Travel group), not requirements, so they don't
    # clutter this section — they're reference limits, not pass/fail checks.
    hyd = config.hydraulics
    effective = p.effective_stroke
    reqs.append(
        Requirement(
            name="MC stroke within operational limit",
            description="In normal operation the effective master-cylinder stroke should stay within "
            "the operational limit, set as a fraction (a healthy 20-40%) of the mechanical limit. "
            "Exceeding it is a target miss, not a failure.",
            requirement_text=f"at most {hyd.max_operational_stroke:,.2f} mm of stroke",
            current_text=f"{effective:,.2f} mm used",
            passed=effective <= hyd.max_operational_stroke,
            hard=False,
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
