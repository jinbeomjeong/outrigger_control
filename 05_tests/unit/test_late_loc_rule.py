"""Spec 419.8 / 419.8.1 (decision 13): the late-LOC FLAG of the reduced harness judges
(``04_scripts/03_control/s9/late_loc_rule.py`` on cad's ``run_S9.p32_late_loc_block``)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "03_control" / "s9"))

import late_loc_rule as rule  # noqa: E402

WEIGHT_N = 376.6e3
F_MIN_KN = 9.415
T_OFF_S = 21.9
T_LOC_S = 25.2
EVENTS = [
    (22.0, "leg_reapproach_start:RR"),
    (22.5, "INFO_LOC_WINDOW_RESTART:RR"),
    (23.9, "leg_reapproach_contact:RR"),
    (T_LOC_S, "crawler_liftoff_confirmed"),
]
"""The ``rigid+J2@FL top Fs0`` shape: LOC 3.3 s after the lift-off, 1.3 s after the re-approach."""
PHASES = [(10.0, "level"), (28.0, "done"), (30.0, "ready")]


def crawler_series(loaded_until_s: float = 21.0, spike: tuple[float, float] | None = None):
    """1 ms true crawler force: loaded until ``loaded_until_s``, then 0 (optional spike)."""
    times = np.round(np.arange(20.0, 27.0, 1e-3), 6)
    forces = np.where(times <= loaded_until_s, 50e3, 0.0)
    if spike is not None:
        forces[np.isclose(times, spike[0])] = spike[1]
    return list(zip(times.tolist(), forces.tolist(), strict=True))


def judge(events=EVENTS, phases=PHASES, series=None, weight_N=WEIGHT_N, **changes) -> dict:
    times = {"t_off_s": T_OFF_S, "t_loc_s": T_LOC_S, "t_done_s": 28.0,
             "min_force_after_off_kN": 20.0}
    times.update(changes)
    return rule.late_loc_reapproach(events, phases, crawler_series() if series is None else series,
                                    weight_N, f_min_kN=F_MIN_KN, **times)


def test_all_five_conditions_give_the_flag_and_the_fields() -> None:
    record = judge()
    assert record["is_flag"] and record["verdict"] == "flag"
    assert all(record["conditions"].values())
    assert record["t_reapproach_end_s"] == 23.9
    assert record["late_loc_reapproach_s"] == pytest.approx(3.3)
    assert record["t_off_s"] == T_OFF_S


def test_the_wrapper_event_counts_as_a_restart() -> None:
    events = [(t, name.replace("INFO_LOC_WINDOW_RESTART", "FIX_LW_RESTART")) for t, name in EVENTS]
    assert judge(events)["is_flag"]


def test_a_restart_before_the_lift_off_counts_when_the_reapproach_overlaps() -> None:
    """419.8.1 (1): LWa writes the event once per non-empty window; the re-approach started and
    cleared the window before t_off and went on after it."""
    events = [(21.0, "leg_reapproach_start:RR"), (21.2, "INFO_LOC_WINDOW_RESTART:RR"),
              (23.9, "leg_reapproach_contact:RR"), (T_LOC_S, "crawler_liftoff_confirmed")]
    assert judge(events)["is_flag"]


def test_inside_the_time_limit_is_a_pass_not_a_flag() -> None:
    record = judge(t_loc_s=24.0)
    assert record["verdict"] == "pass" and not record["is_flag"]


@pytest.mark.parametrize(
    ("changes", "condition"),
    [
        ({"events": [e for e in EVENTS if "RESTART" not in e[1]]}, "1_restart"),
        ({"events": [(19.0, "leg_reapproach_start:RR"), (19.5, "INFO_LOC_WINDOW_RESTART:RR"),
                     (20.0, "leg_reapproach_contact:RR")]}, "1_restart"),  # ended before t_off
        ({"t_loc_s": 26.9}, "2_delay_by_reapproach"),  # 3.0 s after the re-approach end
        ({"events": EVENTS[:2]}, "2_delay_by_reapproach"),  # open interval
        ({"series": crawler_series(spike=(25.15, 0.01 * WEIGHT_N))}, "3_not_false_loc"),
        ({"series": crawler_series(spike=(T_LOC_S, 5e3))}, "3_not_false_loc"),  # at t_LOC
        ({"min_force_after_off_kN": 9.0}, "4_load_strict"),
        ({"events": [*EVENTS, (40.0, "FAULT_STROKE_END:FL")]}, "4_load_strict"),
        ({"phases": [*PHASES, (40.0, "fault_reground")]}, "4_load_strict"),
        ({"t_done_s": 25.0}, "5_loc_before_first_done"),
    ],
)
def test_one_false_condition_keeps_the_failure(changes, condition) -> None:
    record = judge(**changes)
    assert not record["is_flag"] and record["verdict"] == "fail"
    assert record["conditions"][condition] is False


def test_crawler_load_outside_the_loc_period_is_only_recorded() -> None:
    """Condition 3 reads (t_LOC - 0.1 s, t_LOC]; a spike just before that period is ignored."""
    assert judge(series=crawler_series(spike=(25.05, 20e3)))["is_flag"]


def test_without_weight_or_loc_no_flag() -> None:
    assert not judge(weight_N=None)["is_flag"]
    assert not judge(t_loc_s=None)["is_flag"]


# --- spec 420.2b: harness G6-1 / P3-1 by the U-S9-G6d classes ------------------------------------


def recontact_series(recontact_s: float, recontact_N: float):
    """Crawler loaded until 21.0 s, free after, one recontact of ``recontact_s`` at 23.0 s."""
    times = np.round(np.arange(20.0, 30.0, 1e-3), 6)
    forces = np.where(times <= 21.0, 50e3, 0.0)
    forces[(times >= 23.0) & (times < 23.0 + recontact_s - 1e-9)] = recontact_N
    return list(zip(times.tolist(), forces.tolist(), strict=True))


@pytest.mark.parametrize(
    ("recontact_s", "recontact_N", "t_loc_s", "passes", "flags"),
    [
        (0.0, 0.0, 25.0, True, []),  # no recontact
        (0.3, 0.02 * WEIGHT_N, 25.0, True, ["P3-1_transient_recontact"]),
        (0.6, 0.02 * WEIGHT_N, 25.0, False, []),  # longer than 0.5 s
        (0.3, 0.2 * WEIGHT_N, 25.0, False, []),  # above 0.15 W
        (0.3, 0.02 * WEIGHT_N, 23.1, False, []),  # not ended before the LOC
        (0.3, 0.005 * WEIGHT_N, 25.0, True, []),  # below 0.01 W: no recontact event
    ],
)
def test_crawler_gate_uses_the_u_s9_g6d_classes(recontact_s, recontact_N, t_loc_s, passes,
                                                flags) -> None:
    record = rule.crawler_recontact_record(recontact_series(recontact_s, recontact_N), WEIGHT_N,
                                           t_loc_s)
    assert record["departure"]["departed"]
    assert rule.crawler_gate(True, record, legacy_recontact_count=1) == (passes, flags)


def test_crawler_gate_needs_the_ready_crawler_zero_and_falls_back_without_a_record() -> None:
    record = rule.crawler_recontact_record(recontact_series(0.3, 0.02 * WEIGHT_N), WEIGHT_N, 25.0)
    assert rule.crawler_gate(False, record, 0) == (False, [])
    assert rule.crawler_recontact_record([], WEIGHT_N, 25.0) is None
    assert rule.crawler_gate(True, None, 0) == (True, [])
    assert rule.crawler_gate(True, None, 1) == (False, [])


# --- spec 423.3 / 423.4: threshold chatter after the LOC (decision Q-G) -----------------------

THRESHOLD_N = 0.01 * WEIGHT_N
T_LOC_CHATTER_S = 41.4


def _event(start_after_loc_s: float, duration_s: float, peak_over_threshold: float,
           klass: str = "strict_fail") -> dict:
    t_start = T_LOC_CHATTER_S + start_after_loc_s
    return {"t_start_s": t_start, "t_end_s": t_start + duration_s, "duration_s": duration_s,
            "max_normal_N": peak_over_threshold * THRESHOLD_N,
            "max_over_W": peak_over_threshold * 0.01, "ended_before_loc": False, "class": klass}


def _classify(*events, t_ready_s=90.0) -> dict:
    stored = {"events": list(events), "pass": False, "flags": [], "limit_N": THRESHOLD_N}
    return rule.reclassify_recontacts(stored, T_LOC_CHATTER_S, THRESHOLD_N, t_ready_s)


def test_423_1_short_small_event_after_the_loc_is_chatter() -> None:
    result = _classify(_event(0.1, 0.07, 1.06))
    assert [e["class"] for e in result["events"]] == ["threshold_chatter"]
    assert result["pass"] and result["flags"] == ["P3-1_threshold_chatter"]
    assert rule.crawler_gate(True, {"recontact_events": result}, 1) == (
        True, ["P3-1_threshold_chatter"])


@pytest.mark.parametrize(("start_s", "duration_s", "peak"), [
    (0.1, 0.11, 1.06),  # 423.4 test 2: longer than 0.1 s
    (0.1, 0.07, 1.21),  # test 3: above 1.2 x the threshold
    (1.05, 0.07, 1.06),  # test 4: starts later than LOC + 1.0 s
])
def test_423_2_to_4_outside_any_limit_stays_strict(start_s, duration_s, peak) -> None:
    result = _classify(_event(start_s, duration_s, peak))
    assert [e["class"] for e in result["events"]] == ["strict_fail"] and not result["pass"]


def test_423_5_events_before_the_loc_keep_the_transient_rule() -> None:
    before = _event(-0.5, 0.07, 1.06, klass="transient_flag")
    strict_before = _event(-0.5, 0.7, 1.06)
    result = _classify(before, strict_before)
    assert [e["class"] for e in result["events"]] == ["transient_flag", "strict_fail"]
    assert rule.reclassify_recontacts(_classify(before), T_LOC_CHATTER_S, THRESHOLD_N) == (
        _classify(before))  # idempotent


def test_423_6_ready_window_load_still_fails() -> None:
    chatter = {"recontact_events": _classify(_event(0.1, 0.07, 1.06))}
    assert rule.crawler_gate(False, chatter, 0) == (False, [])
    after_ready = _classify(_event(0.1, 0.07, 1.06), t_ready_s=T_LOC_CHATTER_S + 0.05)
    assert [e["class"] for e in after_ready["events"]] == ["strict_fail"]


def test_423_7_one_chatter_and_one_strict_event_fail() -> None:
    result = _classify(_event(0.1, 0.07, 1.06), _event(0.5, 0.3, 1.06))
    assert [e["class"] for e in result["events"]] == ["threshold_chatter", "strict_fail"]
    assert not result["pass"]
    assert rule.crawler_gate(True, {"recontact_events": result}, 0) == (False, [])


def test_chatter_constants_of_spec_423() -> None:
    assert (rule.CHATTER_AFTER_LOC_S, rule.CHATTER_MAX_DURATION_S,
            rule.CHATTER_MAX_OVER_THRESHOLD) == (1.0, 0.1, 1.2)


# --- spec 424.8.1: LOC revoked and confirmed again ----------------------------------------------


def test_loc_timeline_takes_the_first_loc_after_the_last_revocation() -> None:
    events = [(20.3, "crawler_liftoff_confirmed"), (21.5, "FIX_LOC_REVOKE:2.3"),
              (22.0, "crawler_liftoff_confirmed"), (23.0, "FIX_LOC_REVOKE:2.0"),
              (24.0, "crawler_liftoff_confirmed")]
    timeline = rule.loc_timeline(events)
    assert timeline["t_loc_first_s"] == 20.3 and timeline["t_loc_final_s"] == 24.0
    assert timeline["revoked_loc_s"] == [20.3, 22.0] and timeline["t_revoke_last_s"] == 23.0
    assert rule.judged_loc_times(events) == [24.0]
    no_revoke = [(21.0, "crawler_liftoff_confirmed"), (25.0, "crawler_liftoff_confirmed")]
    assert rule.loc_timeline(no_revoke)["t_loc_final_s"] == 21.0
    assert rule.judged_loc_times(no_revoke) == [21.0, 25.0]
    assert rule.loc_timeline([(21.0, "FIX_LOC_REVOKE:2.0")])["t_loc_final_s"] is None


def _revoked(**changes) -> dict:
    arguments = {"t_off_s": 20.0, "t_loc_final_s": 23.5, "t_done_s": 30.0,
                 "revoke_times_s": [22.0], "crawler_loc_period_max_N": 0.0,
                 "weight_N": WEIGHT_N, "min_force_after_off_kN": 20.0, "f_min_kN": F_MIN_KN,
                 "has_fault": False}
    arguments.update(changes)
    return arguments


def test_late_loc_revoked_flag_and_each_condition() -> None:
    assert rule.is_late_loc_revoked(**_revoked())
    record = rule.late_loc_revoked(**_revoked())
    assert record["loc_minus_departure_s"] == pytest.approx(3.5)
    assert record["loc_minus_later_event_s"] == pytest.approx(1.5)
    falsifiers = {"1_revoke": {"revoke_times_s": [19.0]},
                  "2_delay_by_revoke": {"revoke_times_s": [20.5]},
                  "3_not_false_loc": {"crawler_loc_period_max_N": 0.012 * WEIGHT_N},
                  "4_load_strict": {"has_fault": True},
                  "5_loc_before_first_done": {"t_done_s": 23.0}}
    for condition, change in falsifiers.items():
        record = rule.late_loc_revoked(**_revoked(**change))
        assert not record["is_flag"] and record["conditions"][condition] is False, condition
    assert not rule.is_late_loc_revoked(**_revoked(t_loc_final_s=22.5))  # within 2.9 s


def test_late_loc_revoked_takes_the_later_event_with_the_419_8_rule() -> None:
    late_end = _revoked(revoke_times_s=[20.3], t_loc_final_s=23.5,
                        reapproach_restart=True, t_reapproach_end_s=21.0)
    assert rule.late_loc_revoked(**late_end)["loc_minus_later_event_s"] == pytest.approx(2.5)
    assert rule.is_late_loc_revoked(**late_end)
    assert not rule.is_late_loc_revoked(**{**late_end, "reapproach_restart": False})
    assert not rule.is_late_loc_revoked(**{**late_end, "t_reapproach_end_s": None})  # open


def test_t_lim_default_is_the_former_result() -> None:
    """424.8.1 supplement: ``t_lim_s`` = 2.9 s (default) changes nothing."""
    assert judge(t_lim_s=rule.LOC_DELAY_MAX_S) == judge()
    assert judge(t_loc_s=24.0, t_lim_s=2.9) == judge(t_loc_s=24.0)
    assert (rule.late_loc_revoked(**_revoked(t_lim_s=2.9))
            == rule.late_loc_revoked(**_revoked()))


def test_t_lim_boundary_at_2_91_s() -> None:
    """Condition 2 at 2.91 s: a FLAG with T_lim 2.9117 s, none with 2.9 s."""
    revoked = _revoked(revoke_times_s=[21.0], t_loc_final_s=23.91)
    assert rule.is_late_loc_revoked(**revoked, t_lim_s=2.9117)
    assert not rule.is_late_loc_revoked(**revoked, t_lim_s=2.9)
    late = {"t_loc_s": 23.9 + 2.91}  # 2.91 s after the re-approach end
    assert judge(**late, t_lim_s=2.9117)["is_flag"]
    record = judge(**late, t_lim_s=2.9)
    assert not record["is_flag"] and record["conditions"]["2_delay_by_reapproach"] is False


def test_total_delay_cap_of_spec_424_9() -> None:
    """Condition 6: t_LOC^fin - t_off <= (1 + n_revoke) T_lim (one more S-1 window per
    revocation). The J1 A x1.2 shape (12.7 s after the lift-off, LOC 1.5 s after the last of two
    revocations) is no FLAG; the same delay inside 3 T_lim is."""
    long_delay = _revoked(revoke_times_s=[21.0, 31.2], t_loc_final_s=32.7, t_done_s=40.0)
    record = rule.late_loc_revoked(**long_delay)
    assert record["n_revokes"] == 2 and record["total_delay_limit_s"] == pytest.approx(8.7)
    assert record["conditions"]["2_delay_by_revoke"] and not record["conditions"]["6_total_delay"]
    assert not record["is_flag"]
    within = _revoked(revoke_times_s=[21.0, 25.2], t_loc_final_s=26.7)  # 6.7 s <= 8.7 s
    assert rule.is_late_loc_revoked(**within)
    one_revoke = _revoked(revoke_times_s=[24.0], t_loc_final_s=25.9)  # 5.9 s > 5.8 s
    assert not rule.is_late_loc_revoked(**one_revoke)
    assert rule.is_late_loc_revoked(**one_revoke, n_revokes=2)  # explicit count wins
    assert rule.late_loc_revoked(**_revoked(t_loc_final_s=25.8))["conditions"]["6_total_delay"]


def test_total_delay_cap_keeps_the_former_flags() -> None:
    """The former FLAG cases (delay <= 2 T_lim with one revocation) keep their result."""
    record = rule.late_loc_revoked(**_revoked())
    assert record["is_flag"] and record["conditions"]["6_total_delay"]
    assert record["n_revokes"] == 1
    explicit = rule.late_loc_revoked(**_revoked(), n_revokes=1)
    assert explicit == record


def test_recorder_wraps_once_and_keeps_other_hook_markers() -> None:
    calls = []

    def lagged_step(plant, command, valve, steps):
        calls.append(steps)
        return np.arange(16, dtype=float)

    lagged_step.is_truth_hook = True
    module = SimpleNamespace(_lagged_step=lagged_step)
    series: list = []
    rule.install_crawler_recorder(module, lambda: series)
    rule.install_crawler_recorder(module, lambda: series)
    module._lagged_step(SimpleNamespace(t=1.5), None, None, 1)
    assert series == [(1.5, 15.0)] and calls == [1]
    assert module._lagged_step.is_truth_hook and module._lagged_step.is_crawler_recorder
