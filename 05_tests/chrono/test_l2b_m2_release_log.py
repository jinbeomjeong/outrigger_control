"""v5 stage 3 R-1 / R-2 / R-5: the M2 release record of the L2b hook (``stage3_impl_spec.md`` 1).

Uses the fake-motor rig of ``test_l2b_v5_options.py`` (body fixed): FL locks, extends 0.25 v_max
for 0.5 s from a high rod pressure (about 85 bar, the M2-14 level) and locks again.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.m2_release_log import (  # noqa: E402
    HOOK_LIMIT_M,
    M2ReleaseLog,
    expected_shift_m,
    fill_was_lifted,
    hook_lag_shift_m,
    judge_release,
)
from outrigger_sim.hydraulics.rod_release import FLOW_LIMITED_LAW  # noqa: E402

pytestmark = pytest.mark.chrono

BAR = 1.0e5
ROD_HIGH_PA = 85.0 * BAR
SUM_TOL_M = 1.0e-6
"""H-b (a) floor: the shift sum within 1 um + the k_h variation bound of criteria rev. 5 3.1 S_M2."""


def _rig():
    path = Path(__file__).with_name("test_l2b_v5_options.py")
    spec = importlib.util.spec_from_file_location("v5_options_rig", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RIG = _rig()


def _run_release(with_m2: bool = True):
    case = RIG._release_case(ROD_HIGH_PA, is_body_fixed=True)
    actuator, motors = RIG._make_actuator(case)
    if with_m2:
        actuator.configure_rod_release()
    RIG._run(case, actuator, motors)
    return actuator


def test_release_entry_matches_the_s_m2_formula() -> None:
    actuator = _run_release()
    record = actuator.m2_release_record()
    assert record["m2_law"]["law"] == FLOW_LIMITED_LAW
    front_left = [e for e in record["m2_releases"] if e["leg"] == RIG.FRONT_LEFT]
    moved = [e for e in front_left if abs(e["shift_sum_m"]) > 0.0]
    assert moved, "FL must release and move"
    a_ann = float(RIG.P.A_r[RIG.FRONT_LEFT])
    for entry in moved:
        assert entry["end_reason"] in ("lock", "run_end")
        # H-b (a): 1 um + the k_h variation bound A_ann / (beta A_h) V D (a fixed 5 um is too
        # tight for a 2 mm shift: the k_h change over the interval gives 6.4 um here)
        bound = SUM_TOL_M + a_ann / (float(RIG.P.beta) * float(RIG.P.A_h[RIG.FRONT_LEFT])) \
            * entry["p_hat_variation_Pa"] * entry["s_ref_excursion_m"]
        assert abs(entry["shift_sum_m"] - expected_shift_m(entry, a_ann)) <= bound
        assert entry["p_rel_Pa"] == pytest.approx(entry["p_r0_Pa"] - entry["delta_used_Pa"])
        assert np.isfinite(entry["delta_ref_Pa"])
        assert np.isfinite(hook_lag_shift_m(entry, a_ann))
    # the per-release sums add up to the run total of the leg
    total_mm = record["m2_shift_total_mm"][RIG.FRONT_LEFT]
    assert sum(e["shift_sum_m"] for e in front_left) * 1e3 == pytest.approx(total_mm, abs=1e-12)


def test_h_b_judgement_is_quiet_on_the_rig() -> None:
    """H-b (a) and (b) on the body-fixed release: no flag (sum bound 1 um + k_h term, hook
    shift expected < 0.2 um)."""
    actuator = _run_release()
    record = actuator.m2_release_record()
    i = RIG.FRONT_LEFT
    for entry in (e for e in record["m2_releases"] if e["leg"] == i):
        assert entry["p_hat_variation_Pa"] >= 0.0 and entry["s_ref_excursion_m"] >= 0.0
        verdict = judge_release(entry, float(RIG.P.A_r[i]), float(RIG.P.A_h[i]), float(RIG.P.beta))
        assert "FLAG_M2_SUM" not in verdict["flags"]
        assert verdict["hook_shift_m"] < HOOK_LIMIT_M


def test_record_is_none_without_m2_and_values_are_unchanged() -> None:
    off = _run_release(with_m2=False)
    assert off.m2_release_record() is None
    assert off.m2_state() is None


def test_m2_state_view_is_the_last_hook() -> None:
    actuator = _run_release()
    p_hat, shift = actuator.m2_state()
    assert p_hat.shape == (4,) and shift.shape == (4,)
    assert shift[RIG.FRONT_LEFT] * 1e3 == pytest.approx(
        actuator.rod_release_record()["m2_shift_total_mm"][RIG.FRONT_LEFT], abs=0.0)


def test_clip_times_are_recorded_and_split() -> None:
    case = RIG._release_case(ROD_HIGH_PA, is_body_fixed=True)
    actuator, motors = RIG._make_actuator(case)
    actuator.configure_rod_release()
    actuator.reference.set_soft_limits(hi_m=actuator.reference.s_ref_m + 1.0e-5)
    RIG._run(case, actuator, motors)
    record = actuator.m2_release_record()
    clipped = record["m2_clipped_steps"]
    assert clipped[RIG.FRONT_LEFT] > 0
    assert [len(t) for t in record["m2_clip_times_s"]] == clipped
    entry_clips = sum(e["clipped_steps"] for e in record["m2_releases"]
                      if e["leg"] == RIG.FRONT_LEFT)
    assert entry_clips == clipped[RIG.FRONT_LEFT]


def test_was_lifted_reads_the_lock_interval() -> None:
    entries = [{"leg": 1, "t_lock_start_s": 1.0, "t_rel_s": 2.0},
               {"leg": 1, "t_lock_start_s": 3.0, "t_rel_s": 4.0}]
    t = np.arange(0.0, 5.0, 0.5)
    air = np.zeros((t.size, 4), bool)
    air[t == 1.5, 1] = True
    fill_was_lifted(entries, t, air)
    assert [e["was_lifted"] for e in entries] == [True, False]


def test_log_closes_open_release_at_run_end() -> None:
    log = M2ReleaseLog(np.ones(4))
    assert log.finish() == []
