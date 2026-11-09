"""LAS-b K1 forced-block variant ``04_scripts/02_chrono/k1_forced_block.py``.

Rules ``06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md`` 2.3 and 9.3 (tests 1-5). No
simulation: the LOC is forced through ``_confirm_liftoff`` on synthetic state
(``test_c2_k1.py`` helpers), test 5 runs the 10 Hz bench of ``test_c2_r8d1.py``.

Run (Chrono-dev or dynamics-dev, PowerShell, project root):
  $env:PYTHONDONTWRITEBYTECODE = '1'
  <python> -I -m pytest -q -p no:cacheprovider 05_tests/unit/test_k1_forced_block.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from test_c2_k1 import SOIL_MODE_START_S, k1_config, loc_at  # same test folder
from test_c2_p37r4 import FLAT_TARGET_M, TARGET_M, events_named  # same test folder
from test_c2_r8d1 import TOUCH_HOLD_SAMPLES, Bench, operating_strokes  # same test folder

from outrigger_sim.control.c2 import (
    FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT,
    C2Controller,
    C2Geometry,
    C2Phase,
)
from outrigger_sim.params import load_params

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "04_scripts" / "02_chrono" / "k1_forced_block.py"
_SPEC = importlib.util.spec_from_file_location("k1_forced_block", MODULE_PATH)
forced_block = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = forced_block  # dataclasses look the module up while the class is built
_SPEC.loader.exec_module(forced_block)
Forced = forced_block.K1ForcedBlockC2Controller

PLATEAU_AFTER_SOIL_S = SOIL_MODE_START_S + 0.1
"""``n_P`` 31 against ``n_S`` 30: the original rule does not block (dP = +1)."""
REVOKE_T_S = 4.0
RELOC_SOIL_MODE_START_S = 6.0
BENCH_STEPS = 30


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def json_meta(controller: C2Controller) -> dict:
    return json.loads(json.dumps(controller.meta()))


def decisions_of(controller: C2Controller) -> list[dict]:
    return json_meta(controller)["slope_clearance_margin"]["order_gate"]["decisions"]


def reloc(controller: C2Controller, geometry: C2Geometry, t_P_s: float) -> None:
    """Revocation, a new soil-mode start, then a second R4-evaluated LOC at ``t_P_s``."""
    controller._revoke_loc(REVOKE_T_S, 3000.0)
    loc_at(controller, geometry, t_P_s, soil_mode_start_s=RELOC_SOIL_MODE_START_S)


# --- 1 ------------------------------------------------------------------------------------------
def test_1_first_r4_loc_is_blocked(geometry) -> None:
    controller = Forced(geometry, k1_config(True))
    loc_at(controller, geometry, PLATEAU_AFTER_SOIL_S)
    (decision,) = decisions_of(controller)
    assert decision["dP"] == 1  # the original rule would apply R4c30 here
    assert decision["r4_due_without_gate"] is True
    assert decision["would_block"] is True and decision["applied"] is False
    assert controller._clearance_target_m() == pytest.approx(TARGET_M, abs=1e-15)
    skip_base = FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT.split(":", 1)[0]
    assert events_named(controller, skip_base) == [FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT]


# --- 2 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("reloc_t_P_s", "dP", "is_applied"),
    [
        (RELOC_SOIL_MODE_START_S + 3.0, 30, True),  # dP > 0: applied
        (RELOC_SOIL_MODE_START_S, 0, False),  # dP = 0: blocked
        (RELOC_SOIL_MODE_START_S - 0.1, -1, False),  # dP < 0: blocked
    ],
)
def test_2_later_calls_follow_the_original_rule(geometry, reloc_t_P_s, dP, is_applied) -> None:
    controller = Forced(geometry, k1_config(True))
    loc_at(controller, geometry, PLATEAU_AFTER_SOIL_S)
    reloc(controller, geometry, reloc_t_P_s)
    first, second = decisions_of(controller)
    assert (first["would_block"], first["applied"]) == (True, False)
    assert second["dP"] == dP
    assert (second["would_block"], second["applied"]) == (not is_applied, is_applied)
    expected_target_m = FLAT_TARGET_M if is_applied else TARGET_M
    assert controller._clearance_target_m() == pytest.approx(expected_target_m, abs=1e-15)


# --- 3 ------------------------------------------------------------------------------------------
def test_3_gate_off_config_is_refused(geometry) -> None:
    with pytest.raises(ValueError, match="order gate"):
        Forced(geometry, k1_config(False))
    with pytest.raises(ValueError, match="order gate"):
        Forced(geometry)  # class default config: gate off
    with pytest.raises(ValueError, match="order gate"):
        Forced.from_params(load_params())


# --- 4 ------------------------------------------------------------------------------------------
def test_4_forced_record_and_calls(geometry) -> None:
    controller = Forced(geometry, k1_config(True))
    assert json_meta(controller)["k1_forced_block"]["calls"] == []
    loc_at(controller, geometry, PLATEAU_AFTER_SOIL_S)
    reloc(controller, geometry, RELOC_SOIL_MODE_START_S)
    record = json_meta(controller)["k1_forced_block"]
    file_sha256 = hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest()
    assert record == {
        "mode": "first",
        "class": "k1_forced_block.K1ForcedBlockC2Controller",
        "module_sha256": file_sha256,
        "forced_t_loc_s": PLATEAU_AFTER_SOIL_S,
        "forced_n_loc": 31,
        "natural_blocked": False,
        "n_P": 31,
        "n_S": 30,
        "dP": 1,
        "calls": [
            {"t_s": PLATEAU_AFTER_SOIL_S, "forced": True, "result": True, "n_P": 31, "n_S": 30},
            {"t_s": RELOC_SOIL_MODE_START_S, "forced": False, "result": True, "n_P": 60, "n_S": 60},
        ],
    }
    assert forced_block.module_sha256() == file_sha256
    controller.reset()
    assert json_meta(controller)["k1_forced_block"]["calls"] == []


# --- 5 ------------------------------------------------------------------------------------------
def bench_run(geometry: C2Geometry, controller: C2Controller) -> tuple[np.ndarray, dict]:
    """Touch down and level on the synthetic bench (no LOC): outputs and the meta."""
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES + BENCH_STEPS):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    return np.array(bench.outputs), json_meta(controller)


def test_5_same_as_c2controller_before_the_forced_call(geometry) -> None:
    config = k1_config(True)
    plain_outputs, plain_meta = bench_run(geometry, C2Controller(geometry, config))
    forced_outputs, forced_meta = bench_run(geometry, Forced(geometry, config))
    np.testing.assert_array_equal(forced_outputs, plain_outputs)
    record = forced_meta.pop("k1_forced_block")
    assert record["calls"] == [] and record["forced_n_loc"] is None
    assert forced_meta == plain_meta
