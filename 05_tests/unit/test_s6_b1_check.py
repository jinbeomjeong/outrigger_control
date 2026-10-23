"""``s6_stage2_summary.b1_entry`` / ``b1_rows``: B1′ check of spec rev. 7 41.3 supplements."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))

import s6_stage2_summary as sm  # noqa: E402

DEG_H = math.radians(1.0) / 3600.0
DEG_S = math.radians(1.0)


def _case(cid, grade, seed=12345, length=10.0, t_b=10.0, est_deg_h=(18.0, 25.0), events=(),
          revision="R5", meta_drop=(), rms_deg_s=(0.004, 0.003), result=True, outcome=None):
    res_meta = {"outcome": outcome or ("accepted" if est_deg_h is not None else "skipped_motion")}
    if rms_deg_s is not None:
        res_meta["motion_rms_rad_s"] = [v * DEG_S for v in rms_deg_s]
    target = {"gyro_bias_rad_s": None if est_deg_h is None else [v * DEG_H for v in est_deg_h],
              "gyro_bias": {"window_s": t_b, "result": res_meta if result else None}}
    for k in meta_drop:
        target.pop(k)
    meta = {"revision": revision, "target": target}
    return {
        "result": {"case": cid, "settings": {"grade": grade, "seed": seed, "check_time_s": 2.0},
                   "phases": [[0.02, "check"], [0.02 + length, "touch"]],
                   "controller_meta": meta},
        "events": [f"C2Event(t_s=1.0, name='{e}')" for e in events],
        "probes": [[{"is_attitude_rippled": True, "attitude_drift_ratio": 0.4},
                    {"is_attitude_rippled": False, "attitude_drift_ratio": 0.1}]],
    }


def _row(rows, item, case):
    return next(r for r in rows if r["item"] == item and r["case"] == case)


def _none_seed(cid, seed, rms=(0.05, 0.02)):
    return sm.b1_entry(_case(cid, "normal_zeroed", seed, est_deg_h=None, rms_deg_s=rms,
                             events=("WARN_GYRO_BIAS_SKIPPED",)), verdict_7b=True)


def test_normal_seeds_bias_and_check_length() -> None:
    entries = {
        "n0": sm.b1_entry(_case("n0", "normal_zeroed", 12345)),
        "n1": sm.b1_entry(_case("n1", "normal_zeroed", 12346, est_deg_h=(33.0, 20.0))),
        "n2": _none_seed("n2", 12347),
        "rep": sm.b1_entry(_case("rep", "normal_zeroed_repeatability", 12345)),
    }
    assert entries["n0"]["extension_reason"] == "T_b (grade window)"
    assert entries["n0"]["bias_error_deg_h"] == pytest.approx([-2.0, 5.0])
    assert entries["n2"]["events"]["WARN_GYRO_BIAS_SKIPPED"]
    assert entries["n2"]["last_window_rms_deg_s"] == pytest.approx([0.05, 0.02])
    assert not entries["rep"]["independent_seed"]
    rows = sm.b1_rows(entries)
    assert _row(rows, "B1' CHECK length", "n2")["passed"] is True
    assert _row(rows, "B1' bias error per axis", "n0")["passed"] is True
    assert _row(rows, "B1' bias error per axis", "n1")["passed"] is False  # roll 13 deg/h > 12
    held = _row(rows, "B1' bias error per axis", "n2")  # None: held, not failed with 20 deg/h
    assert held["passed"] is None and held["value"] is None and "SKIPPED True" in held["note"]
    assert _row(rows, "B1' None with last-window RMS (logic check)", "n2")["passed"] is True
    shown = _row(rows, "B1' None seed 7b verdict = truth (shown)", "n2")
    assert shown["value"] is True and shown["passed"] is None
    assert not any(r["case"] == "rep" and r["item"] == "B1' bias error per axis" for r in rows)
    seeds = _row(rows, "B1' independent normal seeds", "normal_zeroed")
    assert seeds["value"] == [12345, 12346, 12347] and seeds["passed"] is True
    assert not any(r["item"] == "B1' slope effect" for r in rows)
    q1 = _row(rows, "B1' Q1 abstentions (report)", "n0")
    assert q1["passed"] is None and q1["value"] == [1, 2]


def test_none_with_quiet_window_is_a_logic_defect() -> None:
    e = _none_seed("q", 12345, rms=(0.008, 0.009))
    row = _row(sm.b1_rows({"q": e}), "B1' None with last-window RMS (logic check)", "q")
    assert row["passed"] is False and "logic defect" in row["note"]


def test_all_three_seeds_none_is_held_as_unconfirmed() -> None:
    entries = {f"s{k}": _none_seed(f"s{k}", seed) for k, seed in enumerate(sm.B1_SEEDS)}
    row = _row(sm.b1_rows(entries), "B1' slope effect", "normal_zeroed")
    assert row["passed"] is None and row["note"] == sm.B1_UNCONFIRMED_NOTE


def test_ideal_and_good_windows() -> None:
    ideal = sm.b1_entry(_case("i", "ideal", length=2.0, t_b=2.0, est_deg_h=(0.5, -12.9)))
    good = sm.b1_entry(_case("g", "good_zeroed", length=6.0, t_b=2.5, est_deg_h=(3.0, 1.0)))
    assert good["extension_reason"] == "motion condition (longer than T_b)"
    rows = sm.b1_rows({"i": ideal, "g": good})
    assert _row(rows, "B1' CHECK length", "i")["passed"] is True
    assert not any(r["case"] == "i" and r["item"] == "B1' bias error per axis" for r in rows)
    assert _row(rows, "B1' CHECK length", "g")["passed"] is True
    assert _row(rows, "B1' bias error per axis", "g")["passed"] is True  # |3-5|, |1-5| <= 6


def test_missing_r5_meta_fails_and_r41_is_not_judged() -> None:
    with pytest.raises(sm.B1MetaError, match="gyro_bias"):
        sm.b1_entry(_case("x", "normal_zeroed", meta_drop=("gyro_bias",)))
    with pytest.raises(sm.B1MetaError, match="motion_rms_rad_s"):
        sm.b1_entry(_case("y", "normal_zeroed", est_deg_h=None, rms_deg_s=None))
    old = sm.b1_entry(_case("o", "normal_zeroed", revision="R4.1"))
    assert "before R5" in old["status"] and sm.b1_rows({"o": old}) == []


def test_omega_th_follows_the_window() -> None:
    """Spec rev. 8 44.2: ideal 2 s 0.01, good 2.5 s 0.0112, normal 10 s 0.02 deg/s."""
    assert sm.omega_th_deg_s(2.0) == pytest.approx(0.01)
    assert sm.omega_th_deg_s(2.5) == pytest.approx(0.01118, abs=1e-5)
    assert sm.omega_th_deg_s(10.0) == pytest.approx(0.02)
    quiet_10s = _none_seed("a", 12345, rms=(0.015, 0.012))  # T_b 10 s: below 0.02 -> defect
    row = _row(sm.b1_rows({"a": quiet_10s}), "B1' None with last-window RMS (logic check)", "a")
    assert row["passed"] is False and quiet_10s["omega_th_source"].startswith("computed")
    e = sm.b1_entry(_case("b", "good_zeroed", length=2.5, t_b=2.5, est_deg_h=None,
                         rms_deg_s=(0.015, 0.0), events=("WARN_GYRO_BIAS_SKIPPED",)))
    row = _row(sm.b1_rows({"b": e}), "B1' None with last-window RMS (logic check)", "b")
    assert row["passed"] is True  # 0.015 > 0.0112 at T_b 2.5 s


def test_band_split_into_reading_noise_and_motion() -> None:
    """One probe of FL: extend, hold A, retract, hold B; the reading error is +0.2 kN in A and
    -0.2 kN in B -> static share 0.2 kN, moving share = estimate 1.0 - 0.2 kN."""
    import numpy as np

    n = 40
    u = np.zeros((n, 4))
    u[5:10, 0], u[20:25, 0] = 0.001, -0.001
    f_true = np.full((n, 4), 1e5)
    err = np.zeros((n, 4))
    err[10:20, 0], err[25:35, 0] = 200.0, -200.0
    area = 0.01
    rec = {"t": 0.02 * np.arange(1, n + 1), "u_cmd": u, "F_cyl": f_true,
           "meas.head_pressure": (f_true + err) / area}
    case = {"rec": rec, "probes": [[{"leg_index": 0, "seal_friction_estimate_N": 1000.0}]],
            "result": {"settings": {"start_t_s": 0.0}, "phases": [[0.0, "probe"], [0.7, "ready"]],
                       "controller_meta": {"seal_band_N": 3000.0, "initial_seal_band_N": 13000.0}}}
    out = sm.band_decomposition(case, area)
    leg = out["rounds"][0]["legs"][0]
    assert leg["leg"] == "FL" and leg["static_noise_share_kN"] == pytest.approx(0.2)
    assert leg["moving_share_kN"] == pytest.approx(0.8) and out["seal_band_end_kN"] == 3.0


def test_meta_threshold_is_used_when_present() -> None:
    c = _case("m", "normal_zeroed", est_deg_h=None, rms_deg_s=(0.015, 0.0),
              events=("WARN_GYRO_BIAS_SKIPPED",))
    res = c["result"]["controller_meta"]["target"]["gyro_bias"]
    res["result"]["motion_limit_rad_s"] = math.radians(0.0125)
    res["motion_limit_rad_s"] = math.radians(0.02)
    e = sm.b1_entry(c)
    assert e["omega_th_deg_s"] == pytest.approx(0.0125) and e["omega_th_source"].startswith("meta")
    assert e["omega_th_setting_deg_s"] == pytest.approx(0.02)
    row = _row(sm.b1_rows({"m": e}), "B1' None with last-window RMS (logic check)", "m")
    assert row["passed"] is True  # 0.015 > 0.0125


def test_logic_check_only_for_a_motion_skip() -> None:
    """An implausible (rejected) estimate is not a motion skip: no logic-check row."""
    e = sm.b1_entry(_case("r", "normal_zeroed", est_deg_h=None, rms_deg_s=(0.001, 0.001),
                         outcome="rejected_implausible", events=("WARN_GYRO_BIAS_IMPLAUSIBLE",)))
    rows = sm.b1_rows({"r": e})
    assert not any(r["item"].startswith("B1' None with last-window RMS") for r in rows)
    assert _row(rows, "B1' bias error per axis", "r")["passed"] is None


def test_check_length_is_judged_by_its_reason_code() -> None:
    """U55 / J-3 (spec 55.3): an ideal-grade CHECK extended to 10 s by real motion passes; the
    same length without the motion evidence fails (no blanket '>= 2 s')."""
    moving = sm.b1_entry(_case("m", "ideal", length=10.0, t_b=2.0, est_deg_h=None,
                               rms_deg_s=(0.0, 0.0188), events=("WARN_GYRO_BIAS_SKIPPED",)))
    quiet = sm.b1_entry(_case("q", "ideal", length=10.0, t_b=2.0, est_deg_h=None,
                              rms_deg_s=(0.0, 0.004), events=("WARN_GYRO_BIAS_SKIPPED",)))
    too_long = sm.b1_entry(_case("x", "ideal", length=12.0, t_b=2.0, est_deg_h=None,
                                 rms_deg_s=(0.0, 0.0188), events=("WARN_GYRO_BIAS_SKIPPED",)))
    rows = sm.b1_rows({"m": moving, "q": quiet, "x": too_long})
    assert _row(rows, "B1' CHECK length", "m")["passed"] is True
    assert _row(rows, "B1' CHECK length", "q")["passed"] is False
    assert _row(rows, "B1' CHECK length", "x")["passed"] is False
