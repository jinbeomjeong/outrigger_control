"""verify/s4 (S4 branch A): excitations, judged-run assignment, check helpers."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.scenarios.impulse import modal_reference
from outrigger_sim.verify.reference import ReferenceFile, RefKey, ValueKind, load_references
from outrigger_sim.verify.s4 import (
    EXCITATIONS,
    ROD_SIDE_KV_RATIO,
    ModeRow,
    assign_modes,
    assign_modes_with_runner_up,
    beta_frequency_checks,
    beta_mac_checks,
    beta_static_checks,
    beta_v5_checks,
    beta_v6_checks,
    damping_mode_checks,
    damping_scale,
    first_order_zeta,
    fit_window_s,
    judged_value,
    mode_info_checks,
    predicted_modal_amplitudes,
    v7_l1r_checks,
    v7_six_mode_checks,
    with_lock_reference,
    zeta_num_share,
)

ROD_SIDE_OVER_HEAD_STIFFNESS = RefKey(
    ReferenceFile.REFERENCE, ("hydraulic_circuit", "k_rod_side_over_k_oil_head"),
    ValueKind.NUMBER_ARRAY,
)
LEG_VERTICAL_STIFFNESS = RefKey(
    ReferenceFile.REFERENCE,
    ("chrono_test_references", "L1_rigid_motor_lumped_contact", "k_vertical_N_m"),
    ValueKind.NUMBER_ARRAY,
)
HEAD_OIL_STIFFNESS = RefKey(
    ReferenceFile.REFERENCE, ("stiffness", "k_oil_N_m"), ValueKind.NUMBER_ARRAY
)
KV_RATIO_PRINT_REL_TOL = 2e-3
"""``kv_with_rod_side_over_kv`` is printed with 3-4 significant digits (dynamics 5.13.8)."""


@pytest.fixture(scope="module")
def modal():
    return modal_reference(load_references(), "top")


def test_excitation_velocities() -> None:
    v, w = EXCITATIONS["roll"].velocity(1.8)
    assert np.allclose(v, 0.0)
    assert w == pytest.approx([math.radians(0.02) * 2 * math.pi * 1.8, 0.0, 0.0])
    v, w = EXCITATIONS["heave"].velocity(7.6)
    assert v == pytest.approx([0.0, 0.0, 0.5e-3 * 2 * math.pi * 7.6])
    assert np.allclose(w, 0.0)
    assert set(EXCITATIONS) == {"roll", "pitch", "yaw", "surge", "heave", "sway"}
    assert [e.window_s for e in EXCITATIONS.values()].count(20.0) == 2


def test_assignment_follows_largest_predicted_amplitude(modal) -> None:
    got = assign_modes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
    # REXOME35 (dynamics_model.md 5.13.8 (1)): the rear k_t fell 56 %, so the tangential modes
    # couple with roll. Mode 3 (4.03 Hz) is no longer pure yaw-sway and roll excites it most
    # (roll 0.0680 vs yaw 0.0611); modes 5 and 6 swapped order. REXOME33 gave
    # ["roll", "pitch", "yaw", "pitch", "heave", "yaw"].
    assert got == ["roll", "pitch", "roll", "pitch", "roll", "heave"]
    amps = predicted_modal_amplitudes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
    # mode 1 is excited more by sway, but sway has a 2 s window (modes 1-2 need 20 s)
    assert amps["sway"][0] < amps["roll"][0]
    assert fit_window_s(0, 20.0) == 20.0 and fit_window_s(3, 20.0) == 2.0


def test_close_runner_up_is_recorded_for_mode_three(modal) -> None:
    """5.13.8 (1): mode 3 (roll 0.0680, yaw 0.0611, ratio 0.90) records yaw as the runner-up;
    modes whose runner-up is below 80 % record nothing."""
    details = assign_modes_with_runner_up(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
    assert [a.run for a in details] == assign_modes(modal.phi, modal.mass_matrix,
                                                    modal.f_damped_Hz)
    mode_three = details[2]
    assert (mode_three.run, mode_three.runner_up) == ("roll", "yaw")
    assert mode_three.runner_up_ratio == pytest.approx(0.0611 / 0.0680, abs=2e-3)
    assert mode_three.close_runner_up() == ("yaw", mode_three.runner_up_ratio)
    assert [i for i, a in enumerate(details) if a.is_close] == [2]
    assert details[0].close_runner_up() == (None, None)
    # the judged row carries it as information only: the checks do not read it
    row = _row(runner_up="yaw", runner_up_amplitude_ratio=mode_three.runner_up_ratio)
    assert judged_value(row) == judged_value(_row())


def _row(**kw):
    base = dict(mode=3, run="yaw", f_proj_Hz=5.82, zeta_proj=0.0372, fit_residual_rms_rel=0.002,
                f_era_Hz=5.8195, zeta_era=0.0371, leakage=0.002, zeta_num=0.0036,
                f_ref_Hz=5.8191, zeta_ref=0.0372)
    base.update(kw)
    return ModeRow(**base)


def test_v7_six_mode_checks_pass_and_fail() -> None:
    ok = v7_six_mode_checks([_row()], ref_key_f="f", ref_key_zeta="z")
    assert all(c.passed for c in ok) and len(ok) == 2
    bad = v7_six_mode_checks([_row(f_proj_Hz=6.1, zeta_era=None)], ref_key_f="f",
                             ref_key_zeta="z")
    assert [c.passed for c in bad] == [False, True]  # no ERA -> projection is judged
    info = mode_info_checks([_row(f_proj_Hz=6.1, zeta_era=None)])
    assert sum(not c.passed for c in info) == 2 and all(c.id == "info" for c in info)


def test_judged_value_switches_to_era() -> None:
    assert judged_value(_row()).source == "projection"
    j = judged_value(_row(fit_residual_rms_rel=0.055, f_proj_Hz=6.39, zeta_proj=0.1244))
    assert (j.source, j.f_Hz) == ("ERA", 5.8195)
    j = judged_value(_row(zeta_proj=0.030))  # ERA zeta 0.0371 differs by > 10 %
    assert j.source == "ERA" and j.zeta == 0.0371
    assert judged_value(_row(f_proj_Hz=None, zeta_proj=None)).source == "ERA"


def test_damping_mode_checks_reference_scaled() -> None:
    r = _row(zeta_proj=0.124, zeta_era=0.1240, zeta_ref=float(first_order_zeta([0.0372],
                                                                             10 / 3)[0]))
    c = damping_mode_checks([r], 0.10, ref_key_f="f")
    assert all(x.passed for x in c) and c[0].id == "damping"
    c = damping_mode_checks([_row(zeta_proj=0.2, zeta_era=0.2, zeta_ref=0.124)], 0.10,
                            ref_key_f="f")
    assert [x.passed for x in c] == [True, False]


def test_beta_mac_checks_with_crossing() -> None:
    exp_idx, exp_mac = [0, 1, 2, 3, 5, 4], [0.998, 0.985, 0.999, 0.964, 0.992, 0.971]
    by_label = [0.998, 0.985, 0.999, 0.964, 0.971, 0.992]
    c = beta_mac_checks("b", mac_by_label=by_label, label_of_sorted=[1, 2, 3, 4, 6, 5],
                        expected_index=exp_idx, expected_mac=exp_mac, key="k")
    assert all(x.passed for x in c) and len(c) == 12
    c = beta_mac_checks("b", mac_by_label=by_label, label_of_sorted=[1, 2, 3, 4, 5, 6],
                        expected_index=exp_idx, expected_mac=exp_mac, key="k")
    assert not all(x.passed for x in c)


def test_beta_checks() -> None:
    keys = {"penetration": "p", "pitch": "q", "f_min": "a", "liftoff": "b"}
    c = beta_static_checks("b", penetration_mm=[5.73, 5.64, 3.47, 3.38], pitch_deg=0.0267,
                           ref_penetration_mm=[5.73147, 5.63661, 3.4713, 3.38492],
                           ref_pitch_deg=0.02664, keys=keys)
    assert all(x.passed for x in c)
    v5 = beta_v5_checks("b", dF_N=[4708, -4733, -5273, 5299],
                        ref_dF_per_mm_N=[4770.6, -4770.6, -5239.19, 5239.19], key="k")
    assert v5[0].passed and v5[0].tol == pytest.approx(0.05 * 5239.19)
    v6 = beta_v6_checks("b", f_min_mm=None, liftoff_mm=13.98, ref_f_min_mm=12.07,
                        ref_liftoff_mm=14.08, keys=keys)
    assert [x.passed for x in v6] == [False, True]
    f = beta_frequency_checks("b", [1.8, None], [1.798, 3.005], "k")
    assert [x.passed for x in f] == [True, False]


def test_damping_helpers_and_rod_side_key() -> None:
    assert damping_scale(0.01) == pytest.approx(1 / 3)
    assert damping_scale(0.10) == pytest.approx(10 / 3)
    assert first_order_zeta([0.03, 0.06], 0.5) == pytest.approx([0.015, 0.03])
    assert zeta_num_share([0.001, 0.0], [0.01, 0.0]) == [pytest.approx(0.1), math.inf]
    references = load_references()
    ratio = np.asarray(references.get(ROD_SIDE_KV_RATIO), dtype=float)
    leg_stiffness = np.asarray(references.get(LEG_VERTICAL_STIFFNESS), dtype=float)
    oil_stiffness = np.asarray(references.get(HEAD_OIL_STIFFNESS), dtype=float)
    rod_over_head = np.asarray(references.get(ROD_SIDE_OVER_HEAD_STIFFNESS), dtype=float)
    assert ratio.shape == leg_stiffness.shape == oil_stiffness.shape == rod_over_head.shape == (4,)
    # dynamics_model.md 5.13.8 (2): 1/k_v = 1/k_oil + S (S = rod, frame, contact compliance),
    # and the rod-side column adds rho k_oil in parallel to k_oil, so exactly
    #     k_v' / k_v = 1 / (1 - (k_v / k_oil) rho / (1 + rho)).
    # Front 1.3097, rear 1.3536 against the stored 1.31 / 1.354 (REXOME35; REXOME33 gave
    # about 1.10). Tolerance = the printed digits of the reference.
    expected = 1.0 / (1.0 - (leg_stiffness / oil_stiffness) * rod_over_head / (1.0 + rod_over_head))
    np.testing.assert_allclose(ratio, expected, rtol=KV_RATIO_PRINT_REL_TOL)
    # Physical bounds only (a missing series compliance, r = 1 + rho, would still pass them).
    assert np.all((ratio > 1.0) & (ratio < 1.0 + rod_over_head))


def test_lock_reference_keeps_the_identification_and_shifts_zeta_num() -> None:
    """dynamics 5.17.5: f / zeta references and the subtracted zeta_num become the LOCK ones."""
    row = _row(mode=1, run="roll", f_proj_Hz=2.0741, zeta_proj=0.0087, f_era_Hz=2.0745,
               zeta_era=0.0088, zeta_num=0.0002, f_ref_Hz=1.8454, zeta_ref=0.00902)
    (lock,) = with_lock_reference([row], [2.0748] + [0.0] * 5, [0.008574] + [0.0] * 5,
                                  [0.000264] + [0.0] * 5)
    assert (lock.f_proj_Hz, lock.f_era_Hz) == (row.f_proj_Hz, row.f_era_Hz)
    assert (lock.f_ref_Hz, lock.zeta_ref, lock.zeta_num) == (2.0748, 0.008574, 0.000264)
    assert lock.zeta_proj == pytest.approx(0.0087 + 0.0002 - 0.000264)
    assert lock.zeta_era == pytest.approx(0.0088 + 0.0002 - 0.000264)


def test_v7_l1r_judges_frequency_and_records_zeta() -> None:
    row = _row(mode=6, run="heave", f_proj_Hz=8.6669, zeta_proj=0.062, f_era_Hz=8.6669,
               zeta_era=0.062, zeta_num=0.0, f_ref_Hz=8.917, zeta_ref=0.0304)
    checks = v7_l1r_checks([row], ref_key_f="f", ref_key_zeta="z")
    by_id = {c.id: c for c in checks}
    assert by_id["V7"].passed is True and "natural frequency" in by_id["V7"].item
    assert by_id["info"].passed is False and "V7a" in by_id["info"].note
