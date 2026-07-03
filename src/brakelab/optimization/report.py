"""PDF optimization report — objectives, constraints, variables, best design, alternatives.

Kept separate from the GUI so a report can be produced headlessly.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .metrics import METRICS
from .runner import OptimizationResult


def _table(rows, widths=None) -> Table:
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b57")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b0b8c0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f6")]),
            ]
        )
    )
    return t


def build_optimization_report(result: OptimizationResult, path: str | Path) -> Path:
    path = Path(path)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    story = [Paragraph("Brake Optimization Report", styles["Title"]),
             Paragraph(f"Base configuration: {result.base_config.name}", styles["Heading3"]),
             Spacer(1, 4 * mm)]

    p = result.problem
    story.append(Paragraph("Objectives", styles["Heading3"]))
    obj_rows = [["Metric", "Goal", "Target", "Weight"]]
    for o in p.enabled_objectives():
        obj_rows.append([METRICS[o.metric_key].label, o.sense.value,
                         f"{o.target:g}" if o.sense.value == "Target" else "-", f"{o.weight:g}"])
    story.append(_table(obj_rows if len(obj_rows) > 1 else [["Metric", "Goal", "Target", "Weight"], ["(none)", "", "", ""]]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Constraints", styles["Heading3"]))
    con_rows = [["Metric", "Limit"]]
    for c in p.enabled_constraints():
        limit = {"le": f"≤ {c.upper:g}", "ge": f"≥ {c.lower:g}", "range": f"{c.lower:g} to {c.upper:g}"}.get(c.op.value, "")
        con_rows.append([METRICS[c.metric_key].label, limit])
    story.append(_table(con_rows if len(con_rows) > 1 else [["Metric", "Limit"], ["(none)", ""]]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Variables and ranges", styles["Heading3"]))
    var_rows = [["Variable", "Unit", "Min", "Max"]]
    for v in p.enabled_variables():
        var_rows.append([v.label, v.unit, f"{v.minimum:g}", f"{v.maximum:g}"])
    story.append(_table(var_rows))
    story.append(Spacer(1, 5 * mm))

    best = result.best
    if best:
        story.append(Paragraph("Recommended design", styles["Heading3"]))
        story.append(Paragraph("Feasible" if best.evaluation.feasible else "Best available (not fully feasible)", styles["Italic"]))
        rows = [["Variable", "Value"]]
        for v in p.enabled_variables():
            rows.append([v.label, f"{best.evaluation.values[v.path]:g} {v.unit}".strip()])
        story.append(_table(rows))
        story.append(Spacer(1, 3 * mm))
        mrows = [["Metric", "Value"]]
        for key in ("required_driver_force", "brake_bias_front", "front_line_pressure",
                    "rear_line_pressure", "pedal_travel"):
            m = METRICS[key]
            mrows.append([m.label, f"{best.evaluation.metrics[key]:,.2f} {m.unit}".strip()])
        story.append(_table(mrows))
        story.append(Spacer(1, 5 * mm))

    if len(result.designs) > 1:
        story.append(Paragraph("Ranked alternatives", styles["Heading3"]))
        rank_rows = [["Rank", "Feasible", "Score"] + [v.label for v in p.enabled_variables()]]
        for i, d in enumerate(result.designs, 1):
            rank_rows.append([str(i), "yes" if d.evaluation.feasible else "no", f"{d.evaluation.score:.3f}"]
                             + [f"{d.evaluation.values[v.path]:g}" for v in p.enabled_variables()])
        story.append(_table(rank_rows))

    doc.build(story)
    return path
