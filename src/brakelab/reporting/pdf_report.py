"""Generate an engineering PDF report from a config and its results.

Uses reportlab to lay out input and result tables plus a pass/fail summary. Kept independent of the
GUI so reports can be produced headlessly (scripts, CI, batch studies).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults


def _table(rows: list[list[str]], col_widths=None) -> Table:
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b57")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f6")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b0b8c0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _num(x: float, digits: int = 2) -> str:
    return f"{x:,.{digits}f}"


def build_report(config: VehicleConfig, results: BrakeResults, path: str | Path) -> Path:
    """Write a PDF report for ``config``/``results`` to ``path`` and return the path."""
    path = Path(path)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm
    )
    story = []

    story.append(Paragraph("FSAE Brake Design Report", styles["Title"]))
    story.append(Paragraph(config.name, styles["Heading2"]))
    if config.notes:
        story.append(Paragraph(config.notes, styles["Italic"]))
    story.append(Spacer(1, 6 * mm))

    status = "PASS" if results.ok else "REVIEW REQUIRED"
    story.append(Paragraph(f"<b>Status:</b> {status}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    # Inputs
    story.append(Paragraph("Inputs", styles["Heading3"]))
    m, t, pb = config.mass, config.tires, config.pedal_box
    inputs = [
        ["Parameter", "Value", "Unit"],
        ["Total mass", _num(m.total_mass), "kg"],
        ["CG height", _num(m.cg_height, 4), "m"],
        ["Wheelbase", _num(m.wheelbase, 3), "m"],
        ["Front weight fraction", _num(m.front_weight_fraction, 3), "-"],
        ["Target deceleration", _num(config.target_decel_g, 2), "g"],
        ["Tire friction coeff.", _num(t.friction_coefficient, 2), "-"],
        ["Rotor effective radius", _num(config.rotor.effective_radius, 4), "m"],
        ["Pad friction coeff.", _num(config.pad.friction_coefficient, 2), "-"],
        ["Front / rear rotors", f"{config.front_axle.n_rotors} / {config.rear_axle.n_rotors}", "-"],
        ["Pedal ratio", _num(pb.pedal_ratio, 1), "-"],
        ["Front balance bias", _num(pb.balance_bias_front, 2), "-"],
        ["Driver force", _num(pb.driver_force), "N"],
    ]
    story.append(_table(inputs, col_widths=[70 * mm, 40 * mm, 30 * mm]))
    story.append(Spacer(1, 5 * mm))

    # Results
    d, tq, s, h, p = results.dynamics, results.torque, results.sizing, results.hydraulics, results.pedal_travel
    story.append(Paragraph("Results", styles["Heading3"]))
    res = [
        ["Quantity", "Front", "Rear", "Unit"],
        ["Dynamic axle load", _num(d.dynamic_front), _num(d.dynamic_rear), "N"],
        ["Required torque / rotor", _num(tq.front.torque_per_rotor), _num(tq.rear.torque_per_rotor), "N·m"],
        ["Required clamp force", _num(s.front.clamp_force), _num(s.rear.clamp_force), "N"],
        ["Required line pressure", _num(s.front.line_pressure, 3), _num(s.rear.line_pressure, 3), "MPa"],
        ["MC force required", _num(h.mc_force_front), _num(h.mc_force_rear), "N"],
        ["Pedal force required", _num(h.bar_force_front), _num(h.bar_force_rear), "N"],
        ["Requirement met", str(h.front_requirement_met), str(h.rear_requirement_met), "-"],
    ]
    story.append(_table(res, col_widths=[60 * mm, 35 * mm, 35 * mm, 20 * mm]))
    story.append(Spacer(1, 4 * mm))

    summary = [
        ["Overall quantity", "Value", "Unit"],
        ["Vehicle weight", _num(d.weight), "N"],
        ["Weight transfer", _num(d.weight_transfer), "N"],
        ["Pedal force delivered", _num(h.pedal_force), "N"],
        ["Optimal front bias", _num(h.optimal_bias_front, 3), "-"],
        ["Pedal travel", _num(p.pedal_travel, 1), "mm"],
        ["BOTS trigger (MC stroke)", _num(p.bots_trigger, 2), "mm"],
    ]
    story.append(_table(summary, col_widths=[70 * mm, 40 * mm, 30 * mm]))
    story.append(Spacer(1, 5 * mm))

    # Validation
    if results.messages:
        story.append(Paragraph("Validation", styles["Heading3"]))
        for msg in results.messages:
            colour = {"error": "#b00020", "warning": "#8a6d00"}.get(msg.level, "#333333")
            story.append(Paragraph(f'<font color="{colour}">[{msg.level.upper()}] {msg.message}</font>', styles["Normal"]))

    doc.build(story)
    return path


def build_report_for_config(config: VehicleConfig, path: str | Path, engine: BrakeEngine | None = None) -> Path:
    """Convenience: solve ``config`` and write its report."""
    engine = engine or BrakeEngine()
    return build_report(config, engine.solve(config), path)
