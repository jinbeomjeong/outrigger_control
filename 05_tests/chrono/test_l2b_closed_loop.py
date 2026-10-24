"""S7 control ③ preparation: L2b valve lag, closed-loop measurements, crawler start, pad record.

``04_scripts/02_chrono/run_S7C.py``; ``outrigger_sim.actuation`` (valve on the speed reference),
``chrono/l2b_engine`` (ideal measurements = L1-R definitions), ``chrono/l2b_pad_record``.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.actuation import SpeedReference  # noqa: E402
from outrigger_sim.chrono.actuators import L1SpeedActuator, make_motion_function  # noqa: E402
from outrigger_sim.chrono.l2b_engine import L2bEngine  # noqa: E402
from outrigger_sim.chrono.l2b_model import L2bModel  # noqa: E402
from outrigger_sim.chrono.l2b_pad_record import L2bPadRecorder  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.sensors.averaging import PeriodAverage  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


@pytest.mark.parametrize("amp", ["none", "full_scale", "per_step"])
@pytest.mark.parametrize("tau", [0.1, 0.0])
def test_valve_reference_matches_l1_valve_bit_for_bit(amp, tau) -> None:
    """``SpeedReference.configure_valve`` = ``L1SpeedActuator.configure_valve`` (amplifier
    ramp, exact spool lag, step-mean speed, end cushion, law C) for random commands / forces."""
    rng = np.random.default_rng(11)
    n, dt, v, ramp = 3, 1e-4, 0.0209243016, 0.1
    ext = [278737.808, 278737.808, 199568.0]
    ret = [79168.1349, 79168.1349, 66000.0]
    s0 = [0.02, 0.35, 0.695]
    l1 = L1SpeedActuator(
        [object()] * n, [make_motion_function(x) for x in s0], s0, [(0.0, 0.7)] * n,
        max_speed_m_s=v, ramp_s=ramp, max_force_extend_N=ext, max_force_retract_N=ret)
    ref = SpeedReference(s0, [(0.0, 0.7)] * n, max_speed_m_s=v, ramp_s=ramp,
                         max_force_extend_N=ext, max_force_retract_N=ret)
    l1.configure_valve(tau_s=tau, amp_ramp=amp, amp_ramp_s=0.1)
    ref.configure_valve(tau_s=tau, amp_ramp=amp, amp_ramp_s=0.1)
    assert not ref.command_ramp_active
    t = 0.0
    for k in range(30000):
        if k % 1000 == 0:  # 10 Hz commands
            cmd = rng.choice([-1.0, -0.3, 0.0, 0.25, 1.0], size=n) * v
            l1.set_command(cmd)
            ref.set_command(cmd)
        f = rng.normal(1.0e5, 1.2e5, size=n)
        l1.on_step_end()
        l1.advance(dt, t, cylinder_force_N=f)
        ref.advance(dt, cylinder_force_N=f)
        t += dt
        assert np.array_equal(l1.s_ref_m, ref.s_ref_m)
        assert np.array_equal(l1.u_applied_m_s, ref.u_applied_m_s)
        assert np.array_equal(l1.valve_state_m_s, ref.valve_state_m_s)
    assert ref.valve_meta()["tau_v_s"] == tau


def test_valve_first_order_response() -> None:
    """Step 0 -> v_max: applied speed follows ``1 - e^(-t/tau)`` (step-mean form)."""
    v, dt, tau = 0.02, 1e-4, 0.1
    ref = SpeedReference([0.1], [(0.0, 0.7)], max_speed_m_s=v, ramp_s=0.1)
    ref.configure_valve(tau_s=tau)
    ref.set_command([v])
    for _ in range(round(tau / dt)):
        ref.advance(dt)
    # mean over the last step [tau - dt, tau]
    expected = v * (1.0 - tau / dt * (np.exp(-(tau - dt) / tau) - np.exp(-1.0)))
    assert ref.u_applied_m_s[0] == pytest.approx(expected, rel=1e-12)
    assert ref.valve_state_m_s[0] == pytest.approx(v * (1.0 - np.exp(-1.0)), rel=1e-12)


def test_valve_state_snapshot_round_trip() -> None:
    ref = SpeedReference([0.1, 0.2], [(0.0, 0.7)] * 2, max_speed_m_s=0.02, ramp_s=0.1)
    ref.configure_valve(tau_s=0.1)
    ref.set_command([0.02, -0.01])
    for _ in range(300):
        ref.advance(1e-4)
    arrays = ref.state_arrays()
    other = SpeedReference([0.1, 0.2], [(0.0, 0.7)] * 2, max_speed_m_s=0.02, ramp_s=0.1)
    other.configure_valve(tau_s=0.1)
    other.restore_state(arrays)
    for r in (ref, other):
        r.advance(1e-4)
    assert np.array_equal(ref.s_ref_m, other.s_ref_m)
    assert np.array_equal(ref.valve_state_m_s, other.valve_state_m_s)


def test_engine_ideal_measurements_definitions(p2) -> None:
    """Two pressures with ``p_h A_p - p_r A_ann = F``, ``stroke_m = s_ref``,
    ``stroke_corrected_m`` = piston ``s + F / k_out``; time mismatch refused."""
    m = L2bModel(p2)
    eng = L2bEngine(m, imu_method="chrono_point")
    for _ in range(30):
        eng.step()
    s = eng.imu_sample()
    meas = eng.ideal_measurements(PeriodAverage(s.t_s, s.specific_force_m_s2,
                                                s.angular_rate_rad_s, 1))
    leg = eng.measure_l2b()
    a_r = np.asarray(p2.l2b.rod_side.annulus_area_m2)
    net = meas.head_pressure_Pa * m.actuator.head_area_m2 - meas.rod_pressure_Pa * a_r
    np.testing.assert_allclose(net, leg["cylinder_force_N"], rtol=1e-12)
    assert np.array_equal(meas.stroke_m, m.actuator.reference.s_ref_m)
    s_link = np.array([mo.GetMotorPos() for mo in m.motors])
    np.testing.assert_allclose(meas.stroke_corrected_m,
                               m.actuator.stroke_true_m(s_link, leg["cylinder_force_N"]),
                               rtol=0, atol=1e-15)
    # piston below s_ref by about F / k_oil (a few mm under the static load)
    gap = meas.stroke_m - meas.stroke_corrected_m
    assert np.all(gap > 0.0) and np.all(gap < 0.01)
    with pytest.raises(ValueError):
        eng.ideal_measurements(PeriodAverage(s.t_s - 1.0, s.specific_force_m_s2,
                                             s.angular_rate_rad_s, 1))
    eng.close()


def test_rigid_crawler_start_on_a_slope(p2) -> None:
    """``run_S7C.l2b_crawler_start``: body and floor share the floor rotation; after 0.3 s the
    crawler carries the superstructure + rods along the normal (0.1 s mean, 1 %) and the body
    attitude equals the floor slope."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))
    import run_S7C

    from outrigger_sim.frames import roll_pitch_from_quat

    pose, floor_pose, n = run_S7C.l2b_crawler_start(p2, "fdown3.5")
    m = L2bModel(p2, pose=pose, extensions_m=(0.0,) * 4, start="hanging", crawler=True,
                 floor_pose=floor_pose)
    out = run_S7C.settle_l2b(m, 0.3)
    assert out["crawler_normal_mean_N"] == pytest.approx(out["weight_along_normal_N"], rel=1e-2)
    rp = np.degrees(roll_pitch_from_quat(np.array(pose.quat_wxyz)))
    assert rp[1] == pytest.approx(3.5, abs=1e-9)
    assert out["body_roll_pitch_deg_mean"][1] == pytest.approx(3.5, abs=2e-3)


def test_truth_contact_window_mean(p2) -> None:
    """Truth contact forces = trailing 20 ms mean of every step (5.22.3); None = raw probe."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))
    import run_S7C

    from outrigger_sim.chrono.l2b_model import read_l2b_probe

    pose, floor_pose, _n = run_S7C.l2b_crawler_start(p2, "flat")
    m = L2bModel(p2, pose=pose, extensions_m=(0.0,) * 4, start="hanging", crawler=True,
                 floor_pose=floor_pose)
    eng = L2bEngine(m)
    assert eng.contact_window_meta()["contact_window_steps"] == 200
    rows = []
    for _ in range(400):
        eng.step()
        rows.append(read_l2b_probe(m).crawler_contact_world_N)
    t = eng.truth()
    np.testing.assert_allclose(t.F_crawler_N, np.mean(rows[-200:], axis=0), rtol=1e-12)
    w = (p2.superstructure.mass_properties.mass_kg
         + sum(leg.moving_part.mass_kg for leg in p2.legs)) * p2.meta.gravity_m_s2
    assert t.F_crawler_N[2] == pytest.approx(w, rel=2e-2)
    raw = L2bEngine(m, contact_window_s=None)
    np.testing.assert_array_equal(raw.truth().F_crawler_N, read_l2b_probe(m).crawler_contact_world_N)
    eng.close()
    raw.close()


def test_truth_contact_window_cleared_on_restore(p2) -> None:
    """``restore`` / ``reset`` drop the 20 ms contact window: right after a restore the truth
    is the raw probe, and k < window steps later it is the mean of those k steps only (no
    pre-restore steps mixed in)."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"))
    import run_S7C

    from outrigger_sim.chrono.l2b_model import read_l2b_probe

    pose, floor_pose, _n = run_S7C.l2b_crawler_start(p2, "flat")
    m = L2bModel(p2, pose=pose, extensions_m=(0.0,) * 4, start="hanging", crawler=True,
                 floor_pose=floor_pose)
    eng = L2bEngine(m)
    for _ in range(20):  # crawler still dropping: contact far from the settled value
        eng.step()
    snap = eng.snapshot()
    for _ in range(400):  # fill the window with settled-state forces
        eng.step()
    settled = eng.truth().F_crawler_N.copy()
    for restore in (eng.restore, eng.reset):
        restore(snap)
        np.testing.assert_array_equal(eng.truth().F_crawler_N,
                                      read_l2b_probe(m).crawler_contact_world_N)
        rows = []
        for _ in range(50):
            eng.step()
            rows.append(read_l2b_probe(m).crawler_contact_world_N)
        mean = eng.truth().F_crawler_N
        np.testing.assert_allclose(mean, np.mean(rows, axis=0), rtol=1e-12)
        # a stale window (150 settled + 50 new rows) would be pulled toward the settled value
        assert abs(mean[2] - settled[2]) > 1e-3 * abs(settled[2])
        for _ in range(400):
            eng.step()
    eng.close()


def test_pad_record_reads_law_minimum_and_20ms_contact(p2) -> None:
    m = L2bModel(p2)
    eng = L2bEngine(m)
    rec = L2bPadRecorder(eng, every_steps=10)
    eng.set_step_callback(rec)
    for _ in range(600):
        eng.step()
    a = rec.arrays()
    assert a["t"].size == 60 and rec.window_samples == 20
    assert np.all(a["F_cyl_min_interval"] <= a["F_cyl"] + 1e-9)
    # 20 ms mean contact: much smaller spread than the single-step reading (5.22.3)
    tail = slice(30, 50)
    assert np.std(a["N"][tail], axis=0).max() < np.std(a["N_raw"][tail], axis=0).max()
    assert np.all(a["N"][tail] > 0.6e5)
    eng.close()
