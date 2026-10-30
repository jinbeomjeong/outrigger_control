"""C2 P-S8-32 LOC window against a lifted re-approach (control spec 419.2 / 420.1 (3), user
decision 2026-10-29: LWa = "restart").

Synthetic 10 Hz benches of ``test_c2_p28.py``; a re-approach is stood for by an entry in
``_state.active_reapproaches`` (the rule reads its keys only). The harness comparison against
the LWa wrapper of ``s9_slope_fix_candidates.py`` runs one G6 case in a subprocess (slow).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_p28 import (  # same test folder
    level_bench,
    p28_config,
    plateau_sample,
    stroke_reading,
)
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control.c2 import (
    LOC_WINDOW_RESTART_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    LiftoffWindowReapproach,
    LiftoffWindowReapproachSettings,
    _RunState,
)
from outrigger_sim.params import LEG_ORDER, load_params

ROOT = Path(__file__).resolve().parents[2]
FL, FR, RL = (LEG_ORDER.index(name) for name in ("FL", "FR", "RL"))
BENCH_STEPS = 60
WRAPPER_CASE = "g6|G1+S1@FL|top|Fs4"
"""A G6 case LWa changed (LOC crawler load 71.5 kN -> 0, spec 419.6)."""
WRAPPER_RECORDS = ROOT / "06_analysis" / "02_control" / "s9" / "rev81" / "fix_g6_LW.json"
WRAPPER_SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "s9_slope_fix_candidates.py"
PRE_SWITCH_RUNNER = Path(__file__).with_name("pre_switch_preset_runner.py")
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The G6 harness needs dynamics-dev (numba, sympy), not the Chrono-dev test env."""
RE_APPROACH = object()
"""Stand-in for a ``_Reapproach`` run: the window rule reads the dictionary keys only."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def window_config(mode: LiftoffWindowReapproach) -> C2Config:
    return replace(p28_config(),
                   liftoff_window_reapproach=LiftoffWindowReapproachSettings(mode=mode))


def controller_with_window(geometry: C2Geometry, mode: LiftoffWindowReapproach) -> C2Controller:
    controller = C2Controller(geometry, window_config(mode))
    window = controller._soil_state().window
    window.append(plateau_sample(geometry, operating_strokes(geometry), t_s=4.9))
    return controller


def restart_events(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events
            if event.name.startswith(LOC_WINDOW_RESTART_EVENT)]


# --- settings ----------------------------------------------------------------------------------


def test_class_default_is_off_and_the_r8_preset_restarts() -> None:
    assert C2Config().liftoff_window_reapproach.mode is LiftoffWindowReapproach.OFF
    assert _RunState.loc_window_restart_count == 0  # class attribute (old pickles)
    for preset in (C2Config().with_10hz_d1(), C2Config().with_soil_response()):
        assert preset.liftoff_window_reapproach.mode is LiftoffWindowReapproach.RESTART
    assert LiftoffWindowReapproachSettings(mode="restart").mode is LiftoffWindowReapproach.RESTART
    with pytest.raises(ValueError):
        LiftoffWindowReapproachSettings(mode="exclude")  # LWb not adopted


# --- off path ----------------------------------------------------------------------------------


def test_off_ignores_an_active_reapproach(geometry) -> None:
    controller = controller_with_window(geometry, LiftoffWindowReapproach.OFF)
    controller._state.active_reapproaches[FR] = RE_APPROACH
    assert not controller._is_window_held_by_reapproach(5.0)
    assert len(controller._soil_state().window) == 1
    assert restart_events(controller) == []


def test_restart_without_a_reapproach_commands_as_off(geometry) -> None:
    """No re-approach on the bench: the preset (restart) and off command bit for bit alike."""
    outputs = []
    for mode in (LiftoffWindowReapproach.RESTART, LiftoffWindowReapproach.OFF):
        bench = level_bench(geometry, window_config(mode), operating_strokes(geometry))
        for _ in range(BENCH_STEPS):
            bench.step()
        assert bench.controller._state.loc_window_restart_count == 0
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


# --- restart -----------------------------------------------------------------------------------


def test_restart_clears_a_non_empty_window_once_per_window(geometry) -> None:
    controller = controller_with_window(geometry, LiftoffWindowReapproach.RESTART)
    controller._state.active_reapproaches.update({RL: RE_APPROACH, FL: RE_APPROACH})
    assert controller._is_window_held_by_reapproach(5.0)
    assert len(controller._soil_state().window) == 0
    assert restart_events(controller) == [f"{LOC_WINDOW_RESTART_EVENT}:FL,RL"]
    assert controller._is_window_held_by_reapproach(5.1)  # still held, window already empty
    assert len(restart_events(controller)) == 1
    meta = json.loads(json.dumps(controller.meta()))["liftoff_window_reapproach"]
    assert meta == {"mode": "restart", "restarts": 1}


def test_restart_adds_no_sample_while_held_and_resumes_after(geometry) -> None:
    """Through ``_update_liftoff_window``: a plateau period with a re-approach active adds no
    sample; the period after the re-approach ended starts a new window."""
    controller = C2Controller(geometry, window_config(LiftoffWindowReapproach.RESTART))
    controller._state.applied_output_m_s = np.full(4, 0.25 * geometry.max_speed_m_s)
    assert controller._is_plateau_period()
    reading_strokes = operating_strokes(geometry)
    controller._state.active_reapproaches[FR] = RE_APPROACH
    controller._update_liftoff_window(stroke_reading(5.0, reading_strokes, reading_strokes))
    assert len(controller._soil_state().window) == 0
    del controller._state.active_reapproaches[FR]
    controller._update_liftoff_window(stroke_reading(5.1, reading_strokes, reading_strokes))
    assert len(controller._soil_state().window) == 1
    assert restart_events(controller) == []  # the window was empty when it was held


def test_restart_does_nothing_after_the_loc(geometry) -> None:
    controller = controller_with_window(geometry, LiftoffWindowReapproach.RESTART)
    controller._soil_state().is_liftoff_confirmed = True
    controller._state.active_reapproaches[FR] = RE_APPROACH
    strokes = operating_strokes(geometry)
    controller._update_liftoff_window(stroke_reading(5.0, strokes, strokes))
    assert len(controller._soil_state().window) == 1
    assert restart_events(controller) == []


# --- wrapper hash ------------------------------------------------------------------------------


@pytest.mark.slow
def test_g6_case_matches_the_lwa_wrapper_hash(tmp_path) -> None:
    """The project preset now restarts the window: the harness's "current" controller of a
    G6 case LWa changed commands as the stored LWa wrapper record (spec 419.6)."""
    if not HARNESS_PYTHON.exists() or not WRAPPER_RECORDS.exists():
        pytest.skip("dynamics-dev or the rev. 81 LW records missing")
    records = json.loads(WRAPPER_RECORDS.read_text(encoding="utf-8"))["records"]
    by_candidate = {r["candidate"]: r["hash"] for r in records if r["id"] == WRAPPER_CASE}
    assert by_candidate["LWa"] != by_candidate["current"]
    out_path = tmp_path / "p32_wrapper_case.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1"}
    subprocess.run(  # the LWa records predate the spec 429.11 preset switch (SGS, R4 off)
        [str(HARNESS_PYTHON), "-I", str(PRE_SWITCH_RUNNER), str(WRAPPER_SCRIPT), "run",
         "--suite", "g6",
         "--candidates", "current", "--settle-hook", "p0", "--filter", WRAPPER_CASE,
         "--workers", "1", "--out", str(out_path)],
        cwd=ROOT, env=environment, check=True, capture_output=True, timeout=1800,
    )
    (record,) = json.loads(out_path.read_text(encoding="utf-8"))["records"]
    assert "error" not in record, record.get("error")
    assert record["hash"] == by_candidate["LWa"]
