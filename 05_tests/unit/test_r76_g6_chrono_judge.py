"""Tests for 04_scripts/03_control/s8/r76_g6_chrono_judge.py: record rows (no gates) and the
READY-less gate handling (not-judgeable gates, G6-1 departure-to-end rule)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPT_PATH = (Path(__file__).resolve().parents[2] / "04_scripts" / "03_control" / "s8"
               / "r76_g6_chrono_judge.py")
MODULE_NAME = "r76_g6_chrono_judge"

T_LOOP_START_S = 8.0
F_MIN_N = 9414.58911


def _load_module():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


judge_module = _load_module()


def _result(t_ready_rel_s: float | None, *, setup_relax: dict | None = None) -> dict:
    phases = [{"t_s": T_LOOP_START_S + 1.0, "phase": "level"},
              {"t_s": T_LOOP_START_S + 20.0, "phase": "done"},
              {"t_s": T_LOOP_START_S + 20.1, "phase": "probe"}]
    if t_ready_rel_s is not None:
        phases.append({"t_s": T_LOOP_START_S + t_ready_rel_s, "phase": "ready"})
    result = {
        "p3b": {"t_loop_start_s": T_LOOP_START_S,
                "P3-6_ready": {"t_ready_after_loop_start_s": t_ready_rel_s},
                "P3-2_loc": {"t_loc_s": T_LOOP_START_S + 2.0}},
        "p3b_ext": {"pad_sinkage": {"soft_leg": "RR"}},
        "phases": phases,
        "events": [{"t_s": T_LOOP_START_S + 20.0, "name": "INFO_TWIST_UNSETTLED:-13.2"}],
        "controller_meta": {"twist_relax": {"settings": {"enable": True, "rise_tol_N": 300.0},
                                            "n_relaxed_done": 1, "last_D_N": -13200.0}},
    }
    if setup_relax is not None:
        result["c2_setup"] = {"twist_relax": setup_relax}
    return result


def _write_series(case_dir: Path, decay_per_s: float) -> None:
    """10 Hz D_raw = -20 kN exp(-lambda (t - t0)) and 1 kHz F_cyl with one known dip per leg."""
    completion_t_s = T_LOOP_START_S + np.arange(1, 301) * 0.1
    d_raw_N = -20e3 * np.exp(-decay_per_s * (completion_t_s - T_LOOP_START_S))
    phase = np.where(completion_t_s < T_LOOP_START_S + 20.0, "level", "ready").astype("<U32")
    np.savez(case_dir / "completion_series.npz", t_s=completion_t_s, D_raw_N=d_raw_N, phase=phase)
    step_t_s = T_LOOP_START_S + np.arange(1, 30001) * 1e-3
    forces_N = np.full((step_t_s.size, 4), 50e3)
    dip_index = int(np.searchsorted(step_t_s, T_LOOP_START_S + 25.0))
    forces_N[dip_index, 3] = 30e3
    sinkage_m = np.zeros((step_t_s.size, 4))
    sinkage_m[:, 3] = 0.03
    np.savez(case_dir / "step_series.npz", t_s=step_t_s, F_cyl_N=forces_N,
             pad_sinkage_geometric_m=sinkage_m, sinkage_rate_0p2s_m_s=np.zeros_like(sinkage_m))


def test_record_rows_after_ready_and_decay(tmp_path: Path) -> None:
    decay_per_s = 0.05
    _write_series(tmp_path, decay_per_s)
    rows = judge_module.record_rows(tmp_path, _result(22.0), F_MIN_N)

    after = rows["after_ready"]
    assert after["t_ready_abs_s"] == pytest.approx(30.0)
    assert after["t_done_rel_s"] == pytest.approx(20.0)
    assert after["D_at_done_kN"] == pytest.approx(-20.0 * np.exp(-decay_per_s * 20.0), abs=1e-3)
    assert after["D_at_ready_kN"] == pytest.approx(-20.0 * np.exp(-decay_per_s * 22.0), abs=1e-3)
    rr_minimum = after["F_cyl_min_after_ready"]["RR"]
    assert rr_minimum["min_kN"] == pytest.approx(30.0)
    assert rr_minimum["t_rel_s"] == pytest.approx(25.0)
    assert rr_minimum["ratio_to_F_min"] == pytest.approx(30e3 / F_MIN_N, abs=1e-3)

    decay = rows["end_of_run"]["D_level_decay"]
    assert decay["lambda_per_s"] == pytest.approx(decay_per_s, rel=1e-6)
    # LEVEL samples from LOC + 10 s (t_rel 12 s) up to the DONE at 20 s
    assert decay["t_rel_range_s"] == pytest.approx([12.0, 19.9])
    assert rows["end_of_run"]["soft_pad"]["sinkage_end_mm"] == pytest.approx(30.0)


def test_record_rows_without_ready(tmp_path: Path) -> None:
    _write_series(tmp_path, 0.05)
    rows = judge_module.record_rows(tmp_path, _result(None), F_MIN_N)
    assert rows["after_ready"] is None
    assert rows["end_of_run"]["last_phase"] == "probe"
    last_10s = rows["end_of_run"]["F_cyl_min_last_10s"]
    assert last_10s["RR"]["min_kN"] == pytest.approx(30.0)  # dip at t_rel 25 s, run ends at 30 s
    assert last_10s["FL"]["min_kN"] == pytest.approx(50.0)


def test_relax_record_prefers_c2_setup() -> None:
    setup = {"mode": "off", "overrides": {"twist_completion_relax.enable": False},
             "settings": {"enable": False, "rise_tol_N": 600.0}}
    new_run = judge_module._relax_record(_result(22.0, setup_relax=setup))
    assert new_run["source"] == "c2_setup.twist_relax"
    assert new_run["settings"]["enable"] is False
    old_run = judge_module._relax_record(_result(22.0))
    assert old_run["source"] == "controller_meta.twist_relax"
    assert old_run["settings"]["rise_tol_N"] == 300.0
    assert old_run["n_relaxed_done"] == 1
    assert old_run["n_info_twist_unsettled_events"] == 1


def test_expected_fail_record_and_summary() -> None:
    gates = {"G6-6_fault_ready": False, "READY_le_120s": False, "G6-4_att": True}
    record = judge_module.expected_fail_record(gates, ["G6-6_fault_ready", "READY_le_120s"])
    assert record["as_expected"] is True
    assert record["unexpected_failures"] == []

    surprise = judge_module.expected_fail_record({**gates, "G6-4_att": False}, ["READY_le_120s"])
    assert surprise["as_expected"] is False
    assert surprise["unexpected_failures"] == ["G6-6_fault_ready", "G6-4_att"]

    cases = [{"case": "a", "pass": True}, {"case": "b", "pass": False, "expected_fail": record}]
    summary = judge_module.summarize(cases)
    assert summary["regular_all_pass"] is True
    assert summary["n_regular"] == 1
    assert summary["expected_fail_cases"] == {"b": True}


def test_parse_expect() -> None:
    assert judge_module.parse_expect("case_noTR=G6-6_fault_ready, READY_le_120s") == (
        "case_noTR", ["G6-6_fault_ready", "READY_le_120s"])
    with pytest.raises(SystemExit):
        judge_module.parse_expect("case_without_gates")


def _p3b_without_ready(crawler_max_after_confirm_N: float) -> dict:
    """p3b block of a READY-less run: no crawler_zero, no rut clearance after READY."""
    return {
        "t_loop_start_s": T_LOOP_START_S,
        "departure": {"departed": True, "crawler_normal_max_after_confirm_N":
                      crawler_max_after_confirm_N},
        "P3-1_crawler": {"t_ready_s": None, "recontact_count": 0},
        "P3-2_loc": {"within": True, "t_loc_s": T_LOOP_START_S + 2.0,
                     "loc_minus_departure_s": 0.6, "limit_s": 2.9},
        "P3-3_leg_force": {"within": True, "F_min_after_N": [50e3, 50e3, 50e3, 30e3]},
        "P3-4_attitude": {"within_0p2": False, "p34_absmax_overall_deg": None,
                          "end_mean_roll_pitch_deg": [0.0, 0.0]},
        "P3-5_clearance_stroke": {"rut_clearance_min_after_first_ready_m": None,
                                  "stroke_within": True, "s_motor_max_m": [0.4] * 4},
        "P3-6_ready": {"t_ready_after_loop_start_s": None, "within": False},
        "P3-8_false_triggers": {"within": True, "counts": {}},
    }


def _write_ready_less_case(case_dir: Path, crawler_max_after_confirm_N: float) -> None:
    result = _result(None)
    result["p3b"] = _p3b_without_ready(crawler_max_after_confirm_N)
    result["settle_reference"] = {"roll_pitch_deg": [0.0, 0.15], "z_origin_m": -0.001}
    (case_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    _write_series(case_dir, 0.05)


def test_crawler_zero_uses_ready_window_when_present() -> None:
    p3b = _p3b_without_ready(500.0)
    p3b["P3-1_crawler"]["crawler_zero"] = True
    p3b["P3-6_ready"]["t_ready_after_loop_start_s"] = 22.0
    is_zero, rule = judge_module.crawler_zero_record(p3b)
    assert is_zero is True
    assert rule == judge_module.CRAWLER_ZERO_READY_RULE


@pytest.mark.parametrize(("crawler_max_N", "expected"), [(0.0, True), (12.5, False)])
def test_crawler_zero_without_ready_uses_departure_to_end(crawler_max_N: float,
                                                          expected: bool) -> None:
    is_zero, rule = judge_module.crawler_zero_record(_p3b_without_ready(crawler_max_N))
    assert is_zero is expected
    assert rule == judge_module.CRAWLER_ZERO_NO_READY_RULE


def test_crawler_zero_missing_with_ready_raises() -> None:
    p3b = _p3b_without_ready(0.0)
    p3b["P3-6_ready"]["t_ready_after_loop_start_s"] = 22.0
    with pytest.raises(KeyError):
        judge_module.crawler_zero_record(p3b)


@pytest.mark.parametrize(("rut_min_m", "stroke_within", "expected"), [
    (None, True, False), (0.024, True, False), (0.025, True, True), (0.05, False, False)])
def test_rut_stroke_ok(rut_min_m: float | None, stroke_within: bool, expected: bool) -> None:
    clearance_stroke = {"rut_clearance_min_after_first_ready_m": rut_min_m,
                        "stroke_within": stroke_within}
    assert judge_module.rut_stroke_ok(clearance_stroke) is expected


def test_judge_without_ready_marks_ready_gates_not_judgeable(tmp_path: Path) -> None:
    _write_ready_less_case(tmp_path, crawler_max_after_confirm_N=0.0)
    judgement, _ = judge_module.judge(tmp_path, F_MIN_N)

    ready_gates = list(judge_module.READY_DEPENDENT_GATES)
    assert judgement["not_judgeable_gates"] == ready_gates
    assert judgement["pass"] is False
    assert [name for name, ok in judgement["gates"].items() if not ok] == ready_gates
    assert judgement["gates"]["G6-1_crawler"] is True
    assert judgement["crawler_zero_rule"] == judge_module.CRAWLER_ZERO_NO_READY_RULE
    assert judgement["rut_min_after_ready_mm"] is None

    expected = judge_module.expected_fail_record(judgement["gates"], ready_gates)
    assert expected["as_expected"] is True


def test_judge_without_ready_crawler_load_fails_g6_1(tmp_path: Path) -> None:
    _write_ready_less_case(tmp_path, crawler_max_after_confirm_N=120.0)
    judgement, _ = judge_module.judge(tmp_path, F_MIN_N)
    assert judgement["gates"]["G6-1_crawler"] is False


def test_f_min_from_params_yaml() -> None:
    assert judge_module.load_f_min_N() == pytest.approx(F_MIN_N)
