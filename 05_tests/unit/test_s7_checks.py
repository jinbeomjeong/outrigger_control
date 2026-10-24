"""verify/s7 (S7 L2b-NSC judge): analysis helpers, pre-checks, V-rule pass / fail boundaries."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s7

ROOT = Path(__file__).resolve().parents[2]
REF_FILE = ROOT / "06_analysis" / "00_dynamics" / "reference.json"


@pytest.fixture(scope="module")
def block() -> dict:
    return json.loads(REF_FILE.read_text(encoding="utf-8"))[s7.REF_BLOCK]


# --- helpers ------------------------------------------------------------------------------------


def test_centred_moving_mean_of_a_line_is_the_line_at_the_centre() -> None:
    t = np.arange(0.0, 1.0, 0.001)
    y = np.column_stack([3.0 * t + 1.0, -t])
    tc, m = s7.centred_moving_mean(t, y, 100)
    assert m.shape == (len(t) - 99, 2)
    np.testing.assert_allclose(m[:, 0], 3.0 * tc + 1.0, atol=1e-12)
    np.testing.assert_allclose(m[:, 1], -tc, atol=1e-12)


def test_first_crossing_interpolates_and_reports_none() -> None:
    x = np.array([0.0, 1.0, 2.0])
    assert s7.first_crossing(x, [10.0, 6.0, 2.0], 4.0) == pytest.approx(1.5)
    assert s7.first_crossing(x, [1.0, 2.0, 3.0], 2.5, downward=False) == pytest.approx(1.5)
    assert s7.first_crossing(x, [10.0, 9.0, 8.0], 4.0) is None


def test_integrate_rotation_trapezoid_exact_for_linear_rate() -> None:
    t = np.linspace(0.0, 2.0, 201)
    w = np.column_stack([0.1 * t, np.zeros_like(t), np.full_like(t, 0.5)])
    th = s7.integrate_rotation(t, w)
    np.testing.assert_allclose(th[-1], [0.05 * 4.0, 0.0, 1.0], atol=1e-12)


def test_modal_q_of_a_small_pitch_rotation_about_the_origin() -> None:
    t = np.linspace(0.0, 1.0, 1001)
    omega_y = 1e-4
    w = np.column_stack([np.zeros_like(t), np.full_like(t, omega_y), np.zeros_like(t)])
    origin = np.zeros((len(t), 3))
    q = s7.modal_q(t, origin, np.zeros_like(origin), w, (0.0, 0.0, 2.0), np.zeros((len(t), 4)))
    theta_y = omega_y * t
    np.testing.assert_allclose(q[:, 4], theta_y, atol=1e-15)
    # u = theta x p: pitch about +y moves a point 2 m above the origin to +x
    np.testing.assert_allclose(q[:, 0], 2.0 * theta_y, atol=1e-15)
    assert q.shape == (len(t), 10)


def test_in_plane_removes_the_normal_component() -> None:
    n = np.array([0.0, 0.0, 2.0])
    np.testing.assert_allclose(s7.in_plane([1.0, 2.0, 3.0], n), [1.0, 2.0, 0.0])
    v = np.array([[1.0, 0.0, 1.0], [0.0, 1.0, -1.0]])
    np.testing.assert_allclose(s7.in_plane(v, n), [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def test_envelope_ratio_one_for_an_undamped_sine_below_one_for_decay() -> None:
    t = np.arange(0.0, 60.0, 0.001)
    assert s7.envelope_ratio(t, np.sin(2 * np.pi * 2.0 * t)) == pytest.approx(1.0, abs=1e-4)
    decay = np.exp(-0.05 * t) * np.sin(2 * np.pi * 2.0 * t)
    assert s7.envelope_ratio(t, decay) < 0.1


def test_printed_half_unit() -> None:
    assert s7.printed_half_unit(0.4011) == pytest.approx(5e-5)
    assert s7.printed_half_unit(25905700.0) == pytest.approx(50.0)
    assert s7.printed_half_unit(0.0) == 0.0


# --- creep thresholds / secant ------------------------------------------------------------------


def _creep(slopes=(-6000.0, 6000.0, 7000.0, -7000.0), f0=(20e3, 20e3, 20e3, 15e3)):
    t = np.arange(0.0, 20.0, 0.001)
    travel = 1e-3 * t  # 1 mm/s
    f = np.asarray(f0) + np.outer(travel * 1e3, slopes)
    n = f + 500.0
    return t, travel, f, n


def test_creep_thresholds_find_leg_and_travel() -> None:
    t, travel, f, n = _creep()
    res = s7.creep_thresholds(t, travel, f, n, 9414.59, window=100, exclude_leg=2)
    # RR: 15e3 - 7000 x = 9414.59 -> x = 0.79792 mm; lift-off 15.5e3 / 7000 = 2.2143 mm
    assert res.f_min_leg == "RR"
    assert res.f_min_mm == pytest.approx((15e3 - 9414.59) / 7000.0, abs=1e-6)
    assert res.liftoff_leg == "RR"
    assert res.liftoff_mm == pytest.approx(15.5e3 / 7000.0, abs=1e-6)
    sec = s7.secant_at(travel, f, 1e-3, t, 100)
    np.testing.assert_allclose(sec, [-6000.0, 6000.0, 7000.0, -7000.0], atol=1e-6)


def test_threshold_checks_fail_on_wrong_leg_and_pass_inside_5_percent() -> None:
    got = s7.ThresholdResult("RR", 9.0, "RR", 10.5)
    ok = s7.threshold_checks("V14", "x", got, f_min_ref={"value": 8.8053, "leg": "RR"},
                             liftoff_ref={"value": 10.223, "leg": "RR"}, key="k")
    assert all(c.passed for c in ok)
    bad = s7.threshold_checks("V14", "x", s7.ThresholdResult("RL", 9.5, "RR", 10.5),
                              f_min_ref={"value": 8.8053, "leg": "RR"},
                              liftoff_ref={"value": 10.223, "leg": "RR"}, key="k")
    assert [c.passed for c in bad] == [False, False, True, True]


# --- pre-checks ---------------------------------------------------------------------------------


def _table(lp: s7.LegParameters, s_lock: np.ndarray) -> dict:
    return {
        "locked": [True] * 4,
        "s_lock_m (s_ref at the lock instant)": s_lock.tolist(),
        "k_h_N_m": [lp.k_h(i, s_lock[i]) for i in range(4)],
        "k_r_N_m": [lp.k_r(i, s_lock[i]) for i in range(4)],
        "L0r_m": [lp.l0r_m] * 4,
    }


def test_lock_table_convention_passes_and_rod_body_convention_fails(block) -> None:
    lp = s7.LegParameters.from_block(block)
    ref_ext = block["V14"]["cases"]["max pitch+"]["extension_m"]
    # exact placement extensions (as run_S7 slope_pose produces) round to the printed values
    s_ref = np.array([0.6945082266646883, 0.6945082266646883, 0.34008177333531164,
                      0.34008177333531164])
    rows = s7.lock_table_checks("c", _table(lp, s_ref), s_ref_at_lock_m=s_ref,
                                ref_extensions_m=ref_ext, leg_params=lp, locked_legs=range(4))
    assert all(r.passed for r in rows), [r.item for r in rows if not r.passed]
    # rod-body convention s = s_ref - F / k2 (~7 mm at the stroke end) must be caught
    s_rod = s_ref - np.array([118e3, 116e3, 72e3, 70e3]) / np.array([1.65e7, 1.65e7, 2.2e7, 2.2e7])
    rows = s7.lock_table_checks("c", _table(lp, s_rod), s_ref_at_lock_m=s_ref,
                                ref_extensions_m=ref_ext, leg_params=lp, locked_legs=range(4))
    failed = {r.item.split(": ")[1].split(" (")[0] for r in rows if not r.passed}
    assert "s_lock = own s_ref at the lock instant" in failed
    assert "s_lock vs reference extension" in failed


def test_lock_table_k_from_leg_parameters_match_the_e_op_table(block) -> None:
    """The printed-digit bound must cover the reference's own rounding (k_of_s_table e_op)."""
    lp = s7.LegParameters.from_block(block)
    row = block["leg_parameters"]["k_of_s_table"]["e_op"]
    for i in range(4):
        s = row["s_m"][i]
        kh_ref = row["k_h_N_m"][i]
        bound = (lp.k_h_bound(i, s) + s7.printed_rel(kh_ref)
                 + s7.printed_half_unit(s) / (lp.l0h_m + s))
        assert abs(lp.k_h(i, s) / kh_ref - 1.0) <= bound


def test_lock_table_wrong_l0r_fails(block) -> None:
    lp = s7.LegParameters.from_block(block)
    s = np.array([0.4011, 0.4011, 0.3909, 0.3909])
    table = _table(lp, s)
    table["L0r_m"] = [0.10] * 4
    rows = s7.lock_table_checks("c", table, s_ref_at_lock_m=s, ref_extensions_m=None,
                                leg_params=lp, locked_legs=range(4))
    assert [r.passed for r in rows if "L0r = reference" in r.item] == [False]


def test_piston_checks() -> None:
    mon = {"stop_violation_steps": [0, 0, 0, 0], "piston_max_m": [0.7] * 4,
           "piston_min_m": [0.0] * 4, "tolerance_m": 2e-4}
    assert s7.piston_checks("c", mon)[0].passed
    mon["stop_violation_steps"] = [0, 3, 0, 0]
    assert not s7.piston_checks("c", mon)[0].passed


# --- V11b / V9 / V8a / modes ------------------------------------------------------------------


def test_v11b_expected_force_change_matches_5_20_9(block) -> None:
    lp = block["leg_parameters"]
    c = lp["c_oil_moving_N_s_m (zeta 0.10 on k2(e_op), concrete in series)"]
    k2 = lp["k_of_s_table"]["e_op"]["k2_axial_head_only_N_m (moving)"]
    v = 0.0209243016
    assert s7.v11b_expected_dF(c[0], k2[0], v, 2e-3) == pytest.approx(-1555.0, abs=2.0)
    assert s7.v11b_expected_dF(c[2], k2[2], v, 2e-3) == pytest.approx(-1411.0, abs=2.0)


def test_v11b_phase_and_checks_on_a_synthetic_stop() -> None:
    dt = 1e-4
    t = np.arange(dt, 1.0 + dt / 2, dt)
    v, k2, c, lim = 0.0209243016, 2.59057e7, 100206.0, 278738.0
    sat_t = 0.5
    s_ref = np.where(t < sat_t, v * t, v * sat_t + v * 1e-3)  # 2 ms braking: + v t_stop / 2
    force = np.where(t < sat_t, lim * t / sat_t, lim + s7.v11b_expected_dF(c, k2, v, 2e-3))
    force[np.searchsorted(t, sat_t)] = lim
    sat = t >= sat_t
    pos = s_ref - force / k2
    ph = s7.v11b_phase(t, force, s_ref, sat, pos, t0=0.0, t1=1.0, direction=1, k2_N_m=k2)
    rows = s7.v11b_checks("FL", ph, limit_N=lim, expected_dF_N=s7.v11b_expected_dF(c, k2, v, 2e-3),
                          key="k")
    assert all(r.passed for r in rows), [r.item for r in rows if not r.passed]
    # no change after the stop (damping force kept) -> fails the force-change row
    force2 = np.where(t < sat_t, lim * t / sat_t, lim)
    ph2 = s7.v11b_phase(t, force2, s_ref, sat, pos, t0=0.0, t1=1.0, direction=1, k2_N_m=k2)
    rows2 = s7.v11b_checks("FL", ph2, limit_N=lim,
                           expected_dF_N=s7.v11b_expected_dF(c, k2, v, 2e-3), key="k")
    assert [r.passed for r in rows2 if "force change" in r.item] == [False]


def test_v9_first_order_ratio_passes_constant_error_fails() -> None:
    dts = (1e-4, 5e-5, 2.5e-5, 1e-5)
    ff = {d: [1e5] * 4 for d in dts}
    aa = {d: [0.0, 0.01] for d in dts}
    first = {d: -6000.0 - 1e7 * d for d in dts}
    rows = s7.v9_checks(final_force_N=ff, final_att_deg=aa, transient_N=first, ref_dt_s=1e-5,
                        w_total_N=380113.0)
    ratio = [r for r in rows if "error ratio" in r.item][0]
    assert ratio.passed and ratio.value == pytest.approx(2.0)
    const = {d: -6000.0 - (1.0 if d > 1e-5 else 0.0) for d in dts}
    rows = s7.v9_checks(final_force_N=ff, final_att_deg=aa, transient_N=const, ref_dt_s=1e-5,
                        w_total_N=380113.0)
    assert not [r for r in rows if "error ratio" in r.item][0].passed


def test_v8a_zeta_limit_and_growth() -> None:
    zeta = [0.0085, 0.0179, 0.0376, 0.0338, 0.0488, 0.0306]
    rows = [s7.ModeId(i + 1, 1.0, 0.05 * zeta[i], "projection") for i in range(6)]
    assert all(c.passed for c in s7.v8a_checks(1e-4, rows, [1.0] * 6, zeta, key="k"))
    rows[0] = s7.ModeId(1, 1.0, -0.2 * zeta[0], "projection")  # energy injection
    out = s7.v8a_checks(1e-4, rows, [1.0] * 5 + [1.2], zeta, key="k")
    assert not out[0].passed and not out[-1].passed


def test_mode_checks_zeta_uncorrected_30_percent() -> None:
    rows = [s7.ModeId(1, 2.06 * 1.02, 0.0085 * 1.25, "projection")]
    out = s7.mode_checks("V7", "t", rows, f_ref_Hz=[2.0608], zeta_ref=[0.0085], key_f="f",
                         key_zeta="z")
    assert [c.passed for c in out] == [True, True]
    rows = [s7.ModeId(1, 2.0608 * 1.04, 0.0085 * 1.35, "projection")]
    out = s7.mode_checks("V7", "t", rows, f_ref_Hz=[2.0608], zeta_ref=[0.0085], key_f="f",
                         key_zeta="z")
    assert [c.passed for c in out] == [False, False]


# --- statics / V12 / V4 -------------------------------------------------------------------------


def test_settle_checks_pass_on_the_reference_and_fail_on_a_window_span(block) -> None:
    lv = block["levels"]["top"]
    still = {
        "pad_normal_mean_N": lv["contact_force_N (V1)"],
        "axial_spring_compression_mm": lv["axial_spring_compression_mm (V2, F / k2(e_op))"],
        "roll_pitch_mean_deg": lv["static_attitude_deg (roll, pitch) (V3)"],
        "pad_normal_step_std_N": [1000.0] * 4,
        "cylinder_force_step_std_N": [10.0] * 4,
        "pad_normal_window_span_N": [20.0] * 4,
        "cylinder_force_window_span_N": [5.0] * 4,
        "roll_pitch_span_deg": [1e-5, 1e-5],
    }
    # the reference contact sum is W minus nothing (rods included): 1e-4 rel
    rows = s7.settle_checks("top", still, lv, key="k")
    judged = [r for r in rows if r.id != "info"]
    assert all(r.passed for r in judged), [r.item for r in judged if not r.passed]
    still["pad_normal_window_span_N"] = [20.0, 20.0, 120.0, 20.0]
    rows = s7.settle_checks("top", still, lv, key="k")
    assert not [r for r in rows if r.id == "V13"][0].passed


def test_v12_checks_horizontal_tolerance_is_the_larger_of_10_percent_and_200_N() -> None:
    ref = {"contact_vertical_N": [1e5] * 4,
           "contact_horizontal_xy_N": [[-13.0, 16.0], [-80.0, 16.0], [3000.0, -16.0],
                                       [15.0, -16.0]]}
    c = np.array([[-13.0 + 190, 16.0, 1e5], [-80.0, 16.0, 1e5], [3000 * 1.09, -16.0, 1e5],
                  [15.0, -16.0, 1e5]])
    rows = s7.v12_checks("c", contact_world_N=c, ref=ref, slip_in_plane_m=np.zeros((4, 3)),
                         w_total_N=380113.0, key="k")
    assert all(r.passed for r in rows)
    c[2, 0] = 3000 * 1.11
    rows = s7.v12_checks("c", contact_world_N=c, ref=ref, slip_in_plane_m=np.zeros((4, 3)),
                         w_total_N=380113.0, key="k")
    assert not rows[1].passed


def test_v4_checks(block) -> None:
    ref = block["V4_NSC"]["L2b_dynamic"]["touch_s (FL, FR, RL, RR)"]
    ok = s7.v4_checks([r + 0.04 for r in ref], ref, residual_amp_deg=[5e-4, 5e-4], key="k")
    assert all(c.passed for c in ok)
    bad = s7.v4_checks([ref[0] + 0.06, ref[1], ref[2], None], ref,
                       residual_amp_deg=[5e-4, 2e-3], key="k")
    assert [c.passed for c in bad] == [False, False]


def test_summarize_ids_ignores_info() -> None:
    rows = [{"id": "V1", "passed": True}, {"id": "info", "passed": False},
            {"id": "V1", "passed": False}, {"id": "V2", "passed": True}]
    assert s7.summarize_ids(rows) == {"V1": False, "V2": True}


def test_module_constants_match_the_plan() -> None:
    assert s7.V11B_SREF_TRAVEL_M == pytest.approx(4e-5)
    assert s7.V4_TOUCH_TOL_S == 0.05
    assert s7.V7_ZETA_REL == 0.30 and s7.V7_F_REL == 0.03
    assert math.isclose(s7.V13_W4, 1e-3)


def test_v11b_creep_bound_is_the_moving_damper_share(block) -> None:
    lp = block["leg_parameters"]
    c = lp["c_oil_moving_N_s_m (zeta 0.10 on k2(e_op), concrete in series)"]
    k2 = lp["k_of_s_table"]["e_op"]["k2_axial_head_only_N_m (moving)"]
    v = 0.0209243016
    # c v / k2 = 0.0809 / 0.0933 mm (5.20.9 Q2), + v dt + 0.01 mm
    assert s7.v11b_creep_bound_m(c[0], k2[0], v, 1e-4) == pytest.approx(0.0809e-3 + 2.09e-6 + 1e-5,
                                                                          rel=2e-3)
    assert s7.v11b_creep_bound_m(c[2], k2[2], v, 1e-4) == pytest.approx(0.0933e-3 + 2.09e-6 + 1e-5,
                                                                          rel=2e-3)


def test_slope_rounding_bound_scales_with_the_lever() -> None:
    xy = np.array([[4.0, 1.0], [4.0, -1.0], [-1.0, 1.0], [-1.0, -1.0]])
    b = s7.slope_rounding_bound_m([2.4621, 2.4621], xy)
    h = np.radians(5e-5)
    np.testing.assert_allclose(b, h * 2.5 + h * 1.0)
