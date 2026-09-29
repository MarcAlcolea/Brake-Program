"""Portable, versioned component files and a per-user library.

Built-in parts come from the Python catalog, so they also ship in frozen releases.
Custom parts use one JSON file per UUID; names never become filesystem paths.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from . import catalog
from ..core.attrpath import get_by_path
from ..persistence.library import app_data_dir

FORMAT = "brakelab.component"
VERSION = 1
KINDS = {"pad": "Brake pad", "caliper": "Caliper", "master_cylinder": "Master cylinder"}
# key, display label, minimum, maximum; units are explicit in the labels and file keys.
FIELDS = {
    "pad": [("friction_coefficient", "Friction coefficient (one pad)", 0.2, 0.8)],
    "caliper": [("piston_area_mm2", "Area of ONE piston (mm²)", 100, 2000),
                ("n_pistons", "Total number of pistons", 1, 8)],
    "master_cylinder": [("bore_mm", "Bore diameter (mm)", 10, 30),
                        ("stroke_mm", "Maximum stroke (mm)", 5, 60)],
}
SLOTS = {"pad": "pad", "caliper": "caliper", "front_mc": "master_cylinder",
         "rear_mc": "master_cylinder"}


@dataclass(frozen=True)
class Component:
    id: str
    kind: str
    name: str
    values: dict
    note: str = ""

    def to_dict(self) -> dict:
        return {"format": FORMAT, "schema_version": VERSION, **asdict(self)}


def component_from_dict(data: dict) -> Component:
    """Validate both imported files and user-entered parts before using any values."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("This is not a Brake Design Studio component file.")
    if type(data.get("schema_version")) is not int or data["schema_version"] != VERSION:
        raise ValueError("Unsupported component file version. Update Brake Design Studio.")
    try:
        identifier = str(UUID(data["id"]))
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid component identifier.") from exc
    kind = data.get("kind")
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError("Unknown component type.")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or name.strip().casefold() == "custom":
        raise ValueError("Enter a component name other than 'Custom'.")
    note = data.get("note", "")
    if not isinstance(note, str):
        raise ValueError("Component notes must be text.")
    values = data.get("values")
    keys = {key for key, *_ in FIELDS[kind]}
    if kind == "master_cylinder":
        keys.add("series")
    if not isinstance(values, dict) or set(values) != keys:
        raise ValueError("The component fields do not match its type.")
    for key, label, lo, hi in FIELDS[kind]:
        value = values[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f"{label} must be a finite number between {lo:g} and {hi:g}.")
        if key == "n_pistons" and value != int(value):
            raise ValueError("Number of pistons must be a whole number.")
    if kind == "master_cylinder" and (not isinstance(values["series"], str) or not values["series"].strip()):
        raise ValueError("Enter a master-cylinder series.")
    clean = dict(values)
    if kind == "caliper":
        clean["n_pistons"] = int(clean["n_pistons"])
    if kind == "master_cylinder":
        clean["series"] = clean["series"].strip()
    return Component(identifier, kind, name.strip(), clean, note)


def new_component(kind: str, name: str, values: dict, note: str = "", identifier: str | None = None) -> Component:
    return component_from_dict(Component(identifier or str(uuid4()), kind, name, values, note).to_dict())


def load_component(path: str | Path) -> Component:
    return component_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_component(component: Component, path: str | Path) -> None:
    component = component_from_dict(component.to_dict())
    Path(path).write_text(json.dumps(component.to_dict(), indent=2, allow_nan=False), encoding="utf-8")


def builtins() -> list[Component]:
    result = []
    for kind, parts in (("pad", catalog.BRAKE_PADS), ("caliper", catalog.CALIPERS),
                        ("master_cylinder", catalog.MASTER_CYLINDERS)):
        for part in parts:
            values = asdict(part)
            name, note = values.pop("name"), values.pop("note")
            identifier = str(uuid5(NAMESPACE_URL, f"brakelab/{kind}/{name}"))
            result.append(new_component(kind, name, values, note, identifier))
    return result


def applied_values(component: Component, slot: str) -> dict:
    if SLOTS.get(slot) != component.kind:
        raise ValueError("This component cannot be used in that position.")
    v = component.values
    if slot == "pad":
        return {"pad.friction_coefficient": v["friction_coefficient"]}
    if slot == "caliper":
        return {"caliper.piston_area": v["piston_area_mm2"], "caliper.n_pistons": v["n_pistons"]}
    # The existing model has ONE shared stroke limit. Front selection controls it;
    # rear selection fills its bore only, matching the existing app behaviour.
    if slot == "front_mc":
        return {"hydraulics.mc_bore_front": v["bore_mm"], "hydraulics.max_mc_stroke": v["stroke_mm"]}
    return {"hydraulics.mc_bore_rear": v["bore_mm"]}


def matches(component: Component, config, slot: str) -> bool:
    return all(math.isclose(get_by_path(config, path), value, rel_tol=1e-9, abs_tol=1e-9)
               for path, value in applied_values(component, slot).items())


def selected_component(config, slot: str) -> Component | None:
    """Resolve a snapshot, or infer an unambiguous built-in for an old setup."""
    selections = config.component_selections
    if slot in selections:
        snapshot = selections[slot]
        if snapshot is None:
            return None
        part = component_from_dict(snapshot)
        return part if matches(part, config, slot) else None
    candidates = [p for p in builtins() if p.kind == SLOTS[slot] and matches(p, config, slot)]
    return candidates[0] if len(candidates) == 1 else None


def current_values(config, slot: str) -> dict:
    if slot == "pad":
        return {"friction_coefficient": config.pad.friction_coefficient}
    if slot == "caliper":
        return {"piston_area_mm2": config.caliper.piston_area, "n_pistons": config.caliper.n_pistons}
    return {"bore_mm": config.hydraulics.mc_bore_front if slot == "front_mc" else config.hydraulics.mc_bore_rear,
            "stroke_mm": config.hydraulics.max_mc_stroke, "series": "Custom series"}


class ComponentLibrary:
    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory is not None else app_data_dir() / "components"

    def builtin_ids(self) -> set[str]:
        return {part.id for part in builtins()}

    def all(self, kind: str | None = None) -> list[Component]:
        parts = builtins()
        identifiers = {part.id for part in parts}
        for path in sorted(self.directory.glob("*.json")):
            try:
                part = load_component(path)
            except (ValueError, OSError):
                continue
            if part.id not in identifiers:
                parts.append(part)
                identifiers.add(part.id)
        return sorted((p for p in parts if kind is None or p.kind == kind), key=lambda p: (p.kind, p.name.casefold()))

    def conflict(self, component: Component) -> Component | None:
        parts = self.all()
        # Prefer identity; a rename to somebody else's name must never replace that other part.
        return next((p for p in parts if p.id == component.id), None) or next(
            (p for p in parts if p.kind == component.kind and p.name.casefold() == component.name.casefold()), None)

    def save(self, component: Component, replace: bool = False) -> Component:
        component = component_from_dict(component.to_dict())
        existing = self.conflict(component)
        for part in self.all(component.kind):
            if part.name.casefold() == component.name.casefold() and existing and part.id != existing.id:
                raise ValueError("Another component already uses this name. Choose a different name.")
        if existing and existing == component:
            return existing
        if existing:
            if existing.kind != component.kind:
                raise ValueError("An existing component identifier cannot change its type.")
            if existing.id in self.builtin_ids():
                raise ValueError("Built-in parts cannot be overwritten. Save a copy with a different name.")
            if not replace:
                raise ValueError("A component with this name or identifier already exists.")
            if component.id != existing.id:
                component = new_component(component.kind, component.name, component.values, component.note, existing.id)
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"{component.id}.component.json"
        temporary = target.with_suffix(".tmp")
        save_component(component, temporary)
        temporary.replace(target)
        return component

    def delete(self, component: Component) -> None:
        if component.id in self.builtin_ids():
            raise ValueError("Built-in parts cannot be deleted.")
        (self.directory / f"{str(UUID(component.id))}.component.json").unlink(missing_ok=True)

    def master_cylinder_series(self) -> list[str]:
        return sorted({p.values["series"] for p in self.all("master_cylinder")})

    def bores(self, series: str | None = None) -> list[float]:
        return sorted({p.values["bore_mm"] for p in self.all("master_cylinder")
                       if series is None or p.values["series"] == series})
