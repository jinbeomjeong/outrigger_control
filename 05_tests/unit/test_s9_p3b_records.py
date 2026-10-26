"""S9 P3b runner records (``04_scripts/02_chrono/run_S9.py``; control spec 284 P3-1 ... 9, 287, 301
W-61-1 ... 4; dynamics 5.37.5 #2): track utilisation 5 % rule, crawler departure by the P3a-2 rule
(< 1 % W for 0.1 s), creep stop (0.2 s sinkage rate < 0.1 mm/s), pre-lift-off minimum F_cyl
(first 1.4 F_min .. departure, FLAG < F_min), the P3b record assembly on a synthetic run, the
W-61 watch, the C2 soil guard, the seal-friction override and the 24 + 2 P3b batch definition.
No Chrono: synthetic 1 ms series only."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"
W = 400_000.0
F_MIN = 9415.0
P5 = F_MIN + 7500.0


def _import(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(SCRIPTS))


r9 = _import("run_S9")


def _t(t0: float, t1: float, dt: float = 1e-3) -> np.ndarray:
    return np.round(np.arange(t0 + dt, t1 + 1e-9, dt), 6)


# --- shared rules -----------------------------------------------------------------------------------


def test_mask_track_utilisation_five_percent_of_settle() -> None:
    util = np.full((4, 2), 0.3)
    normal = np.array([[100.0, 100.0], [5.0, 4.9], [6.0, 0.0], [100.0, -1.0]])
    m = r9.mask_track_utilisation(util, normal, [100.0, 100.0])
    assert np.isfinite(m[0]).all()
    assert m[1, 0] == 0.3 and np.isnan(m[1, 1])  # 5.0 = 5 % kept, 4.9 masked
    assert np.isnan(m[2, 1]) and np.isnan(m[3, 1])
    assert np.isnan(r9.mask_track_utilisation(util, normal, [0.0, 100.0])[:, 0]).all()
    assert util[1, 1] == 0.3  # input untouched


def test_crawler_departure_p3a2_rule_hold_break_and_recontact() -> None:
    t = _t(0.0, 3.0)
    cn = np.where(t < 1.0, W, 0.0)
    cn[(t > 1.05) & (t < 1.052)] = 0.02 * W  # blip breaks the 0.1 s run
    cn[(t >= 2.0) & (t < 2.1)] = 0.05 * W  # recontact
    d = r9.crawler_departure(t, cn, W)
    assert d["departed"]
    assert d["t_departure_s"] == pytest.approx(1.052, abs=1e-9)
    assert d["t_confirmed_s"] == pytest.approx(1.152, abs=1e-9)
    assert d["recontact_t_s"] == pytest.approx(2.0, abs=1e-9) and d["recontact_count"] == 1
    assert d["crawler_normal_max_after_confirm_N"] == pytest.approx(0.05 * W)
    assert not r9.crawler_departure(t, np.full(t.size, W), W)["departed"]
    # 10 Hz rows: two samples 0.1 s apart satisfy the hold
    t10 = np.round(np.arange(0.1, 3.0 + 1e-9, 0.1), 6)
    assert r9.crawler_departure(t10, np.where(t10 < 1.0, W, 0.0), W)["t_departure_s"] == pytest.approx(1.0)


def test_creep_stop_first_and_final() -> None:
    t = _t(0.0, 8.0)
    s = np.where(t < 3.0, 1e-3 * t, 3e-3)[:, None].repeat(4, axis=1)
    s[t >= 5.0, 2] += 1e-3 * (np.minimum(t[t >= 5.0], 5.5) - 5.0)  # second creep 5.0 .. 5.5 s on RL
    c = r9.creep_stop(t, s, 1.0)
    # backward 0.2 s rate < 0.1 mm/s once less than 0.02 s of the 1 mm/s ramp is in the window
    assert c["t_first_s"] == pytest.approx(3.181, abs=1.5e-3)
    assert c["t_final_s"] == pytest.approx(5.681, abs=1.5e-3)
    assert c["rate_max_after_m_s"][0] == pytest.approx(1e-3, rel=1e-6)
    assert c["rate_at_m_s"]["+1"][0] == pytest.approx(1e-3, rel=1e-6)
    assert r9.creep_stop(t, s, None)["t_first_s"] is None
    rate = r9.sinkage_rate(t, s)
    assert np.isnan(rate[:200]).all() and np.isfinite(rate[200:]).all()


def test_pre_liftoff_min_force_window_and_flag() -> None:
    t = _t(0.0, 10.0)
    f = np.zeros((t.size, 4))
    f[:, 0] = np.where(t > 2.0, 2.0 * F_MIN, 0.0)
    f[(t > 4.0) & (t < 4.1), 0] = 0.9 * F_MIN  # trough before the departure at 6 s -> FLAG
    f[(t > 7.0) & (t < 7.1), 0] = 0.1 * F_MIN  # after the departure: not in the window
    f[:, 1] = np.where(t > 2.0, 3.0 * F_MIN, 0.0)
    f[:, 3] = np.where(t > 6.5, 3.0 * F_MIN, 0.0)  # first above 1.4 F_min only after the departure
    r = r9.pre_liftoff_min_force(t, f, F_MIN, 6.0)
    legs = {row["leg"]: row for row in r["legs"]}
    assert legs["FL"]["flag"] and legs["FL"]["F_min_N"] == pytest.approx(0.9 * F_MIN)
    assert legs["FL"]["t_first_above_s"] == pytest.approx(2.001, abs=1e-9)
    assert not legs["FR"]["flag"] and legs["FR"]["F_min_N"] == pytest.approx(3.0 * F_MIN)
    assert legs["RL"]["F_min_N"] is None and legs["RR"]["F_min_N"] is None
    assert r["any_flag"]


# --- P3b record assembly ------------------------------------------------------------------------------

T0 = 8.0


def _run(t_dep: float = 30.0, end_pitch_deg: float = 0.05):
    """Synthetic closed-loop run: crawler on until ``t_dep``, legs at 90 kN, pads sink 1 mm/s
    for 2 s after the departure, pitch settles to ``end_pitch_deg``."""
    t = _t(T0, 98.0)
    n = t.size
    cn = np.where(t < t_dep, 0.5 * W, 0.0)
    pn = np.repeat(np.where(t[:, None] < 12.0, 0.0, 0.25 * W - cn[:, None] / 4), 4, axis=1)
    f = np.full((n, 4), 90e3)
    f[t < 12.0] = 0.0
    sink = np.zeros((n, 4))
    late = t >= t_dep
    sink[late] = (1e-3 * np.minimum(t[late] - t_dep, 2.0))[:, None]
    rp = np.zeros((n, 2))
    rp[:, 1] = np.where(t < t_dep + 5.0, 0.5, end_pitch_deg)
    s = {"t_s": t, "scm_crawler_normal_N": cn, "scm_crawler_patches": (cn > 0).astype(float),
         "scm_track_normal_raw_N": np.repeat(cn[:, None] / 2, 2, axis=1),
         "track_utilisation": np.full((n, 2), 0.2), "scm_pad_normal_N": pn, "F_cyl_N": f,
         "s_motor_m": np.full((n, 4), 0.4), "pad_sinkage_geometric_m": sink, "roll_pitch_deg": rp,
         "z_origin_m": np.zeros(n)}
    rows = [{"t_s": float(x), "rut_clearance_m": 0.04 if x >= t_dep - 0.05 else 0.0} for x in np.arange(T0 + 0.1, 98.0, 0.1)]
    phases = [(8.1, "check"), (9.0, "touch"), (12.0, "level"), (40.0, "done"), (45.0, "ready")]
    events = [(t_dep + 0.8, "crawler_liftoff_confirmed")]
    ctx = {"weight_N": W, "F_min_N": F_MIN, "P5_N": P5, "s_motor_limit_m": 0.6848, "t_loop_start_s": T0,
           "settle": {"track_normal_N": [0.25 * W, 0.25 * W], "end_roll_pitch_deg": [0.0, 0.15]},
           "fallback_meta": None, "T_o_s": 0.8}
    return s, rows, events, phases, ctx


def test_p3b_records_nominal_run() -> None:
    s, rows, events, phases, ctx = _run()
    p = r9.p3b_records(s, rows, events, phases, ctx)
    assert p["departure"]["t_departure_s"] == pytest.approx(30.0, abs=1e-9)
    assert p["P3-1_crawler"]["crawler_zero"] and p["P3-1_crawler"]["window_complete"]
    assert p["P3-2_loc"]["within"] and p["P3-2_loc"]["loc_minus_departure_s"] == pytest.approx(0.8, abs=1e-9)
    assert not p["P3-2_loc"]["crawler_loaded_at_loc"] and p["P3-2_loc"]["loc_before_first_done"]
    assert p["P3-3_leg_force"]["within"] and p["P3-3_leg_force"]["F_min_after_N"] == [90e3] * 4
    assert p["creep_stop"]["t_final_s"] == pytest.approx(32.181, abs=1.5e-3)
    a = p["P3-4_attitude"]
    assert a["within_0p2"] and a["window_after_creep_stop"] and not a["within_deadband_0p03_record"]
    assert a["end_mean_roll_pitch_deg"][1] == pytest.approx(0.05)
    assert a["end_mean_minus_settle_deg"][1] == pytest.approx(0.05 - 0.15)
    assert a["post_liftoff_absmax_deg"][1] == pytest.approx(0.5)
    assert not a["done"]["before_creep_stop"]
    assert p["P3-5_clearance_stroke"]["within"]
    assert p["P3-6_ready"]["t_ready_after_loop_start_s"] == pytest.approx(37.0) and p["P3-6_ready"]["within"]
    assert p["P3-8_false_triggers"]["within"] and p["P3-8_false_triggers"]["first_touch_t_s"]["FL"] == pytest.approx(12.0)
    assert p["P3-9_deferred"]["note"] == "deferrals 0" and not p["P3-9_deferred"]["flag"]
    tu = p["track_utilisation"]
    assert tu["max"] == [0.2, 0.2] and tu["t_max_s"][0] < 30.0  # masked after the departure (N = 0)
    assert p["W61_watch"]["fallback_events"] == 0 and not p["W61_watch"]["warnings"]
    assert p["checks"]["P3-4_within_0p2"] and p["checks"]["P3-9_flags"] == 0
    p2 = r9.p3b_records(*_run(end_pitch_deg=0.25)[:4], ctx)
    assert not p2["P3-4_attitude"]["within_0p2"]


def test_p3b_records_false_triggers_deferral_and_w61() -> None:
    s, rows, events, phases, ctx = _run()
    f = s["F_cyl_N"]
    t = s["t_s"]
    f[(t >= 50.0) & (t < 50.5), 3] = 0.5 * F_MIN  # deferred leg dips below F_min
    events = sorted(events + [(20.0, "relevel_predicted:FL"), (12.1, "leg_reapproach_start:RR"),
                              (50.0, "leg_reapproach_deferred:RR"), (55.0, "WARN_ROD_PRESSURE_FALLBACK:FR"),
                              (56.0, "relevel_predicted:FR"), (58.0, "relevel_predicted:FR"),
                              (57.0, "probe_aborted_low_load:FR")])
    phases = phases + [(56.0, "level"), (60.0, "done"), (61.0, "probe"), (70.0, "ready")]
    p = r9.p3b_records(s, rows, events, phases, ctx)
    c = p["P3-8_false_triggers"]["counts"]
    assert c == {"leg_reapproach_start": 1, "relevel_predicted": 1, "probe_aborted_low_load": 0}
    assert not p["P3-8_false_triggers"]["within"]
    ev = {e["event"]: e for e in p["P3-8_false_triggers"]["events"]}
    assert ev["leg_reapproach_start:RR"]["within_first_touch_0p2s_of"] == ["FL", "FR", "RL", "RR"]
    w = p["P3-9_deferred"]["windows"]
    assert len(w) == 1 and w[0]["leg"] == "RR" and w[0]["below_F_min"]
    assert w[0]["window_s"] == [pytest.approx(42.0), pytest.approx(43.1)]  # 50 - 8 .. + T_o 0.8 + 0.3
    assert p["checks"]["P3-9_flags"] == 1
    wr = p["W61_watch"]
    assert wr["fallback_events"] == 1
    row = wr["rows"][0]
    assert row["W-61-1_counts"] == {"relevel_predicted": 2, "probe_aborted_low_load": 1}
    assert row["W-61-1_hits"][0]["F_true_N"] == pytest.approx(90e3) and row["W-61-1_hits"][0]["P5_N"] == P5
    assert row["W-61-3_class"].startswith("false_relevel")  # 90 kN >= 3 x 16.9 kN
    assert row["W-61-2"]["done_to_ready_s"] == pytest.approx(10.0) and row["W-61-2"]["probe_rounds"] == 1
    assert row["after_loc"] and "W-61-4" in row["W-61-1_hits"][0]
    assert len(wr["warnings"]) == 2  # W-61-1 and W-61-3


# --- runner setup -----------------------------------------------------------------------------------


def test_level_c2_config_soil_guard() -> None:
    config, meta = r9.level_c2_config(False)
    assert config.soil.enable and meta["soil_enable"]
    assert r9.lifted_reapproach_meta(config)["max_duration_s"] == 10.0
    off = replace(config, soil=replace(config.soil, enable=False))
    with pytest.raises(SystemExit, match="soil response off"):
        r9.level_c2_config(False, off)
    _, meta_off = r9.level_c2_config(True, off)
    assert not meta_off["soil_enable"] and meta_off["allow_soil_off"]


def test_seal_friction_override() -> None:
    assert r9.seal_friction_override(0.0) == {} and r9.seal_friction_override(None) == {}
    assert r9.seal_friction_override(4.0) == {"actuator.seal_friction.level_N": 4000.0}
    with pytest.raises(ValueError):
        r9.seal_friction_override(-1.0)


def test_p3b_set_24_cases_and_batch_26() -> None:
    cases = r9.p3b_cases()
    assert len(cases) == 24 and len({c["case"] for c in cases}) == 24
    groups = [c["group"] for c in cases]
    assert groups.count("P3b-1") == 10 and groups.count("P3b-2") == 10 and groups.count("P3b-3") == 4
    assert all(c["soil"] == "G1" for c in cases[:10])  # G1 first (5.37.6)
    for soil in ("G1", "J1"):
        sub = [c for c in cases if c["soil"] == soil]
        assert sum(c["fs_kN"] == 4.0 for c in sub) == 6 and {c["fs_kN"] for c in sub} == {0.0, 4.0, 8.0}
        assert all(c["level"] == "top" for c in sub if c["fs_kN"] != 4.0)
    assert {c["grid_m"] for c in cases if c["soil"] in ("J1", "J2")} == {0.01}
    assert {c["grid_m"] for c in cases if c["soil"] in ("G1", "S1")} == {0.02}
    argv = r9.p3b_level_argv(cases[0])
    for a, b in (("--threads", "4"), ("--crawler-grid", "0.04"), ("--fs-kN", "4"), ("--settle-dashpot", "zrp"),
                 ("--duration", "120"), ("--pressure-grade", "normal"), ("--imu-grade", "ideal"),
                 ("--seed", "20261026")):
        assert argv[argv.index(a) + 1] == b
    assert argv[0] == "level" and "--approved" in argv
    batch = _import("s9_batch").batches()["P3b"]
    assert len(batch) == 26
    s8c = [c for c in batch if c.get("s8c")]
    assert [c["case"] for c in s8c] == ["N_RE1c_Fs0_combined", "N_RE1c_Fs8_combined"]
    for c in s8c:
        a = c["argv"]
        assert a[a.index("--only") + 1] == c["case"] and a[a.index("--tag") + 1] == f"p3b_{c['case']}"
        assert a[5].endswith("run_S8C.py") and "--approved" in a
        assert a[6:12] == ["run", "--set", "rest", "--only", c["case"], "--tag"]  # control D-5 command form
    assert r9.P3B_DURATION_S == 120.0 and r9.P3B_SIM_S == 128.0
    assert r9.P3B_EST_S == {"G1": 5800.0, "S1": 5800.0, "J1": 11500.0, "J2": 11500.0}
    assert sum(c["est_s"] for c in batch) == pytest.approx(12 * 5800 + 12 * 11500 + 433 + 528)
    assert [c["case"] for c in batch if not c.get("s8c")] == [c["case"] for c in cases]
    plan = r9.plan_summary()["groups"]
    assert plan["P3b-1"]["cases"] == 10 and plan["P3b-RE1c"]["cases"] == 2


def test_s8c_case_check_reads_the_run_s8c_log(tmp_path) -> None:
    """run_S8C ``run`` exits 0 on a failed case: s9_batch reads the outcome line, the batch folder
    line and result.json (the S8 runner itself is unchanged)."""
    b = _import("s9_batch")
    cid = "N_RE1c_Fs0_combined"
    batch = tmp_path / "S8" / f"p3b_{cid}_20261026_120000"
    (batch / cid).mkdir(parents=True)
    ok_log = f"plan...\n{cid}: ok 431.2s\nbatch wall 433.0 s -> {batch}\n"
    assert (batch / cid / "result.json").exists() is False
    chk = b.s8c_case_check(ok_log, cid)
    assert not chk["ok"] and chk["status"] == "ok" and "result.json missing" in chk["reason"]
    (batch / cid / "result.json").write_text("{}", "utf-8")
    chk = b.s8c_case_check(ok_log, cid)
    assert chk["ok"] and chk["reason"] is None and chk["batch_dir"] == str(batch)
    rel = b.s8c_case_check(f"{cid}: ok 1.0s\nbatch wall 1.0 s -> S8/{batch.name}\n", cid, root=tmp_path)
    assert rel["ok"]  # relative folder resolved against the project root
    failed = b.s8c_case_check(f"{cid}: failed 3.1s\nTraceback ...\nbatch wall 3.2 s -> {batch}\n", cid)
    assert not failed["ok"] and "'failed'" in failed["reason"]
    crashed = b.s8c_case_check("Traceback (most recent call last):\n  ...\nRuntimeError: boom\n", cid)
    assert not crashed["ok"] and crashed["status"] is None and "no 'batch wall" in crashed["reason"]
    other = b.s8c_case_check(f"N_RE1c_Fs8_combined: ok 1.0s\nbatch wall 1.0 s -> {batch}\n", cid)
    assert not other["ok"]  # another case's outcome line does not count
    assert b.S8C_FAILED_RC == 4


def test_s9_batch_marks_an_s8c_row_failed_when_its_case_failed(tmp_path, monkeypatch) -> None:
    """Loop integration: an s8c process exiting 0 with a failed case -> rc 4, batch failed, later
    rows skipped (no new launch); an ok s8c row stays rc 0."""
    import json

    b = _import("s9_batch")
    good = "N_RE1c_Fs0_combined"
    bad = "N_RE1c_Fs8_combined"
    s8 = tmp_path / "S8"
    (s8 / good).mkdir(parents=True)
    (s8 / good / "result.json").write_text("{}", "utf-8")

    def fake(cid: str, status: str) -> list[str]:
        text = f"{cid}: {status} 1.0s\\nbatch wall 1.0 s -> {s8.as_posix()}"
        return [sys.executable, "-I", "-c", f"print('{text}')"]

    rows = [{"case": good, "est_s": 1, "s8c": True, "argv": fake(good, "ok")},
            {"case": bad, "est_s": 1, "s8c": True, "argv": fake(bad, "failed")},
            {"case": "after", "est_s": 1, "s8c": True, "argv": fake("after", "ok")}]
    monkeypatch.setattr(b, "ROOT", tmp_path)
    monkeypatch.setattr(b, "batches", lambda: {"T": rows})
    folder = b.run_batch("T", parallel=1, only=None)
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    by = {c["case"]: c for c in doc["cases"]}
    assert doc["failed"] and by[good]["rc"] == 0 and by[good]["s8c_check"]["ok"]
    assert by[bad]["rc"] == 4 and by[bad]["process_rc"] == 0 and not by[bad]["s8c_check"]["ok"]
    assert by["after"]["rc"] is None  # skipped after the failure
    prog = (folder / "progress.log").read_text("utf-8")
    assert f"END {bad}" in prog and "s8c_check=FAILED" in prog and "SKIP after" in prog


# --- control D-1 ... D-5 (2026-10-26) -------------------------------------------------------------------


def test_creep_stop_two_sided_counts_the_rebound() -> None:
    """D-3: the signed rule takes a rebound (sinkage decreasing) as stopped; |rate| does not."""
    t = _t(0.0, 6.0)
    s = np.zeros((t.size, 4))
    s[:, 0] = np.where(t < 2.0, 1e-3 * t, np.where(t < 3.0, 2e-3 - 1e-3 * (t - 2.0), 1e-3))
    c = r9.creep_stop(t, s, 0.5)
    assert c["t_final_s"] == pytest.approx(2.091, abs=1.5e-3)
    assert c["t_final_two_sided_s"] == pytest.approx(3.181, abs=1.5e-3)
    assert c["t_first_two_sided_s"] == pytest.approx(2.091, abs=1.5e-3)  # the rate passes 0 at the turn


def test_p34_judgement_window() -> None:
    t = _t(0.0, 30.0)
    rp = np.zeros((t.size, 2))
    rp[:, 1] = np.where(t < 20.0, 0.5, 0.03)
    rp[t >= 20.0, 0] = -0.02
    ph = [(1.0, "level"), (15.0, "ready"), (16.0, "probe"), (20.0, "ready")]
    w = r9.p34_judgement_window(t, rp, {"t_final_s": 10.0, "t_final_two_sided_s": 12.0}, ph)
    assert w["t_ready_last_entry_s"] == 20.0 and w["p34_window_s"] == [20.0, 30.0] and w["ready_at_end"]
    assert w["p34_absmax_deg"] == pytest.approx([0.02, 0.03]) and w["within_0p2"] and not w["window_short"]
    assert w["sensor_allowance_left_deg"] == pytest.approx(0.2 - 0.02 - 0.03) and w["budget_residual_le_0p04"]
    assert w["creep_stop_basis"] == "two_sided" and not w["creep_vibration_suspect"] and w["flags"] == []
    short = r9.p34_judgement_window(t, rp, {"t_final_s": 10.0, "t_final_two_sided_s": 27.0}, ph)
    assert short["p34_window_s"] == [27.0, 30.0] and short["window_short"] and "window_short" in short["flags"]
    sus = r9.p34_judgement_window(t, rp, {"t_final_s": 22.0, "t_final_two_sided_s": None}, ph)
    assert sus["creep_vibration_suspect"] and sus["creep_stop_basis"] == "signed" and sus["p34_window_s"][0] == 22.0
    none = r9.p34_judgement_window(t, rp, {"t_final_s": 22.0, "t_final_two_sided_s": 23.0}, ph[:1])
    assert not none["within_0p2"] and "no_ready" in none["flags"] and none["p34_window_s"] is None
    rp2 = rp.copy()
    rp2[t >= 25.0, 1] = 0.21
    bad = r9.p34_judgement_window(t, rp2, {"t_final_s": 10.0, "t_final_two_sided_s": 12.0}, ph)
    assert not bad["within_0p2"] and bad["sensor_allowance_left_deg"] < 0 and not bad["budget_residual_le_0p04"]
    p = r9.p3b_records(*_run())
    assert p["P3-4_attitude"]["p34_window_s"][0] == pytest.approx(45.0)  # last READY entry after the creep stop
    assert p["checks"]["P3-4_absmax_deg"] == pytest.approx(0.05) and p["checks"]["reapproach_limit_fired_FLAG"] == 0


def test_reapproach_limit_records_cause() -> None:
    hist = [{"leg": "RR", "start_s": 10.0, "end_s": 20.0, "travel_m": 0.01, "outcome": "no_contact",
             "protected_periods": 95},
            {"leg": "FL", "start_s": 30.0, "end_s": 31.0, "travel_m": 0.045, "outcome": "no_contact",
             "protected_periods": 0},
            {"leg": "RL", "start_s": 40.0, "end_s": 41.0, "travel_m": 0.01, "outcome": "contact"},
            {"leg": "RR", "start_s": 50.0, "end_s": None, "travel_m": 0.0, "outcome": None}]
    r = r9.reapproach_limit_records(hist, {"max_duration_s": 10.0, "max_travel_m": 0.04})
    assert r["fired"] == 2 and r["by_cause"] == {"time": 1, "travel": 1, "unknown": 0}
    assert r["rows"][0]["protected_periods"] == 95 and r["rows"][0]["duration_s"] == pytest.approx(10.0)
    assert r["open_at_end"] == 1 and r["intervals_total"] == 4
    assert r9.reapproach_limit_records(None, None)["fired"] == 0


def test_level_sensor_setup_grades() -> None:
    from outrigger_sim.control.c2 import C2Config
    from outrigger_sim.sensors.imu import imu_config_for_grade

    cfg = C2Config().with_10hz_d1()
    _, legs, c, m = r9.level_sensor_setup("ideal", "ideal", cfg)
    assert m["leg_sensor_source"] == "LegSensorConfig()" and c is cfg and not m["c2_target_gyro_noise_set_from_grade"]
    imu, legs, c, m = r9.level_sensor_setup("normal", "normal_zeroed", cfg)
    assert legs.stroke_noise_std_m == pytest.approx(1e-4) and str(legs.pressure_error_grade) == "normal"
    assert m["leg_sensors"]["pressure_error_grade"] == "normal" and m["imu_sample_period_s"] == 0.01
    want = imu_config_for_grade("normal_zeroed", sample_period_s=cfg.period_s).gyro_noise_std_rad_s
    assert c.target.gyro_noise_std_rad_s == pytest.approx(want) and m["c2_target_gyro_noise_set_from_grade"]
    assert m["zero_calibration_mode"] == "airborne_roundtrip" and c.zero_calibration == cfg.zero_calibration
    with pytest.raises(ValueError):
        r9.level_sensor_setup("legacy", "ideal", cfg)


def test_zero_calibration_outcome() -> None:
    meta = {"zero_calibration": {"is_active": True, "offsets_N": [1.0, 2.0, 3.0, 4.0],
                                 "result": {"t_start_s": 9.0, "t_end_s": 12.0,
                                            "legs": {"FL": {"status": "calibrated"}, "FR": {"status": "calibrated"},
                                                     "RL": {"status": "skipped", "reason": "grounded"},
                                                     "RR": {"status": "calibrated"}}}}}
    z = r9.zero_calibration_outcome(meta)
    assert not z["all_calibrated"] and z["legs"]["RL"] == {"status": "skipped", "reason": "grounded", "success": False}
    meta["zero_calibration"]["result"]["legs"]["RL"] = {"status": "calibrated"}
    assert r9.zero_calibration_outcome(meta)["all_calibrated"]
    assert not r9.zero_calibration_outcome({})["all_calibrated"]


def _re1c_case(d: Path, *, warn_t: float = 62.6, end_s: float = 62.6, restart: bool = False) -> Path:
    import json

    d.mkdir(parents=True)
    ev = [(7.2, "INFO_PRESSURE_ZERO_CALIBRATED:FL"), (52.6, "leg_reapproach_start:RR"),
          (warn_t, "WARN_LEG_REAPPROACH_NO_CONTACT:RR")]
    if restart:
        ev.append((70.0, "leg_reapproach_start:RR"))
    (d / "controller_events.json").write_text(json.dumps([f"C2Event(t_s={t}, name='{n}')" for t, n in ev]), "utf-8")
    res = {"event": {"forced_retract": {"t_start_s": 50.8}},
           "controller_meta": {"r8": {"lifted_reapproach": {"max_duration_s": 10.0, "max_travel_m": 0.04}},
                               "lifted_reapproach": [{"leg": "RR", "start_s": 52.6, "end_s": end_s, "travel_m": 0.0,
                                                      "outcome": "no_contact", "protected_periods": 100}]},
           "phases": [[0.1, "check"], [20.0, "level"], [60.0, "ready"]],
           "s8_end": {"end_t_s": 92.8, "target_t_s": 92.8, "stopped_at_target": True, "timeout": False}}
    (d / "result.json").write_text(json.dumps(res), "utf-8")
    ts = np.round(np.arange(3.1, 92.85, 0.1), 6)
    cu = np.zeros((ts.size, 4))
    cu[ts >= warn_t, 3] = -0.002
    np.savez(d / "r8_series.npz", t=ts, computed_u=cu)
    (d / "case.log").write_text("... case N_RE1c_Fs0_combined finished: ok\n", "utf-8")
    return d


def test_re1c_summary_r1_to_r5(tmp_path) -> None:
    s = _import("s9_batch_summary")
    ok = s.re1c_summary(_re1c_case(tmp_path / "ok"))
    assert ok["all_ok"] and all(ok[k]["ok"] for k in ("R-1", "R-2", "R-3", "R-4"))
    assert ok["R-2"]["warn_minus_start_s"] == pytest.approx(10.0)
    assert ok["R-5"]["computed_u_RR_at_warning_m_s"] == pytest.approx(-0.002)
    early = s.re1c_summary(_re1c_case(tmp_path / "early", warn_t=61.0, end_s=61.0))
    assert not early["R-2"]["ok"] and not early["R-3"]["ok"] and early["R-1"]["ok"]
    again = s.re1c_summary(_re1c_case(tmp_path / "again", restart=True))
    assert not again["R-4"]["ok"] and again["R-4"]["rr_restarts_after_warning"] == [70.0]
    assert not again["R-1"]["ok"]  # two starts after the forced retract
