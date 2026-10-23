"""S3 check helpers (``verify/s3``) and the multi-component damped fit (``verify/metrics``)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.verify.metrics import fit_damped_sum
from outrigger_sim.verify.s3 import (
    l1r_module_normal_change,
    order_ratio,
    touch_geometric_checks,
    v4_judged_run_comparison,
    v5_l1r_checks,
    v8a_checks,
    v8a_crawler_checks,
    v8a_crawler_modal_checks,
    v9_checks,
    v9_v4_checks,
    v9_v4_r15_touch_record,
)


def test_v4_judged_run_comparison_is_judged_minus_previous() -> None:
    previous = {
        "dt_s": 1e-4,
        "touch_eq_s": [15.0, 15.0, 15.2, 15.2],
        "crawler_off_eq_s": 15.57,
        "peak_cylinder_force_N": [1.0e5, 1.0e5, 9.0e4, 9.0e4],
        "final": {"contact_force_N": [1.2e5, 1.2e5, 7.0e4, 7.0e4], "attitude_deg": [0.0, 0.03]},
    }
    judged = {
        "dt_s": 2e-4,
        "touch_eq_s": [15.001, 15.0, 15.2, 15.2],
        "crawler_off_eq_s": 15.569,
        "peak_cylinder_force_N": [1.0e5 + 3.0, 1.0e5, 9.0e4, 9.0e4],
        "final": {
            "contact_force_N": [1.2e5, 1.2e5, 7.0e4 - 2.0, 7.0e4],
            "attitude_deg": [0.0, 0.031],
        },
    }
    comparison = v4_judged_run_comparison(judged, previous)
    assert comparison["dt_s"] == {"judged": 2e-4, "previous": 1e-4}
    assert comparison["touch_eq_minus_previous_ms"] == pytest.approx([1.0, 0, 0, 0], abs=1e-9)
    assert comparison["crawler_off_eq_minus_previous_ms"] == pytest.approx(-1.0, abs=1e-9)
    assert comparison["peak_cylinder_force_minus_previous_N"] == pytest.approx([3.0, 0, 0, 0])
    assert comparison["final_contact_force_minus_previous_N"] == pytest.approx([0, 0, -2.0, 0])
    assert comparison["final_attitude_minus_previous_deg"] == pytest.approx([0.0, 0.001])


def test_order_ratio_first_order() -> None:
    vals = {2e-4: 1.0 + 2e-4 * 7.0, 1e-4: 1.0 + 1e-4 * 7.0, 5e-5: 1.0 + 5e-5 * 7.0}
    res = order_ratio(vals)
    assert res["ratio"] == pytest.approx(2.0, rel=1e-9)
    checks = v9_checks("x", dts_s=[2e-4, 1e-4, 5e-5, 1e-5], static_force_N=None,
                       total_weight_N=4.0, final_attitude_deg=None, transient_peak_N=None,
                       ref_dt_s=1e-5, order={"lin": res})
    assert all(c.passed for c in checks)
    bad = order_ratio({2e-4: 1.0, 1e-4: 0.9, 5e-5: 0.89})
    assert not v9_checks("x", dts_s=[1e-5], static_force_N=None, total_weight_N=4.0,
                         final_attitude_deg=None, transient_peak_N=None, ref_dt_s=1e-5,
                         order={"b": bad})[0].passed


def test_v8a_energy_rise_and_mode_limits() -> None:
    zref = [0.00783, 0.014, 0.0372, 0.0362, 0.0323, 0.0491]
    ok = v8a_checks("p", dt_s=1e-4, energy_rise_rel=-0.5, zeta_num_fit=[6e-5, 2.4e-4, 1.8e-3,
                    1.35e-3, 2e-4, 2.25e-3], zeta_ref=zref, zeta_pred=None, key_zeta="k",
                    yield_steps=[0, 0, 0, 0], n_events=0)
    assert all(c.passed for c in ok)
    over = v8a_checks("p", dt_s=1e-4, energy_rise_rel=0.02, zeta_num_fit=[0.0] * 5 + [6e-3],
                      zeta_ref=zref, zeta_pred=None, key_zeta="k", yield_steps=[0, 0, 0, 0],
                      n_events=0)
    failed = [c.item for c in over if not c.passed]
    assert any("energy rise" in f for f in failed) and any("mode 6" in f for f in failed)


def test_crawler_modal_and_touch_checks() -> None:
    modes = [{"mode": "pitch", "zeta_fit": -1e-7}, {"mode": "heave", "zeta_fit": -1e-3}]
    res = v8a_crawler_modal_checks("c", modes, {"pitch": 0.0084, "heave": 0.054})
    assert [c.passed for c in res] == [True, False]
    touch = {1e-5: [15.0, 15.0, 15.1, 15.1], 2e-4: [15.00003, 15.0, 15.1, 15.10009]}
    assert all(c.passed for c in touch_geometric_checks(touch, 1e-5))
    touch[2e-4] = [15.0002, 15.0, 15.1, 15.1]
    assert not touch_geometric_checks(touch, 1e-5)[0].passed


def test_crawler_v8a_judges_modal_zeta_and_trend_not_max_rise() -> None:
    """dynamics_model.md 5.7 (a): max(E - E0) is recorded, modal zeta and the trend judged."""
    modes = [{"mode": "pitch", "zeta_fit": -1.8e-5}, {"mode": "roll", "zeta_fit": -8.3e-6},
             {"mode": "heave", "zeta_fit": -5.0e-5}]
    phys = {"pitch": 0.00843, "roll": 0.0191, "heave": 0.0542}
    checks, rec = v8a_crawler_checks("c", dt_s=1e-4, energy_rise_rel=0.0117,
                                     energy_trend_rel_over_window=0.00351, window_s=60.0,
                                     modes=modes, zeta_physical=phys, n_events=0)
    assert all(c.passed for c in checks)
    assert not any("max(E - E0)" in c.item for c in checks)
    assert rec["energy_rise_rel_geometric (max(E - E0) / E_kin0, recorded)"] == 0.0117
    checks, _ = v8a_crawler_checks("c", dt_s=1e-4, energy_rise_rel=0.0, window_s=60.0,
                                   energy_trend_rel_over_window=0.02, modes=modes,
                                   zeta_physical=phys, n_events=0)
    assert [c.item for c in checks if not c.passed] == [
        "c: energy trend of 1-s block means over 60 s / E_kin0 (dt 0.0001 s)"]


def test_v9_v4_r15_touch_is_recorded_with_structural_bound() -> None:
    """dynamics_model.md 5.7 (b): R15 touch differences vs 2 dt - dt_ref + geometric diff."""
    ref = [15.0, 15.0, 15.1, 15.1]
    touch = {1e-5: ref, 2e-4: [15.00039, 15.0003, 15.1003, 15.1003],
             -1.0: [15.00001, 15.0, 15.1, 15.1]}
    rec = v9_v4_r15_touch_record(touch_eq_by_dt=touch, ref_dt_s=1e-5,
                                 dt_at_touch_by_key={2e-4: 2e-4, -1.0: 1e-5},
                                 geometric_diff_max_s=3.2e-5,
                                 label_by_dt={-1.0: "windowed"})
    assert rec["dt 0.0002 s"]["within_structural_bound"]
    assert rec["dt 0.0002 s"]["structural_bound_s (2 dt - dt_ref + geometric diff)"] == (
        pytest.approx(2 * 2e-4 - 1e-5 + 3.2e-5))
    assert rec["windowed"]["within_structural_bound"]
    checks = v9_v4_checks(touch_eq_by_dt=touch, ref_dt_s=1e-5,
                          peak_cyl_by_dt={k: [1.0] * 4 for k in touch},
                          final_force_by_dt={k: [1.0] * 4 for k in touch},
                          final_attitude_by_dt={k: [0.0, 0.0] for k in touch},
                          total_weight_N=4e5)
    assert all(c.passed for c in checks)
    assert not any("touch" in c.item for c in checks)


def test_fit_damped_sum_separates_close_modes() -> None:
    t = np.arange(0.0, 30.0, 2e-3)
    comps = [(6.42, 1.3e-3, 0.08), (7.61, 2.0e-4, 0.01), (8.00, 2.25e-3, 0.005)]
    y = np.zeros_like(t)
    for f, z, a in comps:
        w = 2 * math.pi * f
        y += a * np.exp(-z * w * t) * np.cos(w * math.sqrt(1 - z * z) * t + 0.3)
    fit = fit_damped_sum(t, y + 1e-6, [6.4218, 7.6068, 7.9995], [1e-3, 1e-3, 1e-3])
    main = fit.components[0]
    assert main.f_damped_Hz == pytest.approx(6.42, rel=1e-5)
    assert main.zeta == pytest.approx(1.3e-3, rel=1e-3)
    assert fit.components[2].zeta == pytest.approx(2.25e-3, rel=1e-2)


# --- L1-R V5 (dynamics_model.md 5.17.5) ---------------------------------------------------------

L1R_K1_OVER_K2 = [1.3097, 1.3097, 1.3536, 1.3536]
L1R_KNEE_N = [4089.04, 4089.04, 3170.13, 3170.13]


def test_l1r_module_normal_change_reproduces_the_dynamics_conversion() -> None:
    """Bundle-B S3 v5 +1 mm: FL moving as is, FR / RL x k1/k2, RR above the knee + 828 N."""
    contact = [5877.532, -4518.0797, -4862.1122, 5770.5149]
    module = l1r_module_normal_change(contact, moving_leg=0, k1_over_k2=L1R_K1_OVER_K2,
                                      knee_dF_N=L1R_KNEE_N)
    assert module == pytest.approx([5877.5, -5917.3, -6581.4, 6598.6], abs=0.2)
    assert module[3] - contact[3] == pytest.approx(3170.13 * (1 - 1 / 1.3536))


def test_l1r_module_normal_change_is_continuous_at_the_knee() -> None:
    at_knee = 3170.13 / 1.3536
    below = l1r_module_normal_change([0.0, 0.0, 0.0, at_knee - 1e-6], moving_leg=0,
                                     k1_over_k2=L1R_K1_OVER_K2, knee_dF_N=L1R_KNEE_N)
    above = l1r_module_normal_change([0.0, 0.0, 0.0, at_knee + 1e-6], moving_leg=0,
                                     k1_over_k2=L1R_K1_OVER_K2, knee_dF_N=L1R_KNEE_N)
    assert below[3] == pytest.approx(3170.13, abs=1e-3)
    assert above[3] == pytest.approx(3170.13, abs=1e-3)


def test_v5_l1r_checks_use_the_largest_replica_component() -> None:
    replica = [5887.79, -5912.97, -6582.94, 6608.13]
    ok = v5_l1r_checks(1.0, dN_N=[5877.5, -5917.3, -6581.4, 6598.6], dN_ref_N=replica,
                       key_dN="k", dattitude_deg=[0.012957, -0.005772],
                       dattitude_ref_deg=[0.012969, -0.0057762], key_att="a")
    assert [c.passed for c in ok] == [True, True, True]
    assert ok[0].tol == pytest.approx(0.05 * 6608.13)
    head_only = v5_l1r_checks(1.0, dN_N=[5877.5, -4518.1, -4862.1, 5770.5], dN_ref_N=replica,
                              key_dN="k", dattitude_deg=[0.012957, -0.005772],
                              dattitude_ref_deg=[0.012969, -0.0057762], key_att="a")
    assert head_only[0].passed is False
