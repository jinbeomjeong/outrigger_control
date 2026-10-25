"""Unit tests of the S8 V15 judge (``outrigger_sim.verify.s8_v15``), engine independent."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_v15 as v15

ROOT = Path(__file__).resolve().parents[2]


def test_moving_mean_centred_and_ends():
    x = np.arange(10, dtype=float)
    m = v15.moving_mean(x, 3)
    assert m[5] == pytest.approx(5.0)
    assert m[0] == pytest.approx(0.5)  # shrinking window at the start
    m2 = v15.moving_mean(np.column_stack([x, 2 * x]), 3)
    assert m2.shape == (10, 2)
    assert m2[4, 1] == pytest.approx(8.0)


def test_first_crossing_interpolates_and_picks_first_leg():
    t = np.linspace(0.0, 1.0, 11)
    lam = 1e-3 * t
    y = np.column_stack([np.full(11, 5.0), 10.0 - 20.0 * t, np.full(11, 5.0),
                         10.0 - 12.0 * t])
    c = v15.first_crossing(lam, t, y, 0.0)
    assert c is not None and c.leg == "FR"
    assert c.t_s == pytest.approx(0.5)
    assert c.x == pytest.approx(0.5e-3)
    np.testing.assert_allclose(v15.value_at(c, y), [5.0, 0.0, 5.0, 4.0])
    assert v15.first_crossing(lam, t, y, -100.0) is None


def _synthetic_a(fs: float = 4000.0):
    """Linear RL force decay with the reference thresholds of L4 (5.26.2) built in."""
    t = np.arange(0.0, 120.0, 1e-3)
    lam = 1e-4 * t
    lam_true, lam_lift = 9.832e-3, 11.482e-3
    f_min = 9414.59
    rl_true = f_min + (lam_true - lam) * (f_min + 717.484) / (lam_lift - lam_true)
    N = np.column_stack([np.full_like(t, 1.9e5), np.full_like(t, 5e4),
                         rl_true + 717.484, np.full_like(t, 1.4e5)])
    F = N - 717.484
    f = np.tile([-fs, -fs, -0.8333 * fs, 0.8333 * fs], (t.size, 1))
    return {"t_s": t, "lam_m": lam, "F_N": F, "Fp_N": F - f, "N_N": N, "f_N": f,
            "stuck_frac": np.zeros_like(F)}


def test_metrics_and_judge_a_on_reference_shaped_series():
    ref = v15.load_reference(ROOT)
    ra = v15.reference_a(ref, "rod_side", 4000.0)
    s = _synthetic_a()
    m = v15.metrics_a(s, 9414.59, [4000.0, 4000.0, 3333.2, 3333.2])
    assert m["F_min_true"]["leg"] == "RL"
    assert m["F_min_true"]["mm"] == pytest.approx(9.832, rel=1e-3)
    assert m["liftoff"]["mm"] == pytest.approx(11.482, rel=1e-3)
    checks = v15.judge_a(m, ra, [4000.0, 4000.0, 3333.2, 3333.2])
    names = {c.name: c for c in checks}
    assert names["true F_min threshold [mm]"].passed
    assert names["lift-off threshold [mm]"].passed
    assert names["friction sign at lift-off (FL FR RL RR)"].passed
    assert names["RL true force at lift-off F + m g [N]"].passed
    # net reading at lift-off: synthetic G = -717 + 3333 = 2616 N = upper band edge
    assert names["RL net reading at lift-off in the band [N]"].passed
    # no s_p record in this synthetic series: A-1 cannot pass
    assert not names["FL sliding in W1"].passed


def test_judge_a_fails_on_wrong_leg_and_threshold():
    ref = v15.load_reference(ROOT)
    ra = v15.reference_a(ref, "rod_side", 4000.0)
    m = {"F_min_true": {"mm": 9.0, "leg": "FR"}, "F_min_net_reading": ra["F_min_net_reading"],
         "liftoff": ra["liftoff"]}
    checks = v15.judge_a(m, ra)
    failed = [c.name for c in checks if c.passed is False]
    assert "true F_min threshold [mm]" in failed
    assert "true F_min threshold [mm]: leg" in failed


def test_metrics_b_residual_windows_and_judge():
    ref = v15.load_reference(ROOT)
    rb = v15.reference_b(ref, "rod_side", 4000.0)
    t = np.arange(0.0, 30.0, 1e-3)
    res_t = np.asarray(rb["residual_true_load_change_after_return_N"])
    res_n = np.asarray(rb["residual_net_reading_change_after_return_N"])
    step = (t > 5.0)[:, None]
    F = 1e5 + step * res_t
    G = 1e5 + step * res_n
    lam = np.where(t < 5.0, 0.0, np.where(t < 15.0, 1e-3 * (t - 5.0), 0.0))
    s = {"t_s": t, "lam_m": lam, "F_N": F, "Fp_N": G, "N_N": F + 700.0,
         "f_N": np.zeros_like(F)}
    m = v15.metrics_b(s, 9414.59, t_start_s=5.0, t_end_s=30.0, mean_s=1.0)
    np.testing.assert_allclose(m["residual_true_N"], res_t, atol=1e-9)
    checks = v15.judge_b(m, rb)
    assert all(c.passed for c in checks if c.passed is not None)


def test_oil_energy_locked_is_integral_of_law():
    k1, k2, knee_c, c_lock, f_lock = 3.4e7, 2.6e7, 1.2e-4, 3.0e-3, 2.6e7 * 3.0e-3

    def g(c):
        dc = c - c_lock
        return f_lock + k2 * dc + (k1 - k2) * min(dc, knee_c)

    def u(c):
        return v15.oil_energy_locked_J(k1_N_m=k1, k2_N_m=k2, knee_c_m=knee_c, c_lock_m=c_lock,
                                       F_lock_N=f_lock, c_m=c)

    assert u(c_lock) == pytest.approx(v15.oil_energy_moving_J(k2, c_lock))
    for c in (c_lock - 2e-4, c_lock + 0.5e-4, c_lock + 3e-4):
        h = 1e-9
        assert (u(c + h) - u(c - h)) / (2 * h) == pytest.approx(g(c), rel=1e-6)


def test_ledger_residual_closes_for_consistent_columns():
    n = 50
    w_m = np.linspace(0.0, 100.0, n)
    d_f = np.linspace(0.0, 60.0, n)
    cols = {"E_kin_J": np.zeros(n), "E_grav_J": np.zeros(n), "U_lat_J": np.zeros(n),
            "U_ax_J": w_m - d_f, "D_visc_J": np.zeros(n), "D_f_J": d_f, "W_m_J": w_m,
            "W_L_J": np.zeros(n), "W_res_J": np.zeros(n), "W_switch_J": np.zeros(n)}
    r = v15.ledger_residual(cols)
    np.testing.assert_allclose(r, 0.0, atol=1e-12)
    s = v15.ledger_summary(np.arange(n) * 1e-3, cols, judged=True)
    assert s["E_ref_J"] == pytest.approx(60.0)
    assert s["check_1"]
    assert s["check_4"]
    rows = v15.judge_ledger(s)
    assert [c.row for c in rows] == ["V8(b) (1)", "V8(b) (4)"]
    assert all(c.passed for c in rows)
    assert v15.summarize(rows)["n_checks"] == 2  # L-2: ledger rows are counted


def _creep_noise_series(fs: float = 4000.0, *, deficit_lift_N: float = 450.0, seed: int = 3):
    """Synthetic (a) run with the NSC features of 5.29.2 / 5.29.3:

    * RL contact force falls linearly to 0 at lam 11.482 mm (L4 reference thresholds);
    * every leg creeps along its band edge: ``f = sigma (F_s - 8 N) + zero-mean noise`` (sigma 3 N
      until the last 0.1 mm as in W1 of 5.29.2, 180 N after), piston slip in the expected
      direction;
    * stuck fraction 0.9 on every leg (creep is mostly stuck steps, 5.29.3);
    * in the last 0.1 mm the RL friction is pulled ``deficit_lift_N`` inside the band (ratchet),
      so ``G = F + F_s - deficit``; block minimum contact force 0 in the last 0.2 s.
    """
    rng = np.random.default_rng(seed)
    dt = 1e-3
    t = np.arange(0.0, 120.0, dt)
    lam = 1e-4 * t
    lam_true, lam_lift, f_min, mg = 9.832e-3, 11.482e-3, 9414.59, 717.484
    lim = np.array([fs, fs, 0.8333 * fs, 0.8333 * fs])
    sigma = np.array(v15.FRICTION_SIGN_AT_LIFTOFF)
    rl_true = f_min + (lam_true - lam) * (f_min + mg) / (lam_lift - lam_true)
    F = np.column_stack([np.full_like(t, 1.9e5), np.full_like(t, 5e4), rl_true,
                         np.full_like(t, 1.4e5)])
    last = lam >= lam_lift - 1e-4
    noise = rng.normal(0.0, 1.0, F.shape) * np.where(last, 180.0, 3.0)[:, None]
    f = sigma * (lim - 8.0) + noise
    f = np.clip(f, -lim, lim)
    f[last, 2] = -(lim[2] - deficit_lift_N) + noise[last, 2]
    F = F + noise  # rod-force HF part
    N = F + mg
    s_p = np.outer(t, 1e-5 * np.array(v15.PISTON_SLIP_SIGN))  # 10 um/s along the expected sign
    n_min = N.copy()
    n_min[t > (lam_lift / 1e-4) - 0.5, 2] = 0.0  # noisy crossing lands up to ~0.1 s early
    return {"t_s": t, "lam_m": lam, "F_N": F, "Fp_N": F - f, "N_N": N, "f_N": f,
            "stuck_frac": np.full_like(F, 0.9), "s_p_m": s_p, "N_min_N": n_min}, lim


def test_a1_creep_with_noise_passes_even_at_stuck_fraction_0p9():
    ref = v15.load_reference(ROOT)
    ra = v15.reference_a(ref, "rod_side", 4000.0)
    s, lim = _creep_noise_series()
    fine_t = (11.482e-3 - 1.5e-4) / 1e-4  # fine window starts 0.15 mm before lift-off
    m = v15.metrics_a(s, 9414.59, lim, fine_start_t_s=fine_t)
    assert m["W1"]["end_source"] == "timeline.fine_start_t_s"
    checks = {c.name: c for c in v15.judge_a(m, ra, lim)}
    for leg in v15.LEGS:
        c = checks[f"{leg} sliding in W1"]
        assert c.passed, c.note
        assert c.value["deficit_mean_N"] == pytest.approx(8.0, abs=3.0)
    assert m["at_liftoff"]["stuck_fraction"] == pytest.approx([0.9] * 4)
    assert checks["RL W1 mean G - (F + F_s) [N]"].passed
    assert checks["RL W1 mean G - (F + F_s) [N]"].value == pytest.approx(-8.0, abs=3.0)
    assert checks["friction sign at lift-off (FL FR RL RR)"].passed
    # A-2 (iii): deficit 0.45 kN inside the band passes
    c3 = checks["RL net reading at lift-off in the band [N]"]
    assert c3.passed
    assert checks["RL deficit F + F_s - G at lift-off [N]"].value == pytest.approx(450.0, abs=120.0)
    assert checks["RL deficit F + F_s - G at lift-off [N]"].passed is None  # A-3 record
    hf = checks["1 ms rod-force HF sigma, last 0.1 mm (FL FR RL RR) [N]"].value
    assert hf[2] > 100.0
    assert checks["RL blocks with N_min = 0, last 0.2 s"].value > 150
    # the old rule would have failed (stuck fraction 0.9 at lift-off): no such row any more
    assert not any("all legs sliding" in name for name in checks)


def test_a1_fails_on_large_deficit_wrong_sign_and_short_slip():
    lim = np.array([4000.0, 4000.0, 3333.2, 3333.2])
    w1 = {"edge_deficit_mean_N": [10.0, 90.0, 10.0, 10.0],
          "piston_slip_um": [500.0, 200.0, -300.0, -5.0]}
    res = {c.name: c.passed for c in v15.judge_w1_sliding(w1, lim)}
    assert res == {"FL sliding in W1": True, "FR sliding in W1": False,  # 90 N > max(80, 50)
                   "RL sliding in W1": False,  # wrong sign
                   "RR sliding in W1": False}  # |slip| 5 um < 10 um
    # the 50 N floor applies to small F_s
    small = {c.name: c.passed for c in v15.judge_w1_sliding(
        {"edge_deficit_mean_N": [45.0] * 4, "piston_slip_um": [20.0, 20.0, 20.0, -20.0]},
        np.full(4, 1000.0))}
    assert all(small.values())


def test_a2_iii_fails_above_the_upper_band_edge():
    ref = v15.load_reference(ROOT)
    ra = v15.reference_a(ref, "rod_side", 4000.0)
    s, lim = _creep_noise_series(deficit_lift_N=-400.0)  # 0.4 kN above F + F_s (miss side)
    fine_t = (11.482e-3 - 1.5e-4) / 1e-4
    m = v15.metrics_a(s, 9414.59, lim, fine_start_t_s=fine_t)
    checks = {c.name: c for c in v15.judge_a(m, ra, lim)}
    c3 = checks["RL net reading at lift-off in the band [N]"]
    assert not c3.passed, c3.note
    assert checks["RL true force at lift-off F + m g [N]"].passed


def test_ledger_l1_negative_dvisc_mech_rule_and_eref():
    """Dashpot-NSC loop: D_visc falls linearly (-0.06 W) and the same energy shows up as an
    unbooked contact loss; R closes only without the dashpot channel."""
    n = 2001
    t = np.linspace(0.0, 200.0, n)
    w_m = np.linspace(0.0, 150.0, n)
    d_f = np.linspace(0.0, 100.0, n)
    d_visc = -0.06 * t  # recorded, negative: the lagged dashpot feeds the NSC noise ...
    # ... and the NSC contact absorbs the same energy outside the ledger, so the stored energy
    # follows W_m - D_f only; +0.05 J constant mechanical residual
    u_ax = w_m - d_f + 0.05
    u_ax[0] = 0.0
    cols = {"E_kin_J": np.zeros(n), "E_grav_J": np.zeros(n), "U_lat_J": np.zeros(n),
            "U_ax_J": u_ax, "D_visc_J": d_visc, "D_visc_ax_J": d_visc - 1e-3 * t,
            "D_visc_lat_J": 1e-3 * t, "D_f_J": d_f, "W_m_J": w_m, "W_L_J": np.zeros(n),
            "W_res_J": np.zeros(n), "W_switch_J": np.zeros(n)}
    dt = np.where(t > 190.0, 1e-5, 1e-4)
    s = v15.ledger_summary(t, cols, judged=True, dt_s=dt)
    assert s["E_ref_J"] == pytest.approx(100.0)  # negative D_visc excluded
    assert s["R_end_J"] == pytest.approx(-12.0 + 0.05, abs=1e-9)
    assert s["R_mech_end_J"] == pytest.approx(0.05, abs=1e-9)
    assert s["check_4"]  # 0.05 / 100 = 0.05 % <= 1 %
    assert s["D_visc"]["rate_W"] == pytest.approx(-0.06)
    assert s["D_visc"]["rate_fine_1e-5_W"] == pytest.approx(-0.06)
    assert s["D_visc"]["D_visc_ax_J"] == pytest.approx(-12.2)
    assert "dashpot" in s["D_visc"]["note"]
    # above the 1 % rule
    cols2 = dict(cols, U_ax_J=cols["U_ax_J"] + np.where(t > 0, 1.5, 0.0))
    s2 = v15.ledger_summary(t, cols2, judged=True)
    assert not s2["check_4"]
    assert v15.summarize(v15.judge_ledger(s2))["n_failed"] >= 1
    # F_s 0 (rule (i)): recorded only
    s0 = v15.ledger_summary(t, dict(cols, D_f_J=np.zeros(n)), judged=False)
    assert all(c.passed is None for c in v15.judge_ledger(s0))


def test_round_trip_complete_tolerates_block_mean_at_the_top():
    assert v15.round_trip_complete({"lam_max_mm": 9.99999211624436, "lam_end_mm": 0.0}, 0.010)
    assert not v15.round_trip_complete({"lam_max_mm": 9.99, "lam_end_mm": 0.0}, 0.010)
    assert not v15.round_trip_complete({"lam_max_mm": 10.0, "lam_end_mm": 0.01}, 0.010)


def test_dynamic_df_lookup():
    dyn = v15.load_dynamic_check(ROOT)
    assert v15.dynamic_df_J(dyn, "rod_side", 4000.0, "b") == pytest.approx(103.051, rel=1e-4)
    assert v15.dynamic_df_J(dyn, "rod_side", 8000.0, "a", 5e-5) == pytest.approx(114.576, rel=1e-4)
    assert v15.level_key(8000.0) == "L8"
