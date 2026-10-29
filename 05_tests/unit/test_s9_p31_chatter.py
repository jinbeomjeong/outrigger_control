"""Q-G (2026-10-29, spec 423.3 / 423.4): P3-1 ``threshold_chatter`` class on the S9 runner
(``run_S9.recontact_events``) - spec 423.4 unit items 1-7 on the run_S9 side."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

W = 380_000.0
LIM = 0.01 * W  # departure limit (P3a-2 fraction 0.01, same W)
T_LOC = 14.0


def _run(bumps, t_loc=T_LOC):
    """Crawler loaded until 10 s, off after it, plus (start, duration, peak / limit) bumps."""
    t = np.arange(0.0, 40.0, 1e-3)
    cn = np.where(t < 10.0, 0.5 * W, 0.0)
    for t0, d, f in bumps:
        cn[(t >= t0 - 1e-9) & (t < t0 + d - 1e-9)] = f * LIM
    dep = run_S9.crawler_departure(t, cn, W)
    assert dep["departed"] and dep["t_departure_s"] == pytest.approx(10.0)
    return run_S9.recontact_events(t, cn, W, dep, t_loc)


def test_constants() -> None:
    c = run_S9.chatter_constants()
    assert (c["CHATTER_AFTER_LOC_S"], c["CHATTER_MAX_DURATION_S"], c["CHATTER_MAX_OVER_THRESHOLD"]) == (1.0, 0.1, 1.2)
    assert run_S9.P31_CHATTER_FLAG == "P3-1_threshold_chatter"


def test_1_chatter_is_a_flag() -> None:
    r = _run([(T_LOC + 0.1, 0.07, 1.06)])
    (e,) = r["events"]
    assert e["class"] == "threshold_chatter" and e["max_over_limit"] == pytest.approx(1.06)
    assert e["start_after_loc_s"] == pytest.approx(0.1, abs=1e-6) and e["duration_s"] == pytest.approx(0.07, abs=1e-6)
    assert r["pass"] and r["flags"] == ["P3-1_threshold_chatter"]
    assert "Q-G chatter" in r["rule"] and "U-S9-G6d" in r["rule"]


@pytest.mark.parametrize("bump", [
    (T_LOC + 0.1, 0.11, 1.06),   # 2: 0.11 s > 0.1 s
    (T_LOC + 0.1, 0.07, 1.21),   # 3: 1.21 x limit > 1.2
    (T_LOC + 1.05, 0.07, 1.06),  # 4: starts 1.05 s after the LOC
])
def test_2_3_4_strict(bump) -> None:
    r = _run([bump])
    assert [e["class"] for e in r["events"]] == ["strict_fail"] and not r["pass"] and r["flags"] == []


def test_5_before_loc_keeps_the_transient_rule() -> None:
    small = _run([(T_LOC - 0.5, 0.07, 1.06)])  # chatter-sized but before the LOC: transient rule
    assert [e["class"] for e in small["events"]] == ["transient_flag"]
    assert small["flags"] == ["P3-1_transient_recontact"]
    crossing = _run([(T_LOC - 0.05, 0.07, 1.06)])  # starts before, ends after the LOC: strict as before
    assert [e["class"] for e in crossing["events"]] == ["strict_fail"] and not crossing["pass"]
    no_loc = _run([(T_LOC + 0.1, 0.07, 1.06)], t_loc=None)
    assert [e["class"] for e in no_loc["events"]] == ["strict_fail"]


def _checks(crawler_zero: bool, rc: dict) -> dict:
    out = {"P3-1_crawler": {"crawler_zero": crawler_zero, "recontact_events": rc},
           "departure": {"recontact_t_s": None}, "P3-2_loc": {}, "P3-3_leg_force": {},
           "P3-4_attitude": {"within_0p2": True}, "P3-5_clearance_stroke": {}, "P3-7_plateau": {},
           "P3-9_deferred": {"windows": []}, "reapproach_limit": {"fired": False, "by_cause": {}},
           "P3-6_ready": {"within": True}, "P3-8_false_triggers": {"within": True},
           "pre_liftoff_min_F_cyl": {"any_flag": False}, "W61_watch": {"warnings": []}}
    return run_S9.p3b_checks(out)


def test_6_ready_window_load_still_fails() -> None:
    rc = _run([(T_LOC + 0.1, 0.07, 1.06)])
    c = _checks(False, rc)  # crawler loaded in READY .. READY + 10 s
    assert c["P3-1_crawler_zero_after_ready"] is False
    assert c["P3-1_recontact_pass"] is True and c["P3-1_flags"] == ["P3-1_threshold_chatter"]
    ok = _checks(True, rc)
    assert ok["P3-1_crawler_zero_after_ready"] is True and ok["P3-1_recontact_classes"] == ["threshold_chatter"]


def test_chatter_sized_event_after_ready_is_strict() -> None:
    """late_loc_rule.is_threshold_chatter: the event must start before READY (READY recontacts stay strict)."""
    bump = (T_LOC + 0.1, 0.07, 1.06)
    t = np.arange(0.0, 40.0, 1e-3)
    cn = np.where(t < 10.0, 0.5 * W, 0.0)
    cn[(t >= bump[0] - 1e-9) & (t < bump[0] + bump[1] - 1e-9)] = bump[2] * LIM
    dep = run_S9.crawler_departure(t, cn, W)
    before = run_S9.recontact_events(t, cn, W, dep, T_LOC, t_ready_s=T_LOC + 0.5)
    after = run_S9.recontact_events(t, cn, W, dep, T_LOC, t_ready_s=T_LOC + 0.05)
    assert [e["class"] for e in before["events"]] == ["threshold_chatter"] and before["pass"]
    assert [e["class"] for e in after["events"]] == ["strict_fail"] and not after["pass"]


def test_same_classification_as_the_harness_rule() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_llr_test", ROOT / "04_scripts" / "03_control" / "s9" / "late_loc_rule.py")
    llr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llr)
    if not hasattr(llr, "is_threshold_chatter"):
        pytest.skip("late_loc_rule.is_threshold_chatter not defined yet")
    assert run_S9.chatter_constants()["TIME_TOLERANCE_S"] == llr.TIME_TOLERANCE_S
    cases = [(T_LOC + 0.1, 0.07, 1.06), (T_LOC + 0.1, 0.11, 1.06), (T_LOC + 0.1, 0.07, 1.21),
             (T_LOC + 1.05, 0.07, 1.06), (T_LOC + 0.999, 0.05, 1.19), (T_LOC + 0.3, 0.1, 1.2)]
    for bump in cases:
        for t_ready in (None, T_LOC + 0.2, T_LOC + 5.0):
            t = np.arange(0.0, 40.0, 1e-3)
            cn = np.where(t < 10.0, 0.5 * W, 0.0)
            cn[(t >= bump[0] - 1e-9) & (t < bump[0] + bump[1] - 1e-9)] = bump[2] * LIM
            dep = run_S9.crawler_departure(t, cn, W)
            r = run_S9.recontact_events(t, cn, W, dep, T_LOC, t_ready_s=t_ready)
            (e,) = r["events"]
            assert (e["class"] == "threshold_chatter") == llr.is_threshold_chatter(e, T_LOC, LIM, t_ready), (bump,
                                                                                                          t_ready)


@pytest.mark.parametrize(("args", "limit"), [
    ({"soil": "J1", "pad_variant": "dwg_rear250"}, 100.0),
    ({"soil": "J2", "pad_variant": "dwg_rear250", "floor_roll": 0.0, "floor_pitch": 0.0}, 100.0),
    ({"soil": "S1", "pad_variant": "dwg_rear250"}, 100.0),
    ({"soil": "J1", "pad_variant": "cad330"}, 90.0),
    ({"soil": "G1", "pad_variant": "dwg_rear250"}, 90.0),
    ({"soil": "J1", "pad_variant": "dwg_rear250", "floor_roll": 3.3}, 120.0),
    ({"soil": "G1", "pad_variant": "dwg_rear250", "floor_pitch": 3.2}, 120.0),
    ({"soil": "G1", "pad_variant": "dwg_rear250", "soil_patch": "RR:J1"}, 90.0),   # one rear pad soft
    ({"soil": "J1", "pad_variant": "dwg_rear250", "soil_patch": "FL:G1"}, 100.0),  # both rear pads J1
    ({"soil": "J1", "pad_variant": "dwg_rear250", "soil_patch": "RL:G1"}, 90.0),
    (None, 90.0),
])
def test_p36_ready_limit_rows(args, limit) -> None:
    assert run_S9.p36_ready_limit(args)["limit_s"] == limit


def test_7_chatter_plus_strict_fails() -> None:
    r = _run([(T_LOC + 0.1, 0.07, 1.06), (T_LOC + 5.0, 0.2, 1.06)])
    assert [e["class"] for e in r["events"]] == ["threshold_chatter", "strict_fail"]
    assert not r["pass"] and r["flags"] == ["P3-1_threshold_chatter"]
    c = _checks(True, r)
    assert c["P3-1_recontact_pass"] is False
