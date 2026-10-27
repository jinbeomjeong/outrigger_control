"""C-S8-72 (``s6_control_spec.md`` rev. 67 345): runner and judge changes.

* ``run_S8C.py``: event leg per case, the ``loc+3.0`` reference (LOC = controller event
  ``crawler_liftoff_confirmed``) with the phase offset, the controller phase at the event start
  (``phase_mismatch``), the 11 cases of set ``g1``; every earlier case / set / event definition
  keeps its hash (aggregates computed at master e8ef7df before the change).
* ``run_S6C.py``: set ``ps7r8`` (PS-7a RR / FL, 7b / 7c RR on the R8 preset), snapshot check
  variant with one pre-grounded leg (``verify.s6_bundle_c``), ``s6_stage2`` pre-grounded
  snapshot names.
* judges: U-S8-32 / U57 split with the event leg general (FL / RL), PS-7 TOUCH FLAG rule."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

BEFORE = {
    # sha256 of json.dumps({case id: sha256(json.dumps(meta, sort_keys, default=str))},
    # sort_keys) at master e8ef7df (before C-S8-72)
    "s8": (107, "6aa502598342c8c92b31de4a4bcdcd74b7d8fd097b33f6b921ebec2648746386"),
    "s8_sets": (12, "3148b7717d472e5b5df90470c81c5f06bbdec658bac19fd9e53fcc232eed1831"),
    "s6": (72, "e8e8457f58aa3d640883607fd585bf3125f5af65944ca51ebff162672f586151"),
    "s6_sets": (5, "b4c0b04f1435f9ec0175f718cfac0f4f88833cea801a737d18d5e68d0dc98e33"),
    "stage2": (68, "6031cc03b858f3404cb3b9d9856c3c8f3af37c6ce9a99ff14e97a751e1858216"),
    "s8_events": (15, "96535bd933e145739e2156332e3df0eae5e47e7efe4ca15f1c7150631ca67a02"),
}
G1_IDS = ["G1L_RE1bF_FL_top_Fs0", "G1L_RE1bF_FR_top_Fs0", "G1L_FS24_FR_top_Fs0",
          "G1L_FS24_FL_top_Fs0", "G1L_RE1bF_FL_top_Fs8", "G1R_RE1bF_FL_top_Fs0",
          "G1R_FS24_FL_top_Fs0", "G1R_RE1bF_FR_top_Fs0", "G1L_RE1bF_RL_top_Fs0",
          "G1L_G4_RR_bottom_Fs8", "G1L_RE1bF_FL_bottom_Fs0"]
PS7_IDS = ["PS7a_RR_R8", "PS7a_FL_R8", "PS7b_RR_R8", "PS7c_RR_R8"]


@pytest.fixture(scope="module")
def s8c():
    import run_S8C

    return run_S8C


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _agg(d: dict) -> tuple[int, str]:
    return len(d), hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def test_earlier_definitions_unchanged(s8c) -> None:
    s6c, st = s8c.s6c, s8c.s6c.st
    # C-S8-74 (spec rev. 68 355.1): its 16 cases / set ``c74`` came later; excluded as g1.
    # C-S8-75 (358.6): set ``c75`` (existing case ids only) came later; excluded the same way
    # C-S8-76 (spec rev. 69 363): sets ``g8c76`` / ``g8c76_p28`` came later; excluded the same way
    g8_sets = ("g8c76", "g8c76_p28", "g8c76_p28acc")
    new_s8 = set(G1_IDS) | set(s8c.C74_CASE_IDS)
    new_s6 = set(PS7_IDS) | {c.case_id for n in g8_sets for c in s8c.s6c.CASE_SETS[n]()}
    doc = {"s8": {c.case_id: _h(c.to_meta()) for c in s8c.s8_cases()
                  if c.case_id not in new_s8},
           "s8_sets": {n: [c.case_id for c in s8c.case_set(n)] for n in s8c.SET_NAMES
                       if n not in ("g1", "c74", "c75")},
           "s8_events": {k: _h(v) for k, v in s8c.EVENTS.items()
                         if k not in s8c.G1_EVENT_NAMES},
           "s6": {}, "s6_sets": {},
           "stage2": {c.case_id: _h(asdict(c)) for c in st.all_cases()}}
    for name, fn in s6c.CASE_SETS.items():
        if name == "ps7r8" or name in g8_sets:
            continue
        cases = fn()
        doc["s6_sets"][name] = [c.case_id for c in cases]
        for c in cases:
            doc["s6"][c.case_id] = _h(c.to_meta())
    for c in s6c.case_table().values():
        if c.case_id not in new_s6:
            doc["s6"][c.case_id] = _h(c.to_meta())
    for key, want in BEFORE.items():
        assert _agg(doc[key]) == want, key


def test_g1_set_matches_spec_table(s8c) -> None:
    cases = s8c.case_set("g1")
    assert [c.case_id for c in cases] == G1_IDS
    want = {  # 345.1: (leg, anchor, offset, F_s, level, base)
        "G1L_RE1bF_FL_top_Fs0": ("FL", "loc+3.0", 0.05, 0.0, "top", "RE1bF"),
        "G1L_RE1bF_FR_top_Fs0": ("FR", "loc+3.0", 0.075, 0.0, "top", "RE1bF"),
        "G1L_FS24_FR_top_Fs0": ("FR", "loc+3.0", 0.025, 0.0, "top", "FS24"),
        "G1L_FS24_FL_top_Fs0": ("FL", "loc+3.0", 0.075, 0.0, "top", "FS24"),
        "G1L_RE1bF_FL_top_Fs8": ("FL", "loc+3.0", 0.0, 8.0, "top", "RE1bF"),
        "G1R_RE1bF_FL_top_Fs0": ("FL", "ready+5", 0.0, 0.0, "top", "RE1bF"),
        "G1R_FS24_FL_top_Fs0": ("FL", "ready+5", 0.025, 0.0, "top", "FS24"),
        "G1R_RE1bF_FR_top_Fs0": ("FR", "ready+5", 0.075, 0.0, "top", "RE1bF"),
        "G1L_RE1bF_RL_top_Fs0": ("RL", "loc+3.0", 0.0, 0.0, "top", "RE1bF"),
        "G1L_G4_RR_bottom_Fs8": ("RR", "loc+3.0", 0.0, 8.0, "bottom", "G4"),
        "G1L_RE1bF_FL_bottom_Fs0": ("FL", "loc+3.0", 0.0, 0.0, "bottom", "RE1bF"),
    }
    depth = {"RE1bF": (0.030, 0.05, True), "FS24": (0.024, 0.3, True),
             "G4": (0.0115, 2.0, False)}
    for c in cases:
        leg, at, off, fs, level, base = want[c.case_id]
        ev = c.event_spec()
        assert (ev["leg"], ev["at"], ev["g1_base"]) == (leg, at, base)
        assert c.phase_offset_s == off and c.fs_kN == fs and c.scenario.level == level
        assert (ev["depth_m"], ev["ramp_s"], bool(ev["fine"])) == depth[base]
        assert ev["kind"] == "settle" and c.group == "G1" and c.engine == "L2b_NSC"
        assert ev["expected_phase"] == ("level" if at == "loc+3.0" else "ready")
        assert c.scenario.items == () and c.scenario.floor == "flat"
        rule = s8c.end_rule(c)
        if at == "loc+3.0":
            assert rule["anchor"] == "ready_after_event"
            assert rule["after_s"] == 5.0 and rule["cap_after_event_s"] == 50.0
            assert ev["loc_offset_s"] == 3.0
        else:
            assert rule["anchor"] == "event" and rule["after_s"] == 45.0
        if ev["fine"]:
            assert ev["fine_watch"] == "all"
    assert all(c.group not in s8c.MAIN_GROUPS for c in cases)
    assert not set(G1_IDS) & {c.case_id for c in s8c.case_set("all")}


def test_g1_event_state_phase_mismatch(s8c) -> None:
    ev = s8c.EVENTS["G1L_RE1bF_FL"]
    st = {"loc_t": 120.0, "ready_t": None, "event_t": 123.05, "phase_at_event": "level",
          "ready_after_event_t": 140.0}
    es = s8c.g1_event_state(ev, st, 100.0, 0.05)
    assert es["reference_t_s"] == pytest.approx(23.0) and es["event_t_s"] == pytest.approx(23.05)
    assert es["phase_mismatch"] is False and es["loc_t_s"] == pytest.approx(20.0)
    es = s8c.g1_event_state(ev, {**st, "phase_at_event": "done"}, 100.0, 0.05)
    assert es["phase_mismatch"] is True
    es = s8c.g1_event_state(s8c.EVENTS["G1R_FS24_FL"],
                            {**st, "loc_t": None, "ready_t": 140.0, "phase_at_event": "ready"},
                            100.0, 0.025)
    assert es["reference_t_s"] == pytest.approx(45.0) and es["phase_mismatch"] is False
    assert s8c.g1_event_state(None, st, 100.0, 0.0) is None


def test_worker_layout_p8e3(s8c) -> None:
    assert s8c.WORKER_LAYOUTS["p8e3"] == {"pcore": 8, "ecore": 3}
    plan = s8c.plan(s8c.case_set("g1"), "p8e3")
    assert plan["p8e3"]["cases_per_pool"] == {"pcore": 8, "ecore": 3}


@pytest.mark.parametrize("leg, diag, adj", [("FL", "RR", ("FR", "RL")),
                                            ("RL", "FR", ("FL", "RR")),
                                            ("FR", "RL", ("FL", "RR"))])
def test_u_s8_32_split_event_leg_general(leg, diag, adj) -> None:
    from outrigger_sim.verify import s8_control as s8

    t = np.round(np.arange(0.0, 14.0, 1e-3), 6)
    air = np.zeros((t.size, 4), bool)
    z = np.zeros((t.size, 4))
    j_d = s8.LEGS.index(diag)
    lift = (t >= 10.3) & (t < 11.2)  # diagonal lifted 0.9 s after a front / rear settlement
    air[lift, j_d] = True
    z[lift, j_d] = 0.001
    j_a = s8.LEGS.index(adj[0])
    late = (t >= 13.0) & (t < 13.05)  # adjacent late lift outside the window (ends 12.02 s)
    air[late, j_a] = True
    sp = s8.settle_lift_split(t, air, z, 10.0, leg, 0.03, 0.05, t3_s=0.82)
    assert sp["event_legs"] == [leg, diag] and tuple(sp["adjacent_legs"]) == adj
    assert sp["primary"] == diag
    assert sp["event_cum_max_s"] == pytest.approx(0.9, abs=2e-3)
    assert sp["event_recontact_max_rel_s"] == pytest.approx(1.2, abs=2e-3)
    assert sp["window_end_rel_s"] == pytest.approx(1.2 + 0.82, abs=2e-3)
    assert sp["event_pass"] is True
    assert sp["adjacent_outside_window_s"] == pytest.approx(0.05, abs=2e-3)
    assert sp["u57_pass"] is False


def test_g1_harness_match() -> None:
    from outrigger_sim.verify import s8_control as s8

    runs = [{"event": "RE1bF", "leg": "FL", "level": "top", "fs_kN": 0.0, "timing": "level",
             "offset_s": 0.05, "pair_union_s": 2.067, "pair_last_touch_s": 2.4, "file": "x"},
            {"event": "RE1bF", "leg": "FL", "level": "top", "fs_kN": 0.0, "timing": "level",
             "offset_s": 0.0, "pair_union_s": 1.0, "file": "x"}]
    hm = s8.g1_harness_match(runs, base="RE1bF", leg="FL", level="top", fs_kN=0.0,
                             timing="level", offset_s=0.05)
    assert hm["pair_union_s"] == 2.067
    assert s8.g1_harness_match(runs, base="RE1bF", leg="FR", level="top", fs_kN=0.0,
                               timing="level", offset_s=0.05) is None


def _payload(state=(5, 5, 5, 5), f_lock=(0, 0, 0, 0), contact=(False,) * 4, u=(0, 0, 0, 0)):
    return {"rod_chamber.l1r_state": np.asarray(state, float),
            "rod_chamber.l1r_F_lock_N": np.asarray(f_lock, float),
            "ground_bushing.in_contact": np.asarray(contact, bool),
            "l1_actuator.u_applied_m_s": np.asarray(u, float)}


def test_retag_check_preground_variant() -> None:
    from outrigger_sim.verify import s6_bundle_c as bc

    rrpre = _payload(state=(5, 5, 5, 3), f_lock=(0, 0, 0, 11922.66),
                     contact=(False, False, False, True))
    assert not bc.snapshot_retag_check(rrpre)["passed"]  # unchanged default rule
    chk = bc.snapshot_retag_check(rrpre, preground_leg="RR")
    assert chk["passed"] and chk["preground_leg"] == "RR"
    bad = bc.snapshot_retag_check(rrpre, preground_leg="FL")
    assert not bad["passed"]
    assert bad["conditions"]["no_pad_contact"]["legs_failing"] == ["RR"]
    flpre = _payload(state=(3, 5, 5, 5), f_lock=(14e3, 0, 0, 0), contact=(True, False, False,
                                                                          False))
    assert bc.snapshot_retag_check(flpre, preground_leg="FL")["passed"]
    two = _payload(state=(3, 5, 5, 3), f_lock=(14e3, 0, 0, 1e3), contact=(True, False, False,
                                                                           True))
    assert not bc.snapshot_retag_check(two, preground_leg="FL")["passed"]
    moving = _payload(state=(3, 5, 5, 5), u=(1e-3, 0, 0, 0))
    assert not bc.snapshot_retag_check(moving, preground_leg="FL")["passed"]

    class _Snap:
        params_sha256 = "a"
        payload = flpre

    _, c = bc.retag_snapshot(_Snap(), "a", name="x", preground_leg="FL")
    assert c["passed"] and not c["required"]
    with pytest.raises(bc.SnapshotRetagRefused):
        bc.retag_snapshot(_Snap(), "a", name="x", preground_leg="RR")


def test_ps7r8_cases(s8c) -> None:
    s6c, st = s8c.s6c, s8c.s6c.st
    cases = s6c.ps7r8_cases()
    assert [c.case_id for c in cases] == PS7_IDS
    by = {c.case_id: c for c in cases}
    assert by["PS7a_RR_R8"].snapshot == st.RRPRE_SNAPSHOT == st.preground_snapshot_name("RR")
    assert by["PS7a_FL_R8"].snapshot == "S6_crawler_top_flat_FLpre"
    assert by["PS7a_RR_R8"].preground_leg == "RR" and by["PS7a_FL_R8"].preground_leg == "FL"
    for cid, off in (("PS7b_RR_R8", -1.5), ("PS7c_RR_R8", -2.7)):
        sc = by[cid].scenario
        assert sc.pre_extend_leg == 3 and sc.pre_extend_offset_mm == off
        assert by[cid].preground_leg is None and sc.snapshot == "S6_crawler_top_flat"
    for c in cases:
        assert c.sensor_model and c.end_after_ready_s == 5.0
        assert c.scenario.zero_calibration and c.scenario.pressure_grade == "normal"
        meta = c.to_meta()
        assert meta["end_after_ready_s"] == 5.0
    old = s6c.bundle_c_cases()[0].to_meta()
    assert "preground_leg" not in old and "end_after_ready_s" not in old
    with pytest.raises(ValueError):
        st.preground_snapshot_name("XX")


def test_ps7_touch_flag_rows() -> None:
    from outrigger_sim.verify import s6_control as s6

    base = {"F_min_kN": 9.4146, "times_s": {"liftoff": 30.0}, "final_phase": "ready",
            "min_cyl_after_liftoff": {"min_kN": 50.0, "leg": "RL", "t_s": 40.0},
            "lift_after_liftoff_s": {k: 0.0 for k in s6.LEGS}, "att_last5_maxabs_deg": 0.03,
            "variant": "a", "leg": "RR", "grounded_skips": 1, "allowance_N": 4000.0,
            "gyro_bias_skipped": 0, "events_zero": []}
    ok = dict(base, touch={"length_s": 20.0, "T3_extra_stroke_mm": 30.0,
                           "T4_max_abs_att_deg": [0.1, 0.5], "flag": False})
    bad = dict(base, touch={"length_s": 32.0, "T3_extra_stroke_mm": 147.0,
                            "T4_max_abs_att_deg": [0.1, 2.5], "flag": True})
    rows = s6.ps7_rows({"ok": ok, "bad": bad})
    assert all(r["passed"] is not False for r in rows)
    touch = {r["case"]: r for r in rows if "TOUCH" in r["item"]}
    assert touch["ok"]["flag"] is False and touch["bad"]["flag"] is True
    fl = dict(base, leg="FL", allowance_N=4000.0)
    zr = [r for r in s6.ps7_rows({"fl": fl}) if "PS-7a" in r["item"]][0]
    assert zr["passed"] is False  # front leg needs 5.5 kN
