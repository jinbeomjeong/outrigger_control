"""C2 P-S8-33 LOC revocation, gated form L1gs (control spec 424.10 / 424.10.2, user decision
2026-10-29: L1gs adopted, P-S8-34 = L2 dropped), tests 1 .. 5 of the 424.10.2 table.

Synthetic benches of ``test_c2_p28.py``: the LOC is forced through ``_confirm_liftoff``, the
watch is fed reading by reading through ``_watch_loc_revoke`` (what ``update`` calls after the
command). Test 5 runs harness cases of ``s9_slope_fix_candidates.py`` in subprocesses (slow)
against the stored wrapper ``L1gs`` records.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_p28 import level_bench, p28_config, plateau_sample, stroke_reading  # same folder
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control import c2 as c2_module
from outrigger_sim.control.c2 import (
    LOC_REVOKE_EVENT,
    LOC_REVOKE_SKIPPED_EVENT,
    SLOPE_MARGIN_EVENT,
    STROKE_END_MARGIN_M,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    LocRevokeSettings,
    _RunState,
)
from outrigger_sim.params import load_params
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

ROOT = Path(__file__).resolve().parents[2]
WRAPPER_DIR = ROOT / "04_scripts" / "03_control" / "s9"
WRAPPER_SCRIPT = WRAPPER_DIR / "s9_slope_fix_candidates.py"
REV83 = ROOT / "06_analysis" / "02_control" / "s9" / "rev83"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The harnesses need dynamics-dev (numba, sympy), not the Chrono-dev test env."""
PERIOD_S = 0.1
TILT_RAD = math.radians(1.2)
"""Settle tilt above the 1 deg of the soil sign and of P-S8-31."""
SOIL_SIGN_M = 0.015
"""``c_min(t_P)`` above the 10 mm of the soil sign and of P-S8-31."""
LOW_STROKE_M = 0.30
"""Far below the L1-s limit."""
STROKE_LIMIT_M = 0.6428
"""Lift guard stroke 682.8 mm minus the 40 mm L1-s margin."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def weight_N(geometry: C2Geometry) -> float:
    return geometry.superstructure_mass_kg * STANDARD_GRAVITY_M_S2


def rise_limit_N(geometry: C2Geometry) -> float:
    settings = LocRevokeSettings()
    return max(settings.rise_N, settings.rise_fraction_W * weight_N(geometry))


def revoke_config(**revoke_changes) -> C2Config:
    """Bench preset (R8 soil response, P-S8-31) with the R8 P-S8-33 settings and changes."""
    revoke = replace(C2Config().with_10hz_d1().loc_revoke, **revoke_changes)
    return replace(p28_config(), loc_revoke=revoke)


def level_controller(
    geometry: C2Geometry, config: C2Config, monkeypatch, settle_rad=(TILT_RAD, 0.0)
) -> C2Controller:
    controller = C2Controller(geometry, config)
    controller._state.phase = C2Phase.LEVEL
    controller._soil_state().settle_attitude_rad = settle_rad
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: settle_rad)
    return controller


def set_reading(
    controller: C2Controller, t_s: float, load_sum_N: float, stroke_m: float = LOW_STROKE_M
) -> None:
    strokes = np.full(4, stroke_m)
    reading = stroke_reading(t_s, strokes, strokes)
    controller._state.last_reading = replace(reading, cylinder_force_N=np.full(4, load_sum_N / 4))


def force_loc(
    controller: C2Controller, geometry: C2Geometry, t_s: float,
    clearance_m: float = SOIL_SIGN_M, stroke_m: float = LOW_STROKE_M,
) -> None:
    """A LOC whose plateau-start sample reads exactly ``clearance_m`` on every corner."""
    set_reading(controller, t_s, weight_N(geometry), stroke_m)
    sample = plateau_sample(geometry, operating_strokes(geometry), t_s)
    sample = replace(sample, mean_motor_stroke_m=stroke_m, load_sum_N=weight_N(geometry),
                     corner_clearance_m=np.full(4, clearance_m))
    controller._confirm_liftoff(t_s, [sample], weight_N(geometry))


def feed(
    controller: C2Controller, t_start_s: float, loads_N: list[float],
    stroke_m: float = LOW_STROKE_M,
) -> float:
    """One ``_watch_loc_revoke`` per load (10 Hz); returns the last time."""
    t_s = t_start_s
    for load_N in loads_N:
        t_s = round(t_s + PERIOD_S, 10)
        set_reading(controller, t_s, load_N, stroke_m)
        controller._watch_loc_revoke()
    return t_s


def above_N(geometry: C2Geometry) -> float:
    return weight_N(geometry) + rise_limit_N(geometry) + 500.0


def names(controller: C2Controller, prefix: str) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(prefix)]


def revoke_count(controller: C2Controller) -> int:
    return len(controller._state.loc_revokes)


# --- 1: class defaults off, R8 preset L1gs, no firing = bit for bit ----------------------------


def test_1_class_default_is_off_and_the_r8_preset_is_l1gs() -> None:
    assert C2Config().loc_revoke == LocRevokeSettings()
    assert not LocRevokeSettings().enable
    assert _RunState.loc_revoke_watch is None and _RunState.loc_revokes == ()  # old pickles
    assert _RunState.loc_revoke_skips == ()
    preset = C2Config().with_10hz_d1().loc_revoke
    assert preset == LocRevokeSettings(enable=True, soil_gate=True, stroke_guard=True,
                                       keep_slope_margin_on_revoke=True)
    assert not hasattr(c2_module, "LocConfirmWindowSettings")  # P-S8-34 removed
    assert not hasattr(C2Config(), "loc_confirm_window")


def test_1_settings_equal_the_wrapper_l1gs_token() -> None:
    sys.path.insert(0, str(WRAPPER_DIR))
    import s9_slope_fix_candidates as fx

    token = fx.parse_candidate("L1gs")
    revoke = C2Config().with_10hz_d1().loc_revoke
    assert (revoke.watch_m, revoke.rise_N, revoke.rise_fraction_W, revoke.mean_s,
            revoke.confirm_periods, revoke.max_revokes) == (
        token.l1_watch_m, token.l1_rise_N, token.l1_rise_fraction_W, token.l1_mean_s,
        token.l1_confirm_periods, token.l1_max_revokes)
    assert (revoke.soil_gate, revoke.gate_min_clearance_at_P_m, revoke.gate_tilt_min_rad) == (
        token.l1_soil_gate, token.l1_gate_min_clearance_at_P_m, token.l1_gate_tilt_min_rad)
    assert (revoke.stroke_guard, revoke.stroke_margin_m, revoke.keep_slope_margin_on_revoke) == (
        token.l1_stroke_guard, token.l1_stroke_margin_m, True)


@pytest.mark.parametrize("bad", [{"stroke_margin_m": 0.0}, {"gate_min_clearance_at_P_m": 0.0},
                                 {"confirm_periods": 0}])
def test_1_settings_reject_bad_values(bad) -> None:
    with pytest.raises(ValueError):
        LocRevokeSettings(**bad)


def test_1_on_and_off_command_alike_without_a_loc(geometry) -> None:
    outputs = []
    for config in (revoke_config(), revoke_config(enable=False)):
        bench = level_bench(geometry, config, operating_strokes(geometry))
        for _ in range(60):
            bench.step()
        assert bench.controller._state.loc_revokes == ()
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_1_off_starts_no_watch(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(enable=False), monkeypatch)
    force_loc(controller, geometry, 5.0)
    assert controller._soil_state().is_liftoff_confirmed
    assert controller._state.loc_revoke_watch is None
    meta = json.loads(json.dumps(controller.meta()))["loc_revoke"]
    assert meta["revokes"] == 0 and meta["t_skip_s"] == []
    assert "loc_confirm_window" not in controller.meta()


# --- 2: L1-g soil sign at the LOC --------------------------------------------------------------


@pytest.mark.parametrize(
    ("clearance_m", "tilt_deg", "soil_mode_ran", "is_watched"),
    [
        (0.0, 0.0, False, False),  # level rigid floor: no soil sign
        (0.0100, 1.0, False, False),  # both at the gate values (strict ">")
        (0.0101, 1.0, False, False),
        (0.0100, 1.01, False, False),
        (0.0101, 1.01, False, True),
        (0.0, 0.0, True, True),  # the soil mode started in this lifting cycle
    ],
)
def test_2_soil_gate(geometry, monkeypatch, clearance_m, tilt_deg, soil_mode_ran,
                     is_watched) -> None:
    settle_rad = (math.radians(tilt_deg), 0.0)
    controller = level_controller(geometry, revoke_config(), monkeypatch, settle_rad)
    if soil_mode_ran:
        controller._soil_state().soil_mode_start_s = 3.0
    force_loc(controller, geometry, 5.0, clearance_m=clearance_m)
    assert controller._soil_state().is_liftoff_confirmed
    assert (controller._state.loc_revoke_watch is not None) is is_watched
    feed(controller, 5.0, [above_N(geometry)] * 2)
    assert revoke_count(controller) == (1 if is_watched else 0)


def test_2_gate_off_watches_a_level_rigid_loc(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(soil_gate=False), monkeypatch,
                                  (0.0, 0.0))
    force_loc(controller, geometry, 5.0, clearance_m=0.0)
    assert controller._state.loc_revoke_watch is not None


# --- 3: L1-s stroke guard ----------------------------------------------------------------------


def stroke_limit_m(controller: C2Controller) -> float:
    """The L1-s limit as c2 computes it (lift guard stroke minus the margin)."""
    guard_m = (controller.geometry.stroke_soft_max_m - STROKE_END_MARGIN_M
               - controller.config.lift_stroke_guard.extra_margin_m)
    return guard_m - controller.config.loc_revoke.stroke_margin_m


def test_3_limit_is_642_8_mm(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    assert stroke_limit_m(controller) == pytest.approx(STROKE_LIMIT_M, abs=1e-9)


@pytest.mark.parametrize(("below_limit_m", "is_skipped"), [(0.0001, False), (0.0, True)])
def test_3_stroke_guard_boundary(geometry, monkeypatch, below_limit_m, is_skipped) -> None:
    """642.7 mm revokes, 642.8 mm (the limit, ">=") withholds the revocation."""
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    stroke_m = stroke_limit_m(controller) - below_limit_m
    force_loc(controller, geometry, 5.0, stroke_m=stroke_m)
    feed(controller, 5.0, [above_N(geometry)] * 2, stroke_m=stroke_m)
    soil = controller._soil_state()
    assert soil.is_liftoff_confirmed is is_skipped
    assert revoke_count(controller) == (0 if is_skipped else 1)
    skipped = names(controller, LOC_REVOKE_SKIPPED_EVENT)
    assert skipped == ([f"{LOC_REVOKE_SKIPPED_EVENT}:stroke"] if is_skipped else [])
    assert controller._state.loc_revoke_watch is None  # a skip ends the watch as well
    meta = json.loads(json.dumps(controller.meta()))["loc_revoke"]
    assert len(meta["t_skip_s"]) == (1 if is_skipped else 0)


def test_3_guard_off_revokes_at_the_limit(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(stroke_guard=False), monkeypatch)
    stroke_m = stroke_limit_m(controller) + 0.010
    force_loc(controller, geometry, 5.0, stroke_m=stroke_m)
    feed(controller, 5.0, [above_N(geometry)] * 2, stroke_m=stroke_m)
    assert revoke_count(controller) == 1


# --- 4: revocation, the P-S8-31 margin and the general watch rules -----------------------------


@pytest.mark.parametrize("keep", [True, False])
def test_4_slope_margin_on_revoke(geometry, monkeypatch, keep) -> None:
    """Kept: the first margin stays and the next LOC adds none. Not kept (the L1 form): the
    margin goes with the LOC and the next LOC applies it again."""
    config = revoke_config(keep_slope_margin_on_revoke=keep)
    controller = level_controller(geometry, config, monkeypatch)
    force_loc(controller, geometry, 5.0)
    state = controller._state
    assert controller._clearance_target_m() == pytest.approx(0.08)
    applied_s = state.slope_margin_applied_s
    t_s = feed(controller, 5.0, [above_N(geometry)] * 2)
    assert revoke_count(controller) == 1
    assert (controller._clearance_target_m() == pytest.approx(0.08)) is keep
    assert (state.slope_margin_applied_s == applied_s) is keep
    force_loc(controller, geometry, t_s + 1.0)
    assert controller._clearance_target_m() == pytest.approx(0.08)
    assert len(names(controller, SLOPE_MARGIN_EVENT)) == (1 if keep else 2)


def test_4_revocation_undoes_the_loc(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    force_loc(controller, geometry, 5.0)
    soil = controller._soil_state()
    soil.window.append(plateau_sample(geometry, operating_strokes(geometry), 5.1))
    feed(controller, 5.0, [above_N(geometry)] * 2)
    assert not soil.is_liftoff_confirmed and not soil.is_soil_mode and len(soil.window) == 0
    assert not soil.has_corner_bias and soil.corner_bias_raw_m is None
    assert not soil.is_loc_anchor_applied
    assert soil.weight_estimate_N is None and soil.liftoff_s is None
    assert soil.clearance_at_plateau_start_m is None
    assert names(controller, LOC_REVOKE_EVENT) == [f"{LOC_REVOKE_EVENT}:2.5"]
    force_loc(controller, geometry, 6.0)  # the next LOC: a new W_hat and a new watch
    assert soil.is_liftoff_confirmed and soil.liftoff_s == 6.0
    assert controller._state.loc_revoke_watch is not None


def test_4_revocation_undoes_the_loc_anchor(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    controller._soil_state().soil_mode_start_s = 3.0  # soil sign for c_min below zero
    force_loc(controller, geometry, 5.0, clearance_m=-0.030)  # below the 20 mm anchor zone
    soil = controller._soil_state()
    assert soil.is_loc_anchor_applied and soil.has_corner_bias
    feed(controller, 5.0, [above_N(geometry)] * 2)
    assert not soil.is_loc_anchor_applied and not soil.has_corner_bias


def test_4_two_periods_and_the_one_second_mean(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    force_loc(controller, geometry, 5.0)
    feed(controller, 5.0, [above_N(geometry)])
    assert revoke_count(controller) == 0  # one period is not enough
    feed(controller, 5.1, [weight_N(geometry), above_N(geometry)])
    assert revoke_count(controller) == 0  # interrupted
    for spike_N, expected in ((25e3, 1), (15e3, 0)):  # 1 s mean = W_hat + spike / 10
        controller = level_controller(geometry, revoke_config(), monkeypatch)
        force_loc(controller, geometry, 5.0)
        t_s = feed(controller, 5.0, [weight_N(geometry)] * 10)
        feed(controller, t_s, [weight_N(geometry) + spike_N, weight_N(geometry)])
        assert revoke_count(controller) == expected


def test_4_no_watch_after_max_revokes(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    t_s = 5.0
    for _ in range(LocRevokeSettings().max_revokes):
        force_loc(controller, geometry, t_s)
        t_s = feed(controller, t_s, [above_N(geometry)] * 2)
    assert revoke_count(controller) == 2
    force_loc(controller, geometry, t_s)
    assert controller._state.loc_revoke_watch is None


@pytest.mark.parametrize(("stroke_change_m", "is_watching"), [(0.0199, True), (0.0201, False)])
def test_4_watch_ends_20_mm_past_the_loc(geometry, monkeypatch, stroke_change_m,
                                         is_watching) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    force_loc(controller, geometry, 5.0)
    feed(controller, 5.0, [weight_N(geometry)], stroke_m=LOW_STROKE_M + stroke_change_m)
    assert (controller._state.loc_revoke_watch is not None) is is_watching


def test_4_watch_ends_at_the_first_done(geometry, monkeypatch) -> None:
    controller = level_controller(geometry, revoke_config(), monkeypatch)
    force_loc(controller, geometry, 5.0)
    controller._state.phase = C2Phase.DONE
    feed(controller, 5.0, [above_N(geometry)] * 2)
    assert controller._state.loc_revoke_watch is None and revoke_count(controller) == 0


# --- wrapper guard -----------------------------------------------------------------------------


def test_wrapper_l1_token_steps_the_project_rule_aside() -> None:
    sys.path.insert(0, str(WRAPPER_DIR))
    import s9_slope_fix_candidates as fx

    preset = C2Config().with_10hz_d1()
    for token in ("L1", "L1g", "L1gs", "L1gs+L2g"):
        assert not fx._without_project_l1(preset, fx.parse_candidate(token)).loc_revoke.enable
    for token in ("current", "L2", "L2g"):
        assert fx._without_project_l1(preset, fx.parse_candidate(token)) is preset
    # the candidate class must not shadow a P-S8-33 method of the project class
    candidate_class = fx.make_candidate_class(c2_module, C2Controller, fx.parse_candidate("L1gs"))
    project_methods = {"_start_loc_revoke_watch", "_watch_loc_revoke", "_revoke_loc",
                       "_has_loc_soil_sign", "_is_revoke_stroke_guarded", "_loc_revoke_meta"}
    assert project_methods <= set(vars(C2Controller))
    assert not project_methods & set(vars(candidate_class))


# --- 5: wrapper hash ---------------------------------------------------------------------------

WRAPPER_CASES = (
    # H6 J1 B x1.1 left this set when the R8 preset took P-S8-35 (its DSb75 hold changes the
    # commands, test_c2_p35 test 9); the cases below have no P-S8-35 hold.
    ("h6", "H6|J1|A|top|flat|m1.2", "regBE_h6.json", f"{LOC_REVOKE_EVENT}:2.8"),
    ("h6", "H6|G1|B|top|flat|m1.2", "regBE_h6.json", None),
    ("slope", "H1|S1|B|top|roll_pos", "regB_slope_rejudged.json",
     f"{LOC_REVOKE_SKIPPED_EVENT}:stroke"),
    ("g8", "slope|edgeMp|top|4.0|FR|raised|20.0|proj", "regB_g8.json", None),
)
"""(suite, case, stored record file, expected project L1 event): spec 424.10.2 test 5 - a
revocation, the stroke-guard skip, the gate idle on a rigid edgeMp case - and the H6 pair of
the coordinator (J1 A x1.2 revokes, G1 x1.2 idle)."""


def stored_l1gs_hash(file_name: str, case_id: str) -> str:
    records = json.loads((REV83 / file_name).read_text(encoding="utf-8"))["records"]
    (record,) = [r for r in records if r["id"] == case_id and r["candidate"] == "L1gs"]
    return record["hash"]


def run_harness(tmp_path: Path, suites: str, hook: str, cases: list[str]) -> list[dict]:
    out_path = tmp_path / f"p33_{suites.replace(',', '_')}.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run(
        [str(HARNESS_PYTHON), "-I", "-B", str(WRAPPER_SCRIPT), "run", "--suite", suites,
         "--candidates", "current,L1gs", "--settle-hook", hook, "--filter", ",".join(cases),
         "--workers", "8", "--out", str(out_path)],
        cwd=ROOT, env=environment, check=True, capture_output=True, timeout=1800,
    )
    return json.loads(out_path.read_text(encoding="utf-8"))["records"]


@pytest.mark.slow
def test_5_project_preset_matches_the_wrapper_l1gs_hash(tmp_path) -> None:
    """The harness's ``current`` (R8 preset = L1gs) and the token ``L1gs`` on top of it
    command as the stored wrapper ``L1gs`` records; the project events are the expected ones."""
    if not HARNESS_PYTHON.exists() or not (REV83 / "regBE_h6.json").exists():
        pytest.skip("dynamics-dev or the rev. 83 L1gs records missing")
    harness_cases = [c for c in WRAPPER_CASES if c[0] != "g8"]
    records = run_harness(tmp_path, "h6,slope", "harness", [c[1] for c in harness_cases])
    records += run_harness(tmp_path, "g8", "p0", [c[1] for c in WRAPPER_CASES if c[0] == "g8"])
    by_key = {(r["id"], r["candidate"]): r for r in records}
    assert len(records) == 2 * len(WRAPPER_CASES)
    for _, case_id, file_name, project_event in WRAPPER_CASES:
        expected = stored_l1gs_hash(file_name, case_id)
        for candidate in ("current", "L1gs"):
            record = by_key[(case_id, candidate)]
            assert "error" not in record, record.get("error")
            assert record["hash"] == expected, (case_id, candidate)
        events = [name for _, name in by_key[(case_id, "current")]["metrics"]["fix_events"]
                  if name.startswith("INFO_LOC_REVOKE")]
        assert events == ([] if project_event is None else [project_event]), case_id
