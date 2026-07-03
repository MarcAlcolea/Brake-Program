"""Unit conventions and conversion helpers.

The engine works in a fixed, documented set of units so that every equation can be read without
guessing. Conversions happen only at the boundaries (import of reference data, GUI fields, reports).

Internal unit convention
------------------------
- length (vehicle):        metre        [m]
- length (components):     millimetre   [mm]   (rotor/caliper/MC bores, strokes)
- mass:                    kilogram     [kg]
- force:                   newton       [N]
- torque:                  newton-metre [N·m]
- pressure:                megapascal   [MPa]  (== N/mm², which is why component lengths are mm)
- area (components):       mm²
- acceleration target:     multiples of g ["g"]

Keeping component lengths in mm makes ``N / mm² = MPa`` fall out directly, matching how the
spreadsheet computes line pressure.
"""

from __future__ import annotations

#: Standard acceleration due to gravity [m/s²].
GRAVITY: float = 9.81

#: Millimetres per inch.
MM_PER_INCH: float = 25.4


def inch_to_mm(inches: float) -> float:
    """Convert inches to millimetres."""
    return inches * MM_PER_INCH


def mm_to_inch(mm: float) -> float:
    """Convert millimetres to inches."""
    return mm / MM_PER_INCH


def circle_area_mm2(diameter_mm: float) -> float:
    """Area of a circle from its diameter, in mm²."""
    import math

    return math.pi * (diameter_mm / 2.0) ** 2
