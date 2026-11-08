"""Checks of the LAS-b rule and judge (``las_targeted_rules.md`` 1 .. 3), no harness run.

The rule is checked on synthetic gate inputs, the stage lists on ``d1_rows``, the judge on
synthetic lines (the shadow gate: ``test_las_shadow.py``).
Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
The sealed-appendix check reads ``$LAS_RULES_PATH`` / ``$LAS_BASELINE_PATH`` (default: the
project paths; skipped when absent, e.g. in a worktree without the untracked files).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_judge as lj  # noqa: E402
import las_targeted as lt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

B0 = lt.CANDIDATES["b0"]
W_REF_N = 376_600.0
F_MIN_N = 9414.589
V_MAX_M_S = 0.020924
FAST_SPEEDS = np.array([0.020, 0.012, 0.006, 0.0])
"""Mean 9.5 mm/s > 0.16 v_max = 3.35 mm/s (S8 true)."""


def _inputs(**changes) -> lt.GateInputs:
    """All of S1 .. S8 true: sum L = 0.7 W_ref, min L = 2 F_min, rho 0.43 > previous 0.3."""
    loads = (2 * F_MIN_N, 0.3 * W_REF_N, 0.2 * W_REF_N, 0.7 * W_REF_N - 0.5 * W_REF_N
             - 2 * F_MIN_N)
    base = lt.GateInputs(t_s=10.0, soil_enable=True, is_level=True, has_loc_been_seen=False,
                         has_soil_mode_started=False, in_crawler_zone=True,
                         is_reapproaching=False, loads_N=loads, weight_ref_N=W_REF_N,
                         F_min_N=F_MIN_N, mean_speed_m_s=float(FAST_SPEEDS.mean()),
                         v_max_m_s=V_MAX_M_S, previous_rho=0.3)
    return replace(base, **changes)


# ------------------------------------------------------------------------------- start gates
def test_all_gates_true_starts_once_with_the_lowest_leg() -> None:
    state = lt.LasbState()
    inputs = _inputs()
    assert all(lt.start_gates(inputs, B0).values())
    speeds, events = lt.lasb_step(state, inputs, B0, FAST_SPEEDS)
    assert events == ["INFO_LIFTOFF_SLOW:0"]
    assert state.is_active and not state.is_armed and state.t_start_s == 10.0
    assert np.mean(speeds) == pytest.approx(B0.gamma * V_MAX_M_S)


LOW_SUM = (0.1 * W_REF_N, 0.1 * W_REF_N, 0.1 * W_REF_N, 0.1 * W_REF_N)
HIGH_MIN = (4 * F_MIN_N, 0.2 * W_REF_N, 0.2 * W_REF_N, 0.2 * W_REF_N)


@pytest.mark.parametrize(("gate", "changes"), [
    ("S1", {"soil_enable": False}),
    ("S2", {"is_level": False}),
    ("S3", {"has_loc_been_seen": True}),
    ("S4", {"has_soil_mode_started": True}),
    ("S5", {"in_crawler_zone": False}),
    ("S6", {"is_reapproaching": True}),
    ("S7", {"loads_N": LOW_SUM}),
    ("S7", {"loads_N": HIGH_MIN}),
    ("S7", {"previous_rho": None}),
    ("S7", {"previous_rho": 0.5}),
    ("S8", {"mean_speed_m_s": 0.16 * V_MAX_M_S}),
])
def test_each_false_gate_blocks_the_start(gate: str, changes: dict) -> None:
    inputs = _inputs(**changes)
    gates = lt.start_gates(inputs, B0)
    assert [name for name, ok in gates.items() if not ok] == [gate]
    state = lt.LasbState()
    speeds, events = lt.lasb_step(state, inputs, B0, FAST_SPEEDS)
    assert speeds is FAST_SPEEDS and events == [] and state.is_armed and not state.is_active


def test_s7_sum_is_inclusive_and_min_is_strict() -> None:
    edge_N = B0.beta * F_MIN_N
    loads = np.array([edge_N, 0.0, edge_N, edge_N])
    loads[1] = B0.alpha * W_REF_N
    assert not lt.start_gates(_inputs(loads_N=tuple(loads)), B0)["S7"]  # min == beta F_min
    loads[0] = edge_N - 1.0
    loads[1] = B0.alpha * W_REF_N - loads[0] - 2 * edge_N
    assert loads.sum() == pytest.approx(B0.alpha * W_REF_N)
    assert lt.start_gates(_inputs(loads_N=tuple(loads)), B0)["S7"]  # sum == alpha W_ref


# ------------------------------------------------------------------------------- S7' (rev1 2)
def test_rho_is_the_deficit_of_the_lightest_legs_diagonal() -> None:
    rho, leg = lt.diagonal_deficit_ratio([10e3, 40e3, 30e3, 20e3])  # FL + RR = 30 of 100 kN
    assert leg == 0 and rho == pytest.approx((100 - 2 * 30) / 100)


@pytest.mark.parametrize(("lightest", "partner"), [(0, 3), (1, 2), (2, 1), (3, 0)])
def test_diagonal_partners_are_fl_rr_and_fr_rl(lightest: int, partner: int) -> None:
    loads = np.array([50e3, 60e3, 70e3, 80e3])
    loads[lightest] = 5e3
    rho, leg = lt.diagonal_deficit_ratio(loads)
    total = loads.sum()
    assert leg == lightest
    assert rho == pytest.approx((total - 2 * (loads[lightest] + loads[partner])) / total)


def test_a_tie_picks_the_smaller_index() -> None:
    rho, leg = lt.diagonal_deficit_ratio([10e3, 10e3, 50e3, 30e3])
    assert leg == 0 and rho == pytest.approx(0.2)  # FR (partner RL) would give -0.2


def test_rho_needs_a_previous_level_period_and_a_rise() -> None:
    inputs = _inputs()
    rho, _ = lt.diagonal_deficit_ratio(inputs.loads_N)
    assert rho >= B0.rho_on and lt.twist_rise_gate(inputs, B0)
    assert not lt.twist_rise_gate(replace(inputs, previous_rho=None), B0)  # first LEVEL step
    assert not lt.twist_rise_gate(replace(inputs, previous_rho=rho), B0)  # equal: not rising
    low = (20e3, 60e3, 60e3, 65e3)  # rho (205 - 2 x 85) / 205 = 0.17 < 0.18
    assert not lt.twist_rise_gate(replace(inputs, loads_N=low, previous_rho=-1.0), B0)
    assert lt.twist_rise_gate(replace(inputs, previous_rho=None), lt.CANDIDATES["LASa"])


def test_a_period_without_a_level_step_clears_rho() -> None:
    run = lt.LasRun(B0, lt.MODE_ACT)
    inputs = _inputs(previous_rho=None)
    lt.note_twist_ratio(run, inputs, lt.start_gates(inputs, B0))
    assert run.previous_rho == pytest.approx(lt.diagonal_deficit_ratio(inputs.loads_N)[0])
    assert run.s7p_first is None  # no rho_{k-1}: S7' false
    run.has_level_step_run = True
    assert lt.finish_period(run, 10.0) is None and run.previous_rho is not None
    run.has_level_step_run = False
    assert lt.finish_period(run, 10.1) is None and run.previous_rho is None


def test_finish_period_ends_an_active_slowdown_with_phase() -> None:
    run = lt.LasRun(B0, lt.MODE_ACT)
    lt.lasb_step(run.lasb, _inputs(), B0, FAST_SPEEDS)
    assert lt.finish_period(run, 10.1) == "INFO_LIFTOFF_SLOW_END:phase"
    assert run.lasb.end_reason == "phase" and not run.lasb.is_active


def test_s7p_first_records_time_rho_previous_and_leg() -> None:
    run = lt.LasRun(B0, lt.MODE_GATE)
    inputs = _inputs()
    lt.note_twist_ratio(run, inputs, lt.start_gates(inputs, B0))
    rho, _ = lt.diagonal_deficit_ratio(inputs.loads_N)
    assert run.s7p_first == {"t_s": 10.0, "rho": rho, "rho_prev": 0.3, "leg": 0}


def test_rigid_type_lift_never_meets_s7_prime() -> None:
    """Rigid roll (rev1 3): the light leg rises while lifting and both diagonals are even, so
    the lightest leg's diagonal carries more than half (rho < 0)."""
    run = lt.LasRun(B0, lt.MODE_GATE)
    for step in range(20):
        light_N = 25e3 + 1.5e3 * step  # +1.5 kN per period, stays below beta F_min
        loads = (min(light_N, 32e3), 80e3 + 0.5e3 * step, 34e3 + 0.2e3 * step,
                 92e3 + 0.7e3 * step)
        inputs = _inputs(t_s=10.0 + 0.1 * step, loads_N=loads, previous_rho=run.previous_rho)
        assert lt.diagonal_deficit_ratio(loads)[0] < 0.0
        gates = lt.start_gates(inputs, B0)
        lt.note_twist_ratio(run, inputs, gates)
        assert lt.sum_gate(inputs, B0) and lt.min_gate(inputs, B0) and not gates["S7"]
    assert run.s7p_first is None


def test_named_variants_keep_the_sealed_rho_on() -> None:
    assert all(lt.CANDIDATES[name].rho_on == 0.18 for name in lt.LASB_VARIANTS)
    assert lt.CANDIDATES["LASa"].rho_on is None

    class Args:
        rho_on = 0.25

    with pytest.raises(ValueError, match="custom"):
        lt.resolve_candidates(["b0"], Args)


# ------------------------------------------------------------------------------- end reasons
def _started() -> lt.LasbState:
    state = lt.LasbState()
    lt.lasb_step(state, _inputs(), B0, FAST_SPEEDS)
    return state


@pytest.mark.parametrize(("reason", "changes"), [
    ("loc", {"has_loc_been_seen": True}),
    ("phase", {"is_level": False}),
    ("soil", {"has_soil_mode_started": True}),
    ("reapproach", {"is_reapproaching": True}),
])
def test_state_end_reasons_stop_without_acting(reason: str, changes: dict) -> None:
    state = _started()
    speeds, events = lt.lasb_step(state, _inputs(t_s=10.1, **changes), B0, FAST_SPEEDS)
    assert events == [f"INFO_LIFTOFF_SLOW_END:{reason}"]
    assert speeds is FAST_SPEEDS and not state.is_active and state.end_reason == reason
    assert state.end_t_s == 10.1


def test_sum_end_needs_n_end_consecutive_periods_and_resets() -> None:
    state = _started()
    heavy = (0.25 * W_REF_N, 0.25 * W_REF_N, 0.2 * W_REF_N, 0.2 * W_REF_N)  # 0.9 W_ref
    t_s = 10.0
    for _ in range(B0.n_end - 1):
        t_s += 0.1
        lt.lasb_step(state, _inputs(t_s=t_s, loads_N=heavy), B0, FAST_SPEEDS)
    t_s += 0.1
    lt.lasb_step(state, _inputs(t_s=t_s), B0, FAST_SPEEDS)  # 0.7 W_ref: counter back to 0
    assert state.is_active and state.sum_count == 0
    for _ in range(B0.n_end):
        t_s += 0.1
        _, events = lt.lasb_step(state, _inputs(t_s=t_s, loads_N=heavy), B0, FAST_SPEEDS)
    assert events == ["INFO_LIFTOFF_SLOW_END:sum"] and state.end_reason == "sum"


def test_time_end_at_t_max_and_the_start_period_counts() -> None:
    state = _started()  # start period t = 10.0 acted (active period 1)
    for step in range(1, 15):
        _, events = lt.lasb_step(state, _inputs(t_s=10.0 + 0.1 * step), B0, FAST_SPEEDS)
        assert events == []
    _, events = lt.lasb_step(state, _inputs(t_s=10.0 + 1.5 - 1e-12), B0, FAST_SPEEDS)
    assert events == ["INFO_LIFTOFF_SLOW_END:time"]
    assert state.active_periods == 15 and state.scaled_periods == 15


def test_no_second_start_after_an_end() -> None:
    state = _started()
    lt.lasb_step(state, _inputs(t_s=10.1, is_level=False), B0, FAST_SPEEDS)
    speeds, events = lt.lasb_step(state, _inputs(t_s=10.2), B0, FAST_SPEEDS)
    assert speeds is FAST_SPEEDS and events == [] and not state.is_active


# ------------------------------------------------------------------------------- scaling
def test_scale_keeps_the_direction_and_sets_the_mean() -> None:
    cap = B0.gamma * V_MAX_M_S
    scaled = lt.scale_to_mean(FAST_SPEEDS, cap)
    assert np.mean(scaled) == pytest.approx(cap)
    np.testing.assert_allclose(scaled / scaled[0], FAST_SPEEDS / FAST_SPEEDS[0])
    slow = FAST_SPEEDS * (0.5 * cap / FAST_SPEEDS.mean())
    assert lt.scale_to_mean(slow, cap) is slow


def test_active_period_with_a_slow_command_is_not_scaled() -> None:
    state = _started()
    slow = FAST_SPEEDS * 0.1
    speeds, _ = lt.lasb_step(state, _inputs(t_s=10.1, mean_speed_m_s=float(slow.mean())), B0,
                             slow)
    assert speeds is slow and state.active_periods == 2 and state.scaled_periods == 1


# ------------------------------------------------------------------------------- stage lists
def test_stage_counts_and_job_counts() -> None:
    t0 = lt.stage_keys("T-0")
    t1 = lt.stage_keys("T-1")
    t2 = lt.stage_keys("T-2")
    assert (len(t0), len(t1), len(t2)) == (2, 8, 184)
    assert len(set(t2)) == 184 and not set(t1) & set(t2) and set(t0) <= set(t1)
    t1_jobs = lt.build_jobs(t1, lt.resolve_candidates(list(lt.T1_CANDIDATES), None), "act",
                            None, None)
    assert len(t1_jobs) == 48
    assert len({(lt.composite_key(j), j["las"]["name"]) for j in t1_jobs}) == 48
    b0 = lt.resolve_candidates(["b0"], None)
    assert len(lt.build_jobs(t0, lt.resolve_candidates(["current"], None), "act", None,
                             None)) == 2
    assert len(lt.build_jobs(t2, b0, "act", None, None)) == 184
    rigid = [key for key in t2 if "|H-R-0|" in key]
    assert len(rigid) == 48 and all("|T|" in key for key in rigid)


def test_custom_candidate_needs_all_parameters() -> None:
    class Args:
        alpha, beta, gamma, alpha_end, n_end, t_max = 0.6, 3.5, 0.16, 0.85, 5, None

    with pytest.raises(ValueError, match="custom needs"):
        lt.resolve_candidates(["custom"], Args)
    Args.t_max = 1.2
    ((label, params),) = lt.resolve_candidates(["custom"], Args)
    assert params.t_max_s == 1.2 and label.startswith("custom(") and "T=1.2" in label


RULES = Path(os.environ.get("LAS_RULES_PATH", lt.RULES_PATH))
BASELINE = Path(os.environ.get("LAS_BASELINE_PATH", lt.BASELINE_PATH))


@pytest.mark.skipif(not (RULES.exists() and BASELINE.exists()),
                    reason="sealed rules or d1.jsonl absent")
@pytest.mark.parametrize("stage", ["T-0", "T-1", "T-2"])
def test_stage_keys_equal_the_sealed_appendix(stage: str) -> None:
    _, problems = lt.list_check(stage, RULES, BASELINE)
    assert problems == []


# ------------------------------------------------------------------------------- judge
def _line(key: str, verdict: str = "pass", f_N: float = 20_000.0, *, fail_items=(),
          group: str = "H-R-A", sha: str = "a" * 64, started: float | None = None,
          ready: float = 60.0, stroke: float = 0.6, g62: bool = True, faults=(),
          candidate: str = "b0") -> dict:
    return {"job": {}, "commands_sha256": sha,
            "event_names": {name: 1 for name in faults},
            "d1": {"key": key, "group": group, "verdict": verdict, "F_judged_min_N": f_N,
                   "fail_items": list(fail_items), "items": {"G6-2_loc": g62},
                   "t_ready_s": ready, "stroke_max_m": stroke},
            "las": {"key": key, "candidate": candidate, "start_t_s": started,
                    "loc_minus_t_off_s": 1.0}}


def test_keywise_criteria() -> None:
    base = _line("k", "fail", fail_items=("G6-3_Fmin",))
    assert lj.c2_problem(_line("k", "fail", fail_items=("G6-3_Fmin",)), base) is None
    assert "new fail items" in lj.c2_problem(_line("k", "fail", fail_items=("READY",)), base)
    assert "pass -> fail" in lj.c2_problem(_line("k", "fail"), _line("k"))
    assert lj.c3_problem(_line("k", faults=("FAULT_X",)), _line("k")) == "new FAULT ['FAULT_X']"
    assert lj.c4_problem(_line("k", g62=False), _line("k")) is not None
    assert lj.c5_problem(_line("k", ready=70.0), _line("k")) is None  # rule did not start
    assert "READY +10.00" in lj.c5_problem(_line("k", ready=70.0, started=30.0), _line("k"))
    assert "stroke" in lj.c5_problem(_line("k", stroke=0.6015, started=30.0), _line("k"))
    assert lj.c6_problem(_line("k", group="H-R-0", sha="b" * 64), _line("k")) is not None


def test_ranking_tie_window_and_closeness() -> None:
    def summary(worst: float, loc: float = 1.0) -> dict:
        return {"keys": 8, "criteria": {c: True for c in ("C1", "C2", "C3", "C4", "C5")},
                "worst_F_N": worst, "max_loc_minus_t_off_s": loc, "max_ready_up_s": 1.0}

    summaries = {"b0": summary(12_000.0), "b-T20": summary(12_400.0),
                 "b-a5": summary(12_450.0, loc=0.5), "b-a7": summary(11_000.0)}
    # tie window from 12,450 N: b-a5 (smaller LOC delay), then b0 before b-T20 (closeness)
    assert lj.rank_variants(summaries) == ["b-a5", "b0", "b-T20", "b-a7"]
    summaries["b-a5"]["criteria"]["C3"] = False
    assert lj.rank_variants(summaries) == ["b0", "b-T20", "b-a7"]


def test_t2_judge_adopts_only_with_184_clean_keys(tmp_path: Path) -> None:
    keys = [f"D1|H-R-0|k{i}|V0|e0" for i in range(184)]
    baseline = {key: _line(key, group="H-R-0") for key in keys}
    lines = [_line(key, group="H-R-0") for key in keys]
    assert lj.judge_t2(lines, baseline, None, None)["adopted"] == "b0"
    lines[0]["commands_sha256"] = "c" * 64
    result = lj.judge_t2(lines, baseline, None, None)
    assert result["stop"] == "H-4" and "C6" in result["failed_keys"]
    assert result["t2_prime_allowed"] is False


# ------------------------------------------------------------------------------- preset LAS-b
@dataclass(frozen=True)
class _LasSwitch:
    enable: bool


def _stand_in_c2():
    """A ``c2`` with a fresh ``C2Config`` whose preset turns LAS-b on (as after the switch)."""

    @dataclass(frozen=True)
    class StandInConfig:
        liftoff_approach_slow: _LasSwitch = _LasSwitch(False)
        soil_stop: bool = False

        def with_10hz_d1(self, *, soil_stop: bool = True, liftoff_approach_slow: bool = True):
            return replace(self, soil_stop=soil_stop,
                           liftoff_approach_slow=_LasSwitch(liftoff_approach_slow))

    return SimpleNamespace(C2Config=StandInConfig)


def test_wrapper_turns_the_preset_las_off_and_keeps_the_other_keywords() -> None:
    c2 = _stand_in_c2()
    lt._turn_preset_las_off(c2)
    preset = c2.C2Config().with_10hz_d1(soil_stop=False)
    assert preset.liftoff_approach_slow.enable is False
    assert preset.soil_stop is False
    asked = c2.C2Config().with_10hz_d1(liftoff_approach_slow=True)
    assert asked.liftoff_approach_slow.enable is True


def test_a_controller_with_the_preset_las_on_is_refused() -> None:
    c2 = _stand_in_c2()
    on = SimpleNamespace(config=c2.C2Config().with_10hz_d1())
    with pytest.raises(RuntimeError, match="act twice"):
        lt._refuse_preset_las(on)
    lt._refuse_preset_las(SimpleNamespace(config=c2.C2Config()))
    lt._refuse_preset_las(SimpleNamespace(config=SimpleNamespace()))  # an older config
