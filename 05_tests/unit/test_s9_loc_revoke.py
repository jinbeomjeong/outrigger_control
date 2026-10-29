"""Spec 424.8.1 (user decision 2026-10-29): judged LOC = the last confirmed LOC t_LOC^fin, FLAG
``P3-2_late_loc_revoked`` - unit items 1-6 on the S9 runner side (``run_S9.loc_timeline``,
``recontact_events`` at t_LOC^fin, ``p32_late_loc_revoked_block``, the 419.8 condition 2 with a revocation,
``s1_window_reconstruct_revoked``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import run_S9  # noqa: E402

W = 380_000.0
LIM = 0.01 * W
T_DEP = 10.0
T_FIRST, T_REVOKE, T_FIN = 11.0, 12.0, 13.5  # LOC - departure 3.5 s, t_fin - t_revoke 1.5 s
SOIL = {"settings": {"plateau_window_m": 0.010, "push_speed_fraction": 0.25}}
V_MAX = 0.020924
PHASES = [(0.0, "level"), (20.0, "ready"), (30.0, "done")]
LOC = run_S9.SOIL_LOC_EVENT
REVOKE_EVENTS = [(T_FIRST, LOC), (T_REVOKE, "FIX_LOC_REVOKE:2.3"), (T_FIN, LOC)]


def _series(bumps=()):
    t = np.arange(0.0, 40.0, 1e-3)
    cn = np.where(t < T_DEP, 0.5 * W, 0.0)
    for t0, d, f in bumps:
        cn[(t >= t0 - 1e-9) & (t < t0 + d - 1e-9)] = f * W
    return t, cn


F_MIN = 9415.0
P33 = {"within": True, "F_min_after_N": [20_000.0, 21_000.0, 15_000.0, 16_000.0]}


def _p32(t, cn, events, t_loc):
    tl = run_S9.loc_timeline(events)
    dep = run_S9.crawler_departure(t, cn, W)
    p32 = run_S9.p32_loc_block(t, cn, W, t_loc=t_loc, t_dep=dep["t_departure_s"], t_done=30.0, t_soil_mode=None,
                               soil_meta=SOIL, v_max_m_s=V_MAX)
    p32["late_loc_reapproach"] = run_S9.p32_late_loc_block(
        t, cn, W, events, PHASES, p32, P33,
        t_revoke_last_s=run_S9._last_revoke_before(tl, t_loc))
    p32["late_loc_revoked"] = run_S9.late_loc_revoked_record(tl, p32, P33, W, F_MIN)
    rv = p32["late_loc_revoked"]
    assert rv["decision_source"].startswith("late_loc_rule.late_loc_revoked") and rv["shared_local_agree"]
    return tl, p32


def test_timeline() -> None:
    tl = run_S9.loc_timeline(REVOKE_EVENTS)
    assert tl["t_loc_first_s"] == T_FIRST and tl["t_loc_final_s"] == T_FIN
    assert tl["revoked_loc_s"] == [T_FIRST] and tl["t_revoke_last_s"] == T_REVOKE
    assert tl["loc_revokes"][0]["revoked_loc_s"] == T_FIRST and tl["revoke_source"] == "events"
    # revoked and never confirmed again -> no final LOC
    assert run_S9.loc_timeline(REVOKE_EVENTS[:2])["t_loc_final_s"] is None
    # C2 meta fallback (before the project event exists)
    tm = run_S9.loc_timeline([(T_FIRST, LOC), (T_FIN, LOC)], {"loc_revokes": [{"t_s": T_REVOKE}]})
    assert tm["t_loc_final_s"] == T_FIN and tm["revoke_source"] == "c2_meta soil.loc_revokes"
    # two revocations
    t2 = run_S9.loc_timeline([(11.0, LOC), (11.5, "FIX_LOC_REVOKE:2.0"), (12.0, LOC), (12.5, "FIX_LOC_REVOKE:2.1"),
                              (13.0, LOC)])
    assert t2["revoked_loc_s"] == [11.0, 12.0] and t2["t_loc_final_s"] == 13.0


@pytest.mark.parametrize(("duration", "cls"), [(0.13, "transient_flag"), (0.6, "strict_fail")])
def test_1_2_recontact_after_first_loc_is_before_final_loc(duration, cls) -> None:
    t, cn = _series([(T_FIRST + 0.2, duration, 0.013)])
    dep = run_S9.crawler_departure(t, cn, W)
    tl = run_S9.loc_timeline(REVOKE_EVENTS)
    r = run_S9.recontact_events(t, cn, W, dep, tl["t_loc_final_s"])
    assert [e["class"] for e in r["events"]] == [cls]
    assert r["pass"] is (cls == "transient_flag")
    # the first (revoked) LOC as the basis would make the short one strict (the former definition)
    old = run_S9.recontact_events(t, cn, W, dep, tl["t_loc_first_s"])
    assert [e["class"] for e in old["events"]] == ["strict_fail"]


def test_3_revoke_flag() -> None:
    t, cn = _series()
    _tl, p32 = _p32(t, cn, REVOKE_EVENTS, T_FIN)
    assert p32["within"] is False and p32["loc_minus_departure_s"] == pytest.approx(3.5, abs=1e-6)
    rv = p32["late_loc_revoked"]
    assert rv["loc_minus_later_event_s"] == pytest.approx(1.5) and all(rv["conditions"].values())
    assert rv["flag"] and rv["verdict"] == "flag"
    assert p32["late_loc_reapproach"]["flag"] is False
    assert run_S9.p32_verdict(p32) == "flag"


def test_4_crawler_loaded_at_final_loc_fails() -> None:
    t, cn = _series([(T_FIN - 0.05, 0.1, 0.012)])
    _tl, p32 = _p32(t, cn, REVOKE_EVENTS, T_FIN)
    rv = p32["late_loc_revoked"]
    assert rv["conditions"]["3_not_false_loc"] is False and not rv["flag"] and rv["verdict"] == "fail"
    assert run_S9.p32_verdict(p32) == "fail"


def test_5_no_revoke_unchanged() -> None:
    t, cn = _series()
    events = [(T_FIN, LOC)]
    tl = run_S9.loc_timeline(events)
    assert tl["t_loc_first_s"] == tl["t_loc_final_s"] == T_FIN and tl["loc_revokes"] == []
    dep = run_S9.crawler_departure(t, cn, W)
    p32 = run_S9.p32_loc_block(t, cn, W, t_loc=T_FIN, t_dep=dep["t_departure_s"], t_done=30.0, t_soil_mode=None,
                               soil_meta=SOIL, v_max_m_s=V_MAX)
    a = run_S9.p32_late_loc_block(t, cn, W, events, PHASES, p32, {"within": True})
    b = run_S9.p32_late_loc_block(t, cn, W, events, PHASES, p32, {"within": True},
                                  t_revoke_last_s=run_S9._last_revoke_before(tl, T_FIN))
    assert run_S9._canonical(a) == run_S9._canonical(b)
    p32["late_loc_reapproach"] = a
    assert run_S9.p32_verdict(p32) == a["verdict"] == "fail"
    p32["late_loc_revoked"] = run_S9.late_loc_revoked_record(tl, p32, P33, W, F_MIN)
    assert p32["late_loc_revoked"]["conditions"]["1_revoke"] is False
    assert run_S9.p32_verdict(p32) == "fail"


@pytest.mark.parametrize(("re_end", "flags"), [(12.3, (True, True)), (13.6, (False, False))])
def test_6_with_419_8_both_flags_later_event(re_end, flags) -> None:
    t, cn = _series()
    events = sorted(REVOKE_EVENTS + [(11.5, "leg_reapproach_start:RR"), (11.6, "INFO_LOC_WINDOW_RESTART"),
                                     (re_end, "leg_reapproach_contact:RR")])
    _tl, p32 = _p32(t, cn, events, T_FIN)
    re, rv = p32["late_loc_reapproach"], p32["late_loc_revoked"]
    assert re["conditions"]["1_restart"] and rv["conditions"]["1_revoke"]
    assert (re["flag"], rv["flag"]) == flags
    if flags[0]:
        # later event = re-approach end 12.3 s (after the revocation 12.0 s)
        assert re["loc_minus_later_event_s"] == pytest.approx(1.2) == rv["loc_minus_later_event_s"]
        assert run_S9.p32_verdict(p32) == "flag"


def test_6b_late_revoke_counts_for_the_419_8_flag() -> None:
    """Re-approach ends at 10.5 s, revocation at 12.0 s: condition 2 from the revocation for both."""
    t, cn = _series()
    events = sorted(REVOKE_EVENTS + [(10.2, "leg_reapproach_start:RR"), (10.3, "INFO_LOC_WINDOW_RESTART"),
                                     (10.5, "leg_reapproach_contact:RR")])
    _tl, p32 = _p32(t, cn, events, T_FIN)
    re, rv = p32["late_loc_reapproach"], p32["late_loc_revoked"]
    assert re["loc_minus_later_event_s"] == pytest.approx(1.5) == rv["loc_minus_later_event_s"]
    assert re["flag"] and rv["flag"]


def test_4b_fault_or_low_leg_force_fails() -> None:
    t, cn = _series()
    tl = run_S9.loc_timeline(REVOKE_EVENTS)
    _tl, p32 = _p32(t, cn, REVOKE_EVENTS, T_FIN)
    low = run_S9.late_loc_revoked_record(tl, p32, {"within": False, "F_min_after_N": [9000.0] * 4}, W, F_MIN)
    assert low["conditions"]["4_load_strict"] is False and not low["flag"] and low["verdict"] == "fail"
    p32["late_loc_reapproach"] = {**p32["late_loc_reapproach"], "fault_events": [(25.0, "FAULT_STROKE_END")]}
    fault = run_S9.late_loc_revoked_record(tl, p32, P33, W, F_MIN)
    assert fault["conditions"]["4_load_strict"] is False and fault["shared_local_agree"] is False  # local reads P3-3
    assert not fault["flag"]


@pytest.mark.parametrize("events", [
    REVOKE_EVENTS, REVOKE_EVENTS[:2], [(T_FIN, LOC)], [],
    [(11.0, LOC), (11.5, "FIX_LOC_REVOKE:2.0"), (12.0, LOC), (12.5, "FIX_LOC_REVOKE:2.1"), (13.0, LOC)],
])
def test_timeline_same_as_the_shared_rule(events) -> None:
    llr = run_S9._late_loc_rule_module()
    assert tuple(llr.LOC_REVOKE_EVENTS) == run_S9.LOC_REVOKE_EVENTS and llr.LOC_EVENT == run_S9.SOIL_LOC_EVENT
    assert llr.P32_REVOKED_FLAG == run_S9.P32_LATE_LOC_REVOKED_FLAG
    a, b = run_S9.loc_timeline(events), llr.loc_timeline(events)
    for k in ("t_loc_first_s", "t_loc_final_s", "loc_events_s", "revoked_loc_s", "t_revoke_last_s"):
        assert a[k] == b[k], k
    assert [r["t_s"] for r in a["loc_revokes"]] == b["revoke_times_s"]


def test_t_lim_is_the_p32_limit() -> None:
    """Supplement: condition 2 = 2.905 s is inside the Chrono T_lim 2.9117 s (outside the harness 2.9 s)."""
    t, cn = _series()
    t_fin, t_rev = 13.505, 10.6
    events = [(10.3, LOC), (t_rev, "FIX_LOC_REVOKE:2.0"), (t_fin, LOC)]
    _tl, p32 = _p32(t, cn, events, t_fin)
    rv = p32["late_loc_revoked"]
    assert p32["limit_s"] == pytest.approx(2.9117, abs=1e-4) and rv["t_lim_s"] == p32["limit_s"]
    assert rv["loc_minus_later_event_s"] == pytest.approx(2.905)
    assert rv["conditions"]["2_delay_by_revoke"] and rv["flag"] and rv["shared"]["is_flag"]


@pytest.mark.parametrize(("events", "t_fin", "is_flag"), [
    # one revocation: cap 2 x 2.9117 = 5.8234 s; condition 2 (t_fin - 13.0) <= T_lim in both
    ([(11.0, LOC), (13.0, "FIX_LOC_REVOKE:2.0")], 15.82, True),
    ([(11.0, LOC), (13.0, "FIX_LOC_REVOKE:2.0")], 15.83, False),
    # two revocations: cap 3 x 2.9117 = 8.7351 s
    ([(11.0, LOC), (12.0, "FIX_LOC_REVOKE:2.0"), (13.0, LOC), (16.0, "FIX_LOC_REVOKE:2.1")], 18.73, True),
    ([(11.0, LOC), (12.0, "FIX_LOC_REVOKE:2.0"), (13.0, LOC), (16.0, "FIX_LOC_REVOKE:2.1")], 18.74, False),
])
def test_condition_6_total_delay_cap(events, t_fin, is_flag) -> None:
    """Spec 424.9 decision 1: t_LOC^fin - t_off <= (1 + n_revoke) T_lim (T_lim = P3-2 limit_s)."""
    t, cn = _series()
    _tl, p32 = _p32(t, cn, events + [(t_fin, LOC)], t_fin)
    rv = p32["late_loc_revoked"]
    n = sum(1 for _te, name in events if name.startswith("FIX_LOC_REVOKE"))
    assert rv["local"]["n_revokes"] == n
    assert rv["local"]["total_delay_cap_s"] == pytest.approx((1 + n) * p32["limit_s"])
    assert rv["conditions"]["2_delay_by_revoke"] and rv["conditions"]["6_total_delay"] is is_flag
    assert rv["flag"] is is_flag and run_S9.p32_verdict(p32) == ("flag" if is_flag else "fail")


def test_p35_first_loc_record() -> None:
    rows = [{"t_s": round(0.1 * k, 10), "rut_clearance_m": 0.001 * k} for k in range(200)]
    b = run_S9.p35_clearance_block(rows, [], t_dep=10.0, t_loc=13.5, s_motor_max_m=[0.3] * 4, s_motor_limit_m=0.68,
                                   probe_sinkage=[], t_loc_first=11.0)
    assert b["rut_clearance_at_loc_m"] == pytest.approx(0.135) and b["rut_clearance_at_first_loc_m"] == pytest.approx(0.110)
    same = run_S9.p35_clearance_block(rows, [], t_dep=10.0, t_loc=13.5, s_motor_max_m=[0.3] * 4,
                                      s_motor_limit_m=0.68, probe_sinkage=[])
    assert same["rut_clearance_at_first_loc_m"] == same["rut_clearance_at_loc_m"]


def test_p37_segments() -> None:
    """S-1 replica per segment: LOC at the 21st LEVEL sample, revoked, a fresh window after the revocation."""
    n = 120
    rt = np.round(np.arange(n) * 0.1, 10)
    stroke = np.repeat((np.arange(n) * 0.0005)[:, None], 4, axis=1)
    load = np.full((n, 4), 0.25 * W)
    u = np.full((n, 4), 0.005)
    lev = np.ones(n, bool)
    settings = {"plateau_window_m": 0.010, "plateau_mean_speed_fraction": 0.1, "plateau_rise_max_N": 2000.0,
                "plausibility_fraction": 0.85}
    single = run_S9.s1_window_reconstruct(rt, lev, u, stroke, load, settings, V_MAX, W)
    assert single["t_loc_s"] == pytest.approx(2.0)
    seg = run_S9.s1_window_reconstruct_revoked(rt, lev, u, stroke, load, settings, V_MAX, W, [3.0])
    assert seg["revoked_loc_s"] == [pytest.approx(2.0)]
    assert seg["t_loc_s"] == pytest.approx(5.1)  # first sample after 3.0 s is 3.1 s, + 20 samples
    assert [w["segment"] for w in seg["revoked_windows"]] == [0]
    assert all(w["segment"] == 1 for w in seg["windows"]) and seg["windows"][-1]["t_end_s"] == pytest.approx(5.1)
