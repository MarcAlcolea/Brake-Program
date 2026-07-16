"""Generate an engineering PDF report from a config and its results.

Design goals (2026-07-13 overhaul): a clean, professional engineering document that a subteam lead can
scan in seconds and an engineer can read in full.

- **Requirements read first.** Whether the design passes is stated on the cover as a colour banner and
  a pass/fail summary, and again as a prominent, colour-chipped table in the body. The "what's needed
  vs what you have" numbers never collide.
- **Light, quiet tables.** Soft grey headers (no heavy black bands), a faint zebra, thin rules.
  Colour is used *only* where it means something: green/red for pass/fail and for comparison up/down.
- **Typography carries the hierarchy.** Helvetica throughout — the standard PDF font, so it renders
  the same on macOS and Windows (viewers substitute the metric-compatible Arial). Headline numbers are
  large; supporting detail is small and grey.
- **Navigable.** A table of contents with page numbers and clickable PDF bookmarks; a running header
  and footer on body pages.
- **Complete when asked.** The "extensive" detail level lists every input and every output, phase by
  phase, set small and quiet so the headline tables still lead.

Kept independent of the GUI so reports can be produced headlessly (scripts, CI, batch studies). Which
sections appear, and the cover metadata, are driven by :class:`ReportOptions`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from ..core.attrpath import get_by_path
from ..core.engine import BrakeEngine
from ..core.models import VehicleConfig
from ..core.results import BrakeResults
# The report reuses the app's declarative field/output specs so it can list *every* input and output
# without a second, drifting copy. These modules depend only on ``core`` (importing the ``app``
# package degrades gracefully when Qt is absent), so headless report generation still works.
from ..app.field_spec import GROUPS as INPUT_GROUPS
from ..app.output_spec import GROUPS as OUTPUT_GROUPS

try:  # forward-simulator outputs for the optional Performance section (best-effort)
    from ..app.forward_spec import OUTPUT_GROUPS as FORWARD_GROUPS
except Exception:  # noqa: BLE001
    FORWARD_GROUPS = ()


# =============================================================================================
# Palette — mostly greyscale; colour only carries pass/fail and comparison up/down meaning.
# =============================================================================================
_INK = colors.HexColor("#1c1c1c")        # primary text (near-black, softer than pure black)
_GREY = colors.HexColor("#6a6a6a")        # secondary text (units, notes, metadata)
_FAINT = colors.HexColor("#9a9a9a")       # tertiary text (captions, quiet listings)
_HEADER_BG = colors.HexColor("#eceff2")   # LIGHT table-header band (replaces the old black band)
_ZEBRA = colors.HexColor("#f7f8f9")       # very subtle alternating row shade
_RULE = colors.HexColor("#d7dbe0")        # light grid / rules
_HAIRLINE = colors.HexColor("#c9ced4")

# Semantic (used sparingly and only where meaningful)
_PASS = colors.HexColor("#1f7a3d")
_PASS_BG = colors.HexColor("#e7f4ec")
_FAIL = colors.HexColor("#b02a1e")
_FAIL_BG = colors.HexColor("#fbe8e5")
_WARN = colors.HexColor("#9a6b0d")
_WARN_BG = colors.HexColor("#fbf1dc")
_UP_BG = colors.HexColor("#e3f5e6")       # comparison: higher than baseline (matches the app)
_DOWN_BG = colors.HexColor("#fbe4e4")     # comparison: lower than baseline

_FONT = "Helvetica"
_FONT_B = "Helvetica-Bold"
_FONT_I = "Helvetica-Oblique"

_PAGE_W, _PAGE_H = A4
_MARGIN = 18 * mm
_CONTENT_W = _PAGE_W - 2 * _MARGIN


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
    include_forward: bool = True     # Forward simulator: actual decel, lock-up, grip utilisation
    include_thermal: bool = False    # Thermal-tab heat-flux / film-coefficient section
    include_compare: bool = False    # side-by-side comparison of ``compare_configs``
    compare_backward: bool = True    # in the comparison, show the backward (design-calc) outputs
    compare_forward: bool = True     # in the comparison, show the forward (performance) outputs
    include_optimization: bool = False  # summary of ``optimization_result`` if present
    include_validation: bool = True  # engine warnings / errors
    include_toc: bool = True         # table of contents after the cover (auto-skipped if trivial)

    compare_configs: list[VehicleConfig] = field(default_factory=list)
    optimization_result: object | None = None  # brakelab.optimization result, or None


# =============================================================================================
# Styles
# =============================================================================================
def _styles() -> dict[str, ParagraphStyle]:
    return {
        "cover_title": ParagraphStyle("cover_title", fontName=_FONT_B, fontSize=28, leading=32, textColor=_INK),
        "cover_car": ParagraphStyle("cover_car", fontName=_FONT, fontSize=15, leading=19, textColor=_INK),
        "cover_sub": ParagraphStyle("cover_sub", fontName=_FONT_I, fontSize=10.5, leading=14, textColor=_GREY),
        "cover_meta": ParagraphStyle("cover_meta", fontName=_FONT, fontSize=9.5, leading=14, textColor=_GREY),
        "section": ParagraphStyle("SectionTitle", fontName=_FONT_B, fontSize=15, leading=18, textColor=_INK,
                                  spaceBefore=14, spaceAfter=2),
        # same look as a section title, but a distinct name so it is NOT captured as a TOC entry
        "plain_title": ParagraphStyle("PlainTitle", fontName=_FONT_B, fontSize=15, leading=18, textColor=_INK,
                                      spaceBefore=2, spaceAfter=2),
        "caption": ParagraphStyle("caption", fontName=_FONT, fontSize=8.5, leading=11.5, textColor=_GREY,
                                  spaceAfter=5),
        "block": ParagraphStyle("block", fontName=_FONT_B, fontSize=10.5, leading=13, textColor=_INK,
                                spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", fontName=_FONT, fontSize=9, leading=12.5, textColor=_INK),
        "muted": ParagraphStyle("muted", fontName=_FONT, fontSize=8.5, leading=12, textColor=_GREY),
        "phase": ParagraphStyle("phase", fontName=_FONT_B, fontSize=9, leading=12, textColor=_GREY,
                                spaceBefore=5, spaceAfter=1),
        # cell paragraphs (so long text wraps instead of colliding)
        "cell": ParagraphStyle("cell", fontName=_FONT, fontSize=8.5, leading=10.5, textColor=_INK),
        "cell_b": ParagraphStyle("cell_b", fontName=_FONT_B, fontSize=8.5, leading=10.5, textColor=_INK),
        "cell_r": ParagraphStyle("cell_r", fontName=_FONT, fontSize=8.5, leading=10.5, textColor=_INK,
                                 alignment=TA_RIGHT),
        "cell_muted": ParagraphStyle("cell_muted", fontName=_FONT, fontSize=8.5, leading=10.5, textColor=_GREY),
        # KPI strip
        "kpi_num": ParagraphStyle("kpi_num", fontName=_FONT_B, fontSize=16, leading=18, textColor=_INK,
                                  alignment=TA_CENTER),
        "kpi_lab": ParagraphStyle("kpi_lab", fontName=_FONT, fontSize=7, leading=9, textColor=_GREY,
                                  alignment=TA_CENTER),
        "toc1": ParagraphStyle("toc1", fontName=_FONT, fontSize=10.5, leading=18, textColor=_INK),
    }


# =============================================================================================
# Small helpers
# =============================================================================================
def _num(x: float, digits: int = 2) -> str:
    return f"{x:,.{digits}f}"


def _auto(x: float) -> str:
    """Format a number with a sensible number of decimals for its magnitude."""
    ax = abs(x)
    digits = 3 if ax < 100 else (1 if ax < 100000 else 0)
    return f"{x:,.{digits}f}"


def _unit_text(unit: str) -> str:
    return "" if unit in ("", "-") else unit


def _P(text: str, st, style: str = "cell") -> Paragraph:
    return Paragraph(text if text is not None else "", st[style])


# =============================================================================================
# Custom flowables
# =============================================================================================
class _HRule(Flowable):
    """A thin horizontal rule spanning the frame width."""

    def __init__(self, thickness: float = 0.8, color=_INK, pad_before: float = 2, pad_after: float = 4):
        super().__init__()
        self.thickness = thickness
        self.color = color
        self.pad_before = pad_before
        self.pad_after = pad_after
        self.width = 0.0

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.thickness + self.pad_before + self.pad_after

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.color)
        c.setLineWidth(self.thickness)
        y = self.pad_after
        c.line(0, y, self.width, y)


class _Banner(Flowable):
    """A full-width rounded status bar with a bold verdict — the first thing the reader sees."""

    def __init__(self, text: str, bg, fg, height: float = 15 * mm):
        super().__init__()
        self.text = text
        self.bg = bg
        self.fg = fg
        self.height = height
        self.width = 0.0

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height + 3 * mm

    def draw(self):
        c = self.canv
        h = self.height
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.width, h, radius=3 * mm, stroke=0, fill=1)
        c.setFillColor(self.fg)
        c.setFont(_FONT_B, 15)
        c.drawCentredString(self.width / 2.0, h / 2.0 - 5, self.text)


# =============================================================================================
# Tables
# =============================================================================================
def _base_table_style(header: bool, compact: bool) -> list:
    fs = 8 if compact else 8.5
    pad = 2.5 if compact else 4
    style = [
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("TEXTCOLOR", (0, 0), (-1, -1), _INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, _RULE),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_B),
            ("TEXTCOLOR", (0, 0), (-1, 0), _INK),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, _HAIRLINE),
            ("LINEABOVE", (0, 0), (-1, 0), 0.6, _HAIRLINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ZEBRA]),
        ]
    else:
        style += [("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ZEBRA])]
    return style


def _table(rows: list[list], col_widths=None, header: bool = True, compact: bool = False,
           extra_style: list | None = None, align_right_from: int | None = None) -> Table:
    """A clean light-header data table. ``align_right_from`` right-aligns value columns from that index.

    ``extra_style`` injects per-cell commands (used for pass/fail chips and comparison up/down tints)."""
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = _base_table_style(header, compact)
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
        style.append(("ALIGN", (0, 0), (align_right_from - 1, -1), "LEFT"))
    for cmd in extra_style or []:
        style.append(cmd)
    t.setStyle(TableStyle(style))
    return t


# =============================================================================================
# Requirements presentation
# =============================================================================================
def _req_status(req) -> tuple[str, colors.Color, colors.Color]:
    """(label, text colour, chip background) for a requirement's verdict."""
    if req.passed:
        return "PASS", _PASS, _PASS_BG
    if req.hard:
        return "FAIL", _FAIL, _FAIL_BG
    return "OFF TARGET", _WARN, _WARN_BG


def _requirements_table(story: list, results: BrakeResults, st, compact: bool = False) -> None:
    """The star of the report: what each check needs vs what the setup produces, with a colour chip.

    Columns are generously sized and cells wrap, so the needed/produced numbers never run together."""
    reqs = list(getattr(results, "requirements", ()) or ())
    if not reqs:
        return
    header = ["Requirement", "Needs", "Produces", "Status"]
    rows = [header]
    extra: list = []
    for i, req in enumerate(reqs, start=1):
        label, fg, bg = _req_status(req)
        rows.append([
            _P(req.name, st, "cell"),
            _P(req.requirement_text, st, "cell"),
            _P(req.current_text, st, "cell_b"),
            _P(f"<b>{label}</b>", st, "cell"),
        ])
        extra.append(("BACKGROUND", (3, i), (3, i), bg))
        extra.append(("TEXTCOLOR", (3, i), (3, i), fg))
        extra.append(("ALIGN", (3, i), (3, i), "CENTER"))
    widths = [60 * mm, 45 * mm, 40 * mm, _CONTENT_W - 145 * mm]
    story.append(_table(rows, col_widths=widths, compact=compact, extra_style=extra))


def _requirements_glance(config: VehicleConfig, results: BrakeResults, st) -> Table:
    """A compact pass/fail roster for the cover: every check with a coloured ✓/✗ and its numbers."""
    reqs = list(getattr(results, "requirements", ()) or ())
    rows = []
    extra: list = []
    for i, req in enumerate(reqs):
        label, fg, bg = _req_status(req)
        mark = "✓" if req.passed else ("✗" if req.hard else "!")
        rows.append([
            _P(f"<b>{mark}</b>", st, "cell"),
            _P(req.name, st, "cell"),
            _P(f"needs {req.requirement_text} · has {req.current_text}", st, "cell_muted"),
        ])
        extra.append(("TEXTCOLOR", (0, i), (0, i), fg))
        extra.append(("BACKGROUND", (0, i), (0, i), bg))
        extra.append(("ALIGN", (0, i), (0, i), "CENTER"))
    t = Table(rows, colWidths=[8 * mm, 62 * mm, _CONTENT_W - 70 * mm], hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, _RULE),
    ] + extra
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
        max_w, max_h = 55 * mm, 22 * mm
        scale = min(max_w / iw, max_h / ih)
        img = Image(path, width=iw * scale, height=ih * scale)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001 — a bad path must never break the report
        return None


def _kpi_strip(config: VehicleConfig, results: BrakeResults, st) -> Table:
    """A row of headline numbers — the few figures a reader wants at a glance."""
    s, h, p = results.sizing, results.hydraulics, results.pedal_travel
    peak_p = max(s.front.line_pressure, s.rear.line_pressure)
    stroke_pct = (p.effective_stroke / config.hydraulics.max_mc_stroke * 100.0
                  if config.hydraulics.max_mc_stroke else 0.0)
    kpis = [
        (_num(config.target_decel_g, 2), "Target decel [g]"),
        (_num(peak_p, 2), "Peak line pressure [MPa]"),
        (_num(p.pedal_travel, 1), "Pedal travel [mm]"),
        (_num(stroke_pct, 0) + "%", "MC stroke used"),
        (_num(h.bar_force_front, 0), "Pedal force req. [N]"),
    ]
    nums = [Paragraph(v, st["kpi_num"]) for v, _ in kpis]
    labs = [Paragraph(lab, st["kpi_lab"]) for _, lab in kpis]
    w = _CONTENT_W / len(kpis)
    t = Table([nums, labs], colWidths=[w] * len(kpis))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, _HAIRLINE),
        ("LINEBELOW", (0, 1), (-1, 1), 0.6, _HAIRLINE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, _RULE),
    ]))
    return t


def _cover(story: list, config: VehicleConfig, results: BrakeResults, opt: ReportOptions, st) -> None:
    logo = _logo_flowable(opt.logo_path) if opt.logo_path else None
    if logo is not None:
        story.append(logo)
        story.append(Spacer(1, 10 * mm))
    else:
        story.append(Spacer(1, 20 * mm))

    story.append(Paragraph(opt.title, st["cover_title"]))
    story.append(_HRule(1.2, _INK, pad_before=4, pad_after=6))
    story.append(Paragraph(config.name, st["cover_car"]))
    if opt.subtitle:
        story.append(Paragraph(opt.subtitle, st["cover_sub"]))
    elif config.notes:
        story.append(Paragraph(config.notes, st["cover_sub"]))

    # Verdict banner — instant pass/fail.
    story.append(Spacer(1, 10 * mm))
    reqs = list(getattr(results, "requirements", ()) or ())
    n_fail = sum(1 for r in reqs if r.hard and not r.passed)
    n_soft = sum(1 for r in reqs if not r.hard and not r.passed)
    if results.ok and n_soft == 0:
        _banner_text = "ALL REQUIREMENTS MET"
        story.append(_Banner(_banner_text, _PASS_BG, _PASS))
    elif results.ok:
        story.append(_Banner(f"REQUIREMENTS MET  ·  {n_soft} TARGET(S) OFF", _WARN_BG, _WARN))
    else:
        story.append(_Banner(f"REQUIREMENTS NOT MET  ·  {n_fail} NEED REVIEW", _FAIL_BG, _FAIL))

    story.append(Spacer(1, 7 * mm))
    story.append(_kpi_strip(config, results, st))

    # Pass/fail roster.
    if reqs:
        story.append(Spacer(1, 7 * mm))
        story.append(Paragraph("Requirements at a glance", st["block"]))
        story.append(_requirements_glance(config, results, st))

    # Quiet metadata block near the foot of the cover.
    story.append(Spacer(1, 10 * mm))
    story.append(_HRule(0.6, _RULE, pad_before=2, pad_after=3))
    meta = []
    if opt.author:
        meta.append(f"Prepared by: {opt.author}")
    if opt.include_date:
        meta.append(f"Date: {date.today().strftime('%d %B %Y')}")
    if meta:
        story.append(Paragraph("&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta), st["cover_meta"]))


# =============================================================================================
# Section scaffolding (numbering + TOC-visible headings)
# =============================================================================================
class _Sections:
    """Assigns running numbers and renders TOC-visible section headings."""

    def __init__(self) -> None:
        self.n = 0

    def heading(self, story: list, title: str, st, caption: str = "") -> None:
        self.n += 1
        story.append(Paragraph(f"{self.n}.&nbsp;&nbsp;{title}", st["section"]))
        story.append(_HRule(0.9, _INK, pad_before=1, pad_after=4))
        if caption:
            story.append(Paragraph(caption, st["caption"]))


# =============================================================================================
# Sections
# =============================================================================================
def _selected_components(config: VehicleConfig) -> list[tuple[str, str]]:
    """Best-effort match of the config's values to real catalogued parts (brand + model), so the
    report names the hardware. Falls back to "Custom — <value>" when nothing in the catalog matches."""
    from ..components import catalog

    h, cal, pad, th = config.hydraulics, config.caliper, config.pad, config.thermal

    def nm(spec, fallback: str) -> str:
        return spec.name if spec is not None else fallback

    mc_f = catalog.match_master_cylinder(h.mc_bore_front)
    mc_r = catalog.match_master_cylinder(h.mc_bore_rear)
    same_mc = mc_f is not None and mc_r is not None and mc_f.name == mc_r.name
    rows: list[tuple[str, str]] = []
    if same_mc:
        rows.append(("Master cylinder (front & rear)", mc_f.name))
    else:
        rows.append(("Master cylinder, front", nm(mc_f, f"Custom — {h.mc_bore_front:.2f} mm bore")))
        rows.append(("Master cylinder, rear", nm(mc_r, f"Custom — {h.mc_bore_rear:.2f} mm bore")))
    rows.append(("Caliper", nm(catalog.match_caliper(cal.piston_area, cal.n_pistons),
                                f"Custom — {cal.n_pistons} × {cal.piston_area:.0f} mm² piston")))
    rows.append(("Brake pad", nm(catalog.match_pad(pad.friction_coefficient),
                                  f"Custom — μ {pad.friction_coefficient:.2f}")))
    rows.append(("Rotor material", nm(catalog.match_material(th.rotor_specific_heat, th.emissivity),
                                       "Custom")))
    return rows


def _field_value(config: VehicleConfig, field_spec) -> str:
    v = get_by_path(config, field_spec.path)
    if field_spec.kind == "bool":
        return "yes" if v else "no"
    if field_spec.kind == "int":
        return str(int(v))
    return f"{float(v):,.{field_spec.decimals}f}"


_ASSUMED_TAG = ' <font size="6.5" color="#8f8f8f">(assumed)</font>'


def _input_label(text: str, is_assumed: bool, st, style: str = "cell") -> Paragraph:
    """A table label cell that shows a small, muted '(assumed)' tag when the input is an assumption."""
    return Paragraph(f"{text}{_ASSUMED_TAG}" if is_assumed else text, st[style])


def _assumed_note(story: list, st) -> None:
    story.append(Paragraph("Inputs tagged (assumed) are assumptions, not measured/confirmed values — "
                           "treat results that depend on them as provisional.", st["muted"]))


def _full_inputs(story: list, config: VehicleConfig, st) -> None:
    """Every input, phase by phase, in a compact quiet listing (assumed values tagged)."""
    assumed = set(config.assumed_inputs)
    story.append(Paragraph("Full input listing", st["block"]))
    for group in INPUT_GROUPS:
        story.append(Paragraph(group.title, st["phase"]))
        rows = [["Parameter", "Value", "Unit"]]
        for spec in group.fields:
            rows.append([_input_label(spec.label, spec.path in assumed, st, "cell_muted"),
                         _field_value(config, spec), _unit_text(spec.unit)])
        story.append(_table(rows, col_widths=[_CONTENT_W - 55 * mm, 30 * mm, 25 * mm],
                            compact=True, align_right_from=1))
    if assumed:
        story.append(Spacer(1, 1.5 * mm))
        _assumed_note(story, st)
    story.append(Spacer(1, 3 * mm))


def _full_outputs(story: list, config: VehicleConfig, results: BrakeResults, st,
                  groups=OUTPUT_GROUPS, heading: str = "Full results listing") -> None:
    """Every computed output, phase by phase, in the same compact quiet listing."""
    story.append(Paragraph(heading, st["block"]))
    for group in groups:
        story.append(Paragraph(group.title, st["phase"]))
        rows = [["Quantity", "Value", "Unit"]]
        for output in group.outputs:
            try:
                shown = _auto(output.getter(results, config))
            except Exception:  # noqa: BLE001
                shown = "—"
            rows.append([_P(output.label, st, "cell_muted"), shown, _unit_text(output.unit)])
        story.append(_table(rows, col_widths=[_CONTENT_W - 55 * mm, 30 * mm, 25 * mm],
                            compact=True, align_right_from=1))
    story.append(Spacer(1, 3 * mm))


def _design_section(story: list, config: VehicleConfig, results: BrakeResults, st, sec: _Sections,
                    detail: str = "extensive") -> None:
    sec.heading(story, "Design Summary", st,
                "Primary inputs, the braking quantities they produce, and the requirements check.")
    m, t, pb = config.mass, config.tires, config.pedal_box
    assumed = set(config.assumed_inputs)
    shown_assumed: set[str] = set()

    def lbl(text: str, path: str):
        if path in assumed:
            shown_assumed.add(path)
        return _input_label(text, path in assumed, st)

    story.append(Paragraph("Key inputs", st["block"]))
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
        [lbl("MC bore, front / rear", "hydraulics.mc_bore_front"),
         f"{_num(config.hydraulics.mc_bore_front, 2)} / {_num(config.hydraulics.mc_bore_rear, 2)}", "mm"],
        [lbl("Pedal ratio", "pedal_box.pedal_ratio"), _num(pb.pedal_ratio, 1), "-"],
        [lbl("Front balance bias", "pedal_box.balance_bias_front"), _num(pb.balance_bias_front, 2), "-"],
        [lbl("Driver force", "pedal_box.driver_force"), _num(pb.driver_force, 1), "N"],
    ]
    story.append(_table(inputs, col_widths=[_CONTENT_W - 65 * mm, 40 * mm, 25 * mm], align_right_from=1))

    story.append(Paragraph("Selected components", st["block"]))
    comp_rows = [["Component", "Selected part"]] + [list(r) for r in _selected_components(config)]
    story.append(_table(comp_rows, col_widths=[60 * mm, _CONTENT_W - 60 * mm]))

    d, tq, s, h, p = results.dynamics, results.torque, results.sizing, results.hydraulics, results.pedal_travel
    story.append(Paragraph("Key results — front &amp; rear", st["block"]))
    res = [
        ["Quantity", "Front", "Rear", "Unit"],
        ["Dynamic axle load", _num(d.dynamic_front), _num(d.dynamic_rear), "N"],
        ["Required torque / rotor", _num(tq.front.torque_per_rotor), _num(tq.rear.torque_per_rotor), "N·m"],
        ["Required clamp force", _num(s.front.clamp_force), _num(s.rear.clamp_force), "N"],
        ["Required line pressure", _num(s.front.line_pressure, 3), _num(s.rear.line_pressure, 3), "MPa"],
        ["MC force required", _num(h.mc_force_front), _num(h.mc_force_rear), "N"],
        ["Pedal force required", _num(h.bar_force_front), _num(h.bar_force_rear), "N"],
    ]
    vw = (_CONTENT_W - 22 * mm - 65 * mm) / 2
    story.append(_table(res, col_widths=[65 * mm, vw, vw, 22 * mm], align_right_from=1))

    story.append(Paragraph("Overall", st["block"]))
    summary = [
        ["Overall quantity", "Value", "Unit"],
        ["Vehicle weight", _num(d.weight), "N"],
        ["Weight transfer", _num(d.weight_transfer), "N"],
        ["Pedal force delivered", _num(h.pedal_force), "N"],
        ["Optimal front bias", _num(h.optimal_bias_front, 3), "-"],
        ["Effective MC stroke", _num(p.effective_stroke, 2), "mm"],
        ["Pedal travel", _num(p.pedal_travel, 1), "mm"],
        ["BOTS trigger", _num(p.bots_trigger, 2), "mm"],
    ]
    story.append(_table(summary, col_widths=[_CONTENT_W - 65 * mm, 40 * mm, 25 * mm], align_right_from=1))
    if shown_assumed:
        _assumed_note(story, st)

    # Requirements — front and centre.
    if getattr(results, "requirements", None):
        story.append(Paragraph("Requirements check", st["block"]))
        _requirements_table(story, results, st)

    # Extensive reports also carry the exhaustive listing.
    if detail == "extensive":
        story.append(Spacer(1, 3 * mm))
        story.append(_HRule(0.4, _RULE, pad_before=1, pad_after=4))
        _full_inputs(story, config, st)
        _full_outputs(story, config, results, st)


def _status_row(label: str, ok: bool, ok_text: str, bad_text: str, st) -> tuple[list, list]:
    fg, bg = (_PASS, _PASS_BG) if ok else (_FAIL, _FAIL_BG)
    txt = ok_text if ok else bad_text
    return [_P(label, st, "cell"), _P(f"<b>{txt}</b>", st, "cell")], [fg, bg]


def _forward_section(story: list, config: VehicleConfig, results: BrakeResults, st, sec: _Sections,
                     detail: str = "extensive") -> None:
    """Forward/performance simulation: what the car actually does at the driver's pedal force."""
    fwd = getattr(results, "forward", None)
    if fwd is None:
        return
    sec.heading(story, "Performance (Forward Simulation)", st,
                "Driving the physics forward from the driver's pedal force: the resulting deceleration, "
                "tyre lock-up, and how much of the available grip each axle uses.")

    # Verdict roster: lock-up + target-decel, colour-chipped.
    story.append(Paragraph("Behaviour at the design pedal force", st["block"]))
    target = config.target_decel_g
    checks = [
        _status_row("Front axle", not fwd.front_locked, "does not lock", "LOCKS UP", st),
        _status_row("Rear axle", not fwd.rear_locked, "does not lock", "LOCKS UP", st),
        _status_row("Target deceleration", fwd.actual_decel_g + 1e-9 >= target,
                    f"reached ({_num(fwd.actual_decel_g, 2)} g ≥ {_num(target, 2)} g)",
                    f"short ({_num(fwd.actual_decel_g, 2)} g < {_num(target, 2)} g)", st),
    ]
    rows = [["Check", "Result"]]
    extra: list = []
    for i, (cells, (fg, bg)) in enumerate(checks, start=1):
        rows.append(cells)
        extra.append(("TEXTCOLOR", (1, i), (1, i), fg))
        extra.append(("BACKGROUND", (1, i), (1, i), bg))
    story.append(_table(rows, col_widths=[55 * mm, _CONTENT_W - 55 * mm], extra_style=extra))

    story.append(Paragraph("Key performance figures", st["block"]))
    vals = [
        ["Quantity", "Front", "Rear", "Unit"],
        ["Grip utilisation", _num(fwd.front_utilization * 100, 0) + "%",
         _num(fwd.rear_utilization * 100, 0) + "%", "of limit"],
        ["Brake torque (axle)", _num(fwd.axle_brake_torque_front), _num(fwd.axle_brake_torque_rear), "N·m"],
        ["Grip torque (lock-up)", _num(fwd.grip_torque_front), _num(fwd.grip_torque_rear), "N·m"],
        ["Line pressure produced", _num(fwd.line_pressure_front, 3), _num(fwd.line_pressure_rear, 3), "MPa"],
        ["Dynamic axle load", _num(fwd.dynamic_front), _num(fwd.dynamic_rear), "N"],
    ]
    vw = (_CONTENT_W - 22 * mm - 55 * mm) / 2
    story.append(_table(vals, col_widths=[55 * mm, vw, vw, 22 * mm], align_right_from=1))

    story.append(Paragraph("Overall", st["block"]))
    overall = [
        ["Overall quantity", "Value", "Unit"],
        ["Actual deceleration", _num(fwd.actual_decel_g, 3), "g"],
        ["Total stopping force", _num(fwd.stopping_force), "N"],
        ["Pedal force into balance bar", _num(fwd.pedal_force), "N"],
        ["Optimal front bias (equal utilisation)", _num(fwd.optimal_bias_front, 3), "-"],
    ]
    story.append(_table(overall, col_widths=[_CONTENT_W - 65 * mm, 40 * mm, 25 * mm], align_right_from=1))

    # Brake balance diagram (front vs. rear brake force).
    from ..core.balance import brake_balance

    bd = brake_balance(config)
    who = "front" if bd.front_locks_first else "rear"
    limit_txt = (f"Here the <b>{who}</b> axle reaches its limit first, at about "
                 f"{_num(bd.usable_decel, 2)} g." if bd.usable_decel != float("inf")
                 else f"Here the <b>{who}</b> axle is the first toward its limit.")
    verdict = ("That's the stable outcome you want." if bd.front_locks_first
               else "That's twitchy — to fix it, raise front bias (or resize the rear) to bring the "
                    "line down closer to (just below) the grey curve.")
    balance_chart = _balance_chart(config)
    if balance_chart is not None:
        story.append(KeepTogether([
            Paragraph("Brake balance", st["block"]),
            Paragraph(
                "<b>How to read it:</b> your brakes apply a fixed front:rear ratio, so the design always "
                "plots as a straight line through the origin — that's expected, not a problem. The grey "
                "curve is the ideal split where both axles would lock together. You want your line to sit "
                "just <i>below</i> the grey curve up to your target deceleration, so the FRONT reaches its "
                f"grip limit first (a controllable lock-up). {limit_txt} {verdict}", st["caption"]),
            balance_chart,
        ]))

    # Stopping distance & time + a speed-vs-distance curve.
    from ..core.performance import braking_speeds, stopping_from_config

    vi, vf = braking_speeds(config)
    da, ta = stopping_from_config(config, fwd.actual_decel_g)
    dt, tt = stopping_from_config(config, config.target_decel_g)
    to_txt = f"to {_num(vf * 3.6, 0)} km/h" if config.performance.custom_final_speed else "to a stop"
    stop_block = [
        Paragraph("Stopping distance", st["block"]),
        Paragraph(f"Braking from {_num(vi * 3.6, 0)} km/h ({_num(vi, 1)} m/s) {to_txt}, "
                  "constant-deceleration model. <b>Actual</b> uses the deceleration this pedal force "
                  "produces; <b>design target</b> uses the target deceleration set for the design.",
                  st["caption"]),
        _table([
            ["", "Distance [m]", "Time [s]"],
            [f"Actual ({_num(fwd.actual_decel_g, 2)} g)", _num(da, 1), _num(ta, 2)],
            [f"Design target ({_num(config.target_decel_g, 2)} g)", _num(dt, 1), _num(tt, 2)],
        ], col_widths=[_CONTENT_W - 90 * mm, 45 * mm, 45 * mm], align_right_from=1),
    ]
    chart = _stopping_chart(config, results)
    if chart is not None:
        stop_block.append(Spacer(1, 2 * mm))
        stop_block.append(chart)
    story.append(KeepTogether(stop_block))

    if detail == "extensive" and FORWARD_GROUPS:
        story.append(Spacer(1, 3 * mm))
        story.append(_HRule(0.4, _RULE, pad_before=1, pad_after=4))
        _full_outputs(story, config, results, st, groups=FORWARD_GROUPS,
                      heading="Full forward-simulation listing")


def _speed_curve(vi: float, vf: float, decel_g: float, n: int = 60):
    """(distance[m], speed[km/h]) points for a constant-decel stop from vi to vf."""
    from .. core.units import GRAVITY

    a = decel_g * GRAVITY
    if a <= 0:
        return [0.0], [vi * 3.6]
    total = (vi * vi - vf * vf) / (2.0 * a)
    xs, ys = [], []
    for i in range(n + 1):
        x = total * i / n
        v2 = max(vi * vi - 2.0 * a * x, 0.0)
        xs.append(x)
        ys.append(v2 ** 0.5 * 3.6)  # m/s -> km/h
    return xs, ys


def _stopping_chart(config: VehicleConfig, results: BrakeResults):
    """Speed-vs-distance curve for the stop, at the actual and the target deceleration. Returns a
    reportlab Image (or None). Uses a bare Agg canvas so it is safe under the GUI's Qt loop."""
    fwd = getattr(results, "forward", None)
    if fwd is None:
        return None
    try:
        from io import BytesIO

        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        from ..core.performance import braking_speeds

        vi, vf = braking_speeds(config)
        ink = "#1c1c1c"
        fig = Figure(figsize=(7.0, 2.9), dpi=150)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        xa, ya = _speed_curve(vi, vf, fwd.actual_decel_g)
        xt, yt = _speed_curve(vi, vf, config.target_decel_g)
        ax.plot(xa, ya, color=ink, linewidth=1.5, label=f"Actual ({_num(fwd.actual_decel_g, 2)} g)")
        ax.plot(xt, yt, color=ink, linewidth=1.1, linestyle="--",
                label=f"Design target ({_num(config.target_decel_g, 2)} g)")
        ax.set_xlabel("Distance (m)", fontsize=8, color=ink)
        ax.set_ylabel("Speed (km/h)", fontsize=8, color=ink)
        ax.tick_params(colors=ink, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#c9ced4")
        ax.grid(True, alpha=0.25)
        ax.set_ylim(bottom=0)
        ax.set_xlim(left=0)
        legend = ax.legend(fontsize=7, loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color(ink)
        fig.tight_layout(pad=0.6)
        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        buf.seek(0)
        w = _CONTENT_W
        img = Image(buf, width=w, height=w * 2.9 / 7.0)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001 — a chart must never break the report
        return None


def _balance_chart(config: VehicleConfig):
    """The brake balance diagram (front vs. rear brake force) as a reportlab Image, or None."""
    try:
        from io import BytesIO

        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        from ..core.balance import brake_balance

        bd = brake_balance(config)
        ink = "#1c1c1c"
        fig = Figure(figsize=(6.4, 4.2), dpi=150)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        ax.plot(bd.ideal_front, bd.ideal_rear, color="#8a8a8a", linewidth=1.4,
                label="Ideal distribution")
        ax.plot(bd.actual_front, bd.actual_rear, color=ink, linewidth=1.6, label="Actual (this design)")
        # iso-deceleration lines: F_f + F_r = a·W
        for a in bd.iso_decels:
            total = a * bd.weight
            ax.plot([0, total], [total, 0], color="#c2c2c2", linewidth=0.8, linestyle=":")
            ax.annotate(f"{a:g} g", xy=(total * 0.02, total * 0.98), fontsize=6.5, color="#8a8a8a")
        ax.plot([bd.op_front], [bd.op_rear], marker="o", color=ink, markersize=5,
                label="Design pedal force")

        top = max(max(bd.ideal_front, default=1), max(bd.ideal_rear, default=1), bd.op_front, bd.op_rear)
        ax.set_xlim(0, top * 1.05)
        ax.set_ylim(0, top * 1.05)
        ax.set_xlabel("Front brake force (N)", fontsize=8, color=ink)
        ax.set_ylabel("Rear brake force (N)", fontsize=8, color=ink)
        ax.tick_params(colors=ink, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#c9ced4")
        ax.grid(True, alpha=0.25)
        legend = ax.legend(fontsize=7, loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color(ink)
        fig.tight_layout(pad=0.6)
        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        buf.seek(0)
        w = 130 * mm
        img = Image(buf, width=w, height=w * 4.2 / 6.4)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001
        return None


def _thermal_chart(sim, ambient: float):
    """Render the transient rotor-temperature curve as a reportlab Image, or None on any failure.

    Uses a bare Agg canvas (not pyplot / not the Qt backend) so it is safe to call while the GUI's
    Qt event loop is running, and needs no display."""
    try:
        from io import BytesIO

        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        fig = Figure(figsize=(7.0, 2.9), dpi=150)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ink = "#1c1c1c"
        ax.plot(sim.time, sim.temp_front, color=ink, linewidth=1.4, label="Front rotor")
        ax.plot(sim.time, sim.temp_rear, color=ink, linewidth=1.1, linestyle="--", label="Rear rotor")
        ax.axhline(ambient, color="#9a9a9a", linewidth=0.8, linestyle=":", label="Ambient")
        ax.set_xlabel("Time (s)", fontsize=8, color=ink)
        ax.set_ylabel("Rotor temperature (°C)", fontsize=8, color=ink)
        ax.tick_params(colors=ink, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#c9ced4")
        ax.grid(True, alpha=0.25)
        legend = ax.legend(fontsize=7, loc="upper left", frameon=False)
        for text in legend.get_texts():
            text.set_color(ink)
        fig.tight_layout(pad=0.6)

        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        buf.seek(0)
        w = _CONTENT_W
        h = w * 2.9 / 7.0
        img = Image(buf, width=w, height=h)
        img.hAlign = "LEFT"
        return img
    except Exception:  # noqa: BLE001 — a chart must never break the report
        return None


def _thermal_section(story: list, config: VehicleConfig, results: BrakeResults, st, sec: _Sections) -> None:
    th = getattr(results, "thermal", None)
    if th is None:
        return
    sec.heading(story, "Thermal — ANSYS Boundary Inputs", st,
                "Heat-flux and film-coefficient values that seed a transient rotor thermal study.")
    t = config.thermal
    story.append(Paragraph("Heat load", st["block"]))
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
    story.append(_table(rows, col_widths=[_CONTENT_W - 65 * mm, 40 * mm, 25 * mm], align_right_from=1))

    # Transient duty-cycle simulation (lumped capacitance; see brakelab/thermal/simulation.py).
    try:
        from ..thermal import simulate_temperature

        sim = simulate_temperature(config)
    except Exception:  # noqa: BLE001 — the report must not die on odd thermal inputs
        sim = None
    if sim is not None:
        vw = (_CONTENT_W - 25 * mm - 70 * mm) / 2
        sim_rows = [
            ["Quantity", "Front rotor", "Rear rotor", "Unit"],
            ["Peak temperature", _num(sim.peak_front, 1), _num(sim.peak_rear, 1), "°C"],
            ["End of duty cycle", _num(sim.final_front, 1), _num(sim.final_rear, 1), "°C"],
            ["Rise per stop (no cooling)",
             _num(sim.adiabatic_rise_front, 1), _num(sim.adiabatic_rise_rear, 1), "°C"],
        ]
        # Keep the heading, table and chart together so the graph never orphans onto its own page.
        preview = [
            Paragraph("Transient temperature — rough estimate only", st["block"]),
            Paragraph(
                f"A simplified lumped-capacitance model over {t.n_stops} stops of {_num(t.brake_time, 1)} s "
                f"with {_num(t.cool_time, 1)} s of cooling between. This is an approximate preview to gauge "
                "roughly how hot the rotors get — not an actual thermal simulation. Use ANSYS (or similar) "
                "for design-grade numbers.", st["caption"]),
            _table(sim_rows, col_widths=[70 * mm, vw, vw, 25 * mm], align_right_from=1),
        ]
        chart = _thermal_chart(sim, config.thermal.ambient_temp)
        if chart is not None:
            preview.append(Spacer(1, 3 * mm))
            preview.append(chart)
        story.append(KeepTogether(preview))


# --- comparison ------------------------------------------------------------------------------
def _compare_outputs_block(story: list, title: str, spec: list, names: list[str], configs: list,
                           solved: list, col_widths: list, st) -> None:
    """A block of output rows, each cell shaded green (higher) / red (lower) vs. the leftmost setup."""
    story.append(Paragraph(title, st["block"]))
    rows = [[_P("Quantity", st, "cell_b")] + [_P(nm, st, "cell_b") for nm in names]]
    extra: list = []
    for i, (label, fn) in enumerate(spec, start=1):
        vals = [fn(c, r) for c, r in zip(configs, solved)]
        base = vals[0]
        cells = [_P(label, st, "cell")]
        for j, v in enumerate(vals):
            cells.append(_P(_auto(v) if v is not None else "—", st, "cell_r"))
            if j != 0 and base is not None and v is not None and abs(v - base) > 1e-9:
                extra.append(("BACKGROUND", (1 + j, i), (1 + j, i), _UP_BG if v > base else _DOWN_BG))
        rows.append(cells)
    story.append(_table(rows, col_widths=col_widths, header=True, extra_style=extra, align_right_from=1))


def _compare_section(story: list, configs: list[VehicleConfig], engine: BrakeEngine, st, sec: _Sections,
                     backward: bool = True, forward: bool = True) -> None:
    configs = [c for c in configs if c is not None]
    if len(configs) < 2:
        return
    which = "backward (design-calc) and forward (performance) outputs" if backward and forward else (
        "backward (design-calc) outputs" if backward else
        "forward (performance) outputs" if forward else "inputs")
    sec.heading(story, "Comparison", st,
                f"Setups side by side, comparing their {which}. Inputs that differ are bold; each output "
                "is shaded green when higher and red when lower than the first (leftmost) setup.")
    names = [c.name for c in configs]
    solved = [engine.solve(c) for c in configs]
    n = len(configs)
    label_w = 62 * mm
    vw = (_CONTENT_W - label_w) / n
    col_widths = [label_w] + [vw] * n

    # ---- Inputs: bold the rows that differ -------------------------------------------------
    story.append(Paragraph("Inputs", st["block"]))
    input_rows = [
        ("Total mass [kg]", lambda c, r: _num(c.mass.total_mass, 1)),
        ("Front weight fraction", lambda c, r: _num(c.mass.front_weight_fraction, 3)),
        ("Target decel [g]", lambda c, r: _num(c.target_decel_g, 2)),
        ("Tyre friction coeff.", lambda c, r: _num(c.tires.friction_coefficient, 2)),
        ("Rotor eff. radius [m]", lambda c, r: _num(c.rotor.effective_radius, 4)),
        ("Pad friction coeff.", lambda c, r: _num(c.pad.friction_coefficient, 3)),
        ("Front / rear rotors", lambda c, r: f"{c.front_axle.n_rotors} / {c.rear_axle.n_rotors}"),
        ("MC bore F/R [mm]", lambda c, r: f"{_num(c.hydraulics.mc_bore_front, 2)} / {_num(c.hydraulics.mc_bore_rear, 2)}"),
        ("Pedal ratio", lambda c, r: _num(c.pedal_box.pedal_ratio, 1)),
        ("Front balance bias", lambda c, r: _num(c.pedal_box.balance_bias_front, 2)),
        ("Driver force [N]", lambda c, r: _num(c.pedal_box.driver_force, 0)),
    ]
    rows = [[_P("Parameter", st, "cell_b")] + [_P(nm, st, "cell_b") for nm in names]]
    extra: list = []
    for i, (label, fn) in enumerate(input_rows, start=1):
        cells = [fn(c, r) for c, r in zip(configs, solved)]
        differs = len(set(cells)) > 1
        style = "cell_b" if differs else "cell"
        rows.append([_P(label, st, style)] + [_P(v, st, style) for v in cells])
        if differs:
            extra.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f0f2f5")))
    story.append(_table(rows, col_widths=col_widths, header=True, extra_style=extra, align_right_from=1))

    # ---- Backward (design calc) outputs: green if higher / red if lower than the leftmost -----
    if backward:
        backward_rows = [
            ("Front line pressure [MPa]", lambda c, r: r.sizing.front.line_pressure),
            ("Rear line pressure [MPa]", lambda c, r: r.sizing.rear.line_pressure),
            ("Front clamp force [N]", lambda c, r: r.sizing.front.clamp_force),
            ("Rear clamp force [N]", lambda c, r: r.sizing.rear.clamp_force),
            ("Pedal force required, front [N]", lambda c, r: r.hydraulics.bar_force_front),
            ("Pedal force delivered [N]", lambda c, r: r.hydraulics.pedal_force),
            ("Effective MC stroke [mm]", lambda c, r: r.pedal_travel.effective_stroke),
            ("Pedal travel [mm]", lambda c, r: r.pedal_travel.pedal_travel),
        ]
        _compare_outputs_block(story, "Backward outputs (design calc)", backward_rows, names, configs,
                               solved, col_widths, st)

    # ---- Forward (performance simulation) outputs, same green/red shading --------------------
    if forward and all(getattr(r, "forward", None) is not None for r in solved):
        forward_rows = [
            ("Actual deceleration [g]", lambda c, r: r.forward.actual_decel_g),
            ("Front grip utilisation [%]", lambda c, r: r.forward.front_utilization * 100.0),
            ("Rear grip utilisation [%]", lambda c, r: r.forward.rear_utilization * 100.0),
            ("Front line pressure produced [MPa]", lambda c, r: r.forward.line_pressure_front),
            ("Rear line pressure produced [MPa]", lambda c, r: r.forward.line_pressure_rear),
            ("Total stopping force [N]", lambda c, r: r.forward.stopping_force),
        ]
        _compare_outputs_block(story, "Forward outputs (performance sim)", forward_rows, names, configs,
                               solved, col_widths, st)

        # Lock-up per axle — coloured (red = the axle skids at the design pedal force).
        story.append(Paragraph("Lock-up at design pedal force", st["block"]))
        lock_rows = [[_P("Axle", st, "cell_b")] + [_P(nm, st, "cell_b") for nm in names]]
        lock_extra: list = []
        for i, (axle, attr) in enumerate((("Front", "front_locked"), ("Rear", "rear_locked")), start=1):
            row = [_P(axle, st, "cell")]
            for j, r in enumerate(solved):
                locked = getattr(r.forward, attr)
                row.append(_P(f"<b>{'LOCKS UP' if locked else 'ok'}</b>", st, "cell"))
                lock_extra.append(("TEXTCOLOR", (1 + j, i), (1 + j, i), _FAIL if locked else _PASS))
                lock_extra.append(("BACKGROUND", (1 + j, i), (1 + j, i), _FAIL_BG if locked else _PASS_BG))
                lock_extra.append(("ALIGN", (1 + j, i), (1 + j, i), "CENTER"))
            lock_rows.append(row)
        story.append(_table(lock_rows, col_widths=col_widths, header=True, extra_style=lock_extra))

    # ---- Requirements met row (colour-coded yes/no) ----------------------------------------
    story.append(Paragraph("Verdict", st["block"]))
    oks = [r.ok for r in solved]
    rows = [[_P("All requirements met", st, "cell_b")]]
    extra = []
    for j, ok in enumerate(oks):
        rows[0].append(_P(f"<b>{'yes' if ok else 'no'}</b>", st, "cell"))
        extra.append(("TEXTCOLOR", (1 + j, 0), (1 + j, 0), _PASS if ok else _FAIL))
        extra.append(("BACKGROUND", (1 + j, 0), (1 + j, 0), _PASS_BG if ok else _FAIL_BG))
        extra.append(("ALIGN", (1 + j, 0), (1 + j, 0), "CENTER"))
    story.append(_table(rows, col_widths=col_widths, header=False, extra_style=extra))


def _optimization_section(story: list, result, st, sec: _Sections) -> None:
    designs = getattr(result, "designs", None)
    if not designs:
        return
    sec.heading(story, "Optimization Summary", st,
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
        rows.append([v.label, _num(best.evaluation.values[v.path], 3), _unit_text(v.unit)])
    story.append(_table(rows, col_widths=[_CONTENT_W - 65 * mm, 40 * mm, 25 * mm], align_right_from=1))


def _validation_section(story: list, results: BrakeResults, st, sec: _Sections) -> None:
    if not results.messages:
        return
    sec.heading(story, "Validation Notes", st)
    tags = {"error": (_FAIL, "ERROR"), "warning": (_WARN, "WARNING"), "info": (_GREY, "INFO")}
    msgs = []
    for msg in results.messages:
        color, tag = tags.get(msg.level, (_GREY, msg.level.upper()))
        msgs.append(Paragraph(
            f'<font color="#{color.hexval()[2:]}"><b>[{tag}]</b></font> {msg.message}', st["body"]))
    story.append(KeepTogether(msgs))  # keep the notes together so a line can't orphan onto a new page


# =============================================================================================
# Document template — running header/footer + clickable bookmarks + TOC
# =============================================================================================
class _ReportDoc(BaseDocTemplate):
    """Cover page has no furniture; body pages get a header + footer. Section headings register
    TOC entries and clickable PDF bookmarks."""

    def __init__(self, filename, *, report_title: str, car_name: str, **kw):
        super().__init__(filename, **kw)
        self.report_title = report_title
        self.car_name = car_name
        frame = Frame(_MARGIN, _MARGIN, _CONTENT_W, _PAGE_H - 2 * _MARGIN, id="main")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame], onPage=self._blank),
            PageTemplate(id="body", frames=[frame], onPage=self._furniture),
        ])
        self._bookmark_seq = 0

    def beforeDocument(self) -> None:
        # multiBuild runs several passes; reset the bookmark counter each pass so the TOC entry keys
        # are identical across passes (otherwise the index never converges).
        self._bookmark_seq = 0

    def _blank(self, canvas, doc) -> None:
        pass

    def _furniture(self, canvas, doc) -> None:
        canvas.saveState()
        # Running header
        canvas.setFont(_FONT, 7.5)
        canvas.setFillColor(_FAINT)
        canvas.drawString(_MARGIN, _PAGE_H - 12 * mm, self.report_title)
        canvas.drawRightString(_PAGE_W - _MARGIN, _PAGE_H - 12 * mm, self.car_name)
        canvas.setStrokeColor(_RULE)
        canvas.setLineWidth(0.4)
        canvas.line(_MARGIN, _PAGE_H - 13.5 * mm, _PAGE_W - _MARGIN, _PAGE_H - 13.5 * mm)
        # Footer
        y = 12 * mm
        canvas.line(_MARGIN, y + 3 * mm, _PAGE_W - _MARGIN, y + 3 * mm)
        canvas.setFillColor(_GREY)
        canvas.drawString(_MARGIN, y, "Brake Design Studio")
        canvas.drawRightString(_PAGE_W - _MARGIN, y, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name == "SectionTitle":
            text = flowable.getPlainText()
            self._bookmark_seq += 1
            key = f"sec-{self._bookmark_seq}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


def _toc(st) -> TableOfContents:
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc1", fontName=_FONT, fontSize=10.5, leading=20, textColor=_INK)]
    return toc


# =============================================================================================
# Entry points
# =============================================================================================
def build_report(config: VehicleConfig, results: BrakeResults, path: str | Path,
                 options: ReportOptions | None = None, engine: BrakeEngine | None = None) -> Path:
    """Write a PDF report for ``config``/``results`` to ``path`` and return the path.

    ``options`` selects which sections appear and supplies cover metadata; ``None`` yields the
    default single-car report (cover + design + performance + validation)."""
    path = Path(path)
    options = options or ReportOptions()
    engine = engine or BrakeEngine()
    st = _styles()
    sec = _Sections()

    doc = _ReportDoc(
        str(path), report_title=options.title, car_name=config.name,
        pagesize=A4, title=options.title, author=options.author or "Brake Design Studio",
        topMargin=_MARGIN, bottomMargin=_MARGIN, leftMargin=_MARGIN, rightMargin=_MARGIN,
    )

    story: list = []
    _cover(story, config, results, options, st)

    # Decide whether a TOC is worth showing (more than one body section).
    section_count = sum([
        options.include_design,
        options.include_forward and getattr(results, "forward", None) is not None,
        options.include_thermal and getattr(results, "thermal", None) is not None,
        options.include_compare and len([c for c in options.compare_configs if c is not None]) >= 2,
        options.include_optimization and options.optimization_result is not None,
        options.include_validation and bool(results.messages),
    ])

    story.append(NextPageTemplate("body"))
    story.append(PageBreak())
    if options.include_toc and section_count >= 2:
        story.append(Paragraph("Contents", st["plain_title"]))
        story.append(_HRule(0.9, _INK, pad_before=1, pad_after=6))
        story.append(_toc(st))
        story.append(PageBreak())

    if options.include_design:
        _design_section(story, config, results, st, sec, detail=options.detail)
    if options.include_forward:
        _forward_section(story, config, results, st, sec, detail=options.detail)
    if options.include_thermal:
        _thermal_section(story, config, results, st, sec)
    if options.include_compare and options.compare_configs:
        _compare_section(story, options.compare_configs, engine, st, sec,
                         backward=options.compare_backward, forward=options.compare_forward)
    if options.include_optimization and options.optimization_result is not None:
        _optimization_section(story, options.optimization_result, st, sec)
    if options.include_validation:
        _validation_section(story, results, st, sec)

    # Drop any trailing spacers so the document can't spill onto an empty final page.
    while story and isinstance(story[-1], Spacer):
        story.pop()

    # multiBuild resolves TOC page numbers over repeated passes.
    doc.multiBuild(story)
    return path


def build_report_for_config(config: VehicleConfig, path: str | Path, engine: BrakeEngine | None = None,
                            options: ReportOptions | None = None) -> Path:
    """Convenience: solve ``config`` and write its report."""
    engine = engine or BrakeEngine()
    return build_report(config, engine.solve(config), path, options=options, engine=engine)
