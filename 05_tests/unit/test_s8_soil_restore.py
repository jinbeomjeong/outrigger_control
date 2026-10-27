"""Soil state of S8 branches pickled before the C2 soil response (user decision 2026-10-26).

Control option (다) is the default: an episode restored from a ``branch.pkl`` whose run state has
no soil state gets the lift-off confirmation (LOC) of the offline judge on its base record
(``run_S8C.apply_soil_rule``, ``C2Controller.restore_liftoff_confirmation``); option (가)
(``--soil-off-replay``) runs the episode with the soil response off and no re-approach limit.

The base record is made on the flat sink bench of ``test_c2_soil.py``: the same run with the
soil response off (the "old" controller, then aged like an old pickle) and on (the native
reference). The restored controller must hold the native soil state and command the same bits.
"""

from __future__ import annotations

import importlib.util
import json
import pickle
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_r8d1 import PERIOD_S, lifted_rr_forces, measurements  # same test folder
from test_c2_soil import SinkBench, aged, reference_weight_N, soil_config

from outrigger_sim.control.c2 import (
    SOIL_EVENT_LIFTOFF_CONFIRMED,
    SOIL_EVENT_STATE_RESTORED,
    C2Controller,
    C2Geometry,
    C2Phase,
    RestoredLiftoff,
)
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
import run_S8C  # noqa: E402

READY_TAIL_PERIODS = 20
"""Periods recorded after the first READY (the ML branch is READY + 2 s)."""
CONTINUE_PERIODS = 150
"""15 s after the branch: longer than the 10 s re-approach limit."""
SOIL_EVENT_PREFIXES = (SOIL_EVENT_STATE_RESTORED, SOIL_EVENT_LIFTOFF_CONFIRMED)
MAX_DURATION_S = 10.0


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def soil_off_config():
    """The bench config of the controller before the soil response (revision 56)."""
    return run_S8C.with_soil_off_replay(soil_config())


def flat_bench(geometry: C2Geometry, config) -> SinkBench:
    weight = reference_weight_N(geometry)
    return SinkBench.touching(geometry, config, lambda progress: weight)


def run_to_branch(bench: SinkBench) -> dict[str, list]:
    """Run to the first READY + :data:`READY_TAIL_PERIODS`; per period the series the S8 base
    run records (phase after the call, applied command, readings, calibrated loads)."""
    rows: dict[str, list] = {key: [] for key in ("t", "phase", "issued_u", "stroke",
                                                 "stroke_corrected", "load")}
    controller = bench.controller
    ready_periods = 0
    while ready_periods < READY_TAIL_PERIODS:
        command = bench.step()
        reading = controller._state.last_reading
        rows["t"].append(reading.t_s)
        rows["phase"].append(controller.phase.value)
        rows["issued_u"].append(command)
        rows["stroke"].append(reading.motor_stroke_m.copy())
        rows["stroke_corrected"].append(reading.rod_stroke_m.copy())
        rows["load"].append(reading.cylinder_force_N.copy())
        ready_periods += controller.phase is C2Phase.READY
        assert bench.t_s < 200.0, "bench never reached READY"
    return rows


def write_base_record(base_dir: Path, rows: dict[str, list], geometry: C2Geometry) -> None:
    """The files ``m4_offline.analyse`` reads from an S8 base run directory."""
    (base_dir / "record").mkdir(parents=True)
    t = np.asarray(rows["t"])
    loads = np.asarray(rows["load"])
    np.savez(base_dir / "r8_series.npz", t=t, phase=np.asarray(rows["phase"], dtype="U16"),
             issued_u=np.asarray(rows["issued_u"]))
    np.savez(base_dir / "record" / "record.npz", t=t, **{
        "meas.stroke": np.asarray(rows["stroke"]),
        "meas.stroke_corrected": np.asarray(rows["stroke_corrected"]),
        "meas.head_pressure": loads / geometry.head_area_m2})
    np.savez(base_dir / "s8_series.npz", t=t, F_nominal_N=loads)
    (base_dir / "result.json").write_text(json.dumps({"settings": {"level": "top"}}),
                                          encoding="utf-8")


@pytest.fixture(scope="module")
def branch(geometry, tmp_path_factory) -> dict:
    """The soil-off base run (record + aged controller) and the soil-on native reference."""
    old_bench = flat_bench(geometry, soil_off_config())
    old_rows = run_to_branch(old_bench)
    native_bench = flat_bench(geometry, soil_config())
    native_rows = run_to_branch(native_bench)
    base_dir = tmp_path_factory.mktemp("base") / "ML99"
    write_base_record(base_dir, old_rows, geometry)
    return {"old_bench": old_bench, "old_rows": old_rows, "native_bench": native_bench,
            "native_rows": native_rows, "base_dir": base_dir, "branch_t_s": old_rows["t"][-1]}


def pickled_copy(controller: C2Controller) -> C2Controller:
    """``controller`` pickled and unpickled by the current code (nothing removed)."""
    return pickle.loads(pickle.dumps(controller))


OLD_PICKLE_KINDS = {"old_code": aged, "soil_off_config": pickled_copy}
"""How the soil-off base controller is pickled: by code before the soil response (no soil
state, no soil setting) or by the current code with the soil response off (empty soil state)."""


def restored_controller(branch: dict, *, soil_off_replay: bool = False,
                        kind: str = "old_code"):
    """A pickled copy of the soil-off controller, refreshed and given the soil rule."""
    old = OLD_PICKLE_KINDS[kind](branch["old_bench"].controller)
    ran_without_soil = run_S8C.ran_without_soil_response(old)
    pickled_lr = run_S8C.reapproach_settings_meta(old)
    config = soil_config()
    if soil_off_replay:
        config = run_S8C.with_soil_off_replay(config)
    fresh = C2Controller(branch["old_bench"].geometry, config)
    run_S8C.refresh_restored_controller(old, fresh)
    soil_meta = run_S8C.apply_soil_rule(old, fresh, branch["base_dir"], branch["branch_t_s"],
                                        ran_without_soil=ran_without_soil,
                                        soil_off_replay=soil_off_replay)
    limit_meta = run_S8C.reapproach_limit_meta(pickled_lr, old, fresh)
    return old, fresh, soil_meta, limit_meta, ran_without_soil


def continue_run(controller: C2Controller, bench: SinkBench) -> np.ndarray:
    """Same readings for both controllers after the branch: RR lifted (re-approach)."""
    outputs = []
    strokes = bench.strokes_m.copy()
    for index in range(1, CONTINUE_PERIODS + 1):
        t_s = round(bench.t_s + index * PERIOD_S, 10)
        reading = measurements(t_s, bench.geometry, lifted_rr_forces(), strokes)
        outputs.append(np.array(controller.update(reading).leg_speed_m_s))
    return np.array(outputs)


def without_soil_events(controller: C2Controller) -> list[tuple[float, str]]:
    return [(event.t_s, event.name) for event in controller.events
            if not event.name.startswith(SOIL_EVENT_PREFIXES)]


# --- the bench premise -----------------------------------------------------------------------


def test_soil_off_and_on_base_runs_command_the_same(branch) -> None:
    """M-4 premise on the bench: LOC before DONE, so the soil response changes no command."""
    np.testing.assert_array_equal(np.array(branch["old_rows"]["issued_u"]),
                                  np.array(branch["native_rows"]["issued_u"]))
    native_soil = branch["native_bench"].controller.meta()["soil"]
    assert native_soil["loc"] is True and native_soil["bias_corner_m"] == [0.0] * 4


# --- rule (다): restore ----------------------------------------------------------------------


def test_pickles_without_a_running_soil_state_are_recognised(branch) -> None:
    aged_old = aged(branch["old_bench"].controller)
    assert aged_old._state.soil is None
    assert run_S8C.ran_without_soil_response(aged_old)
    soil_off = pickled_copy(branch["old_bench"].controller)
    assert soil_off._state.soil is not None and not soil_off.config.soil.enable
    assert run_S8C.ran_without_soil_response(soil_off)
    assert not run_S8C.ran_without_soil_response(aged_native(branch))


@pytest.mark.parametrize("kind", sorted(OLD_PICKLE_KINDS))
def test_restored_soil_state_equals_the_native_one(branch, kind) -> None:
    restored, _, soil_meta, _, ran_without_soil = restored_controller(branch, kind=kind)
    assert ran_without_soil and soil_meta["restored"] is True
    assert soil_meta["pickled_with_soil_response"] is False
    got = restored.meta()["soil"]
    want = branch["native_bench"].controller.meta()["soil"]
    for key in ("loc", "soil_mode", "t_P_s", "t_loc_s", "bias_corner_m", "soil_mode_t_s",
                "push_m"):
        assert got[key] == want[key], key
    for key in ("W_hat_N", "W_ratio", "clearance_at_P_m", "clearance_at_loc_m"):
        assert got[key] == pytest.approx(want[key], rel=1e-12, abs=1e-15), key


@pytest.mark.parametrize("kind", sorted(OLD_PICKLE_KINDS))
def test_restored_controller_commands_the_native_bits(branch, kind) -> None:
    restored, *_ = restored_controller(branch, kind=kind)
    native = aged_native(branch)
    native_outputs = continue_run(native, branch["native_bench"])
    np.testing.assert_array_equal(continue_run(restored, branch["old_bench"]), native_outputs)
    assert np.abs(native_outputs).max() > 0.0
    assert without_soil_events(restored) == without_soil_events(native)
    assert "WARN_LEG_REAPPROACH_NO_CONTACT:RR" in [name for _, name in
                                                    without_soil_events(native)]


def test_without_the_rule_the_old_branch_enters_the_soil_mode(branch) -> None:
    """Negative control (the merge problem): refreshed only, the old branch has no LOC, so the
    next crawler-zone release starts the soil mode and the commands differ at once."""
    plain = aged(branch["old_bench"].controller)
    run_S8C.refresh_restored_controller(plain, C2Controller(branch["old_bench"].geometry,
                                                            soil_config()))
    outputs = continue_run(plain, branch["old_bench"])
    assert not np.array_equal(outputs, continue_run(aged_native(branch), branch["native_bench"]))
    assert "soil_mode_start" in [event.name for event in plain.events]


def aged_native(branch: dict) -> C2Controller:
    """A pickled copy of the native soil-on controller."""
    return pickled_copy(branch["native_bench"].controller)


def test_restore_event_and_meta(branch) -> None:
    restored, _, soil_meta, _, _ = restored_controller(branch)
    source = f"{run_S8C.SOIL_RESTORE_SOURCE}:{branch['base_dir'].name}"
    (event,) = [e for e in restored.events if e.name.startswith(SOIL_EVENT_STATE_RESTORED)]
    assert event.name == f"{SOIL_EVENT_STATE_RESTORED}:{source}"
    assert event.t_s == branch["branch_t_s"]
    assert restored.meta()["soil"]["restored_from"] == source
    assert soil_meta["restored_from"] == source
    assert soil_meta["offline_judge"]["loc_before_done"] is True
    json.dumps(soil_meta)
    assert branch["native_bench"].controller.meta()["soil"]["restored_from"] is None


def test_refresh_sets_the_reapproach_time_limit(branch) -> None:
    restored, _, _, limit_meta, _ = restored_controller(branch)
    assert limit_meta == {"pickled": None, "in_use": MAX_DURATION_S, "fresh": MAX_DURATION_S}
    assert restored.config.r8.lifted_reapproach.max_duration_s == MAX_DURATION_S


def test_reapproach_limit_check_refuses_a_stale_value(branch) -> None:
    old = aged(branch["old_bench"].controller)
    fresh = C2Controller(branch["old_bench"].geometry, soil_config())
    with pytest.raises(RuntimeError, match="max_duration_s"):
        run_S8C.reapproach_limit_meta(None, old, fresh)


def test_pickled_soil_state_is_kept(branch) -> None:
    native = aged_native(branch)
    fresh = C2Controller(branch["native_bench"].geometry, soil_config())
    meta = run_S8C.apply_soil_rule(native, fresh, branch["base_dir"], branch["branch_t_s"],
                                   ran_without_soil=False, soil_off_replay=False)
    assert meta["restored"] is False and meta["pickled_with_soil_response"] is True
    assert native.meta()["soil"]["restored_from"] is None


# --- rule (다): refusals -----------------------------------------------------------------------


def test_branch_before_the_liftoff_is_refused(branch) -> None:
    old = aged(branch["old_bench"].controller)
    fresh = C2Controller(branch["old_bench"].geometry, soil_config())
    run_S8C.refresh_restored_controller(old, fresh)
    t_loc = branch["native_bench"].controller.meta()["soil"]["t_loc_s"]
    with pytest.raises(run_S8C.SoilStateRestoreError, match="before the LOC"):
        run_S8C.restore_soil_state(old, fresh, branch["base_dir"], t_loc - PERIOD_S)
    assert not old._soil_state().is_liftoff_confirmed


def test_missing_base_record_is_refused(branch, tmp_path) -> None:
    old = aged(branch["old_bench"].controller)
    fresh = C2Controller(branch["old_bench"].geometry, soil_config())
    run_S8C.refresh_restored_controller(old, fresh)
    with pytest.raises(run_S8C.SoilStateRestoreError, match="not usable"):
        run_S8C.apply_soil_rule(old, fresh, tmp_path / "ML98", branch["branch_t_s"],
                                ran_without_soil=True, soil_off_replay=False)


def test_record_without_liftoff_is_refused(branch, geometry, tmp_path) -> None:
    """A base record cut before the LOC (the window never confirms) stops the episode."""
    rows = branch["old_rows"]
    t_loc = branch["native_bench"].controller.meta()["soil"]["t_loc_s"]
    keep = sum(1 for t in rows["t"] if t < t_loc)
    cut = {key: values[:keep] for key, values in rows.items()}
    base_dir = tmp_path / "ML97"
    write_base_record(base_dir, cut, geometry)
    old = aged(branch["old_bench"].controller)
    fresh = C2Controller(geometry, soil_config())
    run_S8C.refresh_restored_controller(old, fresh)
    with pytest.raises(run_S8C.SoilStateRestoreError, match="no LOC"):
        run_S8C.restore_soil_state(old, fresh, base_dir, branch["branch_t_s"])


JUDGE_OK = {"status": "ok", "loc": {"t_loc_s": 30.0, "clearance_at_P_m": 0.005},
            "loc_before_release": True, "loc_before_done": True, "bias_applied": False,
            "release_t_s": None, "first_done_t_s": 40.0, "reason": ""}


@pytest.mark.parametrize(
    ("changes", "branch_t_s", "phases", "message"),
    [
        ({}, 50.0, (), None),
        ({"loc_before_release": False}, 50.0, (), "crawler-zone release"),
        ({"loc_before_done": False}, 50.0, (), "first DONE"),
        ({"bias_applied": True}, 50.0, (), "S-3 bias"),
        ({}, 29.0, (), "before the LOC"),
        ({}, 50.0, ("level", "touch"), "new lifting cycle"),
        ({"status": "time_mismatch"}, 50.0, (), "status"),
    ],
)
def test_restore_conditions(changes, branch_t_s, phases, message) -> None:
    problems = run_S8C.soil_restore_problems({**JUDGE_OK, **changes}, branch_t_s, phases)
    if message is None:
        assert problems == []
    else:
        assert any(message in problem for problem in problems), problems


def test_restore_api_refusals(geometry) -> None:
    liftoff = RestoredLiftoff(plateau_start_s=1.0, liftoff_s=2.0, weight_estimate_N=3.7e5,
                              clearance_at_plateau_start_m=0.005,
                              clearance_at_liftoff_m=0.010, source="test")
    with pytest.raises(ValueError, match="soil response on"):
        C2Controller(geometry, soil_off_config()).restore_liftoff_confirmation(liftoff)
    with pytest.raises(ValueError, match="dead zone"):
        C2Controller(geometry, soil_config()).restore_liftoff_confirmation(
            replace(liftoff, clearance_at_plateau_start_m=0.021))
    controller = C2Controller(geometry, soil_config())
    controller.restore_liftoff_confirmation(liftoff)
    with pytest.raises(ValueError, match="without LOC"):
        controller.restore_liftoff_confirmation(liftoff)


@pytest.mark.parametrize(("anchor", "c_p", "refused"), [
    (None, -0.030, False), ((False, 0.020), -0.030, False), ((True, 0.020), -0.010, False),
    ((True, 0.020), -0.020, False), ((True, 0.020), -0.0201, True)])
def test_restore_conditions_loc_anchor(anchor, c_p, refused) -> None:
    """C-S8-76 follow-up (가): a LOC-anchor case (P-S8-28 (a)) is a rule (다) problem."""
    judge = {**JUDGE_OK, "loc": {**JUDGE_OK["loc"], "clearance_at_P_m": c_p}}
    problems = run_S8C.soil_restore_problems(judge, 50.0, (), loc_anchor=anchor)
    assert any("LOC anchor" in p for p in problems) is refused, problems


def _anchor_controller(geometry):
    cfg = soil_config()
    if not hasattr(cfg.soil, "loc_anchor_enable"):
        pytest.skip("controller without the P-S8-28 LOC anchor")
    return C2Controller(geometry, replace(cfg, soil=replace(cfg.soil, loc_anchor_enable=True)))


def _fake_offline(monkeypatch, c_p: float) -> None:
    from s9_merge import m4_offline

    loc = {"t_loc_s": 30.0, "t_P_s": 29.0, "W_hat_N": 3.7e5, "clearance_at_P_m": c_p,
           "clearance_at_loc_m": 0.01}
    monkeypatch.setattr(m4_offline, "analyse",
                        lambda *a, **k: {**JUDGE_OK, "loc": loc})
    monkeypatch.setattr(run_S8C, "_phases_after", lambda *a, **k: [])


def test_loc_anchor_case_fails_as_soil_state_restore_error(geometry, monkeypatch,
                                                            tmp_path) -> None:
    """The ValueError of ``restore_liftoff_confirmation`` (c_min(t_P) below the LOC anchor dead
    zone) no longer escapes unnamed: rule (다) refuses it first with SoilStateRestoreError."""
    restored = _anchor_controller(geometry)
    _fake_offline(monkeypatch, -0.030)
    with pytest.raises(run_S8C.SoilStateRestoreError, match="LOC anchor"):
        run_S8C.restore_soil_state(restored, restored, tmp_path, 50.0)
    assert not restored._soil_state().is_liftoff_confirmed  # noqa: SLF001
    # backstop: a controller refusal the check did not foresee keeps the same error type
    monkeypatch.setattr(run_S8C, "loc_anchor_rule", lambda _c: None)
    with pytest.raises(run_S8C.SoilStateRestoreError, match="controller refused"):
        run_S8C.restore_soil_state(restored, restored, tmp_path, 50.0)


# --- option (가) and plumbing ---------------------------------------------------------------


def test_soil_off_replay_config() -> None:
    config = run_S8C.with_soil_off_replay(soil_config())
    assert not config.soil.enable
    assert config.r8.lifted_reapproach.max_duration_s is None
    assert replace(config, soil=soil_config().soil, r8=soil_config().r8) == soil_config()


def test_soil_off_replay_is_the_old_controller(branch) -> None:
    """Option (가): no restore, soil off, no limit; the commands are those of the soil-off
    controller continued as pickled."""
    restored, _, soil_meta, limit_meta, _ = restored_controller(branch, soil_off_replay=True)
    assert soil_meta == {"rule": "(가) soil-off replay", "restored": False,
                         "pickled_with_soil_response": False}
    assert limit_meta["in_use"] is None
    assert not restored.config.soil.enable
    unrefreshed = aged(branch["old_bench"].controller)
    np.testing.assert_array_equal(continue_run(restored, branch["old_bench"]),
                                  continue_run(unrefreshed, branch["old_bench"]))


def test_job_case_passes_the_soil_off_replay_flag(monkeypatch, tmp_path) -> None:
    from outrigger_sim.batch import Case

    seen = {}

    def fake_episode(base, ep, base_dir, case_dir, episode_s=None, variant=None, *,
                     soil_off_replay=False):
        seen["soil_off_replay"] = soil_off_replay
        return {"case": ep["episode_id"]}

    monkeypatch.setattr(run_S8C, "job_ml_episode", fake_episode)
    base = run_S8C.ml_bases(1)[0]
    episode = run_S8C.ml_episodes(base)[0]
    settings = {"kind": "ml_episode", "base": run_S8C.asdict(base), "episode": episode,
                "base_dir": str(tmp_path)}
    run_S8C.job_case(Case(episode["episode_id"], settings), tmp_path)
    assert seen["soil_off_replay"] is False
    settings[run_S8C.SOIL_OFF_REPLAY_KEY] = True
    run_S8C.job_case(Case(episode["episode_id"], settings), tmp_path)
    assert seen["soil_off_replay"] is True


def test_soil_restore_check_reads_the_plan_of_this_tree() -> None:
    """The (나) check script imports from the main tree and points at its own 768 plan
    (it was written in a worktree and once resolved the plan above the worktree)."""
    script = ROOT / "04_scripts" / "02_chrono" / "s9_merge" / "soil_restore_check.py"
    spec = importlib.util.spec_from_file_location("soil_restore_check_under_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.PLAN.is_relative_to(ROOT)
    if not module.PLAN.is_file():
        pytest.skip(f"S8 ML plan not present (07_results is not tracked): {module.PLAN}")
    assert module._plan()["bases"]


@pytest.mark.parametrize("argv", [["list", "--soil-off-replay"],
                                  ["c36", "--bundle", "D", "--soil-off-replay"],
                                  ["ml", "--soil-off-replay"]])
def test_cli_refuses_the_flag_outside_branch_replays(argv) -> None:
    with pytest.raises(SystemExit, match="--soil-off-replay only"):
        run_S8C.main(argv)
