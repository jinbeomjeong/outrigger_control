"""Bundle-C judge helpers (s6_control_spec.md 150 C-5): guard intervals and the load-oscillation
decay metric on synthetic records; dyn rev. 37 5.24 rules (leg zeta record, expected t_sat
warning, snapshot re-tag check incl. the refused S6_crawler_top_flat_RRpre)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s6_bundle_c as bc


def _series(active_from, active_to, t_end=10.0):
    t = np.round(np.arange(0.1, t_end + 1e-9, 0.1), 10)
    g = (t >= active_from - 1e-9) & (t <= active_to + 1e-9)
    return {"t": t, "guard_active": g}


def test_guard_interval_ends_one_period_after_the_last_active_instant() -> None:
    iv = bc.guard_intervals(_series(2.0, 3.0))
    assert len(iv) == 1
    assert iv[0][0] == 2.0 and abs(iv[0][1] - 3.1) < 1e-9


def test_decaying_oscillation_passes_and_sustained_fails() -> None:
    tp = np.arange(0.0, 10.0, 1e-3)
    end = 3.1
    base = np.full((tp.size, 4), 50e3)

    def pads(decay_s):
        osc = 3e3 * np.sin(2 * np.pi * 2.0 * tp) * np.exp(-np.maximum(tp - end, 0) / decay_s)
        f = base.copy()
        f[:, 0] += osc
        return {"t": tp, "F_cyl": f}

    ok = bc.guard_oscillation_metrics(pads(0.5), _series(2.0, 3.0))[0]
    assert ok["passed"] and ok["ratio"] < 0.5
    bad = bc.guard_oscillation_metrics(pads(1e6), _series(2.0, 3.0))[0]
    assert not bad["passed"]


# --- C-5 definitions (spec rev. 31 154.3, 155 C-R3) -----------------------------------------

V_MAX = 0.0209243016


def _cmd_series(u_leg0, guard_from=1.0, guard_to=1.5, t_end=20.0):
    t = np.round(np.arange(0.1, t_end + 1e-9, 0.1), 10)
    u = np.zeros((t.size, 4))
    u[:, 0] = u_leg0(t)
    g = (t >= guard_from - 1e-9) & (t <= guard_to + 1e-9)
    return {"t": t, "issued_u": u, "guard_active": g}


def test_c5a_sustained_half_hertz_fails_and_damped_passes() -> None:
    amp = 0.2 * V_MAX
    sus = bc.command_reversal_metrics(
        _cmd_series(lambda t: amp * np.sin(2 * np.pi * 0.5 * (t - 1.0) + 0.3)), V_MAX)
    assert sus["max_reversals"] >= 4 and bc.c5a_verdict(sus["max_reversals"]) is False
    zeta, wn = 0.5, 2 * np.pi * 0.5
    wd = wn * np.sqrt(1 - zeta**2)

    def damped(t):
        tau = np.maximum(t - 1.0, 0.0)
        return amp * np.exp(-zeta * wn * tau) * np.sin(wd * tau + 0.3) * (t >= 1.0)

    dmp = bc.command_reversal_metrics(_cmd_series(damped), V_MAX)
    assert dmp["max_reversals"] <= 2 and bc.c5a_verdict(dmp["max_reversals"]) is True
    assert bc.c5a_verdict(3) is None
    # commands inside the 0.02 v_max deadband are not counted
    small = bc.command_reversal_metrics(
        _cmd_series(lambda t: 0.01 * V_MAX * np.sin(2 * np.pi * 0.5 * t)), V_MAX)
    assert small["max_reversals"] == 0
    none = bc.command_reversal_metrics(_cmd_series(np.sin, guard_from=99, guard_to=99), V_MAX)
    assert none["max_reversals"] is None and bc.c5a_verdict(None) is None


def test_c5b_guard_restarts_in_ten_seconds() -> None:
    t = np.round(np.arange(0.1, 30.0, 0.1), 10)

    def series(starts):
        g = np.zeros(t.size, dtype=bool)
        for s in starts:
            g |= (t >= s - 1e-9) & (t <= s + 0.5 + 1e-9)
        return {"t": t, "guard_active": g}

    assert bc.guard_restart_metrics(series([2.0, 6.0]))["max_in_window"] == 2
    assert bc.guard_restart_metrics(series([2.0, 6.0, 10.0]))["max_in_window"] == 3
    assert bc.guard_restart_metrics(series([2.0, 13.0, 24.0]))["max_in_window"] == 1
    assert bc.guard_restart_metrics(series([]))["max_in_window"] == 0


def _c5c(freq_hz, amp_deg=0.03, t_end=20.0):
    t = np.arange(0.0, t_end, 1e-3)
    rp = np.zeros((t.size, 2))
    rp[:, 1] = 0.5 + 1e-4 * t + amp_deg * np.sin(2 * np.pi * freq_hz * t)  # trend + oscillation
    win = bc.quiet_ready_windows([(0.0, t_end)], [], t)
    res = bc.attitude_residual_metrics(t, rp, win)
    return res["worst"]


def test_c5c_rocking_residual_is_review_and_slow_oscillation_fails() -> None:
    w = _c5c(1.8)
    assert w["half_range_deg"] > bc.ATT_OSC_LIMIT_DEG and abs(w["zero_cross_hz"] - 1.8) < 0.1
    assert bc.c5c_verdict(w["half_range_deg"], w["zero_cross_hz"]) is None
    w = _c5c(0.5)
    assert abs(w["zero_cross_hz"] - 0.5) < 0.1
    assert bc.c5c_verdict(w["half_range_deg"], w["zero_cross_hz"]) is False
    w = _c5c(0.5, amp_deg=0.005)
    assert bc.c5c_verdict(w["half_range_deg"], w["zero_cross_hz"]) is True
    assert bc.c5c_verdict(None, None) is None


def test_c5c_settlement_step_is_outside_the_quiet_windows() -> None:
    t = np.arange(0.0, 30.0, 1e-3)
    rp = np.zeros((t.size, 2))
    rp[:, 0] = 0.05 * np.clip((t - 10.0) / 2.0, 0.0, 1.0)  # 2 s settlement ramp from 10 s
    rp[:, 0] -= 0.05 * np.clip((t - 12.5) / 1.5, 0.0, 1.0)  # re-levelling 12.5 .. 14 s
    busy = [(10.0, 12.0 + bc.C5C_QUIET_AFTER_S)]  # floor event end + 3 s
    busy += [(x, x + 0.1 + bc.C5C_QUIET_AFTER_S) for x in np.arange(12.5, 14.0, 0.1)]
    win = bc.quiet_ready_windows([(0.0, 30.0)], busy, t)
    assert len(win) == 2 and abs(win[0][0] - 5.0) < 1e-6 and win[0][1] < 10.0
    assert win[1][0] >= 17.0 - 1e-6
    res = bc.attitude_residual_metrics(t, rp, win)
    w = res["worst"]
    assert w["half_range_deg"] < 1e-9 and bc.c5c_verdict(w["half_range_deg"], None) is True
    # the same step inside a window would be seen
    whole = bc.attitude_residual_metrics(t, rp, [(5.0, 30.0)])["worst"]
    assert whole["half_range_deg"] > bc.ATT_OSC_LIMIT_DEG
    # a short gap gives no window
    assert bc.quiet_ready_windows([(0.0, 6.5)], [], t) == []


def test_consistency_rows_null_reference_and_ready() -> None:
    ref = {"A": {"min_force_kN": None, "ready_s": None, "reason": "no floor event"},
           "B": {"min_force_kN": 50.0, "ready_minus_touch_s": 36.0}}
    rows = bc._consistency_rows({"case": "A"}, ref)
    assert len(rows) == 1 and rows[0]["note"] == "not representable: no floor event"
    assert rows[0]["passed"] is None and rows[0]["kind"] == "consistency"
    rows = bc._consistency_rows({"case": "B", "min_cyl_after_liftoff_kN": 44.0,
                                 "t_ready_minus_touch_s": 38.5}, ref)
    assert [r["item"] for r in rows] == ["146 consistency min force",
                                         "146 consistency READY - TOUCH end [s]"]
    assert rows[0]["note"] == "FLAG: explain the difference"  # |44 - 50| > max(5, 5)
    assert rows[1]["value"] == 38.5 and rows[1]["limit"] == 36.0 and "+2.5 s" in rows[1]["note"]
    assert all(r["passed"] is None for r in rows)
    rows = bc._consistency_rows({"case": "B"}, ref)
    assert rows[0]["value"] is None and rows[1]["value"] is None


def test_c5_rows_judged_and_report() -> None:
    m = {"case": "C5_x",
         "c5a_command_reversals": {"max_reversals": 4, "leg": "FL", "window_start_s": 1.0,
                                   "threshold_m_s": 0.02 * V_MAX},
         "c5b_guard_restarts": {"max_in_window": 1, "starts": 1},
         "c5c_ready_settling": {"worst": None, "windows": [], "source": "Record 10 Hz"},
         "guard_oscillation": [{"t_end_s": 3.0, "ratio": 0.7, "passed": False}]}
    rows = {r["item"]: r for r in bc._c5_rows(m)}
    assert rows["C-5a command sign reversals (4 s window)"]["passed"] is False
    assert rows["C-5b guard restarts (10 s window)"]["passed"] is True
    c = rows["C-5c quiet READY attitude residual half range [deg]"]
    assert c["passed"] is None and c["note"].startswith("no quiet READY")
    rep = rows["C-5 guard load oscillation ratio (report)"]
    assert rep["kind"] == "report" and rep["passed"] is None and rep["value"] == 0.7


# --- dyn rev. 37 5.24 rules -----------------------------------------------------------------

STATES = Path(__file__).resolve().parents[2] / "07_results" / "states_L1R"


def _k_beta(beta_key: str) -> list[float]:
    from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references

    return [float(v) for v in load_references().get(BETA_K_L1_N_M, beta=beta_key)]


def test_leg_zeta_effective_matches_dyn_5_24_1() -> None:
    k1 = _k_beta("beta_1.0e+09")
    z069 = bc.leg_zeta_effective(_k_beta("beta_6.9e+08"), k1)
    z16 = bc.leg_zeta_effective(_k_beta("beta_1.6e+09"), k1)
    assert [round(z, 4) for z in z069] == [0.0354, 0.0354, 0.0356, 0.0356]
    assert [round(z, 4) for z in z16] == [0.0246, 0.0246, 0.0244, 0.0244]
    assert bc.leg_zeta_effective(k1, k1) == [0.03] * 4


def _t_sat_max_beta16() -> list[float]:
    """``2 c_n / k_n`` as ``L1SpeedActuator.from_params`` builds it for beta 1.6 (YAML c_n)."""
    from outrigger_sim.params import load_params

    cn = load_params(level="top").get("contact.rigid_floor.L1.cn_per_pad_N_s_m")
    k = _k_beta("beta_1.6e+09")
    return [2.0 * float(cn[leg]) / kn for leg, kn in zip(bc.LEGS, k, strict=True)]


def _msg(ten_dt: float, maxes) -> str:
    # same text as L1SpeedActuator.check_saturation_stop
    return (f"saturation stop time 0.002 s outside 10 dt = {ten_dt} s .. "
            f"2 c_n / k_n = {list(maxes)} s")


def test_beta16_t_sat_warning_is_expected_only_in_that_form() -> None:
    maxes = _t_sat_max_beta16()
    assert abs(maxes[0] - 1.779e-3) < 1e-5 and maxes[2] > 2e-3  # FL / FR only
    for ten_dt in (10 * 2e-4, 10 * 1e-5):  # L1 dt and the transition dt
        c = bc.classify_warning(_msg(ten_dt, maxes), "RuntimeWarning", 1.6)
        assert c["expected"] and c["label"] == bc.EXPECTED_SATURATION_WARNING
        assert c["legs_over"] == ["FL", "FR"]
    assert not bc.classify_warning(_msg(2e-3, maxes), "RuntimeWarning", 1.0)["expected"]
    assert not bc.classify_warning(_msg(2e-3, maxes), "UserWarning", 1.6)["expected"]
    assert not bc.classify_warning(_msg(2.5e-3, maxes), "RuntimeWarning", 1.6)["expected"]
    rl_too = [maxes[0], maxes[1], 1.9e-3, maxes[3]]
    assert not bc.classify_warning(_msg(2e-3, rl_too), "RuntimeWarning", 1.6)["expected"]
    assert not bc.classify_warning("something else", "RuntimeWarning", 1.6)["expected"]


def test_judge_does_not_count_expected_warnings() -> None:
    maxes = _t_sat_max_beta16()
    exp = bc.classify_warning(_msg(2e-3, maxes), "RuntimeWarning", 1.6)
    other = bc.classify_warning("divide by zero", "RuntimeWarning", 1.6)
    row = bc._warning_rows({"case": "x", "bundle_c": {"warnings": [exp, exp]}})[0]
    assert row["value"] == 0 and row["passed"] is True
    row = bc._warning_rows({"case": "x", "bundle_c": {"warnings": [exp, other]}})[0]
    assert row["value"] == 1 and row["passed"] is None  # flag, never a failure


def _payload(state=(5, 5, 5, 5), f_lock=(0, 0, 0, 0), contact=(False,) * 4, u=(0, 0, 0, 0)):
    return {"rod_chamber.l1r_state": np.asarray(state, float),
            "rod_chamber.l1r_F_lock_N": np.asarray(f_lock, float),
            "ground_bushing.in_contact": np.asarray(contact, bool),
            "l1_actuator.u_applied_m_s": np.asarray(u, float)}


@dataclass(frozen=True)
class _Snap:
    params_sha256: str
    payload: dict


def test_retag_check_conditions() -> None:
    assert bc.snapshot_retag_check(_payload())["passed"]
    rrpre = _payload(state=(5, 5, 5, 3), f_lock=(0, 0, 0, 11922.66),
                     contact=(False, False, False, True))
    chk = bc.snapshot_retag_check(rrpre)
    assert not chk["passed"]
    for name in ("l1r_state_LIFT", "F_lock_zero", "no_pad_contact"):
        assert chk["conditions"][name]["legs_failing"] == ["RR"]
    assert chk["conditions"]["u_applied_zero"]["passed"]
    assert not bc.snapshot_retag_check(_payload(u=(0, 0, 1e-6, 0)))["passed"]
    missing = _payload()
    del missing["l1_actuator.u_applied_m_s"]
    assert not bc.snapshot_retag_check(missing)["passed"]


def test_retag_refuses_rrpre_and_keeps_unchanged_sha() -> None:
    rrpre = _Snap("yaml", _payload(state=(5, 5, 5, 3), f_lock=(0, 0, 0, 11922.66),
                                   contact=(False, False, False, True)))
    with pytest.raises(bc.SnapshotRetagRefused):
        bc.retag_snapshot(rrpre, "override", name="S6_crawler_top_flat_RRpre")
    same, chk = bc.retag_snapshot(rrpre, "yaml")  # no override: no re-tag, no refusal
    assert same is rrpre and chk["required"] is False and chk["passed"] is False
    ok = _Snap("yaml", _payload())
    new, chk = bc.retag_snapshot(ok, "override")
    assert new.params_sha256 == "override" and chk["required"] and chk["passed"]


def _stored_payload(name: str) -> dict:
    with np.load(STATES / f"{name}.npz", allow_pickle=False) as z:
        return {k.removeprefix("payload."): z[k] for k in z.files if k.startswith("payload.")}


@pytest.mark.skipif(not (STATES / "S6_crawler_top_flat_RRpre.npz").exists(),
                    reason="07_results/states_L1R snapshots not present")
def test_stored_snapshots_rrpre_refused_top_flat_accepted() -> None:
    rr = bc.snapshot_retag_check(_stored_payload("S6_crawler_top_flat_RRpre"))
    assert not rr["passed"]
    assert rr["conditions"]["l1r_state_LIFT"]["legs_failing"] == ["RR"]
    with pytest.raises(bc.SnapshotRetagRefused):
        bc.retag_snapshot(_Snap("yaml", _stored_payload("S6_crawler_top_flat_RRpre")), "x")
    for name in ("top_flat", "top_roll5.5", "top_fdown3.5", "top_fup3.5", "top_rp05",
                 "middle_rp05", "bottom_rp05", "top_fdown3.2", "top_roll4.4", "top_rpB",
                 "middle_rpB", "bottom_rpB"):
        path = STATES / f"S6_crawler_{name}.npz"
        if path.exists():
            assert bc.snapshot_retag_check(_stored_payload(f"S6_crawler_{name}"))["passed"], name
