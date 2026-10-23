"""verify/s5 (S5 auger three levels): V10 load, mode and order checks; level references."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.params import load_params
from outrigger_sim.scenarios.impulse import modal_reference
from outrigger_sim.verify.reference import (
    L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
    L1_BALL_CENTRE_REV13_F_UNDAMPED_HZ,
    L1_CONTACT_FORCE_N,
    TOTAL_WEIGHT_INCL_RODS_N,
    load_references,
)
from outrigger_sim.verify.s4 import ModeRow, assign_modes
from outrigger_sim.verify.s5 import (
    LEVELS,
    V10_EXCITATIONS,
    pdelta_contact_forces_N,
    summarize_check_ids,
    v10_health_checks,
    v10_load_checks,
    v10_mode_checks,
    v10_order_checks,
)

ROOT = Path(__file__).resolve().parents[2]
PDELTA_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s1_pdelta_check.json"
"""dynamics-expert P-delta nonlinear statics per level (V10 V1 judged reference, rev. 22)."""
# Planned damped frequencies (Hz) of modes 1 and 2 per level, REXOME35 YAML
# (sha 84a46dc1...), dynamics_model.md rev. 31 section 5.13. Kept as literals on
# purpose: reading them from reference.json would compare the reference with itself.
PLAN_F1 = {"top": 1.8454, "middle": 2.3462, "bottom": 2.8203}
PLAN_F2 = {"top": 2.8530, "middle": 3.2004, "bottom": 3.4465}
# 0.01 % of W/4 with W = 380,112.9 N (s1_pdelta_check.json W_N, rev. 31 5.13)
PDELTA_TOL_N = 9.5028


@pytest.fixture(scope="module")
def refs():
    return load_references()


def test_levels_match_yaml_order() -> None:
    assert tuple(load_params().get("superstructure.auger_level_order")) == LEVELS


@pytest.mark.parametrize("level", LEVELS)
def test_level_references_exist_and_match_plan(refs, level) -> None:
    c = np.asarray(refs.get(L1_CONTACT_FORCE_N, level=level))
    assert c.shape == (4,)
    fd = np.asarray(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=level))
    fu = np.asarray(refs.get(L1_BALL_CENTRE_REV13_F_UNDAMPED_HZ, level=level))
    assert fd[0] == pytest.approx(PLAN_F1[level], abs=6e-4)
    assert fd[1] == pytest.approx(PLAN_F2[level], abs=6e-4)
    assert np.all(np.abs(fu[:2] / fd[:2] - 1.0) < 1e-3)
    modal = modal_reference(refs, level)  # mode shapes exist for every level
    assert modal.phi.shape == (6, 6)
    # modes 1 and 2 are judged in the 20 s roll / pitch runs at every level
    got = assign_modes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)[:2]
    assert set(got) <= set(V10_EXCITATIONS)


def test_reference_order_rises(refs) -> None:
    f = {lv: list(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=lv)[:2]) for lv in LEVELS}
    assert all(c.passed for c in v10_order_checks(f))


@pytest.fixture(scope="module")
def pdelta_check():
    return json.loads(PDELTA_CHECK.read_text(encoding="utf-8"))


@pytest.mark.parametrize("level", LEVELS)
def test_pdelta_solution_exists_per_level(refs, pdelta_check, level) -> None:
    forces = pdelta_contact_forces_N(pdelta_check, level)
    # equilibrium with its own W; the reference W is printed to 6 significant digits
    assert forces.sum() == pytest.approx(pdelta_check[level]["W_N"], rel=1e-12)
    assert forces.sum() == pytest.approx(float(refs.get(TOTAL_WEIGHT_INCL_RODS_N)), rel=1e-5)
    # the P-delta share of the linear reference is tens of newtons
    linear = np.asarray(refs.get(L1_CONTACT_FORCE_N, level=level))
    assert np.all(np.abs(forces - linear) < 100.0)


def test_pdelta_solution_missing_level_raises() -> None:
    with pytest.raises(KeyError, match="nonlinear_contact_N"):
        pdelta_contact_forces_N({"top": {}}, "top")


def _load_rows(pdelta, linear, offset_N, weight_N):
    return v10_load_checks("top", contact_mean_N=pdelta + np.asarray(offset_N),
                           pdelta_contact_N=pdelta, ref_contact_N=linear,
                           total_weight_N=weight_N, pdelta_key="p", ref_key="k", weight_key="w")


def test_load_checks_judge_pdelta_record_linear(refs, pdelta_check) -> None:
    """U2 = B: Chrono - P-delta judged at 0.01 % W/4, Chrono - linear recorded at 1 % W/4."""
    pdelta = pdelta_contact_forces_N(pdelta_check, "top")
    linear = np.asarray(refs.get(L1_CONTACT_FORCE_N, level="top"))
    weight_N = float(pdelta.sum())
    pdelta_tol_N = 1e-4 * weight_N / 4
    assert pdelta_tol_N == pytest.approx(PDELTA_TOL_N, abs=1e-3)
    ok = _load_rows(pdelta, linear, [0.9 * pdelta_tol_N, 0, -0.9 * pdelta_tol_N, 0], weight_N)
    assert [c.id for c in ok] == ["V10", "info", "V10"]
    assert all(c.passed for c in ok)
    assert ok[1].tol == pytest.approx(1e-2 * weight_N / 4)
    bad = _load_rows(pdelta, linear, [1.1 * pdelta_tol_N, 0, 0, -1.1 * pdelta_tol_N], weight_N)
    assert [c.passed for c in bad] == [False, True, True]
    # the linear row is information only: it does not enter the verdict
    linear_tol_N = 1e-2 * weight_N / 4
    far_from_linear = linear + [1.1 * linear_tol_N, 0, 0, -1.1 * linear_tol_N]
    far = _load_rows(far_from_linear, linear, np.zeros(4), weight_N)
    assert [c.passed for c in far] == [True, False, True]
    assert summarize_check_ids([c.as_dict() for c in far]) == {"V10": True}


def _row(**kw):
    base = dict(mode=1, run="roll", f_proj_Hz=1.7982, zeta_proj=0.00783,
                fit_residual_rms_rel=0.002, f_era_Hz=1.7983, zeta_era=0.00785, leakage=0.001,
                zeta_num=6e-5, f_ref_Hz=1.7983, zeta_ref=0.00783)
    base.update(kw)
    return ModeRow(**base)


def test_mode_checks_frequency_judged_zeta_info() -> None:
    c = v10_mode_checks("top", [_row()], ref_key_f="f", ref_key_zeta="z")
    assert [x.id for x in c] == ["V10", "info"] and all(x.passed for x in c)
    c = v10_mode_checks("top", [_row(f_proj_Hz=1.86, f_era_Hz=1.86, zeta_era=0.02,
                                     zeta_proj=0.02)], ref_key_f="f", ref_key_zeta="z")
    assert [x.passed for x in c] == [False, False]
    # info rows do not enter the verdict
    by_id = summarize_check_ids([x.as_dict() for x in v10_mode_checks(
        "top", [_row(zeta_proj=0.02, zeta_era=0.02)], ref_key_f="f", ref_key_zeta="z")])
    assert by_id == {"V10": True}


def test_order_checks_detect_swap() -> None:
    f = {"top": [1.8, 3.0], "middle": [2.3, 3.5], "bottom": [2.2, 3.9]}
    c = v10_order_checks(f)
    assert [x.passed for x in c] == [False, True]


def test_health_checks() -> None:
    assert all(c.passed for c in v10_health_checks("top", [[0, 0, 0, 0], [0, 0, 0, 0]], 0))
    assert not all(c.passed for c in v10_health_checks("top", [[0, 3, 0, 0]], 0))
