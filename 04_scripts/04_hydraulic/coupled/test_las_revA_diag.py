"""Tests of ``las_revA_diag.py`` (diagA recorder and judge) and the D-A wiring of
``las_revA_targeted.py``.

The recorder is checked on the real ``C2Controller`` with the synthetic soil bench of
``05_tests/unit`` (commands, events and meta bit for bit with and without every recorder the
D-A worker installs); the judge on hand-made lines (no harness run).
"""
from __future__ import annotations

import copy
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))

import las_phase_diag  # noqa: E402
import las_rev_judge as rj  # noqa: E402
import las_rev_targeted as rev  # noqa: E402
import las_revA_diag as diag  # noqa: E402
import las_revA_judge as judge  # noqa: E402
import las_revA_targeted as reva  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from test_c2_r8d1 import PERIOD_S, bench_config, measurements  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2  # noqa: E402

PINNED_RATE_N_M = 0.6e6
PINNED_START_FRACTION = 0.9
PINNED_UNTIL_M = 0.04
"""Bench load: pinned (rising with the stroke) for 40 mm, then flat: the latch releases at
20 mm clearance into the soil mode, and the flat part confirms the LOC."""
BENCH_LIMIT_S = 90.0
RELEASE_MM = 20.0
RISE_MAX_N = 2000.0
T_LIFT_S = 22.868


# ------------------------------------------------------------------------------- real bench
def _bench_run(geometry, load_sum_N) -> dict:
    """Closed 10 Hz loop: strokes integrate the commands, legs read a quarter of the load."""
    config = replace(bench_config(), soil=c2.SoilResponseSettings(enable=True))
    strokes = geometry.operating_extension_m(0.0).copy()
    start_mean_m = float(np.mean(strokes))
    controller = c2.C2Controller(geometry, config)
    commands, t_s = [], 0.0
    while t_s < BENCH_LIMIT_S and controller.phase not in (c2.C2Phase.READY, c2.C2Phase.FAULT):
        t_s = round(t_s + PERIOD_S, 10)
        forces = np.full(4, load_sum_N(float(np.mean(strokes)) - start_mean_m) / 4.0)
        command = np.array(controller.update(measurements(t_s, geometry, forces,
                                                          strokes.copy())).leg_speed_m_s)
        strokes = strokes + command * PERIOD_S
        commands.append(command)
    return {"commands": np.array(commands), "controller": controller,
            "events": [(event.t_s, event.name) for event in controller.events],
            "soil_meta": controller.meta()["soil"]}


@pytest.fixture(scope="module")
def geometry():
    return c2.C2Geometry.from_params(load_params())


def _knee_load(geometry):
    weight_N = geometry.superstructure_mass_kg * STANDARD_GRAVITY_M_S2

    def load_sum_N(progress_m: float) -> float:
        return PINNED_START_FRACTION * weight_N + PINNED_RATE_N_M * min(progress_m,
                                                                        PINNED_UNTIL_M)

    return load_sum_N


def _install_worker_recorders() -> None:
    """The D-A worker's recorders in its order (period record, DONE record, soil last)."""
    las_phase_diag.install(True, None)
    rev.install_done_recorder()
    diag.install_soil_recorder()


def _uninstall_all() -> None:
    diag.uninstall_soil_recorder()
    rev.uninstall()
    las_phase_diag.uninstall()


@pytest.fixture(scope="module")
def bench_pair(geometry):
    """The knee bench without and with every recorder of the D-A worker."""
    plain = _bench_run(geometry, _knee_load(geometry))
    _install_worker_recorders()
    try:
        recorded = _bench_run(geometry, _knee_load(geometry))
    finally:
        _uninstall_all()
    return plain, recorded


def test_recorders_do_not_change_a_command_bit(bench_pair):
    plain, recorded = bench_pair
    assert plain["commands"].shape == recorded["commands"].shape
    assert plain["commands"].tobytes() == recorded["commands"].tobytes()
    assert plain["events"] == recorded["events"]
    assert plain["soil_meta"] == recorded["soil_meta"]


def test_bench_reaches_soil_mode_and_loc(bench_pair):
    """The bench exercises what D-A records: a latch release into soil mode, then a LOC."""
    _, recorded = bench_pair
    meta = recorded["soil_meta"]
    assert meta["soil_mode_t_s"] is not None and meta["loc"] is True


def test_soil_records_follow_the_controller(bench_pair):
    _, recorded = bench_pair
    controller = recorded["controller"]
    records = controller.__dict__[diag.SOIL_LOG_ATTRIBUTE]
    assert len(records) == len(recorded["commands"])
    meta = recorded["soil_meta"]
    summary = diag.soil_summary(records, None, RELEASE_MM, RISE_MAX_N)
    assert summary["t_S_s"] == pytest.approx(meta["soil_mode_t_s"])
    assert summary["t_LOC_s"] == pytest.approx(meta["t_loc_s"])
    assert summary["t_P_s"] == pytest.approx(meta["t_P_s"])
    # the soil mode starts in the call that releases the latch (W-3 note of the module)
    assert summary["t_rel_s"] == summary["t_S_s"] and summary["t_S_latch_release"] is True
    assert summary["s_rel_mm"] < summary["s_LOC_mm"]
    loc_record = next(record for record in records if record["loc_confirmed_now"])
    assert loc_record["tail_span_ok"] is True and loc_record["is_flat"] is True
    assert loc_record["mean_load_over_W"] >= controller.config.soil.plausibility_fraction
    assert loc_record["window_span_mm"] >= controller.config.soil.plateau_window_m * 1e3
    level = [record for record in records if record["slow_clearance_mm"] is not None]
    assert level and all(record["clearance_target_mm"] > 0 for record in records)


def test_recorder_installs_once_and_uninstalls():
    class Stand:
        def update(self, measurements):
            return measurements

    for name in diag.HOOKED_METHODS[1:]:
        setattr(Stand, name, lambda self, *args: None)
    originals = {name: getattr(Stand, name) for name in diag.HOOKED_METHODS}
    diag.install_soil_recorder(Stand)
    try:
        with pytest.raises(RuntimeError):
            diag.install_soil_recorder(Stand)
        assert Stand.update is not originals["update"]
    finally:
        diag.uninstall_soil_recorder()
    assert {name: getattr(Stand, name) for name in diag.HOOKED_METHODS} == originals


# ------------------------------------------------------------------------------- summary
def _record(t_s, **values):
    return {"t_s": t_s, **diag.SOIL_RECORD_DEFAULTS, "is_flat": None, **values}


def test_soil_summary_counts_between_lift_off_and_loc():
    records = [
        _record(22.8, window_cleared=True, mean_motor_stroke_mm=400.0),  # before lift-off
        _record(22.9, window_cleared=True, mean_motor_stroke_mm=401.0),
        _record(23.0, tail_span_ok=True, rise_N=2500.0, mean_motor_stroke_mm=402.0),
        _record(23.1, tail_span_ok=True, rise_N=1500.0, slow_clearance_mm=20.0,
                latch_release=True, soil_mode_started_now=True, mean_motor_stroke_mm=403.0),
        _record(23.2, loc_confirmed_now=True, window_first_t_s=22.95, plateau_start_s=23.0,
                mean_motor_stroke_mm=404.0),
        _record(23.3, window_cleared=True, tail_span_ok=True, rise_N=9000.0),  # after LOC
    ]
    summary = diag.soil_summary(records, T_LIFT_S, RELEASE_MM, RISE_MAX_N)
    assert summary["clear_times_s"] == [22.9] and summary["n_clear"] == 1
    assert summary["steep_times_s"] == [23.0] and summary["n_steep"] == 1
    assert (summary["t_rel_s"], summary["t_S_s"], summary["t_LOC_s"]) == (23.1, 23.1, 23.2)
    assert (summary["t_w0_s"], summary["t_P_s"]) == (22.95, 23.0)
    assert (summary["s_rel_mm"], summary["s_LOC_mm"]) == (403.0, 404.0)


def test_period_and_force_windows():
    periods = [{"t_s": round(0.1 * k, 10), "phase": "level" if k < 50 else "ready"}
               for k in range(1, 80)]
    window = diag.period_window(periods, [{"t_s": 2.0}])
    assert (window["t0_s"], window["t1_s"]) == (1.5, pytest.approx(6.0))
    columns = {name: index for index, name in enumerate(las_phase_diag.FORCE_WINDOW_COLUMNS)}
    rows = np.zeros((100, len(columns)))
    rows[:, 0] = np.arange(100) * 0.1
    block = diag.force_rows(rows, columns, 2.0, 4.0)
    times = [row[0] for row in block["rows"]]
    assert times[0] == pytest.approx(1.5) and times[-1] == pytest.approx(6.0)
    assert diag.force_rows(rows, columns, None, 4.0) is None


# ------------------------------------------------------------------------------- judge lines
EVENT_SOIL = {diag.SOIL_MODE_EVENT: 1, diag.FLAT_SOIL_MARGIN_EVENT: 1}


def _soil_summary(*, t_rel=None, t_s=None, t_loc=23.5, s_rel=None, s_loc=440.0, clears=(),
                  steeps=(), latch=True, raised=False):
    return {"t_rel_s": t_rel, "t_S_s": t_s, "t_S_latch_release": None if t_s is None else latch,
            "t_LOC_s": t_loc, "s_rel_mm": s_rel, "s_LOC_mm": s_loc,
            "n_clear": len(clears), "clear_times_s": list(clears), "n_steep": len(steeps),
            "steep_times_s": list(steeps), "flat_soil_margin_applied": raised,
            "clearance_target_base_mm": 50.0, "clearance_target_final_mm": 80.0 if raised else 50.0}


def _diag_line(candidate, *, sha=None, soil=None, stroke_max_m=0.43876, events=None,
               start=22.9, end=23.3, t_loc=23.5, cmd=5.0, head="c0"):
    beta, n_min, n_r = judge.CANDIDATE_VALUES[candidate]
    rules = dict(zip(diag.RULES_FIELDS, diag.RULES_VALUES, strict=True))
    tag = rj.CONTROLLER_TAG_BY_SETTING["VB"]
    return {
        "job": {"setting": "VB", "d1": {}}, "controller_tag": tag,
        "commands_sha256": sha or diag.EXPECTED_HASHES.get(candidate, "f" * 64),
        "event_names": dict(events or {}), "d1": {"stroke_max_m": stroke_max_m},
        "las": {"start_t_s": start, "end_t_s": end, "end_reason": "sum", "active_periods": 4,
                "scaled_periods": 4, "start_leg": 3, "t_loc_s": t_loc,
                "params": {"beta": beta, "n_min": n_min, "n_r": n_r},
                "ramp": {"end_t_s": 23.6 if n_r else None}},
        "rev": {"bundle": diag.BUNDLE, "candidate": candidate, "label": candidate,
                "settings": {"light_leg_fraction_of_F_min": beta, "min_active_periods": n_min,
                             "end_ramp_periods": n_r},
                "settings_match": True, "controller_tag": tag, **rules,
                "diag_plan_sha256": diag.PLAN_SHA256,
                "identity": {"git_head": head, "code_diff_sha256": rj.EMPTY_SHA256,
                             "dirty_files": [".gitattributes"]}},
        "diag": {"summary": {"t_lift_s": T_LIFT_S},
                 "periods": [{"t_s": 22.9, "cmd_mm_s": [cmd] * 4},
                             {"t_s": 23.4, "cmd_mm_s": [cmd + 1.0] * 4}],
                 "soil_summary": soil or _soil_summary()}}


def _stored() -> diag.StoredPairs:
    l_line = {"las": {"t_loc_s": 23.5}, "event_names": {}}
    p5r4 = {"las": {"t_loc_s": 24.1}, "event_names": dict(EVENT_SOIL)}
    return diag.StoredPairs(l_line, p5r4)


def _lines(*, p0_soil=None, p5_soil=None, p5r4_soil=None, p5_stroke=0.4688):
    p0 = _diag_line("P0", soil=p0_soil or _soil_summary(s_rel=442.0, s_loc=440.0))
    p5r4 = _diag_line("P5r4", t_loc=24.1, stroke_max_m=0.4689, events=EVENT_SOIL,
                      soil=p5r4_soil or _soil_summary(t_rel=23.8, t_s=23.8, t_loc=24.1,
                                                      s_rel=455.0, s_loc=460.0,
                                                      clears=(23.3,), raised=True))
    p5_events = EVENT_SOIL if p5_soil is None else {}
    p5 = _diag_line("P5", t_loc=24.0, stroke_max_m=p5_stroke, events=p5_events,
                    soil=p5_soil or _soil_summary(t_rel=23.7, t_s=23.7, t_loc=24.0,
                                                  s_rel=450.0, s_loc=455.0, raised=True))
    return [p0, p5, p5r4]


def test_judge_w3_as_written_needs_a_decision_when_t_rel_equals_t_s():
    """t_rel = t_S (c2: same call) fails W-3 as written; the t_rel <= t_S reading gives beta."""
    result = diag.judge_diag(_lines(), _stored())
    assert result["d0"]["D-0d"]["status"] == diag.STATUS_TRUE
    assert result["W1"]["status"] == diag.STATUS_TRUE
    assert result["W2"]["status"] == diag.STATUS_TRUE
    assert result["W3"]["status"] == diag.STATUS_FALSE
    assert result["W3"]["status_le"] == diag.STATUS_TRUE and not result["W3"]["rejected"]
    assert result["B1"]["status"] == diag.STATUS_TRUE
    assert result["branches"] == []
    assert result["branches_alternative_reading"] == [diag.BRANCH_BETA]
    assert result["verdict"] == diag.NEEDS_DECISION


def test_judge_beta_and_ramp_branches():
    lines = _lines(p5r4_soil=_soil_summary(t_rel=23.7, t_s=23.8, t_loc=24.1, s_rel=455.0,
                                           s_loc=460.0, steeps=(23.5,), raised=True))
    result = diag.judge_diag(lines, _stored())
    assert result["branches"] == [diag.BRANCH_BETA] and result["verdict"] == "branch"
    no_soil = _soil_summary(t_loc=23.5, s_rel=452.0, s_loc=450.0)
    lines = _lines(p5_soil=no_soil, p5_stroke=0.4400,
                   p5r4_soil=_soil_summary(t_rel=23.7, t_s=23.8, t_loc=24.1, s_rel=455.0,
                                           s_loc=460.0, steeps=(23.5,), raised=True))
    result = diag.judge_diag(lines, _stored())
    assert result["B1"]["status"] == diag.STATUS_FALSE
    assert result["branches"] == [diag.BRANCH_RAMP]


def test_judge_boundary_and_rejected_branches():
    lines = _lines(p0_soil=_soil_summary(s_rel=438.0, s_loc=440.0),
                   p5r4_soil=_soil_summary(t_rel=23.8, t_s=23.8, t_loc=24.1, s_rel=455.0,
                                           s_loc=460.0, raised=True))
    result = diag.judge_diag(lines, _stored())
    assert result["W1"]["boundary"] is True
    assert diag.BRANCH_BOUNDARY in result["branches"]
    assert diag.BRANCH_REJECTED in result["branches"] and result["W2"]["rejected"]
    far = _lines(p0_soil=_soil_summary(s_rel=450.0, s_loc=440.0))  # 10 mm: W-1 false only
    result = diag.judge_diag(far, _stored())
    assert result["W1"]["status"] == diag.STATUS_FALSE and result["W1"]["boundary"] is False
    assert diag.BRANCH_BOUNDARY in result["branches"]
    assert diag.BRANCH_BOUNDARY not in result["branches_alternative_reading"]
    assert result["verdict"] == diag.NEEDS_DECISION


def test_judge_stops_on_h_d1_h_d3_and_h_d0():
    lines = _lines()
    lines[0]["commands_sha256"] = "0" * 64
    result = diag.judge_diag(lines, _stored())
    assert result["verdict"] == "stop" and result["stop"] == "H-D1"
    assert result["d0"]["D-0a"] == diag.STATUS_FALSE
    lines = _lines()
    lines[1]["diag"]["periods"][0]["cmd_mm_s"] = [9.0] * 4  # P5 differs before the end
    result = diag.judge_diag(lines, _stored())
    assert result["stop"] == "H-D1" and result["d0"]["D-0c"] == diag.STATUS_FALSE
    lines = _lines()
    lines[2]["rev"]["identity"]["git_head"] = "c1"
    assert diag.judge_diag(lines, _stored())["stop"] == "H-D3"
    lines = _lines()
    lines[2]["rev"]["diag_plan_sha256"] = "x"
    assert diag.judge_diag(lines, _stored())["stop"] == "H-D3"
    assert diag.judge_diag(_lines(), _stored(), ["plan missing"])["stop"] == "H-D0"
    assert diag.judge_diag(_lines()[:2], _stored())["verdict"] == "incomplete"


def test_d0c_compares_up_to_the_las_end_only():
    lines = _lines()
    lines[2]["diag"]["periods"][1]["cmd_mm_s"] = [99.0] * 4  # after t_e = 23.3: the ramp
    assert diag.d0c_problems(lines[1], lines[2]) == []
    lines[1]["las"]["end_reason"] = "time"
    assert any("K-A1" in text for text in diag.d0c_problems(lines[1], lines[2]))


def test_batch_checker_stops_on_h_d1():
    identity = {"git_head": "c0", "code_diff_sha256": rj.EMPTY_SHA256, "sha256": {},
                "budget_rule": "R3-1"}
    lines = _lines()
    for line in lines:
        line["rev"]["identity"] = dict(identity)
    check = diag.make_checker()
    state = rev.BatchState()
    for line in lines:
        check(line, diag.BUNDLE, state, {}, {}, identity)
    assert state.stop is None
    bad = copy.deepcopy(lines)
    bad[1]["las"]["active_periods"] = 5
    check = diag.make_checker()
    state = rev.BatchState()
    for line in bad:
        check(line, diag.BUNDLE, state, {}, {}, identity)
    assert state.stop is not None and state.stop.startswith("H-D1")
    state = rev.BatchState()
    wrong = copy.deepcopy(lines[2])
    wrong["commands_sha256"] = "1" * 64
    diag.make_checker()(wrong, diag.BUNDLE, state, {}, {}, identity)
    assert "D-0b" in state.stop


# ------------------------------------------------------------------------------- seals / wiring
def test_seals_and_stored_files(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"sealed\n")
    sha = tmp_path / "plan.sha256"
    digest = rj.lf_sha256(plan)
    sha.write_text(f"{digest}  plan.md\n", encoding="utf-8")
    assert diag.seal_problems(((plan, sha, digest),)) == []
    plan.write_bytes(b"changed\n")
    assert diag.seal_problems(((plan, sha, digest),))
    assert diag.seal_problems(((tmp_path / "none.md", sha, digest),))
    with pytest.raises(ValueError):
        diag.load_stored_pairs(plan, plan)


def test_d_a_jobs_identity_and_rules():
    jobs = reva.bundle_jobs(diag.BUNDLE, diag.CANDIDATE_NAMES)
    assert [job["rev"]["candidate"] for job in jobs] == list(diag.CANDIDATE_NAMES)
    assert {reva.fb.fb_key({k: v for k, v in job.items() if k not in ("rev", "mask")})
            for job in jobs} == {diag.KEY}
    assert all(job["rev"]["record_diag"] and job["rev"]["record_done"] for job in jobs)
    assert reva.resolve_candidates(diag.BUNDLE, None) == diag.CANDIDATE_NAMES
    block = reva.rules_block(diag.BUNDLE)
    assert block["rules_revA_rev3_sha256"] == diag.RULES_REVA_REV3_SHA256
    assert block["diag_plan_sha256"] == diag.PLAN_SHA256 and len(block) == 7
    assert reva.rules_block() == dict(zip(judge.RULES_FIELDS, judge.RULES_VALUES, strict=True))
    assert "las_revA_diag.py" in reva.DIAG_IDENTITY_FILES
    assert "las_revA_diag.py" not in reva.IDENTITY_FILES


def test_d_a_candidates_are_the_rev_a_settings():
    preset = SimpleNamespace()
    assert reva.CANDIDATES["P0"].settings_from(preset) is preset
    assert (reva.CANDIDATES["P5"].beta, reva.CANDIDATES["P5"].n_r) == (4.5, 0)
    assert (reva.CANDIDATES["P5r4"].beta, reva.CANDIDATES["P5r4"].n_r) == (4.5, 4)


def test_d_a_rejects_keys_and_existing_out(tmp_path):
    out = tmp_path / "diagA.jsonl"
    out.write_text("", encoding="utf-8")
    assert reva.main(["run", "--bundle", diag.BUNDLE, "--keys", diag.KEY]) == 2
    assert rev.out_path_problem(out, diag.DIAGA_DIR) is not None
