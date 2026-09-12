"""RA-1.2E RC2 — Sync-page slider label/unit layout tests.

Pins the RC2 UI polish: the slider unit is an explicit create_slider_row
parameter (the old "does the label contain ms" heuristic is gone), the
offset label is short in both locales, and all three Sync sliders start
at the same horizontal position in zh_CN and en_US (fixed-width labels).
"""
import inspect
import json
from pathlib import Path

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication

import ui_main

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

EXPECTED = {
    "zh_CN": {
        "orig": "原声(敲击声): 120%",
        "music": "纯净音乐: 60%",
        "offset": "手动微调: 0 ms",
        "offset_min": "手动微调: -500 ms",
        "orig_max": "原声(敲击声): 200%",
    },
    "en_US": {
        "orig": "Original Vol: 120%",
        "music": "Music Vol: 60%",
        "offset": "Manual fine-adjust: 0 ms",
        "offset_min": "Manual fine-adjust: -500 ms",
        "orig_max": "Original Vol: 200%",
    },
}


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def build_sync_iface(qapp, monkeypatch, lang):
    monkeypatch.setattr(ui_main, "i18n", ui_main.I18nManager(lang))
    interface = ui_main.SyncInterface(None)
    interface.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    interface.resize(900, 700)
    interface.show()
    qapp.processEvents()
    return interface


def test_offset_label_is_short_and_unit_free_in_both_locales():
    zh = json.loads((LOCALES_DIR / "zh_CN.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en_US.json").read_text(encoding="utf-8"))
    assert zh["lbl_offset"] == "手动微调"
    assert en["lbl_offset"] == "Manual fine-adjust"
    # The unit must live in the explicit unit parameter, never in the label.
    assert "ms" not in zh["lbl_offset"].lower()
    assert "ms" not in en["lbl_offset"].lower()


def test_slider_unit_is_supplied_explicitly_not_inferred_from_text():
    params = inspect.signature(ui_main.SyncInterface.create_slider_row).parameters
    assert "unit" in params
    assert params["unit"].default == "%"


@pytest.mark.parametrize("lang", ["zh_CN", "en_US"])
def test_slider_labels_units_and_shared_start_x(qapp, monkeypatch, lang):
    expected = EXPECTED[lang]
    interface = build_sync_iface(qapp, monkeypatch, lang)
    try:
        labels = (interface.orig_lbl, interface.music_lbl, interface.offset_lbl)
        sliders = (interface.orig_slider, interface.music_slider, interface.offset_slider)

        assert interface.orig_lbl.text() == expected["orig"]
        assert interface.music_lbl.text() == expected["music"]
        assert interface.offset_lbl.text() == expected["offset"]

        # Fixed label width -> every slider starts at the same x.
        assert {lbl.width() for lbl in labels} == {ui_main.SLIDER_LABEL_WIDTH}
        start_xs = {s.mapTo(interface, QPoint(0, 0)).x() for s in sliders}
        assert len(start_xs) == 1

        # Offset semantics preserved: -500..500 ms, default 0.
        offset = interface.offset_slider
        assert (offset.minimum(), offset.maximum(), offset.value()) == (-500, 500, 0)

        # Live text keeps the explicit unit.
        offset.setValue(-500)
        interface.orig_slider.setValue(200)
        qapp.processEvents()
        assert interface.offset_lbl.text() == expected["offset_min"]
        assert interface.orig_lbl.text() == expected["orig_max"]
    finally:
        interface.close()
