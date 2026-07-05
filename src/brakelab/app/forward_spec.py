"""Inputs surfaced on the Simulator (forward performance) tab.

The forward calculation shares the one :class:`VehicleConfig`, so these are the same fields as the
Main tab — editing them here changes the car everywhere. We simply group the subset the forward math
actually uses (driver input, brake hardware, tyre/vehicle constants) so the tab is self-contained.
Field definitions are reused verbatim from ``field_spec`` to avoid a second, drifting copy.
"""

from __future__ import annotations

from .field_spec import GROUPS as _MAIN_GROUPS
from .field_spec import Group
from .output_spec import OutputGroup, _o

_BY_PATH = {f.path: f for g in _MAIN_GROUPS for f in g.fields}


def _fields(*paths: str):
    return tuple(_BY_PATH[p] for p in paths)


INPUT_GROUPS: tuple[Group, ...] = (
    Group(
        "Driver Input & Hydraulics",
        _fields(
            "pedal_box.driver_force",
            "pedal_box.pedal_ratio",
            "pedal_box.balance_bias_front",
            "hydraulics.mc_bore_front",
            "hydraulics.mc_bore_rear",
        ),
    ),
    Group(
        "Brake Hardware",
        _fields(
            "caliper.piston_area",
            "caliper.n_pistons",
            "front_axle.n_rotors",
            "rear_axle.n_rotors",
            "rotor.effective_radius",
            "pad.friction_coefficient",
        ),
    ),
    Group(
        "Tyre & Vehicle",
        _fields(
            "tires.friction_coefficient",
            "tires.loaded_radius",
            "mass.total_mass",
            "mass.cg_height",
            "mass.wheelbase",
            "mass.front_weight_fraction",
        ),
    ),
)


# ---- Forward outputs (rendered with the shared OutputsPanel, so each row gets an ⓘ) -------------
def _f(r):
    return r.forward


OUTPUT_GROUPS: tuple[OutputGroup, ...] = (
    OutputGroup(
        "Forward Result — from Pedal Force",
        (
            _o("Actual Deceleration (a)", "g", "a = F(stop) / (M * g)",
               "The deceleration this pedal force produces, assuming the tyres transmit all the brake "
               "force. If an axle locks (see the Lock-Up Check), the real deceleration is limited by "
               "grip and will be lower. Compare with the Target Deceleration from the Main tab.",
               lambda r, c: _f(r).actual_decel_g),
            _o("Pedal force into balance bar (F(pedal))", "N", "F(pedal) = F(driver) * PR",
               "Force delivered by the pedal into the balance bar.", lambda r, c: _f(r).pedal_force),
            _o("Line pressure produced (Front)", "MPa", "P(f) = (F(pedal) * B(f)) / A(f,mc)",
               "Front master-cylinder pressure produced by this pedal force and bias.",
               lambda r, c: _f(r).line_pressure_front),
            _o("Line pressure produced (Rear)", "MPa", "P(r) = (F(pedal) * B(r)) / A(r,mc)",
               "Rear master-cylinder pressure produced.", lambda r, c: _f(r).line_pressure_rear),
            _o("Clamp force, one caliper (Front)", "N", "F(clamp) = P(f) * A(cal)",
               "Clamp force at one front caliper (pressure on the one-side piston area).",
               lambda r, c: _f(r).clamp_force_front),
            _o("Clamp force, one caliper (Rear)", "N", "F(clamp) = P(r) * A(cal)",
               "Clamp force at one rear caliper.", lambda r, c: _f(r).clamp_force_rear),
            _o("Brake torque per rotor (Front)", "N·m", "T(rotor) = F(clamp) * 2 * mu(pad) * R(eff)",
               "Actual brake torque at one front rotor (the 2 is for both pad faces).",
               lambda r, c: _f(r).brake_torque_front),
            _o("Brake torque per rotor (Rear)", "N·m", "T(rotor) = F(clamp) * 2 * mu(pad) * R(eff)",
               "Actual brake torque at one rear rotor.", lambda r, c: _f(r).brake_torque_rear),
            _o("Axle brake torque, at wheels (Front)", "N·m", "T(axle) = T(rotor) * N(f) * driveline",
               "Total front-axle brake torque at the wheels — this is what is compared to the tyre "
               "grip torque for lock-up.", lambda r, c: _f(r).axle_brake_torque_front),
            _o("Axle brake torque, at wheels (Rear)", "N·m", "T(axle) = T(rotor) * N(r) * driveline",
               "Total rear-axle brake torque at the wheels.", lambda r, c: _f(r).axle_brake_torque_rear),
            _o("Total stopping force (F(stop))", "N", "F(stop) = (T(axle,f) + T(axle,r)) / R(tire)",
               "Total longitudinal braking force at the tyre contact patches.",
               lambda r, c: _f(r).stopping_force),
        ),
    ),
    OutputGroup(
        "Lock-Up Check",
        (
            _o("Dynamic Front Axle Load", "N", "W(f,dyn) = static front + M*g*a*h/L",
               "Front axle load at the ACTUAL deceleration above (not the Main-tab target).",
               lambda r, c: _f(r).dynamic_front),
            _o("Dynamic Rear Axle Load", "N", "W(r,dyn) = static rear - M*g*a*h/L",
               "Rear axle load at the actual deceleration.", lambda r, c: _f(r).dynamic_rear),
            _o("Front grip torque (lock-up threshold)", "N·m", "T(grip,f) = W(f,dyn) * mu(tire) * R(tire)",
               "The most brake torque the front tyres can take before skidding. Lock-up occurs when "
               "the front axle brake torque exceeds this.", lambda r, c: _f(r).grip_torque_front),
            _o("Rear grip torque (lock-up threshold)", "N·m", "T(grip,r) = W(r,dyn) * mu(tire) * R(tire)",
               "The most brake torque the rear tyres can take before skidding.",
               lambda r, c: _f(r).grip_torque_rear),
            _o("Front grip utilisation", "%", "T(axle,f) / T(grip,f) * 100",
               "How much of the front tyres' grip the brakes are using. 100% is right on the lock-up "
               "limit; above 100% the front locks.", lambda r, c: _f(r).front_utilization * 100.0),
            _o("Rear grip utilisation", "%", "T(axle,r) / T(grip,r) * 100",
               "How much of the rear tyres' grip the brakes are using. 100% is the lock-up limit.",
               lambda r, c: _f(r).rear_utilization * 100.0),
            _o("Optimal balance-bar bias (Front)", "-", "bias where front & rear utilisation are equal",
               "The front balance-bar bias at which both axles reach the grip limit together — the "
               "bias that gives the most braking before either axle locks. Tune Balance Bar Bias "
               "Front toward this value.", lambda r, c: _f(r).optimal_bias_front),
        ),
    ),
)
