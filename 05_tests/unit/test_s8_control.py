"""S8 judge helpers (verify/s8_control): truth classes, episodes, detection metrics, C1 hold
rule (rev. 40 R40-1 / R40-2), Clopper-Pearson; S8 case matrix (run_S8C, spec rev. 39 202)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]


def test_clopper_pearson() -> None:
    assert s8.clopper_pearson_upper(0, 75) == pytest.approx(1 - 0.05 ** (1 / 75), rel=1e-9)
    assert s8.clopper_pearson_upper(0, 0) is None
    assert s8.clopper_pearson_upper(3, 3) == 1.0


def test_classify_windows_and_episodes() -> None:
    t_pad = np.arange(1, 1001) * 1e-3  # 1 ms, 0.001 .. 1.0 s
    f = np.full((1000, 4), 50e3)
    f[350:420, 1] = 8e3        # FR under F_min in windows 0.4 (0.3, 0.4] and (0.4, 0.5]
    f[700:760, 3] = -700.0     # RR lifted (min + m g <= 0.5 kN) in (0.7, 0.8]
    t_ctrl = np.arange(1, 11) * 0.1
    lab, wmin = s8.classify_windows(t_pad, f, t_ctrl, 9414.59, [1047.0, 1047.0, 718.0, 718.0])
    assert lab[:, 1].tolist() == [0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
    assert lab[:, 3].tolist() == [0, 0, 0, 0, 0, 0, 0, 2, 0, 0]
    eps = s8.episodes(lab)
    assert eps == [(1, 3, 4), (3, 7, 7)]
    assert wmin[3, 1] == 8e3
    bm = s8.boundary_mask(lab)
    assert bm[2, 1] and bm[5, 1] and not bm[0, 1]


def test_detection_metrics_miss_late_delay() -> None:
    t = np.arange(1, 11) * 0.1
    eps = [(1, 3, 4), (3, 7, 7)]
    level = np.zeros((10, 4), bool)
    level[4, 1] = True               # FR flagged 0.1 s after t_on: in time
    action = np.zeros((10, 4), bool)
    action[1:5, 1] = True            # FR action from 0.2 s: 0.2 s before t_on
    d = s8.detection_metrics(eps, level, action, t, transient=[False, True])
    assert d["M1_missed"] == 1 and d["n"] == 2       # RR never level-flagged
    assert d["M1p_late"] == 0
    assert d["episodes"][0]["action_delay_s"] == pytest.approx(-0.2)
    assert d["episodes"][1]["action_delay_s"] is None
    assert d["transient_episodes"] == 1


def test_false_flags_and_near_fmin() -> None:
    t = np.arange(1, 41) * 0.1
    act = np.zeros((40, 4), bool)
    act[5, 0] = True
    truth = np.full((40, 4), 30e3)
    assert s8.false_flags(act, truth, t, 9414.59) == 1
    truth[8, 0] = 10e3
    assert s8.false_flags(act, truth, t, 9414.59) == 0
    est = np.array([10e3, 12e3, 50e3])
    tru = np.array([9.5e3, 12e3, 50e3])
    m4 = s8.near_fmin_errors(est, tru, 9414.59)
    assert m4["n"] == 2 and m4["max_kN"] == pytest.approx(0.5)


def test_c1_hold_rule() -> None:
    """R40-2: raw below, within 8 s, slow >= limit -> hold (rigid only); compliant -> fail."""
    t = np.arange(0, 20000) * 1e-3
    f = np.full((t.size, 4), 40e3)
    f[2100:2110, 2] = 10e3  # 10 ms dip 1.1 s after lift-off
    c1 = s8.c1_metrics(t, f, 1.0)
    assert c1["raw_min_kN"] == pytest.approx(10.0)
    assert c1["raw_after_liftoff_s"] == pytest.approx(1.1)
    assert c1["slow_min_first8_kN"] > 14.41
    hold = s8.c1_row("c", c1, 14.41, rigid=True)
    assert hold["kind"] == "hold" and hold["passed"] is None
    fail = s8.c1_row("c", c1, 14.41, rigid=False)
    assert fail["passed"] is False
    ok = s8.c1_row("c", c1, 9.0, rigid=True)
    assert ok["passed"] is True
    sens = s8.c1_row("c", c1, 9.0, rigid=True, condition="sensitivity")
    assert sens["passed"] is None and sens["passed_raw"] is True
    f[12000:12010, 2] = 9e3  # the minimum 11 s after lift-off is never a hold
    c1b = s8.c1_metrics(t, f, 1.0)
    assert s8.c1_row("c", c1b, 14.41, rigid=True)["passed"] is False


def test_rigid_meta_default() -> None:
    assert s8.is_rigid_crawler({})
    assert not s8.is_rigid_crawler({"crawler_contact": "nsc_compliant"})


S7_RPB = ROOT / "07_results/S7/ctrl3_20261024_154939/L2b_D8_top_rpB_b1.0"


@pytest.mark.skipif(not S7_RPB.exists(), reason="S7 ctrl3 record not present")
def test_c1_on_the_s7_rpb_record() -> None:
    """C-S8-7 test 1 / 2 (spec rev. 40 210.6): raw 35.67 kN at lift-off + 0.145 s, slow 45.79 kN,
    passed, no hold; with a 40 kN limit the same record is one hold."""
    case, m, _pr, params = s8._load(S7_RPB)
    sm = s8.s8_case_metrics(case, m, params)
    c1 = sm["c1"]
    assert c1["raw_min_kN"] == pytest.approx(35.67, abs=0.01)
    assert c1["raw_after_liftoff_s"] == pytest.approx(0.145, abs=1e-3)
    assert c1["slow_min_kN"] == pytest.approx(45.79, abs=0.01)
    lim = (sm["F_min_N"] + 5000.0) / 1e3
    r = s8.c1_row("rpB", c1, lim, rigid=sm["rigid"])
    assert r["passed"] is True and r["kind"] == "judged"
    r40 = s8.c1_row("rpB", c1, 40.0, rigid=sm["rigid"])
    assert r40["kind"] == "hold"


def _run_s8c():
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import run_S8C

    return run_S8C


def test_case_matrix_counts() -> None:
    pytest.importorskip("pychrono")
    r = _run_s8c()
    assert len(r.case_set("p1")) == 36  # rev. 41: + K0V 5
    p1r = r.case_set("p1r")  # rev. 43 C-S8-18: + N_D8 rpB pressure-only
    assert len(p1r) == 37 and p1r[-1].case_id == "N_D8_top_rpB_Fs8_pressure"
    assert len({c.case_id for c in p1r}) == 37
    assert len(r.case_set("rest")) == 49
    assert len(r.case_set("all")) == 85
    groups = {}
    for c in r.case_set("all"):
        groups[c.group] = groups.get(c.group, 0) + 1
    assert groups == {"K0": 4, "K0V": 5, "K8": 9, "K24": 18, "A": 8, "B": 4, "S": 2, "E": 16,
                      "N": 15, "L": 4}
    assert sum(1 for c in r.case_set("all") if c.engine == "L1R") == 4
    assert len(r.case_set("cb")) == 6
    # R41-2: every K8 / K24 case pairs inside the batch; no external twin left
    table = r.case_table()
    for c in r.case_set("all"):
        assert c.pair_fs0_external is None
        if c.group in ("K8", "K24"):
            assert c.pair_fs0 in table and table[c.pair_fs0].fs_kN == 0.0
            assert table[c.pair_fs0].floor == c.floor
        if c.group == "K0V":
            assert c.ref_s7 is not None and c.priority == 1
    bases = r.ml_bases()
    assert len(bases) == 24 and sum(len(r.ml_episodes(b)) for b in bases) == 192
    assert [b.fs_kN for b in bases[:4]] == [0.0, 2.0, 4.0, 8.0]
    for b in bases:
        assert abs(b.floor_deg[0]) / 5.5 + abs(b.floor_deg[1]) / 3.5 <= 1.0 + 1e-3
        assert len(b.leg_scale) == 4 and all(0.8 <= v <= 1.2 for v in b.leg_scale)
        assert 0.02 <= b.rod_dead_length_m <= 0.10
        assert b.not_applied == ()


def test_ml_bases_keep_the_spec_205_draws() -> None:
    """The ML input draws come from a second generator: the spec 205.3 draws of 2026-10-24
    (ML03: seed 1329216061, floor (1.2764, 2.1951), beta 1.2301) are unchanged."""
    pytest.importorskip("pychrono")
    b = _run_s8c().ml_bases()[3]
    assert (b.seed, b.floor_deg, b.beta_GPa, b.fs_kN) == (1329216061, (1.2764, 2.1951), 1.2301,
                                                          8.0)


def _i4_synthetic(*, with_reapproach: bool):
    """Pressure-only SS F_s 8 type record (211.7 C-S8-10): one under-F_min episode of RR after
    the event, no J_P judgement-level flag, (optionally) a re-approach event."""
    period = 0.1
    tc = np.arange(1, 201) * period  # 0.1 .. 20 s
    labels = np.zeros((tc.size, 4), dtype=int)
    labels[120:127, 3] = 1  # U for 0.7 s from 12.0 s
    eps = s8.episodes(labels)
    level = np.zeros_like(labels, dtype=bool)  # J_P never below F_min (reading F_s high)
    t_pad = np.arange(1, 20001) * 1e-3
    f = np.full((t_pad.size, 4), 30e3)
    f[(t_pad >= 11.95) & (t_pad <= 12.65), 3] = 7.9e3
    obs = s8.i4_classify(t_ev=10.0, t_end=20.0, tc=tc, labels=labels, episode_list=eps,
                         transient=[False] * len(eps), level_flag=level, t_pad=t_pad,
                         f_judged=f, f_min=9414.59,
                         reapproach_times=[12.3] if with_reapproach else [])
    return obs


def test_i4_pressure_ss_fs8_type_matches() -> None:
    obs = _i4_synthetic(with_reapproach=False)
    assert (obs["p_miss"], obs["item6"], obs["reapproach"]) == ("miss", "fail", "no")
    exp = {"p_miss": "miss", "item6": "fail", "reapproach": "no"}  # N_SS_Fs8_pressure row
    c = s8.i4_compare(exp, obs)
    assert c["passed"] is True and c["mismatches"] == []


def test_i4_reapproach_mismatch() -> None:
    obs = _i4_synthetic(with_reapproach=True)
    c = s8.i4_compare({"p_miss": "miss", "item6": "fail", "reapproach": "no"}, obs)
    assert c["passed"] is False and c["mismatches"] == ["reapproach"]


def test_i4_na_and_if_lift() -> None:
    obs = {"p_miss": "miss", "item6": "fail", "reapproach": "no", "lift_long_s": 0.1}
    c = s8.i4_compare({"p_miss": "n/a", "item6": "n/a", "reapproach": "if_lift"}, obs)
    assert c["passed"] is None  # nothing compared: lift 0.1 s < 0.3 s
    c = s8.i4_compare({"p_miss": "n/a", "item6": "n/a", "reapproach": "if_lift"},
                      {**obs, "lift_long_s": 0.4})
    assert c["passed"] is False and c["mismatches"] == ["reapproach"]


def test_i4_rows_with_the_control_table() -> None:
    exp = s8.load_i4_expected(ROOT)
    if exp is None:
        pytest.skip("s8_i4_expected.json not present")
    assert exp["meta"]["n_cases"] == len(exp["cases"]) == 33
    # rev. 42 table (2026-10-24 20:30): N_G4_Fs8_pressure = miss / fail / no (the SS F_s 8 type
    # record matches); N_SS_Fs8_pressure compares only the re-approach now
    assert exp["cases"]["N_G4_Fs8_pressure"]["expected"] == {"p_miss": "miss", "item6": "fail",
                                                              "reapproach": "no"}
    obs = _i4_synthetic(with_reapproach=False)
    sms = {"N_G4_Fs8_pressure": {"case": "N_G4_Fs8_pressure", "i4": obs},
           "N_SS_Fs8_pressure": {"case": "N_SS_Fs8_pressure", "i4": obs}}
    rows = s8.i4_rows(sms, exp)
    by = {r["case"]: r for r in rows}
    assert by["N_G4_Fs8_pressure"]["passed"] is True
    cells = by["N_SS_Fs8_pressure"]["cells"]
    assert [k for k, c in cells.items() if c["compared"]] == ["reapproach"]
    assert by["N_SS_Fs8_pressure"]["passed"] is True and by["*"]["passed"] is True
    bad = s8.i4_rows({"N_G4_Fs8_pressure": {"case": "N_G4_Fs8_pressure",
                                            "i4": _i4_synthetic(with_reapproach=True)}}, exp)
    assert bad[0]["passed"] is False and bad[-1]["passed"] is False


def test_g4_rr_summary() -> None:
    tc = np.arange(1, 101) * 0.1
    u = np.zeros((100, 4))
    u[60:65, 3] = -2.5e-3  # 6.1 .. 6.5 s
    band = np.full((100, 4), 4.5e3)
    t_pad = np.arange(1, 10001) * 1e-3
    f = np.full((t_pad.size, 4), 30e3)
    f[7000, 3] = 8.0e3
    ev = [(5.5, "x"), (6.1, "relevel_predicted"), (6.5, "leg_reapproach_start:RR")]
    meta = {"twist_gain_stiffness": {"measured_scale": 1.23, "scale_in_use": 1.2}}
    g = s8.g4_rr_summary(t_ev=6.0, events=ev, tc=tc, issued_u=u, band=band, t_pad=t_pad,
                         f_judged=f, controller_meta=meta)
    assert g["relevel_predicted_s"] == 6.1 and g["reapproach_start_s"] == 6.5
    assert g["u_rr_mean_mm_s"] == pytest.approx(-2.5)
    assert g["min_true_kN"] == pytest.approx(8.0) and g["min_true_t_s"] == pytest.approx(7.001)
    assert g["F_band_kN"] == pytest.approx(4.5) and g["twist_stiffness_scale"] == 1.23


def test_pair_rows_crawler_differs_r41_4() -> None:
    a = {"case": "K8_top_rpB_Fs8", "crawler_contact": "nsc_rigid",
         "pair_window": {"t_ready_minus_touch_s": 30.0, "nF_true_ready_kN": 9.0,
                         "min_cyl_reanchor_kN": 20.0, "min_late8_to_ready_kN": 30.0}}
    b = {"crawler_contact": "nsc_compliant",
         "pair_window": {"t_ready_minus_touch_s": 10.0, "nF_true_ready_kN": 1.0,
                         "min_cyl_reanchor_kN": 22.0, "min_late8_to_ready_kN": 31.0}}
    rows = s8.pair_rows_s8(a, b, source="batch K0V", kind_pair="fs0")
    assert rows and all(r["passed"] is None for r in rows)
    assert all(r.get("report_cause", None) is None for r in rows)
    assert all("not attributable to F_s" in r["note"] for r in rows)
    same = s8.pair_rows_s8(a, {**b, "crawler_contact": "nsc_rigid"}, source="x", kind_pair="fs0")
    assert any(r.get("report_cause") is True for r in same)  # C10 +20 s, F9 +8 kN


def test_sampling_only_flag() -> None:
    t = np.arange(1, 21) * 0.1
    level = np.zeros((20, 4), bool)
    action = np.zeros((20, 4), bool)
    action[4:7, 0] = True  # action level 0.1 s before t_on
    d = s8.detection_metrics([(0, 5, 6)], level, action, t)
    e = d["episodes"][0]
    assert e["missed"] and e["sampling_only"]
    sm = {"case": "c", "item9": {"J_C": d}}
    assert len(s8.sampling_only_episodes(sm, "J_C")) == 1
    action[:] = False
    d2 = s8.detection_metrics([(0, 5, 6)], level, action, t)
    assert not d2["episodes"][0]["sampling_only"]


def test_s7_regression_rows() -> None:
    sm = {"case": "K0V_top_rpB_Fs0", "crawler_contact": "nsc_rigid", "ready_s": 40.0,
          "c1": {"raw_min_kN": 35.70}}
    ref = {"crawler_contact": "nsc_rigid", "ready_s": 40.05, "c1": {"raw_min_kN": 35.67}}
    r = s8.s7_regression_rows(sm, ref, ref_label="S7/x")[0]
    assert r["regression_flag"] is False and r["value"][0] == pytest.approx(0.03)
    r = s8.s7_regression_rows(sm, {**ref, "ready_s": 41.0}, ref_label="S7/x")[0]
    assert r["regression_flag"] is True
    r = s8.s7_regression_rows(sm, {**ref, "crawler_contact": "nsc_compliant"},
                              ref_label="S7/x")[0]
    assert r["regression_flag"] is None and "record only" in r["note"]
    r = s8.s7_regression_rows(sm, ref, ref_label="S7/x", settings_this={"duration_s": 330.0},
                              settings_ref={"duration_s": 120.0})[0]
    assert r["value"] is None and "settings differ" in r["note"]


def test_judged_force_min_airborne() -> None:
    pads = {"F_cyl_min_interval": np.array([[-16e3, 5e3], [-2e3, 6e3]]),
            "F_cyl_mean_20ms": np.array([[-0.9e3, 5.5e3], [-0.8e3, 6.5e3]]),
            "airborne": np.array([[True, False], [True, False]])}
    f = s8.judged_force_min(pads)
    np.testing.assert_array_equal(f, [[-0.9e3, 5e3], [-0.8e3, 6e3]])
    rec = s8.air_record(pads, [900.0, 900.0])
    assert rec["min_1ms_kN"][0] == pytest.approx(-15.1) and rec["min_1ms_kN"][1] is None
    old = {"F_cyl_min_interval": pads["F_cyl_min_interval"]}
    np.testing.assert_array_equal(s8.judged_force_min(old), pads["F_cyl_min_interval"])


def test_lower_estimate_series_sources() -> None:
    """C-S8-16 ①: recorded F_lower_est_N first, else F_lower_N - leg_band_N, else F_hat - band;
    F_nominal_N first, else F_lower_N."""
    hat = np.full((3, 4), 20e3)
    low = hat - 500.0  # calibration offset 0.5 kN
    band = np.full((3, 4), 13e3)
    s = {"F_hat_N": hat, "F_lower_N": low, "leg_band_N": band, "F_band_N": np.full(3, 13e3)}
    est, nom, src = s8.lower_estimate_series(s)
    np.testing.assert_allclose(est, 6.5e3)
    np.testing.assert_allclose(nom, 19.5e3)
    assert src["lower"].startswith("F_lower_N - leg_band_N")
    s2 = {**s, "F_lower_est_N": np.full((3, 4), 1.0), "F_nominal_N": np.full((3, 4), 2.0)}
    est, nom, src = s8.lower_estimate_series(s2)
    assert est[0, 0] == 1.0 and nom[0, 0] == 2.0 and src["lower"].startswith("F_lower_est_N")
    s3 = {**s, "F_lower_N": np.full((3, 4), np.nan), "leg_band_N": np.full((3, 4), np.nan)}
    est, nom, src = s8.lower_estimate_series(s3)
    np.testing.assert_allclose(est, 7e3)  # common band
    np.testing.assert_allclose(nom, 20e3)
    assert "not calibrated" in src["lower"]


def test_f1_share_r43_1() -> None:
    """R43-1 with the U-S8-15 constant term 0.85 kN (WIKA); ideal stays 0.1 kN."""
    f = np.array([0.0, 9.4e3, 120e3, -10e3])
    np.testing.assert_allclose(s8.f1_share_N(f, wika=False), 100.0)
    np.testing.assert_allclose(s8.f1_share_N(f, wika=True), [850.0, 1085.0, 3850.0, 1100.0])


def test_run_end_cause_r43_4() -> None:
    assert s8.run_end_cause("ready", None) == "ready"
    assert s8.run_end_cause("fault", {"timeout": True}) == "controller"
    assert s8.run_end_cause("level", {"timeout": True}) == "timeout"
    assert s8.run_end_cause("probe", {"timeout": False}) == "controller"
    assert s8.run_end_cause("level", None).startswith("timeout (fixed duration")


def test_h4_one_sided_r43_3() -> None:
    """K8 fdown3.5 F_s 8 (spec rev. 43 213.2 #9): RL T_READY 17.87 > T_DONE 17.69 kN (+0.18 kN,
    1 %) passes with max(0.5 kN, 3 %); +0.6 kN fails; a ratio above 1.1 fails."""
    mech = {"ratio": [1.0309, 1.0166], "T_done_kN": [17.6864, 17.7431],
            "T_ready_kN": [17.8699, 17.6234]}
    ok, slack = s8.h4_one_sided_ok(mech)
    assert ok and slack[0] == pytest.approx(17.6864 + 0.5306 - 17.8699, abs=1e-3)
    assert not s8.h4_one_sided_ok({**mech, "T_ready_kN": [18.3, 17.6]})[0]
    assert not s8.h4_one_sided_ok({**mech, "ratio": [1.11, 1.0]})[0]
    red = s8.h4_reduction(mech)
    assert red[0] == pytest.approx(-0.0104, abs=1e-4) and red[1] == pytest.approx(0.0067, abs=1e-4)


def test_i4_p_miss_counts_crawler_transient() -> None:
    """C-S8-16 ④ (R40-5): an episode inside the lift-off window is counted in p_miss."""
    tc = np.arange(1, 101) * 0.1
    labels = np.zeros((100, 4), dtype=int)
    labels[60:63, 3] = 1
    eps = s8.episodes(labels)
    level = np.zeros_like(labels, dtype=bool)
    level[61, 3] = True
    t_pad = np.arange(1, 10001) * 1e-3
    f = np.full((t_pad.size, 4), 30e3)
    obs = s8.i4_classify(t_ev=5.0, t_end=10.0, tc=tc, labels=labels, episode_list=eps,
                         transient=[True], level_flag=level, t_pad=t_pad, f_judged=f,
                         f_min=9414.59, reapproach_times=[])
    assert obs["p_miss"] == "detect" and obs["transient_episodes_after_t_ev"] == 1
    assert obs["p_miss_ex_transient"] == "none"


def test_apply_rev43_rows() -> None:
    def row(item, case, value, passed, **kw):
        return {"item": item, "case": case, "value": value, "limit": None, "passed": passed,
                "note": "", "kind": "function", **kw}

    mech = {"legs": ["RL", "RR"], "ratio": [1.03, 1.02], "T_done_kN": [17.69, 17.74],
            "T_ready_kN": [17.87, 17.62], "P_stop_last_kN": [33.95, 33.95]}
    mech0 = {**mech, "T_ready_kN": [7.15, 9.61]}
    sms = {"K8": {"s8": {"fs_kN": 8.0, "pair_fs0": "K0V"}, "h4_mechanism": mech, "end": None},
           "K0V": {"s8": {"fs_kN": 0.0, "pair_fs0": None}, "h4_mechanism": mech0,
                   "end": {"timeout": False}}}
    rows = [row("run", "K8", "level", False), row("run", "K0V", "ready", True),
            row(s8.F7C_ITEM, "K8", 2.52, False), row(s8.F7C_ITEM, "K0V", -4.8, True),
            row(s8.H4_ONE_SIDED_ITEM, "K8", {k: mech[k] for k in
                                             ("legs", "ratio", "T_done_kN", "T_ready_kN")},
                False)]
    extra = s8.apply_rev43_rows(rows, sms)
    assert rows[0]["end_cause"].startswith("timeout (fixed") and rows[0]["passed"] is False
    assert rows[1]["end_cause"] == "ready"
    assert rows[2]["passed"] is None and rows[2]["passed_raw"] is False
    assert rows[2]["kind"] == "record"
    assert rows[3]["passed"] is True  # F_s 0: 7c stays judged
    assert rows[4]["passed"] is True and rows[4]["passed_rev42"] is False
    f5 = [r for r in extra if r["item"].startswith("F5 7c")]
    assert len(f5) == 1 and f5[0]["value"] == pytest.approx(7.32)
    assert f5[0]["report_cause"] is True
    f6 = {r["case"]: r for r in extra if r["item"].startswith("F6 H4")}
    assert set(f6) == {"K8", "K0V"} and f6["K8"]["value"][0] < 0.0


def test_l2b_pads_view_contact_point_anchor() -> None:
    cp = np.zeros((3, 4, 3))
    cp[:, 0, 0] = [0.0, 0.001, 0.002]
    pads = {"anchor_world": np.full((3, 4, 3), np.nan), "contact_point_world": cp,
            "N": np.array([[1.0, 1.0, 1.0, 1.0], [1.0, 0.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]])}
    v = s8.l2b_pads_view(pads)
    assert v["anchor_world"][2, 0, 0] == 0.002
    assert np.isnan(v["anchor_world"][1, 1]).all()
    assert np.isnan(pads["anchor_world"]).all()  # the record itself is not changed


P1_BATCH = ROOT / "07_results/S8/p1_20261024_204911"
CONTROL_RECHECK = ROOT / "06_analysis/02_control/s8/s8_p1_rev43_f2_f1_recheck.json"


@pytest.mark.skipif(not (P1_BATCH / "E_RE1bF_Fs8" / "pads.npz").exists(),
                    reason="S8 p1 batch not present")
def test_rev43_on_the_p1_re1bf_fs8_case() -> None:
    """C-S8-16 tests on E_RE1bF_Fs8 (spec rev. 43 213.8): F2 = control recheck (F_hat - F_band
    - F max -4.891 kN, spec-199 lower bound with the calibration offset -4.93 kN), no violation;
    FR rise <= 0.01 mm (L1 formula gave 4.3 mm); I4 p_miss detect."""
    import json

    case, m, _pr, params = s8._load(P1_BATCH / "E_RE1bF_Fs8")
    sm = s8.s8_case_metrics(case, m, params)
    ref = json.loads(CONTROL_RECHECK.read_text(encoding="utf-8"))["E_RE1bF_Fs8"]
    assert sm["F2"]["max_raw_minus_band_kN"] == pytest.approx(ref["F2_spec_max_kN"], abs=1e-6)
    assert sm["F2"]["violations"] == 0 and sm["F2"]["max_kN"] < -4.0
    e = m["event3"]
    assert e["other_legs_rise_max_m"][1] <= 1e-5
    assert e["rise_l1_formula_m"][1] > 4e-3
    assert sm["i4"]["p_miss"] == "detect"


@pytest.mark.skipif(not (P1_BATCH / "verify_S8C.json").exists()
                    or not CONTROL_RECHECK.exists(), reason="S8 p1 verdict not present")
def test_rev43_verdict_matches_the_control_f2_recheck() -> None:
    """The re-judged p1 verdict (C-S8-16 ①): per case the F2 cross-check value F_hat - F_band - F
    equals control's recheck (36 cases, 22 of them failed F2 under rev. 42), F2 violations 0,
    I4 summary passed, E_RE1bP p_miss = detect."""
    import json

    doc = json.loads((P1_BATCH / "verify_S8C.json").read_text(encoding="utf-8"))
    if "judge_revision" not in doc["meta"]:
        pytest.skip("verify_S8C.json is not a rev. 43 verdict")
    ref = json.loads(CONTROL_RECHECK.read_text(encoding="utf-8"))
    sms = doc["s8_metrics"]
    assert set(ref) <= set(sms)
    for cid, r in ref.items():
        f2 = sms[cid]["F2"]
        assert f2["max_raw_minus_band_kN"] == pytest.approx(r["F2_spec_max_kN"], abs=1e-6), cid
        assert f2["violations"] == 0, cid
        assert f2["max_kN"] <= 0.0, cid
    assert sms["S_top_fdown3.5_wika_Fs8"]["F2"]["max_raw_minus_band_kN"] == pytest.approx(
        -3.28, abs=0.005)
    rows = doc["rows"]
    assert not [r for r in rows if r["item"].startswith("F2 ") and r["passed"] is False]
    i4 = [r for r in rows if r["item"].startswith("I4 summary")]
    assert i4 and i4[0]["passed"] is True
    for cid in ("E_RE1bP_Fs0", "E_RE1bP_Fs8"):
        assert sms[cid]["i4"]["p_miss"] == "detect"


def test_end_rule_c_s8_17() -> None:
    """D8 READY + 10 s, event + 45 s, HOLD READY + 120 s, upper = duration + 60 s."""
    pytest.importorskip("pychrono")
    r = _run_s8c()
    t = r.case_table()
    d8, g4, hold, re1bp = (t["K8_top_flat_Fs8"], t["E_G4_Fs8"], t["E_HOLD120_Fs8"],
                           t["E_RE1bP_Fs0"])
    assert (r.end_rule(d8)["anchor"], r.end_rule(d8)["after_s"]) == ("ready", 10.0)
    assert (r.end_rule(g4)["anchor"], r.end_rule(g4)["after_s"]) == ("event", 45.0)
    assert (r.end_rule(hold)["anchor"], r.end_rule(hold)["after_s"]) == ("ready", 120.0)
    assert r.end_rule(g4)["upper_s"] == pytest.approx(g4.duration_s + 60.0)
    assert r.expected_run_s(d8) == pytest.approx(52.8)
    assert r.expected_run_s(g4) == pytest.approx(42.8 + 5.0 + 45.0)
    assert r.expected_run_s(hold) == pytest.approx(162.8)
    assert r.expected_run_s(re1bp) == pytest.approx(30.9 + 0.1 + 45.0)
    pl = r.phase_lengths([(0.1, "check"), (4.7, "touch"), (23.9, "level"), (30.8, "ready"),
                          (40.0, "level")], 50.0)
    assert pl["first_touch_s"] == pytest.approx(19.2)
    assert pl["first_level_s"] == pytest.approx(6.9)
    assert pl["total_s"]["level"] == pytest.approx(16.9)


def test_makespan_layouts() -> None:
    pytest.importorskip("pychrono")
    r = _run_s8c()
    p = r.simulate_makespan([100.0] * 15, "p7")
    assert p["makespan_s"] == pytest.approx(300.0)
    m = r.simulate_makespan([100.0] * 15, "p7e8")
    assert m["makespan_s"] <= p["makespan_s"]
    assert m["cases_per_pool"]["ecore"] >= 1


# --- rev. 44 (C-S8-19, U-S8-15 ... 17) --------------------------------------------------------


def test_air_residual_selects_airborne_samples_and_flags() -> None:
    """② only samples with F < 0.5 kN and no pad contact outside CHECK; flag above 1.7 kN
    (R45-3, rev. 45; was 1.3 kN)."""
    sens = np.array([[1.8e3, 0.2e3, 0.0, 0.0],   # FL airborne 1.8 kN -> flag
                     [5.0e3, 0.0, 0.0, 0.0],     # in contact: ignored
                     [9.0e3, 0.0, 0.0, 0.0]])    # CHECK: ignored
    f_true = np.array([[-1e3, 0.0, 20e3, 20e3], [0.0, 0.0, 20e3, 20e3], [0.0, 0.0, 20e3, 20e3]])
    n_pad = np.array([[0.0, 0.0, 1e4, 1e4], [5.0, 0.0, 1e4, 1e4], [0.0, 0.0, 1e4, 1e4]])
    use = np.array([True, True, False])
    a = s8.air_residual(sens, f_true, n_pad, use, ["touch", "touch", "check"])
    assert a["n"] == 3 and a["leg"] == "FL" and a["phase"] == "touch"
    assert a["max_abs_kN"] == pytest.approx(1.8) and a["flag"] is True
    assert a["per_leg_max_abs_kN"][2] is None
    b = s8.air_residual(sens * 0.5, f_true, n_pad, use, ["touch", "touch", "check"])
    assert b["flag"] is False
    assert s8.air_residual(sens, f_true + 2e3, n_pad, use, ["t"] * 3)["max_abs_kN"] is None


def test_probe_7c_split_sums_and_filters() -> None:
    """③ E - T0 = (E - T2) + (T2 - T0); overlap / skipped / ringing rows are left out."""
    base = {"event_class": "pre", "is_skipped": False, "zero_cal_deduction": False}
    pr = {"legs": [
        {**base, "round": 0, "leg": "RR", "load_estimate_kN": 70.0, "truth_cyl_kN": 61.0,
         "truth_end_kN": 66.0},
        {**base, "round": 0, "leg": "FL", "load_estimate_kN": 100.0, "truth_cyl_kN": 98.0,
         "truth_end_kN": 96.0},
        {**base, "round": 0, "leg": "FR", "event_class": "overlap", "load_estimate_kN": 0.0,
         "truth_cyl_kN": 90.0, "truth_end_kN": 50.0},
        {**base, "round": 1, "leg": "RL", "truth_undefined": True, "load_estimate_kN": 0.0,
         "truth_cyl_kN": 90.0, "truth_end_kN": 50.0}]}
    sp = s8.probe_7c_split(pr)
    assert len(sp["rows"]) == 2
    for r in sp["rows"]:
        assert r["err_kN"] == pytest.approx(r["est_bias_kN"] + r["hyst_kN"])
    assert sp["worst_7c"]["leg"] == "RR"  # 9 - 6.1 = +2.9 kN margin
    assert sp["worst_7c"]["margin_kN"] == pytest.approx(9.0 - 6.1)
    assert sp["est_bias"]["leg"] == "RR" and sp["est_bias"]["value_kN"] == pytest.approx(4.0)
    assert sp["hyst"]["value_kN"] == pytest.approx(5.0)
    assert s8.probe_7c_split({"legs": []}) is None and s8.probe_7c_split(None) is None


def test_score_ex_transient_counts_by_t_on() -> None:
    """④ (R42-3): an episode that starts inside the lift-off window and runs past it is left out
    whole (no tail episode); one that starts before it and crosses it counts; M2 / M4 use the
    samples outside the window."""
    from dataclasses import replace

    from outrigger_sim.verify.contact_metrics import ContactClass, RecordJudgement, score_judge

    g, u = ContactClass.GROUNDED, ContactClass.UNDER_LOADED
    n = 60
    classes = np.full((n, 4), g)
    classes[8:26, 0] = u    # starts at row 8, before the window 10..19, crosses it: counts
    classes[12:25, 1] = u   # t_on inside the window, runs past it: left out (old rule: tail)
    classes[40:44, 2] = u   # after the window: counts
    flags = np.zeros((n, 4), bool)
    rj = RecordJudgement(t_s=(np.arange(n) + 1) * 0.1, classes=classes, decision_flags=flags,
                         action_flags=flags, estimate_N=np.full((n, 4), 50e3),
                         true_force_N=np.full((n, 4), 50e3),
                         true_force_min_N=np.full((n, 4), 50e3), watched=np.ones(n, bool))
    early = np.zeros(n, bool)
    early[10:20] = True
    sx = s8.score_ex_transient(rj, early, 9414.59, replace, score_judge)
    assert sx["episodes"] == 2 and sx["M1_missed"] == 2
    old = score_judge([replace(rj, watched=rj.watched & ~early)], 9414.59).to_dict()
    assert old["episodes"] == 4  # former rule: FL split in two, FR tail counted
    assert score_judge([rj], 9414.59).to_dict()["episodes"] == 3


def test_reconstruct_twist_history_matches_controller_rule() -> None:
    """⑤ median of measured / nominal S_ii over >= 3 stiffness-grounded legs, bounded to
    [1.0, 1.5]; a round with fewer legs keeps the previous scale; times relative to t0."""
    nominal = [5.0e6, 5.0e6, 6.0e6, 6.0e6]

    def rnd(k, t_end, skip=()):
        return [{"leg_index": i, "incremental_stiffness_N_m": k[i] * nominal[i],
                 "is_grounded_by_stiffness": i not in skip, "is_skipped": False,
                 "t_second_hold_end_s": t_end - 3 * (3 - i)} for i in range(4)]

    probes = [rnd([1.2, 1.3, 1.4, 1.6], 45.7), rnd([2.0, 2.0, 2.0, 2.0], 73.5),
              rnd([1.1, 1.1, 1.1, 1.1], 90.0, skip=(0, 1))]
    cfg = ("R8(pre_probe_stiffness_scale=1.2, measured_stiffness_scale_min=1.0, "
           "measured_stiffness_scale_max=1.5)")
    h = s8.reconstruct_twist_history(probes, {"denominator_N_m": nominal}, cfg, 3.0)
    assert [x["round"] for x in h] == [0, 1, 2]
    assert h[0]["t_s"] == pytest.approx(42.7)
    assert h[0]["raw_ratio"] == pytest.approx(1.35) and h[0]["scale_in_use"] == pytest.approx(1.35)
    assert h[1]["raw_ratio"] == pytest.approx(2.0) and h[1]["scale_in_use"] == 1.5
    assert h[2]["raw_ratio"] is None and h[2]["scale_in_use"] == 1.5  # 2 legs: kept
    at = s8.scale_at(h, 50.0, 1.2)
    assert at["round"] == 0 and at["scale_in_use"] == pytest.approx(1.35)
    assert s8.scale_at(h, 10.0, 1.2)["scale_in_use"] == 1.2
    assert s8.twist_history({"result": {"twist_stiffness_history": [{"round": 0}],
                                        "settings": {}}}, 3.0)[1] == "runner"


def test_touch_air_commands_and_reapproach_windows() -> None:
    """⑦ path 1: slow / zero TOUCH command without contact in the reading period; 1.4 side effect
    windows before the event."""
    tc = np.array([0.1, 0.2, 0.3, 0.4])
    phase = np.array(["touch", "touch", "touch", "ready"])
    vmax = 0.02
    raw = np.array([[vmax, vmax, vmax, vmax], [0.25 * vmax, vmax, vmax, vmax],
                    [0.25 * vmax, 0.0, vmax, vmax], [0.0, 0.0, 0.0, 0.0]])
    tp = np.arange(1, 401) * 1e-3
    n = np.zeros((400, 4))
    n[250:, 0] = 1e3  # FL in contact from 0.251 s; FR never
    air = s8.touch_air_commands(tc, phase, raw, tp, n, vmax)
    assert air[0] == [0.2] and air[1] == [0.3] and air[2] == [] and air[3] == []
    phases = [(0.0, "level"), (10.0, "probe"), (20.0, "ready")]
    ev = [(12.0, "leg_reapproach_start:RR"), (25.0, "leg_reapproach_start:RR"),
          (31.0, "leg_reapproach_start:RR"), (26.0, "relevel_predicted")]
    ra = s8.reapproach_outside_events(phases, 40.0, ev, 30.0)
    assert ra == {"probe": [12.0], "ready": [25.0]}
    assert s8.reapproach_outside_events(phases, 40.0, ev, None)["ready"] == [25.0, 31.0]


def test_r44_touch_fix_and_g4_rows() -> None:
    """⑦ TOUCH fix row against the same-floor twin, U-S8-9 batch row from the item-6 rows."""
    sms = {
        "K0V_top_flat_Fs0": {"s8": {"fs_kN": 0.0, "floor": "flat", "level": "top"},
                             "F_min_N": 9414.59, "r44": {"touch_len_s": 19.2}},
        "K8_top_flat_Fs8": {"s8": {"fs_kN": 8.0, "floor": "flat", "level": "top",
                                   "pair_fs0": "K0V_top_flat_Fs0"},
                            "F_min_N": 9414.59, "r44": {"touch_len_s": 19.9}},
        "S_top_flat_wika_Fs8": {"s8": {"fs_kN": 8.0, "floor": "flat", "level": "top"},
                                "F_min_N": 9414.59, "r44": {"touch_len_s": 20.4}},
        "E_G4_Fs4": {"s8": {"fs_kN": 4.0, "event": "G4", "group": "E"},
                     "F_min_N": 9414.59, "r44": {"touch_len_s": None}},
    }
    rows = [{"case": "E_G4_Fs4", "item": "6 min after settlement", "value": 11.14},
            {"case": "E_G4_Fs4", "item": "6 re-READY <= 40 s", "value": 22.8}]
    out = s8.r44_gate_rows(sms, rows)
    fix = {r["case"]: r for r in out if r["item"].startswith("R44-213.6 TOUCH fix")}
    assert fix["K8_top_flat_Fs8"]["passed"] is True
    assert fix["S_top_flat_wika_Fs8"]["passed"] is False  # +1.2 s over the twin
    assert fix["E_G4_Fs4"]["passed"] is None  # no twin in the batch
    g4 = [r for r in out if r["item"].startswith("R44-213.6 U-S8-9")][0]
    assert g4["passed"] is True
    reg = [r for r in out if r["item"].startswith("R44-213.6 TOUCH regression")][0]
    assert reg["kind"] == "record"  # no reference batch


def test_runner_rev44_meta_and_costs() -> None:
    """C-S8-19 ⑥ planner costs and the P-S8-9 sensor fields (consistent with
    ``contact_episode.normalize_sensor_meta``)."""
    pytest.importorskip("pychrono")
    r = _run_s8c()
    assert r.E_CORE_FACTOR == pytest.approx(1.7)
    assert r.step_us(8.0) == pytest.approx(530.0)
    assert r.step_us(0.0) == pytest.approx(530.0 / 1.23)
    assert r.step_us(8.0, "counterbalance") > r.step_us(8.0)
    assert r.sensor_condition("normal", False) == "normal_no_cal"
    assert r.sensor_condition("conservative", True) == "conservative"
    from outrigger_sim.contact_episode import normalize_sensor_meta

    for grade, cal in (("normal", True), ("normal", False), ("conservative", True)):
        meta = {"sensor_grade": grade, "zero_calibration": cal,
                "sensor_condition": r.sensor_condition(grade, cal)}
        out = normalize_sensor_meta(meta)
        assert out["sensor_grade"] == grade and out["zero_calibration"] is cal

    class FakeC2:
        def __init__(self):
            self.probe_history = []

        def meta(self):
            return {"twist_gain_stiffness": {"scale_in_use": 1.35, "raw_ratio": 1.35,
                                             "measured_scale": 1.35, "grounded_leg_count": 4}}

    c2 = FakeC2()
    h = r.TwistScaleHistory(c2, 3.0)
    h(10.0)
    assert h.rows == []
    c2.probe_history.append(("round",))
    h(45.8)
    h(45.9)
    assert len(h.rows) == 1 and h.rows[0]["t_s"] == pytest.approx(42.8)
    assert h.rows[0]["scale_in_use"] == 1.35 and h.rows[0]["round"] == 0
