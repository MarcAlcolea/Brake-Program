"""Unit conversion for display purposes.

The engine stores every value in one canonical unit per field (see ``models``). For display, a value
can be shown in any unit of the same physical dimension (e.g. a length stored in metres shown in mm
or inches). Conversions go through a base unit per dimension:

    value_in_unit = value_in_canonical · factor(canonical) / factor(unit)

Metric stays the default; switching units never changes the stored value, only how it is shown/typed.
Units not listed here (dimensionless ratios, "g" of deceleration, counts) simply can't be switched.
"""

from __future__ import annotations

# unit name -> (dimension, factor to that dimension's base unit)
_UNITS: dict[str, tuple[str, float]] = {
    # length (base: metre)
    "m": ("length", 1.0),
    "cm": ("length", 1e-2),
    "mm": ("length", 1e-3),
    "in": ("length", 0.0254),
    # mass (base: kilogram)
    "kg": ("mass", 1.0),
    "g": ("mass", 1e-3),
    "lb": ("mass", 0.45359237),
    # force (base: newton)
    "N": ("force", 1.0),
    "lbf": ("force", 4.4482216153),
    # pressure (base: pascal)
    "MPa": ("pressure", 1e6),
    "bar": ("pressure", 1e5),
    "psi": ("pressure", 6894.757293),
    # area (base: square metre)
    "mm²": ("area", 1e-6),
    "cm²": ("area", 1e-4),
    "in²": ("area", 6.4516e-4),
    # volume (base: cubic metre)
    "mm³": ("volume", 1e-9),
    "cm³": ("volume", 1e-6),
    "in³": ("volume", 1.6387064e-5),
}

# Display order preference within each dimension (metric first).
_ORDER = ["m", "cm", "mm", "in", "kg", "g", "lb", "N", "lbf",
          "MPa", "bar", "psi", "mm²", "cm²", "in²", "mm³", "cm³", "in³"]


def compatible_units(unit: str) -> list[str]:
    """All units sharing ``unit``'s dimension, metric-first. Empty if the unit isn't switchable."""
    if unit not in _UNITS:
        return []
    dim = _UNITS[unit][0]
    return [u for u in _ORDER if _UNITS[u][0] == dim]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert ``value`` from one unit to another within the same dimension."""
    if from_unit == to_unit or from_unit not in _UNITS or to_unit not in _UNITS:
        return value
    if _UNITS[from_unit][0] != _UNITS[to_unit][0]:
        raise ValueError(f"Cannot convert {from_unit} to {to_unit}: different dimensions.")
    return value * _UNITS[from_unit][1] / _UNITS[to_unit][1]
