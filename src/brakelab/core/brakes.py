"""Phase 3 — caliper and rotor sizing.

A rotor has two friction faces, so its braking torque is ``T = F_clamp · (2·μ_pad) · R_eff``.
Inverting gives the clamp force required for a target torque, and dividing by the caliper's
one-side piston area gives the line pressure:

    F_clamp = T / (2 · μ_pad · R_eff)
    P_line  = F_clamp / A_one_side          # N / mm² = MPa

Audit **B2**: the factor of two is applied here for *every* axle (the spreadsheet dropped it for
the single inboard rear rotor, doubling its pressure). Using one function everywhere makes that
class of drift impossible.
"""

from __future__ import annotations

from .models import Caliper, Pad, Rotor
from .results import AxleSizingResult, SizingResult, TorqueResult


def clamp_force_from_torque(torque: float, pad: Pad, rotor: Rotor) -> float:
    """Clamp force [N] needed at one caliper to produce ``torque`` [N·m] at the rotor."""
    return torque / (2.0 * pad.friction_coefficient * rotor.effective_radius)


def line_pressure(clamp_force: float, caliper: Caliper) -> float:
    """Hydraulic line pressure [MPa] to produce ``clamp_force`` [N] (mm² areas → MPa)."""
    return clamp_force / caliper.one_side_area


def _axle_sizing(torque: float, pad: Pad, rotor: Rotor, caliper: Caliper) -> AxleSizingResult:
    clamp = clamp_force_from_torque(torque, pad, rotor)
    return AxleSizingResult(clamp_force=clamp, line_pressure=line_pressure(clamp, caliper))


def solve_sizing(
    torque: TorqueResult, pad: Pad, rotor: Rotor, caliper: Caliper
) -> SizingResult:
    """Required clamp force and line pressure for both axles."""
    return SizingResult(
        front=_axle_sizing(torque.front.torque_per_rotor, pad, rotor, caliper),
        rear=_axle_sizing(torque.rear.torque_per_rotor, pad, rotor, caliper),
    )
