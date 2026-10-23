"""L1-R Chrono link (``chrono/rod_chamber_link``, dynamics_model.md 5.12.4-5.12.8,
rod_side_pressure.md 14): mechanics-off regression, locked stiffness k_n', knee, lock
continuity, total normal force to the ground bushing, sensor truth from the same step, R16
snapshot (bit-identical with locked legs, old snapshots default, mismatch refused) and the
per-leg force-saturation limits.

Parameters: the project YAML. ``OUTRIGGER_TEST_PARAMS`` (a YAML path) overrides it while the
loader cannot read the regenerated YAML's text / bool keys (2026-10-22, python-expert fix
pending). L1-R is switched on with ``L1Model(rod_side_mechanics=...)``.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.actuators import leg_force_limits_N  # noqa: E402
from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.l1_engine import L1Engine  # noqa: E402
from outrigger_sim.chrono.model import L1Model, operating_extensions_m, zero_pose  # noqa: E402
from outrigger_sim.chrono.rod_chamber_link import (  # noqa: E402
    PART_PREFIX,
    one_sided_extra_force_N,
)
from outrigger_sim.engine import Snapshot  # noqa: E402
from outrigger_sim.frames import quat_from_euler_zyx  # noqa: E402
from outrigger_sim.hydraulics.rod_chamber import RodChamberMode  # noqa: E402
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402
from outrigger_sim.scenarios.settle import linear_static_solution  # noqa: E402
from outrigger_sim.signals import Command  # noqa: E402

pytestmark = pytest.mark.chrono

ON = "one_sided_parallel"


@pytest.fixture(scope="module")
def params():
    return load_params(os.environ.get("OUTRIGGER_TEST_PARAMS") or None, level="top")


def _static_pose(params) -> BodyPose:
    """Linear static pose of the head-only pads (crawler off): small residual vibration."""
    ext = operating_extensions_m(params)
    z0 = zero_pose(params, ext).origin_m[2]
    kn = [params.contact.rigid_floor.L1.kn_per_pad_N_m[i] for i in range(4)]
    u_z, roll, pitch = (float(v) for v in linear_static_solution(params, kn)["q"])
    q = tuple(float(c) for c in quat_from_euler_zyx(0.0, pitch, roll))
    return BodyPose((0.0, 0.0, z0 + u_z), q)


def _model(params, mechanics=ON, **kw) -> L1Model:
    return L1Model(params, pose=_static_pose(params), crawler=False, actuator=True,
                   rod_side_mechanics=mechanics, **kw)


def _state(model: L1Model) -> np.ndarray:
    out = []
    for body in model.bodies:
        p, q, v = body.GetPos(), body.GetRot(), body.GetPosDt()
        out += [p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3, v.x, v.y, v.z]
    out += [m.GetMotorForce() for m in model.motors]
    out += list(model.bushing.normal_force_raw_N)
    return np.array(out)


def test_off_machine_path_bit_identical_to_formulas(params) -> None:
    """Mechanics off: stepping the machine (legacy output as sensor truth) changes nothing,
    bit for bit, against the idle machine (formula truth); zero pose drop with touch events
    and leg moves through the closed-loop callback."""
    runs = []
    for machine in (False, True):
        model = L1Model(params, actuator=True, rod_side_mechanics="off")
        model.rod_chamber.step_when_off = machine
        engine = L1Engine(model)
        v = params.actuator.max_speed_m_s
        rows: list[np.ndarray] = []

        def on_step(eng: L1Engine) -> None:
            t = eng.time_s
            m = eng.measure()
            rows.append(np.concatenate([m.head_pressure_Pa, m.stroke_corrected_m, m.stroke_m]))
            u = [v, 0.0, 0.0, -0.5 * v] if 0.1 <= t < 0.25 else [0.0] * 4
            eng.apply_command(Command(t_s=t, leg_speed_m_s=np.array(u)))
            assert m.rod_pressure_Pa is None

        engine.set_step_callback(on_step)
        states = []
        for _ in range(round(0.4 / model.dt_s)):
            engine.step()
            states.append(_state(model))
        assert (model.rod_chamber.last_step is not None) is machine
        runs.append((np.array(states), np.array(rows)))
    assert np.array_equal(runs[0][0], runs[1][0])
    assert np.array_equal(runs[0][1], runs[1][1])


def test_on_locked_stiffness_knee_and_equilibrium(params) -> None:
    """Locked from the first step; a slow downward force at the COG: dN/d delta = k_n' below
    the knee, k_n above it (machine and physics F_cyl + m_rod g); the knee at dF_knee;
    static sum of the pad forces = weight (+ load) within 1e-3."""
    model = _model(params)
    sup = model.superstructure
    acc = sup.AddAccumulator()
    f_max = 50.0e3
    dt = model.dt_s
    g = params.meta.gravity_m_s2
    m_rod = np.array([leg.moving_part.mass_kg for leg in params.legs])
    weight = (params.superstructure.mass_properties.mass_kg + m_rod.sum()) * g

    def load(t: float) -> float:
        return 0.0 if t < 0.4 else min(1.0, (t - 0.4) / 1.2) * f_max

    def hook(m: L1Model, _dt: float) -> None:
        sup.EmptyAccumulator(acc)
        sup.AccumulateForce(acc, ch.ChVector3d(0.0, 0.0, -load(float(m.system.GetChTime()))),
                            sup.GetPos(), False)

    model.load_hooks.append(hook)
    rod = model.rod_chamber
    rows = []
    for _ in range(round(1.9 / dt)):
        model.step()
        out = rod.last_step
        rows.append((float(model.system.GetChTime()), rod.last_deflection_m.copy(),
                     np.array(out.normal_force_N), out.mode.copy(),
                     np.array([m.GetMotorForce() for m in model.motors]),
                     np.array([np.nan if leg.anchor is None else leg.anchor.pad_force_N
                               for leg in rod.machine.legs])))
    t = np.array([r[0] for r in rows])
    delta = np.array([r[1] for r in rows])
    normal = np.array([r[2] for r in rows])
    mode = np.array([r[3] for r in rows])
    f_pad = np.array([r[4] for r in rows]) + m_rod * g
    anchor = np.array([r[5] for r in rows])
    assert np.all(mode[0] == RodChamberMode.LOCK)  # fresh legs lock on the first standstill
    for name, (t0, t1, extra) in {"rest": (0.3, 0.4, 0.0), "loaded": (1.75, 1.9, f_max)}.items():
        sel = (t > t0) & (t <= t1)
        total = float(f_pad[sel].sum(axis=1).mean())
        assert abs(total - (weight + extra)) / (weight + extra) < 1e-3, name
    ramp = (t > 0.45) & (t <= 1.6)
    knees_seen = 0
    for i, lp in enumerate(rod.leg_params):
        for state, k_ref in ((RodChamberMode.LOCK, lp.pad_stiffness_locked_N_m),
                             (RodChamberMode.FLOOR, lp.pad_stiffness_head_only_N_m)):
            idx = np.flatnonzero(ramp & (mode[:, i] == state))
            if idx.size < 400:
                continue
            idx = idx[idx.size // 10: -idx.size // 10]
            slope_machine = np.polyfit(delta[idx, i], normal[idx, i], 1)[0]
            slope_phys = np.polyfit(delta[idx, i], f_pad[idx, i], 1)[0]
            assert slope_machine == pytest.approx(k_ref, rel=1e-9), (LEG_ORDER[i], state)
            assert slope_phys == pytest.approx(k_ref, rel=1e-2), (LEG_ORDER[i], state)
        entries = np.flatnonzero((mode[1:, i] == RodChamberMode.FLOOR)
                                 & (mode[:-1, i] == RodChamberMode.LOCK)) + 1
        knee = lp.knee_force_increment_N(lp.p_rod_locked_after_extend_Pa)
        for k in entries:
            knees_seen += 1
            assert normal[k - 1, i] - anchor[k - 1, i] <= knee <= normal[k, i] - anchor[k, i]
    assert knees_seen >= 1


def test_on_lock_continuity_and_bushing_total_normal(params) -> None:
    """A leg that moves and stops relocks without a force step (F_x continuous through the
    release residual, |F_x| at the lock <= (k_n' - k_n) |d delta| dt + 1 N); the ground
    bushing reads the machine's total normal force of the previous step (Q-D2)."""
    model = _model(params)
    rod = model.rod_chamber
    v = params.actuator.max_speed_m_s
    prev = None
    lock_seen = False
    for k in range(round(0.8 / model.dt_s)):
        t = float(model.system.GetChTime())
        model.set_command([0.2 * v if 0.2 <= t < 0.4 else 0.0, 0.0, 0.0, 0.0])
        model.step()
        out = rod.last_step
        if prev is not None:
            np.testing.assert_array_equal(model.bushing.normal_force_raw_N, prev.normal_force_N)
            if prev.mode[0] == RodChamberMode.EXT and out.mode[0] == RodChamberMode.LOCK:
                lp = rod.leg_params[0]
                dk = lp.pad_stiffness_locked_N_m - lp.pad_stiffness_head_only_N_m
                bound = dk * abs(rod.last_deflection_rate_m_s[0]) * model.dt_s + 1.0
                assert abs(out.extra_force_N[0] - prev.extra_force_N[0]) <= bound
                lock_seen = True
        prev = out
    assert lock_seen


def test_on_sensor_truth_same_step_identity(params) -> None:
    """Measurements carry the machine pressures of the same step: p_h A_p - p_r A_ann =
    F_cyl, rod pressure present, stroke_corrected = machine stroke_true."""
    model = _model(params)
    engine = L1Engine(model)
    seen = []

    def on_step(eng: L1Engine) -> None:
        m = eng.measure()
        out = eng.rod_chamber.output_at(eng.time_s)
        assert out is not None and m.rod_pressure_Pa is not None
        f = np.array([mo.GetMotorForce() for mo in eng.model.motors])
        lp = eng.rod_chamber.leg_params
        a_p = np.array([p.head_area_m2 for p in lp])
        a_r = np.array([p.annulus_area_m2 for p in lp])
        np.testing.assert_allclose(m.head_pressure_Pa * a_p - m.rod_pressure_Pa * a_r, f,
                                   rtol=0, atol=1e-6 * np.abs(f).max())
        np.testing.assert_array_equal(m.stroke_corrected_m, out.stroke_true_m)
        seen.append(eng.time_s)

    engine.set_step_callback(on_step)
    for _ in range(50):
        engine.step()
    assert len(seen) == 50
    truth = engine.truth()
    np.testing.assert_array_equal(truth.F_contact_n_N, model.rod_chamber.last_step.normal_force_N)


def _rod_payload(snap: Snapshot) -> dict[str, np.ndarray]:
    head = f"{PART_PREFIX}."
    return {k[len(head):]: v for k, v in snap.payload.items() if k.startswith(head)}


def test_on_snapshot_round_trip_and_rewind(params) -> None:
    """R16 with L1-R on, legs locked: the restored rod-chamber state equals the snapshot bit
    for bit (state keys, last output, accumulator content); the continuation matches within
    the restore noise of the model without L1-R (contact and actuator restore, about 1e-11
    relative; the REXOME35 YAML of 2026-10-22 continued bit-identically):
    1e-10 on positions (m), quaternions and velocities (m/s), 1e-10 relative on the forces (old
    REXOME33 YAML: 2e-12 m/s and 2.3e-6 N, the same as with mechanics off)."""
    model = _model(params)
    for _ in range(1000):
        model.step()
    snap = model.snapshot()
    saved = _rod_payload(snap)
    assert saved
    expected = []
    for _ in range(200):
        model.step()
        expected.append(_state(model))
    for target in (_model(params), model):  # fresh build, then rewind
        target.restore(snap)
        now = target.rod_chamber.state_arrays()
        for key, value in saved.items():
            if key == "engine_next_step_full_update":
                continue  # the restore leaves the system updated (its own flush)
            assert np.array_equal(np.asarray(now[key]), np.asarray(value), equal_nan=True), key
        got = []
        for _ in range(200):
            target.step()
            got.append(_state(target))
        got_a, exp_a = np.array(got), np.array(expected)
        n_body = 10 * len(model.bodies)
        assert np.abs(got_a[:, :n_body] - exp_a[:, :n_body]).max() <= 1e-10
        scale = np.abs(exp_a[:, n_body:]).max()
        assert np.abs(got_a[:, n_body:] - exp_a[:, n_body:]).max() <= 1e-10 * scale


def test_old_snapshot_defaults_and_mismatch_refused(params) -> None:
    model = _model(params)
    for _ in range(500):
        model.step()
    snap = model.snapshot()
    old = Snapshot(engine=snap.engine, params_sha256=snap.params_sha256, time_s=snap.time_s,
                   held_command=snap.held_command,
                   payload={k: v for k, v in snap.payload.items()
                            if not k.startswith(f"{PART_PREFIX}.")})
    fresh = _model(params)
    fresh.restore(old)
    assert fresh.rod_chamber.state_defaulted
    assert fresh.rod_chamber.meta()["l1r_state_defaulted"] is True
    fresh.step()
    out = fresh.rod_chamber.last_step
    assert np.all(out.mode == RodChamberMode.LOCK)
    anchors = [leg.anchor.pad_force_N for leg in fresh.rod_chamber.machine.legs]
    np.testing.assert_array_equal(anchors, out.normal_force_N)
    off = _model(params, mechanics="off")
    with pytest.raises(ValueError, match="mechanics"):
        off.restore(snap)


def test_one_sided_extra_force_rule() -> None:
    """M1 (rod_side_pressure.md 17.1): F_x unchanged without a clip, total pad force
    N_smc + F_x >= 0 with one, continuous across both clip boundaries."""
    fx, spring = -18.5e3, 19.0e3
    assert one_sided_extra_force_N(fx, spring, 0.0) == fx  # no clip: bit for bit
    for damping in np.linspace(-40.0e3, 5.0e3, 451):
        applied = one_sided_extra_force_N(fx, spring, damping)
        smc = max(0.0, spring + damping)
        assert smc + applied >= -1e-9
        assert smc + applied == pytest.approx(max(0.0, spring + fx + damping), abs=1e-9)
    for edge in (-spring, -(spring + fx)):  # N_smc = 0 and N_tot = 0 boundaries
        below = one_sided_extra_force_N(fx, spring, edge - 1e-6)
        above = one_sided_extra_force_N(fx, spring, edge + 1e-6)
        assert below == pytest.approx(above, abs=1e-3)


def test_leg_force_limits(params) -> None:
    ext, ret = leg_force_limits_N(params)
    try:
        want = [float(params.get(f"legs.{leg}.cylinder.max_force_extend_N")) for leg in LEG_ORDER]
    except Exception:  # noqa: BLE001 - YAML before the REXOME35 regeneration
        want = [float(params.get("actuator.max_force_extend_N"))] * 4
    assert ext == want and len(ret) == 4
    model = _model(params, mechanics="off")
    limits = model.actuator.force_limits_N
    assert limits is not None
    assert np.allclose(np.broadcast_to(limits[0], (4,)), want, rtol=0, atol=0)


def test_sensor_source_reads_the_engine_machine(params) -> None:
    """sensors.rod_side l1r_state_machine source over the engine's machine: the engine steps
    the machine through ``source.step`` (one owner); the source's last step is the engine's."""
    from outrigger_sim.sensors.rod_side import build_rod_pressure_source

    model = _model(params)
    rod = model.rod_chamber
    lp = rod.leg_params
    source = build_rod_pressure_source(
        "l1r_state_machine",
        head_area_m2=[p.head_area_m2 for p in lp],
        annulus_area_m2=[p.annulus_area_m2 for p in lp],
        stroke_max_m=float(params.get("actuator.stroke_m")),
        head_dead_length_m=float(params.get("actuator.oil_dead_length_m")),
        period_s=0.02,
        machine=rod.machine,
    )
    rod.attach_sensor_source(source)
    for _ in range(20):
        model.step()
    assert source.last_step is rod.last_step
    head, rod_p = source.update(np.zeros(4), np.zeros(4), np.zeros(4))
    np.testing.assert_array_equal(head, rod.last_step.head_pressure_Pa)
    np.testing.assert_array_equal(rod_p, rod.last_step.rod_pressure_Pa)
    other = _model(params)
    with pytest.raises(ValueError, match="RodChamberStateMachine"):
        other.rod_chamber.attach_sensor_source(source)


# --- sensitivity cases (S4 beta / rod side): k_n above the YAML k_h ---------------------------

KN_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"


def _beta_case_params(*, with_beta: bool):
    """S4 beta 1.6 GPa case: the reference k_L1 per leg, with or without the beta override."""
    from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references

    k_l1 = load_references().get(BETA_K_L1_N_M, beta="beta_1.6e+09")
    overrides = {f"{KN_KEY}.{leg}": float(k) for leg, k in zip(LEG_ORDER, k_l1, strict=True)}
    if with_beta:
        overrides["actuator.oil_bulk_modulus_eff_Pa"] = 1.6e9
    return load_params(os.environ.get("OUTRIGGER_TEST_PARAMS") or None, level="top",
                       overrides=overrides)


def test_off_model_builds_when_the_sensitivity_kn_exceeds_k_h(params) -> None:
    """S4: mechanics off and k_n above k_h (beta 1.6 k_n, YAML beta) -> the model
    builds, steps and records why the idle L1-R machine was not built."""
    case = _beta_case_params(with_beta=False)
    model = _model(case, mechanics="off")
    rod = model.rod_chamber
    assert rod.machine is None and "k_h" in rod.unavailable_reason
    assert rod.meta()["machine_unavailable_reason"] == rod.unavailable_reason
    from outrigger_sim.hydraulics.rod_chamber import STATE_KEYS

    arrays = rod.state_arrays()
    assert not set(STATE_KEYS) & set(arrays) and "engine_mechanics_on" in arrays
    model.system.DoStepDynamics(model.dt_s)
    with pytest.raises(RuntimeError, match="not available"):
        rod.attach_sensor_source(object())


def test_on_model_uses_the_run_beta_for_k_h() -> None:
    """With the beta override k_h is computed with the same beta, so the beta 1.6 k_n is
    below it and L1-R builds; the record names the source."""
    case = _beta_case_params(with_beta=True)
    model = _model(case)
    rod = model.rod_chamber
    assert rod.machine is not None
    for record, leg_params in zip(rod._align_records, rod.leg_params, strict=True):
        assert record["head_stiffness_source"] == "run beta (override)"
        assert leg_params.head_stiffness_N_m > record["kn_smc_float32_N_m"]
    with pytest.raises(ValueError, match="k_h"):
        _model(_beta_case_params(with_beta=False))  # on without the beta: refused as before

