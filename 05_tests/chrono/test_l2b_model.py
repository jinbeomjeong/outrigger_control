"""S7 four-leg L2b-NSC model (chrono/l2b_model, l2b_engine): static start, NSC pad force
readings (plan S7 risk 5), snapshot round trip, engine members."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.l2b_engine import L2bEngine  # noqa: E402
from outrigger_sim.chrono.l2b_model import (  # noqa: E402
    L2bModel,
    axial_stiffness_at_N_m,
    pad_force_crosscheck,
    static_cylinder_forces_N,
)
from outrigger_sim.chrono.model import operating_extensions_m  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono

# reference.json / L2b_NSC_reference_rev33 / levels / top (dynamics_model.md 5.20.4)
CYLINDER_REF_N = (118225.0, 115980.0, 71958.6, 70419.9)
CONTACT_REF_N = (119272.0, 117027.0, 72676.1, 71137.3)


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


def test_static_start_equals_the_rev33_static_solution(p2) -> None:
    k = axial_stiffness_at_N_m(p2, operating_extensions_m(p2))
    f = static_cylinder_forces_N(p2, k)
    assert f == pytest.approx(CYLINDER_REF_N, abs=1.0)
    w_sup = p2.superstructure.mass_properties.mass_kg * p2.meta.gravity_m_s2
    assert f.sum() == pytest.approx(w_sup, rel=1e-12)


def test_static_start_pose_lock_table_and_piston_monitor(p2) -> None:
    """Column convention (5.20.2 supplement 1): s_ref = e_op, rod bodies at e_op - F / k_2, so
    the start attitude is the V3 reference and the lock happens at s_lock = e_op with the
    reference k_h, k_r (leg_parameters, 6 printed digits); no piston stop violation."""
    from outrigger_sim.frames import roll_pitch_from_quat

    m = L2bModel(p2)
    rp = np.degrees(roll_pitch_from_quat(np.array(m.pose.quat_wxyz)))
    assert rp == pytest.approx((-0.001875, 0.01027), abs=2e-6)
    comp = 1e3 * (np.array(m.start_s_ref_m) - np.array(m.extensions_m))
    assert comp == pytest.approx((4.5637, 4.4770, 3.6893, 3.6104), abs=1e-4)
    for _ in range(50):
        m.step()
    lock = m.actuator.rod_side.lock_table()
    assert lock["s_lock_m (s_ref at the lock instant)"] == list(
        p2.contact.rigid_floor.L1.operating_extension_m)
    assert lock["k_h_N_m"] == pytest.approx([29424100.0] * 2 + [21554400.0] * 2, rel=5e-6)
    assert lock["k_r_N_m"] == pytest.approx([10805100.0] * 2 + [8748520.0] * 2, rel=5e-6)
    assert lock["L0r_m"] == pytest.approx([0.05] * 4, rel=1e-12)
    assert m.actuator.piston_monitor()["stop_violation_steps"] == [0, 0, 0, 0]


def test_pad_force_readings_agree(p2) -> None:
    """GetContactForce = ReportAllContacts per rod (same container, exact); the 0.1 s window
    mean matches the rod axial balance and the V1 reference (0.1 % W/4); pads + crawler =
    weight in the window mean (1e-4)."""
    m = L2bModel(p2)
    n_win = round(0.1 / m.dt_s)
    for _ in range(round(0.2 / m.dt_s)):
        m.step()
    rows = []
    for _ in range(n_win):
        m.step()
        rows.append(pad_force_crosscheck(m))
    body = np.array([r["get_contact_force_N"] for r in rows])
    report = np.array([r["report_contacts_N"] for r in rows])
    balance = np.array([r["axial_balance_N"] for r in rows])
    np.testing.assert_array_equal(body, report)
    assert all(r["report_contact_count"] == [1, 1, 1, 1] for r in rows)
    w4 = rows[0]["weight_along_normal_N"] / 4.0
    assert np.abs(body.mean(axis=0) - balance.mean(axis=0)).max() < 1e-3 * w4
    assert np.abs(body.mean(axis=0) - np.array(CONTACT_REF_N)).max() < 1e-3 * w4
    total = np.array([r["pads_plus_crawler_N"] for r in rows]).mean()
    assert total == pytest.approx(rows[0]["weight_along_normal_N"], rel=1e-4)


@pytest.mark.parametrize("moving", [False, True])
def test_snapshot_round_trip(p2, moving) -> None:
    """Snapshot mid-run (locked, or FL extending), restore into a fresh build, continue
    0.05 s: same body positions (<= 1e-9 m) and the same force-law values."""
    m = L2bModel(p2)
    if moving:
        m.set_command([p2.actuator.max_speed_m_s, 0.0, 0.0, 0.0])
    for _ in range(300):
        m.step()
    snap = m.snapshot()
    for _ in range(500):
        m.step()
    expected = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in m.bodies])
    f_expected = m.actuator.force_N
    fresh = L2bModel(p2)
    fresh.restore(snap)
    for _ in range(500):
        fresh.step()
    got = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in fresh.bodies])
    assert np.abs(got - expected).max() <= 1e-9
    assert np.abs(fresh.actuator.force_N - f_expected).max() <= 1e-3


def test_engine_members(p2) -> None:
    m = L2bModel(p2)
    eng = L2bEngine(m)
    for _ in range(20):
        eng.step()
    t = eng.truth()
    assert np.all(np.isfinite(t.F_cyl_N))
    meas = eng.measure_l2b()
    assert np.all(meas["rod_pressure_Pa"] > 0.0)
    head = meas["head_pressure_Pa"] * m.actuator.head_area_m2
    np.testing.assert_allclose(
        head - meas["rod_pressure_Pa"] * np.asarray(p2.l2b.rod_side.annulus_area_m2),
        meas["cylinder_force_N"], rtol=1e-12,
    )
    eng.measure()
    assert eng.step_monitor()["nonfinite_steps"] == 0
    eng.close()
