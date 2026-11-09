"""Tests of ``s2_defer_targeted.py`` (S2D wrappers, trace, jobs) and ``s2_defer_judge.py``.

The trace recorder and the soil-candidate wrapper are checked on the real ``C2Controller`` with
the synthetic soil sink bench of ``05_tests/unit/test_c2_s2d.py`` (commands bit for bit with and
without the recorder); the judge on hand-made lines (no harness run).
"""
from __future__ import annotations

import copy
import hashlib
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
    assert trace["defer_rows"][-1]["end_reason"] == "periods"


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
    rows = [{"t_s": 20.0, "active": True, "in_zone": True, "min_command_m_s": 0.0},
            {"t_s": 20.1, "active": True, "in_zone": False, "min_command_m_s": -1e-3},
            {"t_s": 20.2, "active": False, "in_zone": False, "min_command_m_s": -1.0}]
    line = _line("k", "S-D", trace={"defer_rows": rows})
    assert len(sj.k_s4_problems(line)) == 2
    deferral = {"start_s": 20.0, "end_s": 20.5, "end_reason": "periods", "periods": 5,
                "start_stroke_m": 0.37}
    expired = _line("k", "S-D", soil_start=20.5, deferral=deferral)
    expired["s2d"]["soil"]["soil_mode_start_stroke_m"] = 0.37
    assert sj.k_s5_problems(expired) == []
    expired["s2d"]["soil"]["soil_mode_start_stroke_m"] = 0.376
    assert len(sj.k_s5_problems(expired)) == 1


def test_sc_t_record_checks() -> None:
    deferral = {"start_s": 20.0, "end_s": 20.5, "end_reason": "periods", "periods": 5,
                "start_stroke_m": 0.37}
    rows = [[round(20.0 + 0.1 * index, 10), 3e4] for index in range(-2, 25)]
    cand = _line("k", "S-D", soil_start=20.5, deferral=deferral)
    cand["s2d"]["load_trace"] = {"rows": [[t_s, value - 900.0] for t_s, value in rows]}
    base = _line("k", "S-C", soil_start=20.0)
    base["s2d"]["load_trace"] = {"rows": rows}
    record = sj.sc_t_record(cand, base)
    assert record["checks"] == {"a": True, "b": True, "c": True, "d": True}
    cand["s2d"]["load_trace"]["rows"][10][1] = 3e4 - 1100.0
    assert sj.sc_t_record(cand, base)["checks"]["d"] is False
    late = _line("k", "S-D", soil_start=20.6, deferral=deferral)
    late["s2d"]["load_trace"] = {"rows": rows}
    assert sj.sc_t_record(late, base)["checks"]["a"] is False
    g6 = copy.deepcopy(cand)
    g6["d1"]["items"] = {"G6-3_Fmin": False}
    assert sj.sc_t_record(g6, base)["new_g6_failures"] == ["G6-3_Fmin"]


def test_worst_status_order() -> None:
    assert sj.worst_status([sj.STATUS_PASS, sj.STATUS_FAIL]) == sj.STATUS_FAIL
    assert sj.worst_status([sj.STATUS_UNDECIDABLE, sj.STATUS_FAIL]) == sj.STATUS_UNDECIDABLE
    assert sj.worst_status([sj.STATUS_STOP, sj.STATUS_INCOMPLETE]) == sj.STATUS_STOP
    assert sj.worst_status([sj.STATUS_INCOMPLETE]) == sj.STATUS_INCOMPLETE
    assert math.isclose(sj.Q_S1_STROKE_LIMIT_M, 0.439764)
