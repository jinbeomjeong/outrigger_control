"""Tests of ``s2_defer_targeted.py`` (S2D wrappers, trace, jobs) and ``s2_defer_judge.py``.

The trace recorder and the soil-candidate wrapper are checked on the real ``C2Controller`` with
the synthetic soil sink bench of ``05_tests/unit/test_c2_s2d.py`` (commands bit for bit with and
without the recorder); the judge on hand-made lines (no harness run).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "05_tests" / "unit"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import s2_defer_judge as sj  # noqa: E402
import s2_defer_targeted as st  # noqa: E402
from test_c2_s2d import S2D_VALUES, load_of  # noqa: E402
from test_c2_soil import SinkBench, soil_config  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

BENCH_LIMIT_S = 60.0


@pytest.fixture(scope="module")
def geometry() -> c2.C2Geometry:
    return c2.C2Geometry.from_params(load_params())


@pytest.fixture
def installed():
    yield
    st.uninstall()
    st._INSTALLED.clear()


def _run(geometry, config) -> tuple[list[np.ndarray], c2.C2Controller]:
    bench = SinkBench.touching(geometry, config, load_of("defer_periods", geometry))
    controller = bench.controller
    while controller.phase not in (c2.C2Phase.READY, c2.C2Phase.FAULT) and (
            bench.t_s < BENCH_LIMIT_S):
        bench.step()
    return bench.outputs, controller


# ------------------------------------------------------------------------------- wrappers
def test_trace_recorder_keeps_the_commands_and_records_the_deferral(geometry, installed) -> None:
    plain, plain_controller = _run(geometry, soil_config(**S2D_VALUES))
    st.install_trace_recorder()
    traced, controller = _run(geometry, soil_config(**S2D_VALUES))
    np.testing.assert_array_equal(np.array(plain), np.array(traced))
    assert [e.name for e in plain_controller.events] == [e.name for e in controller.events]
    trace = controller.__dict__[st.TRACE_ATTRIBUTE].to_record()
    defer = controller.meta()["soil"]["defer"]
    (check,) = defer["checks"]
    assert trace["first_check_t_s"] == check["t_s"] == trace["t_rel_s"]
    before = [output for output, t_s in zip(traced, _times(len(traced)), strict=True)
              if t_s < check["t_s"] - 1e-9]
    digest = hashlib.sha256()
    for output in before:
        digest.update(np.asarray(output, dtype=float).tobytes())
    assert trace["prefix_sha256"] == digest.hexdigest()
    active = [row for row in trace["defer_rows"] if row["active"]]
    assert len(active) == defer["deferral"]["periods"]
    assert all(row["in_zone"] and row["min_command_m_s"] >= 0.0 for row in active)
    assert all(row["min_computed_m_s"] >= 0.0 for row in active)
    assert trace["defer_rows"][-1]["end_reason"] == "periods"
    # d = 1: the command computed in a period is the one returned in the next period
    rows = trace["defer_rows"]
    assert controller.config.r8.output_delay_periods == 1
    for earlier, later in zip(rows[:-1], rows[1:], strict=True):
        assert later["min_command_m_s"] == earlier["min_computed_m_s"]
    assert check["rise_delta_N"] == check["rise_N"] - check["prev_rise_N"]
    assert sj.k_s4_problems(_trace_line(controller, trace)) == []


def _trace_line(controller: c2.C2Controller, trace: dict) -> dict:
    """A judge line around a bench controller's meta and trace record."""
    soil = controller.meta()["soil"]
    return {"rev": {"key": "bench"}, "event_names": {sj.DEFER_EVENT: 1},
            "s2d": {"soil": {"t_S_s": soil["soil_mode_t_s"], "defer": soil["defer"],
                             "soil_mode_start_stroke_m": soil["soil_mode_start_stroke_m"]},
                    "trace": trace}}


def test_computed_speeds_reads_the_queue_without_changing_it() -> None:
    from collections import deque

    queued = np.array([0.1, 0.2, 0.3, 0.4])
    state = SimpleNamespace(output_queue=deque([np.zeros(4), queued]),
                            applied_output_m_s=np.full(4, 9.0))
    controller = SimpleNamespace(_state=state)
    computed = st.computed_speeds(controller)
    np.testing.assert_array_equal(computed, queued)
    computed[0] = -1.0
    assert queued[0] == 0.1 and len(state.output_queue) == 2
    state.output_queue.clear()
    np.testing.assert_array_equal(st.computed_speeds(controller), np.full(4, 9.0))


def test_trace_recorder_keeps_the_commands_without_a_deferral(geometry, installed) -> None:
    """Record only: with N_d 0 (no deferral rows) the recorder keeps every command too."""
    plain, plain_controller = _run(geometry, soil_config())
    st.install_trace_recorder()
    traced, controller = _run(geometry, soil_config())
    np.testing.assert_array_equal(np.array(plain), np.array(traced))
    assert [e.name for e in plain_controller.events] == [e.name for e in controller.events]
    assert controller.__dict__[st.TRACE_ATTRIBUTE].defer_rows == []


def _times(count: int) -> list[float]:
    return [round((index + 1) * 0.1, 10) for index in range(count)]


def test_soil_candidate_sets_only_the_deferral_fields(geometry, installed) -> None:
    st.install_soil_candidate({name: sj.SOIL_CANDIDATES["P0"][name] for name in st.DEFER_FIELDS})
    config = soil_config()
    controller = c2.C2Controller(geometry, config)
    soil = controller.config.soil
    assert soil.mode_defer_periods == 5 and soil.mode_defer_shadow is True
    assert soil.mode_defer_stroke_m == 0.006 and soil.mode_defer_rise_factor == 4.0
    restored = c2.SoilResponseSettings(**{name: getattr(soil, name)
                                          for name in c2.SoilResponseSettings.__dataclass_fields__
                                          if name not in st.DEFER_FIELDS})
    assert restored == config.soil
    with pytest.raises(RuntimeError):
        st.install_soil_candidate({})


def test_shadow_candidate_keeps_the_bench_commands(geometry, installed) -> None:
    plain, _ = _run(geometry, soil_config())
    st.install_soil_candidate({name: sj.SOIL_CANDIDATES["P0"][name] for name in st.DEFER_FIELDS})
    shadow, controller = _run(geometry, soil_config())
    np.testing.assert_array_equal(np.array(plain), np.array(shadow))
    assert controller.meta()["soil"]["defer"]["shadow"]["start_s"] is not None


def test_load_trace_takes_the_smallest_leg_force_per_period() -> None:
    from harness_flow import COLUMN, COLUMNS

    t = np.round(np.arange(1, 3001) * 1e-3, 6)
    rows = np.zeros((t.size, len(COLUMNS)))
    rows[:, COLUMN["t"]] = t
    for leg_index, leg in enumerate(("FL", "FR", "RL", "RR")):
        rows[:, COLUMN[f"true_force_{leg}"]] = 1e5 + leg_index * 1e3 + t * 1e3
    rows[1550, COLUMN["true_force_RL"]] = 5e4  # t = 1.551 s -> period ending at 1.6 s
    plant = SimpleNamespace(flow_limiter=SimpleNamespace(rows=lambda: rows))
    trace = st.load_trace(plant, 1.5)
    values = dict((round(t_s, 6), value) for t_s, value in trace["rows"])
    assert trace["t0_s"] == pytest.approx(1.3)
    assert values[1.6] == 5e4
    assert values[1.5] == pytest.approx(1e5 + 1.401e3)  # first row of (1.4, 1.5]
    assert st.load_trace(plant, None) is None


# ------------------------------------------------------------------------------- jobs
def test_bundle_jobs_counts_and_entries() -> None:
    jobs = st.s0_jobs(None)
    assert len(jobs) == 9 and [job["rev"]["id"] for job in jobs] == list(range(9))
    assert {job["rev"]["s2d"]["candidate"] for job in jobs} == {"N0"}
    sc = st.sc_jobs(None)
    assert len(sc) == sj.SC_LINES
    assert all(job["rev"]["record_done"] is False for job in sc)
    a_s = st.as_jobs(None)
    assert len(a_s) == sj.A_S_LINES
    recorded = [job for job in a_s if job["rev"]["s2d"]["soil_record"]]
    assert [job["rev"]["bundle"] for job in recorded] == ["R-S"]
    assert recorded[0]["rev"]["record_diag"] is True


# ------------------------------------------------------------------------------- judge
def _line(key: str, bundle: str, *, soil_start=None, sha="a", checks=(), deferral=None,
          trace=None, d1=None, loc=None, group="H-S-0") -> dict:
    return {"commands_sha256": sha, "final_phase": "ready",
            "job": {"d1": {"group": group}},
            "rev": {"key": key, "bundle": bundle, "label": "P0"},
            "event_names": {}, "d1": d1 or {"verdict": "pass", "fail_items": [],
                                           "items": {}, "t_ready_s": 50.0,
                                           "F_judged_min_N": 2e4, "stroke_max_m": 0.4},
            "s2d": {"bundle": bundle, "soil": {"t_S_s": soil_start, "t_loc_s": loc,
                                               "soil_mode_start_stroke_m": None,
                                               "defer": {"checks": list(checks),
                                                         "deferral": deferral, "shadow": None}},
                    "trace": trace or {"t_rel_s": None, "first_check_t_s": None,
                                       "prefix_sha256": None, "defer_rows": []},
                    "load_trace": None}}


def test_sd_selection_is_seeded_sorted_and_keeps_every_soil_key() -> None:
    lines = [_line(f"k{index:03d}", "S-C", soil_start=10.0 if index % 3 == 0 else None)
             for index in range(120)]
    first, second = sj.sd_selection(lines), sj.sd_selection(list(reversed(lines)))
    assert first == second
    assert len(first["soil_keys"]) == 40 and len(first["random_keys"]) == 40
    assert first["random_keys"] == sorted(first["random_keys"])
    assert not set(first["random_keys"]) & set(first["soil_keys"])


def test_judge_s0_passes_only_with_every_stored_hash() -> None:
    lines = []
    for (bundle, key, label), sha in sj.S0_EXPECTED.items():
        line = _line(key, "S-0", sha=sha)
        line["rev"].update(bundle=bundle, label=label)
        line["controller_tag"] = line["rev"]["controller_tag"] = "final_C4G2_P3_LAS"
        line["job"]["setting"] = "VB"
        line["s2d"].update(settings_match=True, identity={"code_diff_sha256": sj.fb.EMPTY_SHA256},
                           **dict(zip(sj.RULES_FIELDS, sj.RULES_VALUES, strict=True)))
        lines.append(line)
    assert sj.judge_s0(lines)["status"] == sj.STATUS_PASS
    broken = copy.deepcopy(lines)
    broken[0]["commands_sha256"] = "x"
    assert sj.judge_s0(broken)["status"] == sj.STATUS_STOP
    assert sj.judge_s0([])["status"] == sj.STATUS_INCOMPLETE


def test_pair_k_problems() -> None:
    trace = {"t_rel_s": 20.0, "first_check_t_s": 20.0, "prefix_sha256": "p", "defer_rows": []}
    entered = [{"t_s": 20.0, "entered": True}]
    base = _line("k", "S-C", soil_start=20.0, sha="a", checks=entered, trace=trace)
    same = _line("k", "S-D", sha="a", trace=trace)
    assert sj.pair_k_problems(same, base, is_random=False) == []
    changed = _line("k", "S-D", sha="b", trace=trace)
    assert sj.pair_k_problems(changed, base, is_random=False) == []
    other_prefix = _line("k", "S-D", sha="b", trace={**trace, "prefix_sha256": "q"})
    assert any(text.startswith("K-S3") for text in
               sj.pair_k_problems(other_prefix, base, is_random=False))
    not_entered = _line("k", "S-C", soil_start=20.0, checks=[{"t_s": 20.0, "entered": False}],
                        trace=trace)
    found = sj.pair_k_problems(changed, not_entered, is_random=False)
    assert any(text.startswith("K-S2") for text in found)
    no_soil = _line("k", "S-C", trace=trace)
    found = sj.pair_k_problems(changed, no_soil, is_random=True)
    assert any(text.startswith("K-S1") for text in found)


def test_k_s4_and_k_s5() -> None:
    rows = [{"t_s": 20.0, "active": True, "in_zone": True, "min_command_m_s": 0.0,
             "min_computed_m_s": 0.0},
            {"t_s": 20.1, "active": True, "in_zone": False, "min_command_m_s": -1e-3,
             "min_computed_m_s": 0.0},
            {"t_s": 20.2, "active": False, "in_zone": False, "min_command_m_s": -1.0,
             "min_computed_m_s": -1.0}]
    line = _line("k", "S-D", trace={"defer_rows": rows})
    assert len(sj.k_s4_problems(line)) == 2
    deferral = {"start_s": 20.0, "end_s": 20.5, "end_reason": "periods", "periods": 5,
                "start_stroke_m": 0.37}
    expired = _line("k", "S-D", soil_start=20.5, deferral=deferral)
    expired["s2d"]["soil"]["soil_mode_start_stroke_m"] = 0.37
    assert sj.k_s5_problems(expired) == []
    expired["s2d"]["soil"]["soil_mode_start_stroke_m"] = 0.376
    assert len(sj.k_s5_problems(expired)) == 1


def _defer_rows(start_s: float, periods: int, reason: str = "periods",
                computed_m_s: float = 0.0) -> list[dict]:
    """Trace rows of a deferral: ``periods`` active rows, then the end row."""
    rows = [{"t_s": round(start_s + 0.1 * index, 10), "active": True, "in_zone": True,
             "min_command_m_s": 0.0, "min_computed_m_s": computed_m_s,
             "end_reason": None} for index in range(periods)]
    rows.append({"t_s": round(start_s + 0.1 * periods, 10), "active": False, "in_zone": True,
                 "min_command_m_s": computed_m_s, "min_computed_m_s": 0.0,
                 "end_reason": reason})
    return rows


def _deferred_trace(start_s: float = 20.0, periods: int = 5) -> dict:
    return {"t_rel_s": start_s, "first_check_t_s": start_s, "prefix_sha256": "p",
            "defer_rows": _defer_rows(start_s, periods)}


def test_sc_t_record_checks() -> None:
    deferral = {"start_s": 20.0, "end_s": 20.5, "end_reason": "periods", "periods": 5,
                "start_stroke_m": 0.37}
    rows = [[round(20.0 + 0.1 * index, 10), 3e4] for index in range(-2, 25)]
    cand = _line("k", "S-D", soil_start=20.5, deferral=deferral, trace=_deferred_trace())
    cand["s2d"]["load_trace"] = {"rows": [[t_s, value - 900.0] for t_s, value in rows]}
    base = _line("k", "S-C", soil_start=20.0)
    base["s2d"]["load_trace"] = {"rows": rows}
    record = sj.sc_t_record(cand, base)
    assert record["checks"] == {"a": True, "b": True, "c": sj.NOT_APPLICABLE, "d": True}
    cand["s2d"]["load_trace"]["rows"][10][1] = 3e4 - 1100.0
    assert sj.sc_t_record(cand, base)["checks"]["d"] is False
    late = _line("k", "S-D", soil_start=20.6, deferral=deferral, trace=_deferred_trace())
    late["s2d"]["load_trace"] = {"rows": rows}
    assert sj.sc_t_record(late, base)["checks"]["a"] is False
    g6 = copy.deepcopy(cand)
    g6["d1"]["items"] = {"G6-3_Fmin": False}
    g6_record = sj.sc_t_record(g6, base)
    assert g6_record["new_g6_failures"] == ["G6-3_Fmin"] and g6_record["checks"]["c"] is False
    with_items = copy.deepcopy(base)
    with_items["d1"]["items"] = {"G6-1_crawler": True}
    assert sj.sc_t_record(cand, with_items)["checks"]["c"] is True


def test_sc_t_undecidable_parts_rs1_2() -> None:
    """(a) without a P0 soil-mode start and (d) without a covered load window are None
    (undecidable), not violations; SC-T and Q-S3 then read None."""
    deferral = {"start_s": 20.0, "end_s": 20.5, "end_reason": "periods", "periods": 5,
                "start_stroke_m": 0.37}
    rows = [[round(20.0 + 0.1 * index, 10), 3e4] for index in range(-2, 25)]
    cand = _line("k", "S-D", soil_start=20.5, deferral=deferral, trace=_deferred_trace())
    cand["s2d"]["load_trace"] = {"rows": rows}
    no_soil_base = _line("k", "S-C")
    no_soil_base["s2d"]["load_trace"] = {"rows": rows}
    record = sj.sc_t_record(cand, no_soil_base)
    assert record["checks"]["a"] is None
    short = _line("k", "S-C", soil_start=20.0)
    short["s2d"]["load_trace"] = {"rows": rows[:12]}  # ends at 20.9 s < 21.5 s
    record = sj.sc_t_record(cand, short)
    assert record["checks"]["d"] is None and record["min_load_P0_N"] is None
    assert "P0: load trace misses" in record["window_problems"][0]
    gap = _line("k", "S-C", soil_start=20.0)
    gap["s2d"]["load_trace"] = {"rows": rows[:5] + rows[6:]}
    assert sj.sc_t_record(cand, gap)["checks"]["d"] is None
    none_trace = _line("k", "S-C", soil_start=20.0)
    assert sj.sc_t_record(cand, none_trace)["window_problems"] == ["P0: no load trace"]
    assert sj.check_outcome([True, None, sj.NOT_APPLICABLE]) is None
    assert sj.check_outcome([True, None, False]) is False
    assert sj.check_outcome([True, sj.NOT_APPLICABLE]) is True
    assert sj.sc_t_undecidable([record])[0].startswith("k: SC-T ['d']")


def test_deferral_record_problems_rs1_4() -> None:
    ended = {"start_s": 20.0, "end_s": 20.3, "end_reason": "loc", "periods": 3,
             "start_stroke_m": 0.37}
    line = _line("k", "S-D", deferral=ended, trace=_deferred_trace(periods=3))
    line["event_names"] = {sj.DEFER_EVENT: 1}
    assert sj.deferral_record_problems(line) == []
    open_deferral = copy.deepcopy(line)
    open_deferral["s2d"]["soil"]["defer"]["deferral"].update(end_s=None, end_reason=None)
    assert "never ended" in sj.deferral_record_problems(open_deferral)[0]
    reset = copy.deepcopy(line)
    reset["s2d"]["soil"]["defer"]["deferral"] = None
    assert "reset" in sj.deferral_record_problems(reset)[0]
    events_only = _line("k", "S-D")
    events_only["event_names"] = {sj.DEFER_EVENT: 1}
    assert "reset" in sj.deferral_record_problems(events_only)[0]
    twice = copy.deepcopy(line)
    twice["event_names"] = {sj.DEFER_EVENT: 2}
    assert "2 deferral entries" in sj.deferral_record_problems(twice)[0]


def test_k_s4_checks_computed_and_returned_commands_rs1_8() -> None:
    deferral = {"start_s": 20.0, "end_s": 20.3, "end_reason": "loc", "periods": 3,
                "start_stroke_m": 0.37}
    rows = _defer_rows(20.0, 3, reason="loc")
    line = _line("k", "S-D", deferral=deferral, trace={"defer_rows": rows})
    assert sj.k_s4_problems(line) == []
    computed = copy.deepcopy(line)
    computed["s2d"]["trace"]["defer_rows"][2]["min_computed_m_s"] = -1e-6  # last active one
    (problem,) = sj.k_s4_problems(computed)
    assert "computed command" in problem and "t 20.2" in problem
    returned = copy.deepcopy(line)
    returned["s2d"]["trace"]["defer_rows"][0]["min_command_m_s"] = -1e-6
    assert "returned command" in sj.k_s4_problems(returned)[0]
    short = copy.deepcopy(line)
    del short["s2d"]["trace"]["defer_rows"][1]
    assert "2 deferral rows for 3" in sj.k_s4_problems(short)[0]
    unrecorded = copy.deepcopy(line)
    del unrecorded["s2d"]["trace"]["defer_rows"][0]["min_computed_m_s"]
    with pytest.raises(sj.rj.MissingField):
        sj.k_s4_problems(unrecorded)


def test_sh8_counts_the_pair_level_sc_r_rs1_6() -> None:
    base = _line("k", "S-C", sha="a")
    for dt_s, expected in ((5.0, False), (5.1, True)):
        cand = _line("k", "S-D", sha="b")
        cand["d1"]["t_ready_s"] = 50.0 + dt_s
        pair = sj.sc_pair_record(cand, base)
        assert pair["SC-R_fail"] is expected and sj.is_sh8_pair(pair) is expected
    same = _line("k", "S-D", sha="a")
    same["d1"]["t_ready_s"] = 56.0  # an unchanged hash is not in the SC-R population
    assert sj.sc_pair_record(same, base)["SC-R_fail"] is False
    assert sj.sc_violation_count({"x": sj.sc_pair_record(cand, base)}) == 1


def test_flat_entries_rs1_3() -> None:
    checks = [{"t_s": 20.0, "entered": True, "rise_delta_N": -0.5},
              {"t_s": 21.0, "entered": True, "rise_delta_N": -1.0},
              {"t_s": 22.0, "entered": False, "rise_delta_N": 0.0}]
    flat = _line("a", "S-C", checks=checks)
    missing = _line("b", "S-C", checks=[{"t_s": 20.0, "entered": True}])
    result = sj.flat_entries([flat, missing])
    assert result["entries"] == 3 and result["flat"] == 1 and result["flat_keys"] == ["a"]
    assert result["unrecorded"] == 1 and result["unrecorded_keys"] == ["b"]


def test_worst_status_order() -> None:
    assert sj.worst_status([sj.STATUS_PASS, sj.STATUS_FAIL]) == sj.STATUS_FAIL
    assert sj.worst_status([sj.STATUS_UNDECIDABLE, sj.STATUS_FAIL]) == sj.STATUS_UNDECIDABLE
    assert sj.worst_status([sj.STATUS_STOP, sj.STATUS_INCOMPLETE]) == sj.STATUS_STOP
    assert sj.worst_status([sj.STATUS_INCOMPLETE]) == sj.STATUS_INCOMPLETE
    assert math.isclose(sj.Q_S1_STROKE_LIMIT_M, 0.439764)


# ------------------------------------------------------------------------------- S judgement
IDENTITY = {"git_head": "h1", "sha256": {"tool.py": "t1"}, "code_diff_sha256": None,
            "dirty_files": []}


def _identified(line: dict, git_head: str = "h1") -> dict:
    identity = {**IDENTITY, "git_head": git_head, "code_diff_sha256": sj.fb.EMPTY_SHA256}
    line["s2d"].update(settings_match=True, identity=identity,
                       **dict(zip(sj.RULES_FIELDS, sj.RULES_VALUES, strict=True)))
    line["job"]["d1"]["key"] = sj.key_of(line)
    return line


SOIL_KEYS = ("k000", "k001")


def _s_lines() -> tuple[list[dict], dict[str, dict]]:
    """456 S-C lines in the rules-3 groups (two with soil mode) and the S-D lines (by key)
    of the selection, every S-D line equal to its S-C line."""
    sc_lines = []
    for group, count in sj.SOIL_GROUP_COUNTS.items():
        for _ in range(count):
            key = f"k{len(sc_lines):03d}"
            soil_start = 20.0 if key in SOIL_KEYS else None
            sc_lines.append(_identified(_line(key, "S-C", soil_start=soil_start, group=group)))
    sd_lines = {}
    for key in sj.sd_selection(sc_lines)["keys"]:
        line = copy.deepcopy(next(line for line in sc_lines if sj.key_of(line) == key))
        line["rev"]["bundle"] = line["s2d"]["bundle"] = "S-D"
        sd_lines[key] = line
    return sc_lines, sd_lines


def test_judge_s_passes_on_equal_pairs() -> None:
    sc_lines, sd_lines = _s_lines()
    result = sj.judge_s(sc_lines + list(sd_lines.values()))
    assert result["status"] == sj.STATUS_PASS, result["undecidable"]
    assert len(result["pairs"]) == len(SOIL_KEYS) + sj.SD_RANDOM_KEYS
    assert result["sc_t_c_not_applicable"] == {"pairs": 42, "expired_pairs": 0,
                                               "expired_keys": []}


def test_judge_s_unfinished_deferral_is_undecidable_and_keeps_other_violations() -> None:
    sc_lines, sd_lines = _s_lines()
    line = sd_lines["k000"]
    line["s2d"]["soil"]["defer"]["deferral"] = {"start_s": 20.0, "end_s": None,
                                                "end_reason": None, "periods": 2,
                                                "start_stroke_m": 0.37}
    line["final_phase"] = "fault"
    result = sj.judge_s(sc_lines + list(sd_lines.values()))
    assert result["status"] == sj.STATUS_UNDECIDABLE
    assert any("never ended" in text for text in result["undecidable"])
    assert "k000" in result["c2_violations"]  # both recorded (RS1-4)


def test_judge_s_incomplete_sc_and_extra_keys_are_undecidable() -> None:
    sc_lines, sd_lines = _s_lines()
    not_selected = next(line for line in sc_lines if sj.key_of(line) not in sd_lines)
    short = [line for line in sc_lines if line is not not_selected]
    result = sj.judge_s(short + list(sd_lines.values()))
    assert result["status"] == sj.STATUS_UNDECIDABLE
    assert any(text.startswith("S-C: 455 lines") for text in result["undecidable"])
    extra = copy.deepcopy(not_selected)
    extra["rev"]["bundle"] = extra["s2d"]["bundle"] = "S-D"
    result = sj.judge_s(sc_lines + list(sd_lines.values()) + [extra])
    assert result["status"] == sj.STATUS_UNDECIDABLE
    assert result["extra"] == [sj.key_of(extra)] and sj.key_of(extra) not in result["pairs"]


def test_judge_s_window_not_covered_is_undecidable_without_sh7() -> None:
    sc_lines, sd_lines = _s_lines()
    base = next(line for line in sc_lines if sj.key_of(line) == "k000")
    base["s2d"]["soil"]["defer"]["checks"] = [{"t_s": 20.0, "entered": True,
                                               "rise_delta_N": -100.0}]
    base["s2d"]["trace"] = {**_deferred_trace(), "defer_rows": []}
    base["s2d"]["load_trace"] = {"rows": [[round(19.8 + 0.1 * i, 10), 3e4] for i in range(8)]}
    cand = sd_lines["k000"]
    cand["commands_sha256"] = "b"
    cand["s2d"]["soil"].update(t_S_s=20.5, soil_mode_start_stroke_m=0.37)
    cand["s2d"]["soil"]["defer"]["deferral"] = {"start_s": 20.0, "end_s": 20.5,
                                                "end_reason": "periods", "periods": 5,
                                                "start_stroke_m": 0.37}
    cand["s2d"]["trace"] = _deferred_trace()
    cand["s2d"]["load_trace"] = {"rows": [[round(19.8 + 0.1 * i, 10), 3e4] for i in range(27)]}
    cand["event_names"] = {sj.DEFER_EVENT: 1}
    result = sj.judge_s(sc_lines + list(sd_lines.values()))
    assert result["k_problems"] == []
    assert result["checks"]["SC-T"] is None and result["status"] == sj.STATUS_UNDECIDABLE
    assert not any(text.startswith("SH-7") for text in result["asks"])
    assert result["sc_t_c_not_applicable"]["expired_keys"] == ["k000"]


# ------------------------------------------------------------------------------- SH-9, identity
def _stored_l(sc_lines: list[dict], keys: list[str], soil_keys: list[str]) -> dict:
    by_key = {sj.key_of(line): line for line in sc_lines}
    stored = {"F-3": {}, "F-4": {}}
    for index, key in enumerate(keys):
        events = {sj.SOIL_MODE_EVENT: 1} if key in soil_keys else {}
        stored["F-3" if index % 2 else "F-4"][key] = {
            "job": copy.deepcopy(by_key[key]["job"]),
            "commands_sha256": by_key[key]["commands_sha256"], "event_names": events}
    return stored


def test_sh9_check_rs1_9() -> None:
    sc_lines, _ = _s_lines()
    keys = [f"k{index:03d}" for index in range(100, 100 + sj.SH9_KEYS)]
    stored = _stored_l(sc_lines, keys, keys[: sj.SH9_SOIL_KEYS])
    assert sj.sh9_check(sc_lines, stored)["status"] == sj.STATUS_PASS
    assert sj.sh9_check(sc_lines[:150], stored)["status"] == sj.STATUS_INCOMPLETE
    assert sj.sh9_check(sc_lines, None)["status"] == sj.STATUS_UNDECIDABLE
    assert sj.sh9_check([], stored)["status"] == sj.STATUS_INCOMPLETE
    changed = copy.deepcopy(stored)
    changed["F-4"][keys[0]]["commands_sha256"] = "other"
    result = sj.sh9_check(sc_lines[:150], changed)
    assert result["status"] == sj.STATUS_STOP and result["different"] == [keys[0]]
    other_job = copy.deepcopy(stored)
    other_job["F-4"][keys[0]]["job"]["setting"] = "V0"  # not job-identical: not compared
    result = sj.sh9_check(sc_lines, other_job)
    assert result["status"] == sj.STATUS_STOP and result["keys"] == sj.SH9_KEYS - 1


def test_sh9_gate_before_s_d(tmp_path) -> None:
    sc_lines, _ = _s_lines()
    path = tmp_path / st.OUT_NAMES["S-C"]
    path.write_text("\n".join(json.dumps(line) for line in sc_lines) + "\n", encoding="utf-8")
    inputs = st.Inputs(tmp_path, *(tmp_path for _ in range(7)))
    keys = [f"k{index:03d}" for index in range(100, 100 + sj.SH9_KEYS)]
    stored = _stored_l(sc_lines, keys, keys[: sj.SH9_SOIL_KEYS])
    assert st.sh9_gate_problems(inputs, stored) == []
    stored["F-3"][keys[1]]["commands_sha256"] = "other"
    (problem,) = st.sh9_gate_problems(inputs, stored)
    assert problem.startswith("SH-9 stop")


def test_cross_bundle_identity_and_judge_all() -> None:
    s0 = _identified(_line("a", "S-0"))
    sc = _identified(_line("b", "S-C"))
    assert sj.cross_bundle_identity_problems([s0, sc]) == []
    other = _identified(_line("c", "A-S"), git_head="h2")
    assert len(sj.cross_bundle_identity_problems([s0, sc, other])) == 1
    tools = _identified(_line("d", "S-D"))
    tools["s2d"]["identity"]["sha256"] = {"tool.py": "t2"}
    assert len(sj.cross_bundle_identity_problems([s0, tools])) == 1
    error = {"error": "x", "rev": {"key": "e", "s2d": {"bundle": "S-C"}}}
    assert sj.cross_bundle_identity_problems([s0, error]) == []
    stored = {"F-3": {}, "F-4": {}}
    same = sj.judge_all([sc], None, stored, None, None)
    assert same["status"] == sj.STATUS_INCOMPLETE and same["SH-9"]["status"] == "incomplete"
    mixed = sj.judge_all([sc, _identified(_line("b2", "S-C"), git_head="h2")], None, stored,
                         None, None)
    assert mixed["status"] == sj.STATUS_UNDECIDABLE and mixed["identity_across_bundles"]


def test_k_s1_coverage_and_rules_fields() -> None:
    assert sj.k_s1_coverage_problems({"targets": 311, "seen_targets": 311}) == []
    assert sj.k_s1_coverage_problems({"targets": 311, "seen_targets": 310})
    assert sj.k_s1_coverage_problems({"targets": 312, "seen_targets": 312})
    fields = dict(zip(sj.RULES_FIELDS, sj.RULES_VALUES, strict=True))
    assert fields["rules_s2d_rev1_sha256"] == sj.RULES_S2D_REV1_SHA256
    assert st.rules_block() == fields
    sealed = [entry[0].name for entry in sj.sealed_files()]
    assert sealed[:2] == ["s2_soil_defer_rules.md", "s2_soil_defer_rules_rev1.md"]
    assert sj.seal_problems() == []
    line = _identified(_line("k", "S-D"))
    assert sj.rules_problems(line) == []
    del line["s2d"]["rules_s2d_rev1_sha256"]
    assert sj.rules_problems(line)
