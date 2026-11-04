"""C2 clips only its returned command to +-v_max (user decision 2026-11-04, decision_log 4).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` for the rule itself; the slow tests run stored
harness rows in dynamics-dev (``returned_clip_hash_runner.py``). Their hashes were saved before
this switch: the plant-clip digests of the design check are the same strings as the ``on`` values.
"""

from __future__ import annotations

import json
import os
import pickle
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    operating_strokes,
)

from outrigger_sim.control.c2 import C2Config, C2Controller, C2Geometry, C2Phase
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
HASH_RUNNER = Path(__file__).with_name("returned_clip_hash_runner.py")
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The harnesses need dynamics-dev (numba, sympy), not the Chrono-dev test env."""
STORED_FILES = ("finB2_harness.json", "finB2_p0.json")
STORED_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev85"
HARNESS_WORKERS = 4
HARNESS_TIMEOUT_S = 900
OVER_LIMIT_FRACTIONS = (0.0, 1.2, 1.5, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 0.9, 0.0)
"""Scripted fractions of ``v_max``: the increment limit makes them cross the limit stepwise."""
PERIODS_PAST_THE_SCRIPT = 6
ACTING_ROW_HASHES = {
    "S1": (
        "5f251876fc6adf41c2c9713c2e8e293bf7607dc78f53470729eb060b5a202c83",
        "6198f676af09c56ee58a0718c2b9f2d5d1b1d1b016044839f995db5cb57628b1",
    ),
    "S4": (
        "fddac2514e54eab5ac04203bec108c7bf5d6d324635a44b6653253a88964c488",
        "cfdc31de9b3c49782ec480c4da7dbbf352e0fe178b8c60c1b1ba1b710069f664",
    ),
    "S5": (
        "6dba5b4113b3636aa29893af318c9969b53608039816bc04fd24f9ca6f9358b0",
        "f1740d783739109540b4cf83e6f609d3de43c086e47197a41b3eea7dc6147968",
    ),
}
"""Case: (clip on = the plant-clip digest of the design check, clip off = stored finB2 row)."""
RESTING_ROW_IDS = {
    "R1": "base|rigid|0,0|top|Fs4|b1",
    "R4": "base|rigid|5.5,0|top|Fs4|b1",
    "S8": "H3|J1|B|top|roll_pos@k0.875",
}
"""Rows without a DSb75 hold: the switch must not move a bit, on or off."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def scripted_bench(geometry, monkeypatch, *, is_clipped: bool, fractions) -> Bench:
    """10 Hz bench in LEVEL whose ``_phase_command`` returns ``fractions * v_max``."""
    config = replace(bench_config(), clip_returned_command=is_clipped)
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    speeds = iter(np.asarray(fractions, float) * geometry.max_speed_m_s)
    zero = np.zeros(4)
    monkeypatch.setattr(bench.controller, "_phase_command", lambda _reading: next(speeds, zero))
    return bench


def internal_state(controller: C2Controller) -> dict[str, np.ndarray]:
    state = controller._state
    return {
        "applied_output_m_s": np.array(state.applied_output_m_s),
        "previous_output_m_s": np.array(state.previous_output_m_s),
        "last_nonzero_output_m_s": np.array(state.last_nonzero_output_m_s),
        "output_queue": np.array(list(state.output_queue)),
    }


def run_pair(geometry, monkeypatch, leg_fractions) -> tuple[list, list, list, list]:
    """The same script with the clip off and on: outputs and internal states of each period."""
    fractions = [fraction * np.asarray(leg_fractions, float) for fraction in OVER_LIMIT_FRACTIONS]
    off = scripted_bench(geometry, monkeypatch, is_clipped=False, fractions=fractions)
    on = scripted_bench(geometry, monkeypatch, is_clipped=True, fractions=fractions)
    outputs_off, outputs_on, states_off, states_on = [], [], [], []
    for _ in range(len(fractions) + PERIODS_PAST_THE_SCRIPT):
        outputs_off.append(off.step())
        outputs_on.append(on.step())
        states_off.append(internal_state(off.controller))
        states_on.append(internal_state(on.controller))
    return outputs_off, outputs_on, states_off, states_on


# --- settings ------------------------------------------------------------------------------------


def test_class_default_is_off_and_the_preset_is_on() -> None:
    assert C2Config().clip_returned_command is False
    assert C2Config.clip_returned_command is False  # class attribute (old pickles)
    assert C2Config().with_10hz_d1().clip_returned_command is True
    assert C2Config().with_soil_response().clip_returned_command is True


def test_preset_keyword_touches_only_the_clip() -> None:
    preset = C2Config().with_10hz_d1()
    switched_off = C2Config().with_10hz_d1(clip_returned_command=False)
    assert switched_off == replace(preset, clip_returned_command=False)


def test_unpickled_config_without_the_field_reads_off() -> None:
    older_config = pickle.loads(pickle.dumps(C2Config()))
    object.__delattr__(older_config, "clip_returned_command")
    assert older_config.clip_returned_command is False


def test_meta_reports_the_switch(geometry) -> None:
    for is_clipped in (False, True):
        config = C2Config().with_10hz_d1(clip_returned_command=is_clipped)
        assert C2Controller(geometry, config).meta()["clip_returned_command"] is is_clipped


# --- the rule ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "leg_fractions",
    [(1.0, 0.5, -0.5, 0.0), (-1.0, -0.5, 0.5, 0.0), (1.0, -1.0, 1.0, -1.0)],
    ids=["extend", "retract", "both_ways"],
)
def test_returned_command_is_the_clip_of_the_unclipped_one(
    geometry, monkeypatch, leg_fractions
) -> None:
    outputs_off, outputs_on, _, _ = run_pair(geometry, monkeypatch, leg_fractions)
    limit = geometry.max_speed_m_s
    stacked_off, stacked_on = np.array(outputs_off), np.array(outputs_on)
    assert np.abs(stacked_off).max() > limit, "the script must pass the limit"
    assert np.abs(stacked_on).max() == limit
    np.testing.assert_array_equal(stacked_on, np.clip(stacked_off, -limit, limit))


def test_internal_states_keep_the_unclipped_value(geometry, monkeypatch) -> None:
    outputs_off, _, states_off, states_on = run_pair(geometry, monkeypatch, (1.0, -1.0, 0.5, 0.0))
    assert np.abs(np.array(outputs_off)).max() > geometry.max_speed_m_s
    for state_off, state_on in zip(states_off, states_on, strict=True):
        for name, value_off in state_off.items():
            np.testing.assert_array_equal(state_on[name], value_off, err_msg=name)
    peak_state = max(np.abs(state["applied_output_m_s"]).max() for state in states_on)
    assert peak_state > geometry.max_speed_m_s


def test_speed_just_below_the_limit_passes_bit_for_bit(geometry) -> None:
    config = C2Config().with_10hz_d1()
    controller = C2Controller(geometry, config)
    limit = geometry.max_speed_m_s
    below = np.array([np.nextafter(limit, 0.0), -np.nextafter(limit, 0.0), limit, -0.0])
    returned = controller._returned_speeds(below)
    assert returned.tobytes() == below.tobytes()


def test_speed_just_above_the_limit_is_cut_to_it(geometry) -> None:
    controller = C2Controller(geometry, C2Config().with_10hz_d1())
    limit = geometry.max_speed_m_s
    above = np.array([np.nextafter(limit, 1.0), -np.nextafter(limit, 1.0), 1.75 * limit, 0.0])
    np.testing.assert_array_equal(controller._returned_speeds(above), [limit, -limit, limit, 0.0])


def test_off_returns_the_applied_output_unchanged(geometry) -> None:
    controller = C2Controller(geometry, C2Config())
    applied = np.array([1.75, -1.75, 0.5, 0.0]) * geometry.max_speed_m_s
    assert controller._returned_speeds(applied) is applied


# --- stored harness rows -------------------------------------------------------------------------


def stored_hash(row_id: str) -> str:
    for file_name in STORED_FILES:
        records = json.loads((STORED_DIR / file_name).read_text(encoding="utf-8"))["records"]
        for record in records:
            if record["id"] == row_id:
                return record["hash"]
    raise KeyError(row_id)


def _run_harness_row(job: tuple[str, str], out_dir: Path) -> dict:
    case_id, clip_switch = job
    out_path = out_dir / f"{case_id}_{clip_switch}.json"
    environment = {
        **os.environ,
        "MKL_THREADING_LAYER": "TBB",
        "OMP_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(
        [str(HARNESS_PYTHON), "-I", "-B", str(HASH_RUNNER), case_id, clip_switch, str(out_path)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        timeout=HARNESS_TIMEOUT_S,
    )
    return json.loads(out_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def harness_rows(tmp_path_factory) -> dict[tuple[str, str], dict]:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_dir = tmp_path_factory.mktemp("returned_clip")
    jobs = [
        (case_id, switch)
        for case_id in (*ACTING_ROW_HASHES, *RESTING_ROW_IDS)
        for switch in ("on", "off")
    ]
    with ThreadPoolExecutor(HARNESS_WORKERS) as pool:
        rows = list(pool.map(lambda job: _run_harness_row(job, out_dir), jobs))
    for row in rows:
        assert row["foreign_modules"] == [], "the run must import this checkout only"
    return {(row["case"], row["clip"]): row for row in rows}


@pytest.mark.slow
@pytest.mark.parametrize("case_id", ACTING_ROW_HASHES)
def test_acting_row_on_equals_the_plant_clip_and_off_equals_the_stored_row(
    harness_rows, geometry, case_id
) -> None:
    hash_on, hash_off = ACTING_ROW_HASHES[case_id]
    row_on, row_off = harness_rows[(case_id, "on")], harness_rows[(case_id, "off")]
    assert row_on["hold_events"] > 0
    assert row_on["hash"] == hash_on
    assert row_on["peak_command_m_s"] <= geometry.max_speed_m_s
    assert row_off["hash"] == hash_off == stored_hash(_acting_row_id(case_id))
    assert row_off["peak_command_m_s"] > geometry.max_speed_m_s


def _acting_row_id(case_id: str) -> str:
    return {
        "S1": "base|J1|B|top|Fs4",
        "S4": "H6|J1|B|top|flat|m1.1",
        "S5": "H6|J2|B|top|flat|m1.1",
    }[case_id]


@pytest.mark.slow
@pytest.mark.parametrize("case_id", RESTING_ROW_IDS)
def test_row_without_a_hold_does_not_move(harness_rows, case_id) -> None:
    row_on, row_off = harness_rows[(case_id, "on")], harness_rows[(case_id, "off")]
    assert row_on["hold_events"] == 0
    assert row_on["hash"] == row_off["hash"] == stored_hash(RESTING_ROW_IDS[case_id])
