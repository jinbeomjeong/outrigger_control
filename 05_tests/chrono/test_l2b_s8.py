"""S8 plant on the four-leg L2b-NSC model: seal friction path, counterbalance option, sensor truth,
snapshot, crawler NSC compliance option (spec s8_seal_friction_counterbalance.md 5 C-3..C-9,
dynamics_model.md 5.25.5 S8-L3)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.l2b_engine import L2bEngine  # noqa: E402
from outrigger_sim.chrono.l2b_model import L2bModel  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono

LEVEL = 4000.0


def _params(level=0.0, lock_valve="pilot_check", **extra):
    ov = {"actuator.seal_friction.level_N": level, "actuator.lock_valve": lock_valve, **extra}
    return load_params(level="top", model="L2b_NSC", overrides=ov)


def test_level_zero_pilot_check_is_the_s7_path() -> None:
    m = L2bModel(_params(), crawler_contact="rigid")
    act = m.actuator
    assert act.seal_friction is None and act.counterbalance is None and not act.friction_path
    assert act.meta()["s8"]["friction_path"] is False
    for _ in range(20):
        m.step()
    np.testing.assert_array_equal(act.acting_pressure_force_N, act.acting_force_N)
    s = np.array([mo.GetMotorPos() for mo in m.motors])
    np.testing.assert_array_equal(act.stroke_sensor_true_m(s),
                                  act.stroke_true_m(s, act.acting_force_N))


def test_friction_path_limits_and_sensor_truth() -> None:
    p = _params(LEVEL)
    m = L2bModel(p, crawler_contact="rigid")
    eng = L2bEngine(m)
    act = m.actuator
    np.testing.assert_allclose(act.seal_friction.limits_N,
                               [LEVEL, LEVEL, 0.8333 * LEVEL, 0.8333 * LEVEL], rtol=1e-12)
    for _ in range(2000):
        eng.step()
    f = act.acting_friction_N
    assert np.all(np.abs(f) <= act.seal_friction.limits_N + 1e-9)
    meas = eng.measure_l2b()
    a_r = np.asarray(p.l2b.rod_side.annulus_area_m2)
    net = meas["head_pressure_Pa"] * act.head_area_m2 - meas["rod_pressure_Pa"] * a_r
    np.testing.assert_allclose(net, act.acting_force_N - f, rtol=1e-12)
    np.testing.assert_allclose(meas["cylinder_force_N"], act.acting_force_N - f, rtol=1e-12)
    np.testing.assert_array_equal(meas["stroke_m"], act.acting_piston_m)
    # law C judged force is the pressure force of the step just taken
    np.testing.assert_allclose(act.last_judged_force_N, net, rtol=0, atol=1e-6)
    # F = k_out (s_p - s) + dashpot: spring part equals the oil force + friction
    rec = act.s8_record()
    assert rec["friction_path"] and rec["seal_friction"]["armed"]
    assert eng.step_monitor()["nonfinite_steps"] == 0
    eng.close()


def test_extending_leg_slides_with_inward_friction() -> None:
    """FL extends on the floor: the piston slides outward, friction acts inward (f = -F_s) and
    the pressure force exceeds the rod force by F_s (spec 1 sign check)."""
    m = L2bModel(_params(LEVEL), crawler_contact="rigid")
    m.set_command([0.5 * m.params.actuator.max_speed_m_s, 0.0, 0.0, 0.0])
    for _ in range(3000):
        m.step()
    act = m.actuator
    assert act.acting_friction_N[0] == pytest.approx(-LEVEL)
    assert not act.seal_friction.stuck[0]
    assert act.acting_pressure_force_N[0] - act.acting_force_N[0] == pytest.approx(LEVEL)
    assert act.seal_friction.dissipation_J[0] > 0.0


def test_zero_level_counterbalance_path_matches_the_series_law() -> None:
    """CB option with F_s = 0 uses the oil-only law (k_out = inf): same forces as the S7 path
    within 1e-6 relative over 0.03 s at rest (CB closed: pressures ~90 bar). Not bit-equal: the
    oil-only solve differs by round-off (1 / (1 / k) != k), which the NSC step noise amplifies
    (measured 0.03 N of 118 kN)."""
    a = L2bModel(_params(), crawler_contact="rigid")
    b = L2bModel(_params(0.0, "counterbalance"), crawler_contact="rigid")
    assert b.actuator.friction_path and b.actuator.counterbalance is not None
    for _ in range(300):
        a.step()
        b.step()
    fa, fb = a.actuator.force_N, b.actuator.force_N
    assert np.abs(fb - fa).max() <= 1e-6 * np.abs(fa).max()
    assert np.all(b.actuator.counterbalance.volume_m3 == 0.0)


@pytest.mark.parametrize("moving", [False, True])
def test_snapshot_round_trip_with_friction(moving) -> None:
    p = _params(LEVEL)
    m = L2bModel(p, crawler_contact="rigid")
    if moving:
        m.set_command([p.actuator.max_speed_m_s, 0.0, 0.0, 0.0])
    for _ in range(300):
        m.step()
    snap = m.snapshot()
    assert any("fr_" in str(k) for k in snap.payload)
    for _ in range(500):
        m.step()
    expected = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in m.bodies])
    sp_expected = m.actuator.seal_friction.s_p.copy()
    fresh = L2bModel(p, crawler_contact="rigid")
    fresh.restore(snap)
    for _ in range(500):
        fresh.step()
    got = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in fresh.bodies])
    assert np.abs(got - expected).max() <= 1e-9
    assert np.abs(fresh.actuator.seal_friction.s_p - sp_expected).max() <= 1e-9
    assert not fresh.actuator.friction_state_defaulted


def test_params_sha_includes_s8_keys_for_l2b_only() -> None:
    base_l1 = load_params(level="top")
    other_l1 = load_params(level="top", overrides={"actuator.seal_friction.level_N": 8000.0})
    assert base_l1.sha256 == other_l1.sha256  # L1 fingerprint excludes the L2b-only blocks
    assert _params(0.0).sha256 != _params(LEVEL).sha256


def test_crawler_compliance_option() -> None:
    p = _params()
    m = L2bModel(p, crawler_contact="compliant", start="hanging", extensions_m=(0.0,) * 4)
    meta = m.meta()["crawler_contact"]
    assert meta["model"] == "compliant"
    assert meta["material_float32"]["compliance"] == pytest.approx(1.2e-7, rel=1e-6)
    assert meta["material_float32"]["dampingf"] == pytest.approx(2.0e-3, rel=1e-6)
    rigid = L2bModel(p, crawler_contact="rigid", start="hanging", extensions_m=(0.0,) * 4)
    assert rigid.meta()["crawler_contact"]["model"] == "rigid"
    assert rigid.bundle.floor_material.GetDampingF() == 0.0
