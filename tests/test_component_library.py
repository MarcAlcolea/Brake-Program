"""Sharing, validation, identity and GUI integration for custom components."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from brakelab import reference_configs as rc
from brakelab.app.controller import ProjectController
from brakelab.app.panels.component_manager import ComponentEditor, ComponentManager
from brakelab.app.panels.components_panel import ComponentsPanel
from brakelab.app.panels.optimization_tab import OptimizationTab
from brakelab.app.panels.config_bar import _config_equal
from brakelab.components.library import (
    ComponentLibrary, builtins, component_from_dict, load_component, new_component, save_component,
)
from brakelab.persistence import ConfigLibrary, config_from_dict, config_to_dict, load_config, save_config


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller(app, tmp_path):
    return ProjectController(rc.outboarded_x2(), ComponentLibrary(tmp_path / "components"))


def pad(name="Test pad", mu=0.37):
    return new_component("pad", name, {"friction_coefficient": mu}, "Measured on test rig")


@pytest.mark.parametrize("kind,values", [
    ("pad", {"friction_coefficient": 0.35}),
    ("caliper", {"piston_area_mm2": 700, "n_pistons": 4}),
    ("master_cylinder", {"bore_mm": 18, "stroke_mm": 28, "series": "Test series"}),
])
def test_export_import_and_restart(tmp_path, kind, values):
    original = new_component(kind, "Team part", values, "Test note")
    first = ComponentLibrary(tmp_path / "first")
    first.save(original)
    exported = tmp_path / "shared.component.json"
    save_component(original, exported)
    second = ComponentLibrary(tmp_path / "second")
    second.save(load_component(exported))
    assert original in ComponentLibrary(second.directory).all(kind)
    assert second.save(original) == original  # repeat import is idempotent
    assert len(list(second.directory.glob("*.json"))) == 1


def test_purple_is_builtin_and_release_download_matches(tmp_path):
    purple = next(p for p in ComponentLibrary(tmp_path).all("pad") if "PURPLE" in p.name)
    assert purple.values["friction_coefficient"] == 0.35
    assert "pessimistic" in purple.note
    asset = Path(__file__).resolve().parents[1] / "packaging/components/Wilwood_PURPLE.component.json"
    assert load_component(asset) == purple


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 0, 1.5, "0.35", True])
def test_invalid_friction_is_rejected(value):
    with pytest.raises(ValueError):
        new_component("pad", "Bad pad", {"friction_coefficient": value})


@pytest.mark.parametrize("change", [
    {"format": "car.setup"}, {"schema_version": 999}, {"kind": "unknown"},
    {"id": "../../outside"}, {"name": "  "}, {"name": "Custom"},
    {"values": {"friction_coefficient": 0.3, "extra": 1}}, {"note": []},
])
def test_invalid_files_are_rejected(change):
    data = pad().to_dict()
    data.update(change)
    with pytest.raises(ValueError):
        component_from_dict(data)


def test_caliper_requires_integer_count():
    with pytest.raises(ValueError):
        new_component("caliper", "Bad count", {"piston_area_mm2": 700, "n_pistons": 2.5})


def test_conflicts_protect_defaults_and_rename(tmp_path):
    library = ComponentLibrary(tmp_path)
    first, second = pad("First"), pad("Second", 0.4)
    library.save(first)
    library.save(second)
    with pytest.raises(ValueError):
        library.save(pad("first", 0.5))
    updated = library.save(pad("FIRST", 0.5), replace=True)
    assert updated.id == first.id
    assert first not in library.all()
    with pytest.raises(ValueError):
        library.save(replace(updated, name="Second"), replace=True)
    # Conflicts must also be caught when the target name sorts before the edited part.
    with pytest.raises(ValueError):
        library.save(replace(second, name="FIRST"), replace=True)
    builtin = next(p for p in builtins() if p.kind == "pad")
    with pytest.raises(ValueError):
        library.save(replace(builtin, values={"friction_coefficient": 0.4}), replace=True)
    with pytest.raises(ValueError):
        library.delete(builtin)
    library.delete(updated)
    assert updated not in library.all()


def test_invalid_library_file_does_not_hide_valid_parts(tmp_path):
    library = ComponentLibrary(tmp_path)
    original = pad("../A name with slashes")
    library.save(original)
    (tmp_path / "broken.json").write_text("{}", encoding="utf-8")
    assert original in library.all()
    assert (tmp_path / f"{original.id}.component.json").exists()


def test_same_mu_retains_identity_and_setup_is_portable(controller, tmp_path):
    first, second = pad("First", 0.48), pad("Second", 0.48)
    controller.component_library.save(first)
    controller.component_library.save(second)
    controller.select_component("pad", second)
    path = tmp_path / "car.json"
    save_config(controller.config, path)
    recipient = ProjectController(load_config(path), ComponentLibrary(tmp_path / "empty"))
    assert recipient.selected_component("pad") == second
    assert recipient.config.pad.friction_coefficient == 0.48
    panel = ComponentsPanel(recipient)
    assert panel._combos["pad"].currentText() == "Second (saved values)"


def test_edit_or_delete_library_does_not_mutate_car(controller):
    original = pad()
    controller.component_library.save(original)
    controller.select_component("pad", original)
    panel = ComponentsPanel(controller)
    edited = replace(original, values={"friction_coefficient": 0.5})
    controller.component_library.save(edited, replace=True)
    controller.componentsChanged.emit()
    assert controller.selected_component("pad") == original
    assert panel._combos["pad"].currentText().endswith("(saved values)")
    controller.component_library.delete(edited)
    controller.componentsChanged.emit()
    assert controller.config.pad.friction_coefficient == 0.37
    assert controller.selected_component("pad") == original


def test_manual_edit_clears_selection_even_if_matching_another_pad(controller):
    controller.select_component("pad", pad())
    controller.set_value("pad.friction_coefficient", 0.48)
    assert controller.selected_component("pad") is None
    assert controller.config.component_selections["pad"] is None
    restored = ProjectController(config_from_dict(config_to_dict(controller.config)), controller.component_library)
    assert restored.selected_component("pad") is None


def test_old_setups_load_and_gain_unambiguous_identity(controller):
    data = config_to_dict(rc.outboarded_x2())
    data.pop("component_selections")
    data["schema_version"] = 1
    old = ProjectController(config_from_dict(data), controller.component_library)
    assert "BP-28" in old.selected_component("pad").name
    assert old.config.component_selections["pad"]["name"].endswith("BP-28")
    controller.replace_config(config_from_dict(data))
    assert controller.config.component_selections["pad"]["name"].endswith("BP-28")
    assert _config_equal(config_from_dict(data), controller.config)
    # Selecting another named pad with the same numbers still counts as an edit.
    controller.select_component("pad", pad("Different identity", 0.48))
    assert not _config_equal(config_from_dict(data), controller.config)


def test_apply_all_component_types_and_both_panels_refresh(controller):
    first, second = ComponentsPanel(controller), ComponentsPanel(controller)
    custom = pad()
    controller.component_library.save(custom)
    controller.componentsChanged.emit()
    combo = first._combos["pad"]
    combo.setCurrentIndex(combo.findText(custom.name))
    combo.activated.emit(combo.currentIndex())
    assert second._combos["pad"].currentText() == custom.name
    assert controller.config.pad.friction_coefficient == 0.37
    cal = new_component("caliper", "Four piston", {"piston_area_mm2": 700, "n_pistons": 4})
    controller.select_component("caliper", cal)
    assert controller.config.caliper.one_side_area == 1400
    mc = new_component("master_cylinder", "Test MC", {"bore_mm": 18, "stroke_mm": 28, "series": "Test"})
    controller.select_component("front_mc", mc)
    assert controller.config.hydraulics.max_mc_stroke == 28
    rear = replace(mc, values={"bore_mm": 20, "stroke_mm": 30, "series": "Test"})
    controller.select_component("rear_mc", rear)
    assert controller.config.hydraulics.mc_bore_rear == 20
    assert controller.config.hydraulics.max_mc_stroke == 28


def test_editor_shows_fields_and_rejects_bad_input(app):
    editor = ComponentEditor(kind="pad")
    editor._name.setText("New pad")
    editor._fields["friction_coefficient"].setText("nan")
    editor._save()
    assert editor.result() != QDialog.Accepted
    assert editor._error.text()
    editor._fields["friction_coefficient"].setText("0.35")
    editor._save()
    assert editor.result() == QDialog.Accepted
    assert editor.component.values == {"friction_coefficient": 0.35}
    editor._kind.setCurrentIndex(editor._kind.findData("master_cylinder"))
    assert set(editor._fields) == {"bore_mm", "stroke_mm", "series"}


def test_manager_import_export_and_protection(controller, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming.component.json"
    part = pad()
    save_component(part, incoming)
    manager = ComponentManager(controller)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (str(incoming), ""))
    manager._import()
    assert manager._part() == part
    assert manager._buttons["Edit…"].isEnabled()
    outgoing = tmp_path / "outgoing.component.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(outgoing), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a: QMessageBox.Ok)
    manager._export()
    assert load_component(outgoing) == part
    builtin = builtins()[0]
    manager._reload(builtin.id)
    assert not manager._buttons["Edit…"].isEnabled()
    assert not manager._buttons["Delete"].isEnabled()
    assert manager._buttons["Export…"].isEnabled()


def test_optimizer_sees_new_series_without_restart(controller, tmp_path):
    tab = OptimizationTab(controller, ConfigLibrary(tmp_path / "configs"))
    mc = new_component("master_cylinder", "Test MC", {"bore_mm": 18, "stroke_mm": 28, "series": "New series"})
    controller.component_library.save(mc)
    controller.componentsChanged.emit()
    row = next(r for r in tab._var_rows if r["path"] == "hydraulics.mc_bore_front")
    assert row["source"].findText("New series") >= 0
    row["source"].setCurrentText("New series")
    problem = tab._collect()
    variable = next(v for v in problem.variables if v.path == "hydraulics.mc_bore_front")
    assert variable.choices == [18]
