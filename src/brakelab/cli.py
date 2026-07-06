"""Headless command-line interface: solve a config, print results, optionally export a PDF.

    python -m brakelab.cli configs/2026_baseline.json
    python -m brakelab.cli configs/2026_baseline.json --report out.pdf
"""

from __future__ import annotations

import argparse

from .core.engine import BrakeEngine
from .persistence import load_config
from . import reference_configs


def _print_results(config, results) -> None:
    d, tq, s, h, p = results.dynamics, results.torque, results.sizing, results.hydraulics, results.pedal_travel
    print(f"=== {config.name} ===")
    print(f"Weight {d.weight:.1f} N | transfer {d.weight_transfer:.1f} N")
    print(f"Dynamic load  front {d.dynamic_front:.1f} N   rear {d.dynamic_rear:.1f} N")
    print(f"Torque/rotor  front {tq.front.torque_per_rotor:.2f}    rear {tq.rear.torque_per_rotor:.2f} N·m")
    print(f"Clamp force   front {s.front.clamp_force:.1f} N   rear {s.rear.clamp_force:.1f} N")
    print(f"Line pressure front {s.front.line_pressure:.3f}    rear {s.rear.line_pressure:.3f} MPa")
    print(f"Pedal force required  front {h.bar_force_front:.1f}  rear {h.bar_force_rear:.1f}  delivered {h.pedal_force:.0f} N")
    print(f"Requirements met  front {h.front_requirement_met}  rear {h.rear_requirement_met}")
    print(f"Pedal travel {p.pedal_travel:.1f} mm | optimal front bias {h.optimal_bias_front:.3f}")
    print(f"Status: {'PASS' if results.ok else 'REVIEW REQUIRED'}")
    for m in results.messages:
        print(f"  [{m.level.upper()}] {m.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Solve a brake configuration headlessly.")
    parser.add_argument("config", nargs="?", help="Path to a config JSON (defaults to the built-in baseline).")
    parser.add_argument("--report", help="Also write a PDF report to this path.")
    args = parser.parse_args(argv)

    config = load_config(args.config) if args.config else reference_configs.outboarded_x2()
    results = BrakeEngine().solve(config)
    _print_results(config, results)

    if args.report:
        from .reporting import build_report
        build_report(config, results, args.report)
        print(f"Report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
