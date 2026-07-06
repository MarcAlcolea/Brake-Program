"""Generate an engineering PDF report from a config and its results.

Design goals (2026-07-05 redesign): a professional, black-and-white document set in Helvetica, with
a cover page carrying the essentials (title, car, date, headline results) and a body of selectable
sections (Design, Thermal, Comparison, Optimization, Validation). Typography does the work of a
hierarchy: headline numbers are large and black, supporting detail is small and grey, so the
important information reads first and the rest is present but quiet.

Kept independent of the GUI so reports can be produced headlessly (scripts, CI, batch studies).
Which sections appear, and the cover metadata, are driven by :class:`ReportOptions`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

from ..core.attrpath import get_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
# The report reuses the app's declarative field/output specs so it can list *every* input and output
# without a second, drifting copy. These modules depend only on ``core`` (importing the ``app``
# package degrades gracefully when Qt is absent), so headless report generation still works.
from ..app.field_spec import GROUPS as INPUT_GROUPS
from ..app.output_spec import GROUPS as OUTPUT_GROUPS

# --- palette (grayscale only) -----------------------------------------------------------------
_BLACK = colors.black
_GREY = colors.HexColor("#6a6a6a")      # secondary text (units, notes, metadata)
_HEADER_BG = colors.HexColor("#1a1a1a")  # table header band
_ZEBRA = colors.HexColor("#f2f2f2")     # alternating row shade
_RULE = colors.HexColor("#bdbdbd")      # thin grid / rules
_FONT = "Helvetica"
_FONT_B = "Helvetica-Bold"
_FONT_I = "Helvetica-Oblique"


# =============================================================================================
# Options
# =============================================================================================
@dataclass
class ReportOptions:
    """What goes into the report and what the cover says.

    A bare ``ReportOptions()`` reproduces the classic single-car report (cover + design + validation),
    so existing callers keep working. The Report tab fills the rest.
    """

    title: str = "FSAE Brake Design Report"
    author: str = ""                 # team / author line on the cover (quiet, grey)
    subtitle: str = ""               # optional descriptive line under the car name
    include_date: bool = True        # print today's date on the cover
    logo_path: str = ""              # optional letterhead image at the top of the cover
    detail: str = "extensive"        # "extensive" (all inputs+outputs) or "simplified" (key only)

    include_design: bool = True      # Main-tab inputs + results + requirements
    include_thermal: bool = False    # Thermal-tab heat-flux / film-coefficient section
    include_compare: bool = False    # side-by-side comparison of ``compare_configs``
    include_optimization: bool = False  # summary of ``optimization_result`` if present
    include_validation: bool = True  # engine warnings / errors

    compare_configs: list[VehicleConfig] = field(default_factory=list)
    optimization_result: object | None = None  # brakelab.optimization result, or None


# =============================================================================================
# Styles & shared flowables
# =============================================================================================
def _styles() -> dict[str, ParagraphStyle]:
    return {
        "cover_title": ParagraphStyle("cover_title", fontName=_FONT_B, fontSize=30, leading=34, textColor=_BLACK),
        "cover_car": ParagraphStyle("cover_car", fontName=_FONT, fontSize=16, leading=20, textColor=_BLACK),
        "cover_sub": ParagraphStyle("cover_sub", fontName=_FONT_I, fontSize=11, leading=15, textColor=_GREY),
        "cover_meta": ParagraphStyle("cover_meta", fontName=_FONT, fontSize=10, leading=15, textColor=_GREY),
        "status": ParagraphStyle("status", fontName=_FONT_B, fontSize=15, leading=18, textColor=_BLACK),
        "h2": ParagraphStyle("h2", fontName=_FONT_B, fontSize=13, leading=16, textColor=_BLACK,
                             spaceBefore=12, spaceAfter=3),
        "caption": ParagraphStyle("caption", fontName=_FONT, fontSize=8, leading=11, textColor=_GREY,
                                  spaceAfter=4),
        "body": ParagraphStyle("body", fontName=_FONT, fontSize=9, leading=12, textColor=_BLACK),
        "muted": ParagraphStyle("muted", fontName=_FONT, fontSize=8.5, leading=12, textColor=_GREY),
        "kpi_num": ParagraphStyle("kpi_num", fontName=_FONT_B, fontSize=17, leading=19, textColor=_BLACK,
                                  alignment=TA_CENTER),
        "kpi_lab": ParagraphStyle("kpi_lab", fontName=_FONT, fontSize=7.5, leading=9, textColor=_GREY,
                                  alignment=TA_CENTER),
    }


def _num(x: float, digits: int = 2) -> str:
    return f"{x:,.{digits}f}"


def _rule(thickness: float = 1.0, color=_BLACK, space: float = 4) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceBefore=space, spaceAfter=space)


def _data_table(rows: list[list], col_widths=None, bold_rows: set[int] | None = None,
                compact: bool = False) -> Table:
    """A grayscale data table: dark header band, zebra body, light grid. ``bold_rows`` (1-based body
    row indices) are emphasised — used to flag comparison rows that differ. ``compact`` shrinks the
    type/padding for the full detail listings, so the exhaustive data is present but quieter."""
    fs = 7.5 if compact else 8.5
    pad = 2 if compact else 3
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_B),
        ("FONTNAME", (0, 1), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ZEBRA]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, _RULE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.25, _RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for r in bold_rows or set():
        style.append(("FONTNAME", (0, r), (-1, r), _FONT_B))
    t.setStyle(TableStyle(style))
    return t


# =============================================================================================
# Cover
# =============================================================================================
def _logo_flowable(path: str):
    """A left-aligned letterhead image scaled into a modest bounding box, or None if unusable."""
    try:
        iw, ih = ImageReader(path).getSize()
        if not iw or not ih:
            return None
        max_w, max_h = 60 * mm, 24 * mm
        scale = min(max_w / iw, max_h / ih)
        img = Image(path, width=iw * scale, height=ih * scale)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001 — a bad path must never break the report
        return None


def _cover(story: list, config: VehicleConfig, results: BrakeResults, opt: ReportOptions, st) -> None:
    logo = _logo_flowable(opt.logo_path) if opt.logo_path else None
    if logo is not None:
        story.append(logo)
        story.append(Spacer(1, 14 * mm))
        story.append(Paragraph(opt.title, st["cover_title"]))
    else:
        story.append(Spacer(1, 38 * mm))
        story.append(Paragraph(opt.title, st["cover_title"]))
    story.append(_rule(1.2, _BLACK, space=8))
    story.append(Paragraph(config.name, st["cover_car"]))
    if opt.subtitle:
        story.append(Paragraph(opt.subtitle, st["cover_sub"]))
    elif config.notes:
        story.append(Paragraph(config.notes, st["cover_sub"]))

    story.append(Spacer(1, 16 * mm))
    status = "PASS — all requirements met" if results.ok else "REVIEW REQUIRED — requirements not met"
    story.append(Paragraph(status, st["status"]))
    story.append(Spacer(1, 6 * mm))
    story.append(_kpi_strip(config, results, st))

    # Quiet metadata block near the foot of the cover.
    story.append(Spacer(1, 34 * mm))
    story.append(_rule(0.6, _RULE, space=4))
    meta = []
    if opt.author:
        meta.append(f"Prepared by: {opt.author}")
    if opt.include_date:
        meta.append(f"Date: {date.today().strftime('%d %B %Y')}")
    if meta:
        story.append(Paragraph("&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta), st["cover_meta"]))
    story.append(PageBreak())


def _kpi_strip(config: VehicleConfig, results: BrakeResults, st) -> Table:
    """A row of headline numbers — the few figures a reader wants at a glance."""
    peak_p = max(results.sizing.front.line_pressure, results.sizing.rear.line_pressure)
    kpis = [
        (_num(config.target_decel_g, 2), "Target decel [g]"),
        (_num(peak_p, 2), "Peak line pressure [MPa]"),
        (_num(results.pedal_travel.pedal_travel, 1), "Pedal travel [mm]"),
        (_num(results.hydraulics.bar_force_front, 0), "Pedal force, front [N]"),
    ]
    nums = [Paragraph(v, st["kpi_num"]) for v, _ in kpis]
    labs = [Paragraph(lab, st["kpi_lab"]) for _, lab in kpis]
    t = Table([nums, labs], colWidths=[42 * mm] * len(kpis))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, _RULE),
        ("LINEBELOW", (0, 1), (-1, 1), 0.6, _RULE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, _RULE),
    ]))
    return t


# =============================================================================================
# Sections
# =============================================================================================
def _heading(story: list, text: str, st, caption: str = "") -> None:
    story.append(Paragraph(text, st["h2"]))
    story.append(_rule(0.8, _BLACK, space=2))
    if caption:
        story.append(Paragraph(caption, st["caption"]))


def _subheading(story: list, text: str, st) -> None:
    story.append(Paragraph(text, st["muted"]))


def _field_value(config: VehicleConfig, field) -> str:
    v = get_by_path(config, field.path)
    if field.kind == "bool":
        return "yes" if v else "no"
    if field.kind == "int":
        return str(int(v))
    return f"{float(v):,.{field.decimals}f}"


def _unit_text(unit: str) -> str:
    return "" if unit in ("", "-") else unit


def _full_inputs(story: list, config: VehicleConfig, st) -> None:
    """Every input, phase by phase, in a compact quiet listing (assumed values flagged with *)."""
    assumed = set(config.assumed_inputs)
    story.append(Paragraph("Full input listing", st["body"]))
    for group in INPUT_GROUPS:
        _subheading(story, group.title, st)
        rows = [["Parameter", "Value", "Unit"]]
        for spec in group.fields:
            label = spec.label + (" *" if spec.path in assumed else "")
            rows.append([label, _field_value(config, spec), _unit_text(spec.unit)])
        story.append(_data_table(rows, col_widths=[95 * mm, 30 * mm, 25 * mm], compact=True))
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 3 * mm))


def _full_outputs(story: list, config: VehicleConfig, results: BrakeResults, st) -> None:
    """Every computed output, phase by phase, in the same compact quiet listing."""
    story.append(Paragraph("Full results listing", st["body"]))
    for group in OUTPUT_GROUPS:
        _subheading(story, group.title, st)
        rows = [["Quantity", "Value", "Unit"]]
        for output in group.outputs:
            try:
                val = output.getter(results, config)
                decimals = 3 if abs(val) < 100 else 1
                shown = f"{val:,.{decimals}f}"
            except Exception:  # noqa: BLE001
                shown = "—"
            rows.append([output.label, shown, _unit_text(output.unit)])
        story.append(_data_table(rows, col_widths=[95 * mm, 30 * mm, 25 * mm], compact=True))
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 3 * mm))


def _design_section(story: list, config: VehicleConfig, results: BrakeResults, st,
                    detail: str = "extensive") -> None:
    _heading(story, "1. Design Inputs & Results", st,
             "Primary inputs and the braking quantities they produce, front and rear.")
    m, t, pb = config.mass, config.tires, config.pedal_box
    assumed = set(config.assumed_inputs)
    shown_assumed: set[str] = set()

    def lbl(text: str, path: str) -> str:
        if path in assumed:
            shown_assumed.add(path)
            return text + " *"
        return text

    inputs = [
        ["Parameter", "Value", "Unit"],
        [lbl("Total mass", "mass.total_mass"), _num(m.total_mass, 1), "kg"],
        [lbl("CG height", "mass.cg_height"), _num(m.cg_height, 4), "m"],
        [lbl("Wheelbase", "mass.wheelbase"), _num(m.wheelbase, 3), "m"],
        [lbl("Front weight fraction", "mass.front_weight_fraction"), _num(m.front_weight_fraction, 3), "-"],
        [lbl("Target deceleration", "target_decel_g"), _num(config.target_decel_g, 2), "g"],
        [lbl("Tyre friction coeff.", "tires.friction_coefficient"), _num(t.friction_coefficient, 2), "-"],
        [lbl("Rotor effective radius", "rotor.effective_radius"), _num(config.rotor.effective_radius, 4), "m"],
        [lbl("Pad friction coeff.", "pad.friction_coefficient"), _num(config.pad.friction_coefficient, 2), "-"],
        ["Front / rear rotors", f"{config.front_axle.n_rotors} / {config.rear_axle.n_rotors}", "-"],
        [lbl("Pedal ratio", "pedal_box.pedal_ratio"), _num(pb.pedal_ratio, 1), "-"],
        [lbl("Front balance bias", "pedal_box.balance_bias_front"), _num(pb.balance_bias_front, 2), "-"],
        [lbl("Driver force", "pedal_box.driver_force"), _num(pb.driver_force, 1), "N"],
    ]
    story.append(_data_table(inputs, col_widths=[75 * mm, 40 * mm, 25 * mm]))
    if shown_assumed:
        story.append(Paragraph("* value marked as assumed — dependent results should be treated as provisional.",
                               st["muted"]))
    story.append(Spacer(1, 4 * mm))

    d, tq, s, h, p = results.dynamics, results.torque, results.sizing, results.hydraulics, results.pedal_travel
    res = [
        ["Quantity", "Front", "Rear", "Unit"],
        ["Dynamic axle load", _num(d.dynamic_front), _num(d.dynamic_rear), "N"],
        ["Required torque / rotor", _num(tq.front.torque_per_rotor), _num(tq.rear.torque_per_rotor), "N·m"],
        ["Required clamp force", _num(s.front.clamp_force), _num(s.rear.clamp_force), "N"],
        ["Required line pressure", _num(s.front.line_pressure, 3), _num(s.rear.line_pressure, 3), "MPa"],
        ["MC force required", _num(h.mc_force_front), _num(h.mc_force_rear), "N"],
        ["Pedal force required", _num(h.bar_force_front), _num(h.bar_force_rear), "N"],
    ]
    story.append(_data_table(res, col_widths=[65 * mm, 33 * mm, 33 * mm, 22 * mm]))
    story.append(Spacer(1, 3 * mm))

    summary = [
        ["Overall quantity", "Value", "Unit"],
        ["Vehicle weight", _num(d.weight), "N"],
        ["Weight transfer", _num(d.weight_transfer), "N"],
        ["Pedal force delivered", _num(h.pedal_force), "N"],
        ["Optimal front bias", _num(h.optimal_bias_front, 3), "-"],
        ["Pedal travel", _num(p.pedal_travel, 1), "mm"],
        ["BOTS trigger (MC stroke)", _num(p.bots_trigger, 2), "mm"],
    ]
    story.append(_data_table(summary, col_widths=[75 * mm, 40 * mm, 25 * mm]))

    # Requirements pass/fail — a professional addition (see module notes).
    if getattr(results, "requirements", None):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Requirements check", st["body"]))
        rows = [["Requirement", "Required", "Produced", "Status"]]
        for req in results.requirements:
            status = "PASS" if req.passed else ("FAIL" if req.hard else "off target")
            rows.append([req.name, req.requirement_text, req.current_text, status])
        story.append(_data_table(rows, col_widths=[55 * mm, 40 * mm, 40 * mm, 25 * mm]))
    story.append(Spacer(1, 5 * mm))

    # Extensive reports also carry the exhaustive listing — every input and output, phase by phase,
    # set small and quiet so the headline tables above still lead.
    if detail == "extensive":
        story.append(_rule(0.4, _RULE, space=3))
        _full_inputs(story, config, st)
        _full_outputs(story, config, results, st)


def _thermal_section(story: list, config: VehicleConfig, results: BrakeResults, st) -> None:
    th = getattr(results, "thermal", None)
    if th is None:
        return
    _heading(story, "2. Thermal — ANSYS Boundary Inputs", st,
             "Heat-flux and film-coefficient values for a transient rotor thermal study.")
    t = config.thermal
    rows = [
        ["Quantity", "Value", "Unit"],
        ["Braking event speed (vi → vf)", f"{_num(t.v_initial, 1)} → {_num(t.v_final, 1)}", "m/s"],
        ["Braking time", _num(t.brake_time, 2), "s"],
        ["Braking energy", _num(th.braking_energy, 0), "J"],
        ["Braking power", _num(th.braking_power, 0), "W"],
        ["Power into one front rotor", _num(th.power_front_rotor, 0), "W"],
        ["Power into one rear rotor", _num(th.power_rear_rotor, 0), "W"],
        ["Peak heat flux, front rotor", _num(th.heat_flux_front, 0), "W/m²"],
        ["Peak heat flux, rear rotor", _num(th.heat_flux_rear, 0), "W/m²"],
        ["Film coefficient at brake start", _num(th.film_coeff_start, 1), "W/m²·K"],
        ["Film coefficient at brake end", _num(th.film_coeff_end, 1), "W/m²·K"],
    ]
    story.append(_data_table(rows, col_widths=[80 * mm, 40 * mm, 25 * mm]))
    story.append(Spacer(1, 3 * mm))

    # Transient duty-cycle simulation (lumped capacitance; see brakelab/thermal/simulation.py).
    try:
        from ..thermal import simulate_temperature

        sim = simulate_temperature(config)
    except Exception:  # noqa: BLE001 — the report must not die on odd thermal inputs
        sim = None
    if sim is not None:
        _subheading(
            story,
            f"Transient simulation — {t.n_stops} stops of {_num(t.brake_time, 1)} s, "
            f"{_num(t.cool_time, 1)} s cooling between", st)
        sim_rows = [
            ["Quantity", "Front rotor", "Rear rotor", "Unit"],
            ["Peak temperature", _num(sim.peak_front, 1), _num(sim.peak_rear, 1), "°C"],
            ["End of duty cycle", _num(sim.final_front, 1), _num(sim.final_rear, 1), "°C"],
            ["Rise per stop (no cooling)",
             _num(sim.adiabatic_rise_front, 1), _num(sim.adiabatic_rise_rear, 1), "°C"],
        ]
        story.append(_data_table(sim_rows, col_widths=[60 * mm, 30 * mm, 30 * mm, 25 * mm]))
    story.append(Spacer(1, 5 * mm))


def _compare_section(story: list, configs: list[VehicleConfig], engine: BrakeEngine, st) -> None:
    configs = [c for c in configs if c is not None]
    if len(configs) < 2:
        return
    _heading(story, "3. Comparison", st,
             "Selected setups side by side; rows where they differ are shown in bold.")
    headers = ["Parameter"] + [c.name for c in configs]
    solved = [engine.solve(c) for c in configs]

    param_rows = [
        ("Total mass [kg]", lambda c, r: _num(c.mass.total_mass, 1)),
        ("Front weight fraction", lambda c, r: _num(c.mass.front_weight_fraction, 3)),
        ("Target decel [g]", lambda c, r: _num(c.target_decel_g, 2)),
        ("Front / rear rotors", lambda c, r: f"{c.front_axle.n_rotors} / {c.rear_axle.n_rotors}"),
        ("MC bore F/R [mm]", lambda c, r: f"{_num(c.hydraulics.mc_bore_front, 2)} / {_num(c.hydraulics.mc_bore_rear, 2)}"),
        ("Pedal ratio", lambda c, r: _num(c.pedal_box.pedal_ratio, 1)),
        ("Front balance bias", lambda c, r: _num(c.pedal_box.balance_bias_front, 2)),
        ("Front line pressure [MPa]", lambda c, r: _num(r.sizing.front.line_pressure, 3)),
        ("Rear line pressure [MPa]", lambda c, r: _num(r.sizing.rear.line_pressure, 3)),
        ("Pedal travel [mm]", lambda c, r: _num(r.pedal_travel.pedal_travel, 1)),
        ("Pedal force, front [N]", lambda c, r: _num(r.hydraulics.bar_force_front, 0)),
        ("All requirements met", lambda c, r: "yes" if r.ok else "no"),
    ]
    rows = [headers]
    bold_rows: set[int] = set()
    for i, (label, fn) in enumerate(param_rows, start=1):
        cells = [fn(c, r) for c, r in zip(configs, solved)]
        rows.append([label] + cells)
        if len(set(cells)) > 1:
            bold_rows.add(i)
    n = len(configs)
    col_widths = [55 * mm] + [(120 * mm / n)] * n
    story.append(_data_table(rows, col_widths=col_widths, bold_rows=bold_rows))
    story.append(Spacer(1, 5 * mm))


def _optimization_section(story: list, result, st) -> None:
    designs = getattr(result, "designs", None)
    if not designs:
        return
    _heading(story, "4. Optimization Summary", st,
             "Best design found by the optimizer versus the starting point.")
    feasible = sum(1 for d in designs if d.evaluation.feasible)
    story.append(Paragraph(
        f"{len(designs)} design(s) evaluated · {feasible} feasible. "
        "Full details are available from the Optimize tab's dedicated report.", st["muted"]))
    story.append(Spacer(1, 2 * mm))

    variables = result.problem.enabled_variables()
    best = designs[0]
    rows = [["Variable", "Best value", "Unit"]]
    for v in variables:
        unit = "" if v.unit in ("", "-") else v.unit
        rows.append([v.label, _num(best.evaluation.values[v.path], 3), unit])
    story.append(_data_table(rows, col_widths=[80 * mm, 40 * mm, 25 * mm]))
    story.append(Spacer(1, 5 * mm))


def _validation_section(story: list, results: BrakeResults, st) -> None:
    if not results.messages:
        return
    _heading(story, "Validation Notes", st)
    for msg in results.messages:
        tag = msg.level.upper()
        story.append(Paragraph(f"<b>[{tag}]</b> {msg.message}", st["body"]))
    story.append(Spacer(1, 3 * mm))


# =============================================================================================
# Page furniture (footer with car name + page number)
# =============================================================================================
def _make_footer(config_name: str):
    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(_FONT, 7.5)
        canvas.setStrokeColor(_RULE)
        canvas.setLineWidth(0.4)
        y = 12 * mm
        canvas.line(18 * mm, y + 3 * mm, A4[0] - 18 * mm, y + 3 * mm)
        canvas.setFillColor(_GREY)
        canvas.drawString(18 * mm, y, config_name)
        canvas.drawRightString(A4[0] - 18 * mm, y, f"Page {doc.page}")
        canvas.restoreState()
    return footer


# =============================================================================================
# Entry points
# =============================================================================================
def build_report(config: VehicleConfig, results: BrakeResults, path: str | Path,
                 options: ReportOptions | None = None, engine: BrakeEngine | None = None) -> Path:
    """Write a PDF report for ``config``/``results`` to ``path`` and return the path.

    ``options`` selects which sections appear and supplies cover metadata; ``None`` yields the
    default single-car report (cover + design + validation)."""
    path = Path(path)
    options = options or ReportOptions()
    engine = engine or BrakeEngine()
    st = _styles()

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, title=options.title, author=options.author or "BrakeLab",
        topMargin=18 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story: list = []
    _cover(story, config, results, options, st)
    if options.include_design:
        _design_section(story, config, results, st, detail=options.detail)
    if options.include_thermal:
        _thermal_section(story, config, results, st)
    if options.include_compare and options.compare_configs:
        _compare_section(story, options.compare_configs, engine, st)
    if options.include_optimization and options.optimization_result is not None:
        _optimization_section(story, options.optimization_result, st)
    if options.include_validation:
        _validation_section(story, results, st)

    footer = _make_footer(config.name)
    doc.build(story, onLaterPages=footer)  # cover page deliberately has no footer
    return path


def build_report_for_config(config: VehicleConfig, path: str | Path, engine: BrakeEngine | None = None,
                            options: ReportOptions | None = None) -> Path:
    """Convenience: solve ``config`` and write its report."""
    engine = engine or BrakeEngine()
    return build_report(config, engine.solve(config), path, options=options, engine=engine)
