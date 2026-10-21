"""S4 V8(b) energy-budget formulas and checks (engine independent).

``chrono/energy`` helper functions (return-mapping slip energy, explicit contact damping work,
rigid kinetic energy) and ``verify/s4_energy`` (residual, reference energy, checks, dt record).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.chrono.energy import (
    contact_damping_work_J,
    return_mapping_slip_energy,
    rigid_kinetic_energy_J,
)
from outrigger_sim.signals import ENERGY_TERMS
from outrigger_sim.verify.s4_energy import (
    BUDGET_TERMS,
    DIAGNOSTIC_TERMS,
    budget_summary,
    dissipation_end_J,
    dt_ratio_record,
    reference_energy_J,
    reference_energy_old_J,
    residual_series,
    slip_ratio,
    v8b_checks,
    v8b_pair_checks,
)

K = 8.5e6  # N/m, order of the YAML bushing stiffness
LIMIT = 4.7e4  # N, mu N of a pad


@pytest.mark.parametrize("excess_m", [1.0e-7, 1.0e-5, 1.0e-4, 2.0e-3])
def test_return_mapping_slip_energy_identities(excess_m: float) -> None:
    d_yield = LIMIT / K
    d_trial = d_yield + excess_m
    dissipation, coulomb = return_mapping_slip_energy(d_trial, LIMIT, K)
    # anchor moves by the excess, the spring keeps mu N / k
    assert coulomb == pytest.approx(LIMIT * excess_m, rel=1e-9)
    assert dissipation == pytest.approx(0.5 * K * (d_trial**2 - d_yield**2), rel=1e-9)
    assert dissipation == pytest.approx(LIMIT * excess_m + 0.5 * K * excess_m**2, rel=1e-9)
    assert dissipation / coulomb == pytest.approx(1.0 + K * excess_m / (2.0 * LIMIT), rel=1e-9)


def test_return_mapping_slip_energy_elastic_and_lifted() -> None:
    assert return_mapping_slip_energy(0.9 * LIMIT / K, LIMIT, K) == (0.0, 0.0)
    assert return_mapping_slip_energy(LIMIT / K, LIMIT, K) == (0.0, 0.0)  # on the circle
    # lifted pad (mu N = 0): the whole spring energy is released, no Coulomb work
    d = 3.0e-3
    dissipation, coulomb = return_mapping_slip_energy(d, 0.0, K)
    assert dissipation == pytest.approx(0.5 * K * d * d, rel=1e-12)
    assert coulomb == 0.0


def test_return_mapping_matches_ground_bushing_arithmetic() -> None:
    """Same expression as ``GroundBushingCoulomb._return_mapping`` (s = 1 - limit / (k dn))."""
    rng = np.random.default_rng(3)
    for _ in range(200):
        dn = float(rng.uniform(1e-4, 1e-2))
        limit = float(rng.uniform(0.0, 0.9 * K * dn))
        s = 1.0 - limit / (K * dn)
        expect = (0.5 * K * dn * dn * s * (2.0 - s), limit * dn * s)
        assert return_mapping_slip_energy(dn, limit, K) == expect


def test_contact_damping_work() -> None:
    kn, cn = 2.08e7, 2.7e4
    # no overlap at the step start: no force, no work
    assert contact_damping_work_J(kn, cn, 0.0, 0.1, 1e-5) == 0.0
    assert contact_damping_work_J(kn, cn, -1e-6, 0.1, 1e-5) == 0.0
    # pressing in: damping force c delta_dot over the step
    w = contact_damping_work_J(kn, cn, 4.5e-3, 0.02, 4.5e-3 + 0.02 * 2e-4)
    assert w == pytest.approx(cn * 0.02 * 0.02 * 2e-4, rel=1e-12)
    assert w > 0.0
    # separating fast: Chrono clips the total force at 0 -> damping part = -k delta
    d0, ddot0 = 1.0e-4, -0.2  # k d0 = 2080 N < c |ddot| = 5400 N
    d1 = d0 + ddot0 * 2e-4
    w = contact_damping_work_J(kn, cn, d0, ddot0, d1)
    assert w == pytest.approx(-kn * d0 * (d1 - d0), rel=1e-12)


def test_rigid_kinetic_energy() -> None:
    inertia = np.diag([2.0, 3.0, 4.0])
    assert rigid_kinetic_energy_J(10.0, (1.0, 2.0, 2.0), inertia, (0.0, 0.0, 0.0)) == 45.0
    assert rigid_kinetic_energy_J(10.0, (0.0, 0.0, 0.0), inertia, (1.0, 1.0, 1.0)) == 4.5
    full = np.array([[2.0, 0.5, 0.0], [0.5, 3.0, 0.0], [0.0, 0.0, 4.0]])
    w = np.array([1.0, -1.0, 0.5])
    assert rigid_kinetic_energy_J(1.0, (0, 0, 0), full, w) == pytest.approx(0.5 * w @ full @ w)


def _columns(n: int = 50) -> dict[str, np.ndarray]:
    """A closed synthetic budget: kinetic energy goes into viscous, slip and gravity terms."""
    t = np.linspace(0.0, 1.0, n)
    kin = 1000.0 * np.exp(-3.0 * t)
    lost = 1000.0 - kin
    return {
        "kinetic": kin,
        "gravity": 5.0e5 - 0.1 * lost,
        "contact_spring": np.full(n, 900.0) + 0.05 * lost,
        "bushing_spring": 0.05 * lost,
        "dissipated_viscous": 0.4 * lost,
        "dissipated_slip": 0.6 * lost,
        "motor_work": np.zeros(n),
        "t": t,
    }


def test_budget_terms_are_the_record_terms() -> None:
    assert BUDGET_TERMS == ENERGY_TERMS

def test_residual_closed_budget_and_reference() -> None:
    c = _columns()
    r = residual_series(c)
    assert np.max(np.abs(r)) < 1e-9
    lost_end = 1000.0 * (1.0 - math.exp(-3.0))
    assert dissipation_end_J(c) == pytest.approx(lost_end)
    # E_ref = max(E_kin0, D_visc + D_slip)
    assert reference_energy_J(c) == pytest.approx(1000.0)
    c2 = dict(c)
    c2["dissipated_slip"] = c["dissipated_slip"] * 2.0
    assert reference_energy_J(c2) == pytest.approx(0.4 * lost_end + 1.2 * lost_end)
    # motor work is excluded from E_ref (it was in the former definition)
    c["motor_work"] = np.linspace(0.0, 250.0, len(c["t"]))
    c["gravity"] = c["gravity"] + c["motor_work"]  # the motor lifts the machine
    assert np.max(np.abs(residual_series(c))) < 1e-9
    assert reference_energy_J(c) == pytest.approx(1000.0)
    assert reference_energy_old_J(c) == pytest.approx(1250.0)
    # 10 J of unaccounted loss at the end, 0.5 J created early on
    c["kinetic"] = c["kinetic"] - np.linspace(0.0, 10.0, len(c["t"]))
    c["kinetic"][1] += 0.5 + 10.0 / 49.0
    s = budget_summary(c["t"], c)
    assert s["residual_end_J"] == pytest.approx(-10.0)
    assert s["residual_max_signed_J"] == pytest.approx(0.5)
    assert s["residual_creation_rel"] == pytest.approx(0.5 / 1000.0)
    assert s["old_residual_max_rel"] == pytest.approx(10.0 / 1250.0)
    assert s["residual_end_over_dissipation"] == pytest.approx(-10.0 / lost_end)
    assert s["remainder_end_J"] == pytest.approx(-10.0)  # no diagnostic shares given
    assert not s["diagnostics_complete"]
    for k in DIAGNOSTIC_TERMS:
        c[k] = np.linspace(0.0, -2.0, len(c["t"]))
    s = budget_summary(c["t"], c)
    assert s["diagnostics_complete"]
    assert s["remainder_end_J"] == pytest.approx(-10.0 + 2.0 * len(DIAGNOSTIC_TERMS))


def _checks(**kw):
    base = dict(residual_max_signed_J=0.5, residual_end_J=-100.0, dissipation_end_J=4800.0,
                e_ref_J=4870.0, slip_dissipation_J=1010.0, coulomb_work_J=1000.0,
                yield_steps=[1, 0, 0, 0], crawler_contact_max_N=0.0)
    base.update(kw)
    return {c.id + ("" if c.id != "V8(b)" else c.item[-20:]): c.passed
            for c in v8b_checks("c", **base)}


def test_v8b_checks_and_slip_ratio() -> None:
    assert all(_checks().values())
    # (1) energy creation above 1e-3 E_ref
    assert not _checks(residual_max_signed_J=5.0)["V8(b)-1"]
    assert _checks(residual_max_signed_J=4.8)["V8(b)-1"]
    # (4) the end residual must be a loss within 10 % of the dissipation
    assert not _checks(residual_end_J=+1.0)["V8(b)-4"]
    assert not _checks(residual_end_J=-481.0)["V8(b)-4"]
    assert _checks(residual_end_J=-479.0)["V8(b)-4"]
    # (5) slip ratio band
    assert not _checks(slip_dissipation_J=990.0)["V8(b)-5"]
    assert not _checks(slip_dissipation_J=1060.0)["V8(b)-5"]
    assert math.isnan(slip_ratio(0.0, 0.0))
    assert not _checks(slip_dissipation_J=0.0, coulomb_work_J=0.0)["V8(b)-5"]
    bad = _checks(yield_steps=[0, 0, 0, 0], crawler_contact_max_N=5.0)
    assert sum(not v for v in bad.values()) == 2


def test_v8b_pair_checks() -> None:
    ok = v8b_pair_checks("c", dt_s=1e-4, residual_end_dt_J=-56.3, residual_end_2dt_J=-111.6,
                         e_ref_J=4870.0)
    assert [c.passed for c in ok] == [True, True]
    assert ok[0].value == pytest.approx(111.6 / 56.3)
    assert ok[1].value == pytest.approx(abs(2 * -56.3 + 111.6) / 4870.0)
    # not first order (ratio 1.1) and a large dt -> 0 value
    bad = v8b_pair_checks("c", dt_s=1e-4, residual_end_dt_J=-100.0, residual_end_2dt_J=-110.0,
                          e_ref_J=4870.0)
    assert [c.passed for c in bad] == [False, False]


def test_dt_ratio_record() -> None:
    rec = dt_ratio_record({5e-5: -25.0, 1e-4: -50.0, 2e-4: -100.0})
    assert [p["dt_s"] for p in rec["pairs"]] == [5e-5, 1e-4]
    assert all(p["ratio_2dt_over_dt"] == pytest.approx(2.0) for p in rec["pairs"])
    assert all(p["richardson_dt0"] == pytest.approx(0.0) for p in rec["pairs"])
    assert dt_ratio_record({1e-4: 1.0, 3e-4: 2.0})["pairs"] == []
