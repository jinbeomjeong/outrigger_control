"""Readers of ``04_scripts/01_dynamics/leg_extension_peaks.py`` on small temporary JSON files.

``load_crawler_handover_window`` (quasi-static first touch -> crawler off, cross-checked against
reference.json) and ``load_dynamic_deviation`` (damped 3-DoF - quasi-static, cross-checked
against the leg zeta 0.03 case) replace REXOME33 constants of ``run_mast_bending_check.py``.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))

import leg_extension_peaks as lep  # noqa: E402

LAYOUT_D = lep.REFERENCE_LAYOUT_D

LOADS: dict[str, Any] = {
    "key_values": {
        "events_s": {
            "touch_FL": 16.29571,
            "touch_FR": 16.2944,
            "touch_RL": 16.41019,
            "touch_RR": 16.40991,
            "crawler_off": 16.84716,
        }
    },
    "validation": {
        "quasi_static_check (damped 3-DoF)": {
            "max_abs_diff_pad_N (FL, FR, RL, RR)": [26000.0, 26010.0, 22590.0, 23070.0],
            "max_abs_diff_pad_N_at_s": 16.493,
        },
        "quasi_static_check_leg_zeta_sensitivity": {
            "crawler_zeta": 0.05,
            "cases": {
                "zeta_leg_0.03": {"max_abs_diff_vs_quasi_static_N": 26010.0},
                # the zeta 0.1 value that looks like the old 23.2 kN constant
                "zeta_leg_0.1": {"max_abs_diff_vs_quasi_static_N": 23220.0},
            },
        },
    },
}

REFERENCE: dict[str, Any] = {
    "lift_V4_compliant_crawler": {
        "layouts": {
            LAYOUT_D: {
                "quasi_static_events_s": {
                    "first_touch_leg": "FR",
                    "first_touch_s": 16.294,
                    "crawler_fully_off_s": 16.847,
                }
            }
        }
    }
}


def _write(tmp_path: Path, name: str, tree: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(tree), encoding="utf-8")
    return path


def _files(tmp_path: Path, loads: dict[str, Any] | None = None,
           reference: dict[str, Any] | None = None) -> tuple[Path, Path]:
    return (_write(tmp_path, "loads.json", loads if loads is not None else LOADS),
            _write(tmp_path, "reference.json", reference if reference is not None else REFERENCE))


def _ref_events(tree: dict[str, Any]) -> dict[str, Any]:
    return tree["lift_V4_compliant_crawler"]["layouts"][LAYOUT_D]["quasi_static_events_s"]


# ------------------------------------------------------------------ crawler hand-over window
def test_handover_window_reads_quasi_static_events(tmp_path):
    loads, ref = _files(tmp_path)
    window = lep.load_crawler_handover_window(loads, ref)
    assert window.first_touch_leg == "FR"
    assert window.first_touch_s == pytest.approx(16.2944)
    assert window.crawler_off_s == pytest.approx(16.84716)
    assert window.duration_s == pytest.approx(0.55276, abs=1e-9)
    assert window.source["reference_check_max_abs_diff_s"] == pytest.approx(4e-4, abs=1e-9)
    assert window.source["definition"] == lep.HANDOVER_DEFINITION
    assert "0.534" in window.source["replaces"]
    assert len(window.source["leg_extension_loads"]["sha256"]) == 64
    assert len(window.source["reference"]["sha256"]) == 64


def test_handover_window_missing_key_raises(tmp_path):
    tree = copy.deepcopy(LOADS)
    del tree["key_values"]["events_s"]["crawler_off"]
    loads, ref = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="crawler_off"):
        lep.load_crawler_handover_window(loads, ref)


def test_handover_window_missing_reference_layout_raises(tmp_path):
    tree = copy.deepcopy(REFERENCE)
    layouts = tree["lift_V4_compliant_crawler"]["layouts"]
    layouts["D rollers"] = layouts.pop(LAYOUT_D)  # a near name must not match
    loads, ref = _files(tmp_path, reference=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="not found"):
        lep.load_crawler_handover_window(loads, ref)


def test_handover_window_missing_file_raises(tmp_path):
    _, ref = _files(tmp_path)
    with pytest.raises(lep.LegExtensionLoadsError, match="not found"):
        lep.load_crawler_handover_window(tmp_path / "absent.json", ref)


@pytest.mark.parametrize("bad_value", ["16.29", True, None])
def test_handover_window_non_number_raises(tmp_path, bad_value):
    tree = copy.deepcopy(LOADS)
    tree["key_values"]["events_s"]["touch_RL"] = bad_value
    loads, ref = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="not a number"):
        lep.load_crawler_handover_window(loads, ref)


def test_handover_window_non_positive_duration_raises(tmp_path):
    tree = copy.deepcopy(LOADS)
    tree["key_values"]["events_s"]["crawler_off"] = 16.2944
    loads, ref = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="not after the first touch"):
        lep.load_crawler_handover_window(loads, ref)


@pytest.mark.parametrize("field", ["first_touch_s", "crawler_fully_off_s"])
def test_handover_window_reference_mismatch_raises(tmp_path, field):
    tree = copy.deepcopy(REFERENCE)
    _ref_events(tree)[field] += 2.0e-3
    loads, ref = _files(tmp_path, reference=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="differs from"):
        lep.load_crawler_handover_window(loads, ref)


def test_handover_window_other_first_leg_far_apart_raises(tmp_path):
    tree = copy.deepcopy(REFERENCE)
    _ref_events(tree)["first_touch_leg"] = "RR"  # RR touches 115 ms after FR
    loads, ref = _files(tmp_path, reference=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="first touch leg"):
        lep.load_crawler_handover_window(loads, ref)


def test_handover_window_other_first_leg_near_tie_warns(tmp_path):
    loads_tree = copy.deepcopy(LOADS)
    loads_tree["key_values"]["events_s"]["touch_FL"] = 16.2950  # 0.6 ms after FR
    ref_tree = copy.deepcopy(REFERENCE)
    _ref_events(ref_tree)["first_touch_leg"] = "FL"
    loads, ref = _files(tmp_path, loads=loads_tree, reference=ref_tree)
    with pytest.warns(UserWarning, match="near tie"):
        window = lep.load_crawler_handover_window(loads, ref)
    assert window.first_touch_leg == "FR"


# ------------------------------------------------------------------ dynamic deviation
def test_dynamic_deviation_reads_nominal_zeta(tmp_path):
    loads, _ = _files(tmp_path)
    deviation = lep.load_dynamic_deviation(loads)
    assert deviation.max_N == 26010.0
    assert deviation.max_leg == "FR"
    assert deviation.per_leg_N == (26000.0, 26010.0, 22590.0, 23070.0)
    assert deviation.at_s == pytest.approx(16.493)
    assert deviation.source["quantity"] == lep.DEVIATION_QUANTITY
    assert deviation.source["cross_check_rel_diff"] == 0.0


def test_dynamic_deviation_missing_key_raises(tmp_path):
    tree = copy.deepcopy(LOADS)
    del tree["validation"]["quasi_static_check (damped 3-DoF)"]["max_abs_diff_pad_N_at_s"]
    loads, _ = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="not found"):
        lep.load_dynamic_deviation(loads)


@pytest.mark.parametrize("bad_list", [[26000.0, "x", 1.0, 2.0], [26000.0, 26010.0, 1.0],
                                      [1.0, False, 2.0, 3.0], "26010"])
def test_dynamic_deviation_non_number_list_raises(tmp_path, bad_list):
    tree = copy.deepcopy(LOADS)
    tree["validation"]["quasi_static_check (damped 3-DoF)"][lep.DEVIATION_KEY] = bad_list
    loads, _ = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError):
        lep.load_dynamic_deviation(loads)


def test_dynamic_deviation_zeta_case_mismatch_raises(tmp_path):
    tree = copy.deepcopy(LOADS)
    case = tree["validation"]["quasi_static_check_leg_zeta_sensitivity"]["cases"]["zeta_leg_0.03"]
    case["max_abs_diff_vs_quasi_static_N"] = 26010.0 * (1 + 1e-5)
    loads, _ = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="differs from"):
        lep.load_dynamic_deviation(loads)


def test_dynamic_deviation_other_crawler_zeta_raises(tmp_path):
    tree = copy.deepcopy(LOADS)
    tree["validation"]["quasi_static_check_leg_zeta_sensitivity"]["crawler_zeta"] = 0.2
    loads, _ = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="crawler_zeta"):
        lep.load_dynamic_deviation(loads)


def test_dynamic_deviation_does_not_read_zeta_0_1(tmp_path):
    """Without the zeta 0.03 case the reader stops; it must not fall back to zeta 0.1."""
    tree = copy.deepcopy(LOADS)
    del tree["validation"]["quasi_static_check_leg_zeta_sensitivity"]["cases"]["zeta_leg_0.03"]
    loads, _ = _files(tmp_path, loads=tree)
    with pytest.raises(lep.LegExtensionLoadsError, match="zeta_leg_0.03"):
        lep.load_dynamic_deviation(loads)
