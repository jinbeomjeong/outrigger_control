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
