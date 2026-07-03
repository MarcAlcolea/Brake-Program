"""Brake engine — orchestrates the calculation phases into a single result.

This is a thin pipeline. Each phase lives in its own module and is independently testable; the
engine simply wires them together and gathers validation messages.

    dynamics → torque → sizing → hydraulics → pedal travel → validation → BrakeResults
"""

from __future__ import annotations

from . import brakes, dynamics, hydraulics, pedal_travel, requirements, tires, validation
from .models import VehicleConfig
from .results import BrakeResults
from .units import GRAVITY


class BrakeEngine:
    """Runs the full brake calculation for a :class:`VehicleConfig`."""

    def __init__(self, gravity: float = GRAVITY) -> None:
        self.gravity = gravity

    def solve(self, config: VehicleConfig) -> BrakeResults:
        """Compute all phases and return an aggregated, validated result."""
        dyn = dynamics.solve_dynamics(config.mass, config.target_decel_g, self.gravity)
        torque = tires.solve_torque(dyn, config.tires, config.front_axle, config.rear_axle)
        sizing = brakes.solve_sizing(torque, config.pad, config.rotor, config.caliper)
        hyd = hydraulics.solve_hydraulics(sizing, config.hydraulics, config.pedal_box)
        travel = pedal_travel.solve_pedal_travel(
            config.caliper, config.front_axle, config.rear_axle, config.hydraulics, config.pedal_box
        )

        reqs = tuple(requirements.evaluate_requirements(config, hyd, travel))
        messages = tuple(
            validation.validate_config(config) + validation.validate_results(sizing, hyd, travel)
        )

        return BrakeResults(
            dynamics=dyn,
            torque=torque,
            sizing=sizing,
            hydraulics=hyd,
            pedal_travel=travel,
            requirements=reqs,
            messages=messages,
        )
