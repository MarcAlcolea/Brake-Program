"""Catalog of metrics the optimizer can read from a solved design.

A metric is any scalar the objectives or constraints can act on. Metrics are defined once here and
referenced by key elsewhere, so adding a new quantity (e.g. rotor temperature once the thermal model
exists) is a one-line addition that the UI picks up automatically. Metrics flagged ``available=False``
are recognised but not yet computable; the UI shows them disabled with their note.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.models import VehicleConfig
from ..core.results import BrakeResults


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    unit: str
    getter: Callable[[BrakeResults, VehicleConfig], float]
    available: bool = True
    note: str = ""


def _required_driver_force(r: BrakeResults, c: VehicleConfig) -> float:
    return max(r.hydraulics.bar_force_front, r.hydraulics.bar_force_rear) / c.pedal_box.pedal_ratio


def _unavailable(_r, _c) -> float:  # placeholder getter for not-yet-modelled metrics
    return 0.0


_METRIC_LIST = [
    Metric("required_driver_force", "Required driver pedal force", "N", _required_driver_force,
           note="Pedal force the driver must apply so both axles reach the tire limit."),
    Metric("pedal_force_front", "Pedal force required (front)", "N",
           lambda r, c: r.hydraulics.bar_force_front),
    Metric("pedal_force_rear", "Pedal force required (rear)", "N",
           lambda r, c: r.hydraulics.bar_force_rear),
    Metric("front_rear_balance", "Front/rear pedal-force imbalance", "N",
           lambda r, c: abs(r.hydraulics.bar_force_front - r.hydraulics.bar_force_rear),
           note="0 means the front and rear reach their limit at the same pedal force."),
    Metric("lockup_order", "Front-before-rear margin", "N",
           lambda r, c: r.hydraulics.bar_force_rear - r.hydraulics.bar_force_front,
           note="Positive means the front reaches its limit before the rear (stable)."),
    Metric("brake_bias_front", "Brake bias (front)", "-",
           lambda r, c: c.pedal_box.balance_bias_front),
    Metric("front_line_pressure", "Front line pressure", "MPa",
           lambda r, c: r.sizing.front.line_pressure),
    Metric("rear_line_pressure", "Rear line pressure", "MPa",
           lambda r, c: r.sizing.rear.line_pressure),
    Metric("max_line_pressure", "Peak line pressure", "MPa",
           lambda r, c: max(r.sizing.front.line_pressure, r.sizing.rear.line_pressure)),
    Metric("pedal_travel", "Pedal travel", "mm",
           lambda r, c: r.pedal_travel.pedal_travel),
    Metric("mc_stroke_headroom", "Master-cylinder stroke headroom", "mm",
           lambda r, c: c.hydraulics.max_mc_stroke - max(r.pedal_travel.mc_stroke_front, r.pedal_travel.mc_stroke_rear),
           note="Available stroke minus the stroke needed; must stay positive."),
    Metric("vehicle_mass", "Vehicle mass", "kg", lambda r, c: c.mass.total_mass),
    Metric("rotor_temperature", "Peak rotor temperature", "°C", _unavailable, available=False,
           note="Requires the thermal model (not yet implemented)."),
    Metric("stopping_distance", "Stopping distance", "m", _unavailable, available=False,
           note="Requires a vehicle stopping model (not yet implemented)."),
]

METRICS: dict[str, Metric] = {m.key: m for m in _METRIC_LIST}

#: Metrics offered as optimization objectives.
OBJECTIVE_KEYS = [
    "required_driver_force", "front_rear_balance", "brake_bias_front",
    "pedal_travel", "max_line_pressure", "vehicle_mass",
]

#: Metrics offered as constraints, with the operator and default bound(s) the UI pre-fills.
# op: "le" (value <= upper) | "ge" (value >= lower) | "range" (lower..upper)
CONSTRAINT_DEFAULTS = [
    ("required_driver_force", "le", None, 400.0),
    ("brake_bias_front", "range", 0.35, 0.65),
    ("lockup_order", "ge", 0.0, None),
    ("pedal_travel", "range", 30.0, 60.0),
    ("mc_stroke_headroom", "ge", 0.0, None),
    ("max_line_pressure", "le", None, 10.0),
    ("rotor_temperature", "le", None, 500.0),
    ("stopping_distance", "le", None, 40.0),
]


def all_available_keys() -> list[str]:
    return [k for k, m in METRICS.items() if m.available]
