"""S2a V checks (chrono_build_plan.md S2a, 3.4): V7 diagnosis and V12 slope statics.

``sim``: yaw initial velocity 2 s (mode 3, diagnosis 5; about 5 s wall on a P-core) and roll
20 s (mode 1; about 35 s). ``slow``: one V12 case (pitch 2 deg, 61 s simulated, about 100 s).
The judging run with every case and the Records is ``04_scripts/02_chrono/run_S2a.py all``;
this test uses the same library functions.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import L1Model, operating_extensions_m  # noqa: E402
from outrigger_sim.chrono.runs import (  # noqa: E402
    run_free_vibration,
    run_gravity_ramp,
    set_rigid_velocity,
)
from outrigger_sim.chrono.system import gravity_vector, set_gravity  # noqa: E402
from outrigger_sim.frames import quat_to_matrix  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_snapshot  # noqa: E402
from outrigger_sim.scenarios.impulse import (  # noqa: E402
    EXCITATIONS,
    angular_velocity_world,
    modal_reference,
)
from outrigger_sim.scenarios.settle import analytic_static_pose  # noqa: E402
from outrigger_sim.scenarios.slope import (  # noqa: E402
    MEAN_WINDOW_S,
    RAMP_S,
    STILL_WINDOW_S,
    gravity_ramp,
    settle_after_ramp_s,
    slope_start,
)
from outrigger_sim.verify.metrics import (  # noqa: E402
    fit_damped_sine,
    modal_coordinates,
    rigid_displacement,
)
from outrigger_sim.verify.reference import SLOPE_V12_CASES, load_references  # noqa: E402
from outrigger_sim.verify.s2a import (  # noqa: E402
    ModeResult,
    hold_checks,
    run_health_checks,
    slope_v13_checks,
    slope_window_stats,
    v7_mode_checks,
    v7_thresholds,
    v7_yaw_verdict,
    v12_checks,
    v12_plan_a_diagnosis,
)


def _failed(results):
    return [(r.id, r.item, r.value, r.ref, r.tol) for r in results if not r.passed]


def _identify(name: str):
    params = load_params(level="top")
    refs = load_references()
    modal = modal_reference(refs, "top")
    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz))
    t0 = model.restore(load_snapshot("S1_L1_top", params_sha256=params.sha256))
    p0 = model.probe()
    point = p0.body_pos_m + quat_to_matrix(p0.body_quat_wxyz) @ modal.reference_point_body_m
    excitation = EXCITATIONS[name]
    set_rigid_velocity(model, (0.0, 0.0, 0.0), angular_velocity_world(excitation, modal), point)
    run = run_free_vibration(model, excitation.window_s)
    s = run.series
    q = rigid_displacement(
        s["origin"], s["quat"], p0.body_pos_m, p0.body_quat_wxyz, modal.reference_point_body_m
    )
    i = excitation.mode_index
    eta = modal_coordinates(q, modal.phi, modal.mass_matrix)[:, i]
    fit = fit_damped_sine(s["t"] - t0, eta, float(modal.f_damped_Hz[i]))
    zeta_num = float(modal.zeta_num_at(model.dt_s)[0][i])
    result = ModeResult(
        mode=i + 1,
        fit=fit,
        zeta_num=zeta_num,
        zeta_corrected=fit.zeta - zeta_num,
        zeta_log_decrement=None,
        f_ref_Hz=float(modal.f_damped_Hz[i]),
        zeta_ref=float(modal.zeta[i]),
    )
    checks = v7_mode_checks(name, result) + run_health_checks(
        name, s, n_events=len(run.events), yield_steps=model.bushing.yield_steps.tolist()
    )
    return result, checks


@pytest.mark.sim
def test_v7_yaw_mode3_damping_confirms_bushing_input() -> None:
    result, checks = _identify("yaw")
    limits = v7_thresholds(load_references(), "top")
    assert not _failed(checks)
    # diagnosis 5: between the c_t-doubled minimum and the missing-damping maximum
    assert v7_yaw_verdict(result.zeta_corrected, limits).startswith("c_t as intended")
    assert result.zeta_corrected == pytest.approx(limits.nominal_zeta3, rel=0.05)


@pytest.mark.sim
def test_v7_roll_mode1() -> None:
    result, checks = _identify("roll")
    low, high = v7_thresholds(load_references(), "top").normal_zeta1_band
    assert not _failed(checks)
    assert low <= result.zeta_corrected <= high


@pytest.mark.sim
@pytest.mark.slow
def test_v12_pitch_2deg() -> None:
    params = load_params(level="top")
    refs = load_references()
    case = SLOPE_V12_CASES[0]
    st = slope_start(params, refs, case)
    model = L1Model(
        params,
        pose=BodyPose(st.body_origin_m),
        extensions_m=st.extensions_m,
        attach_bushings=False,
        floor_pose=BodyPose(st.floor_pos_m, st.floor_quat_wxyz),
    )
    model.bushing.attach(hold_until_loaded=True)
    set_gravity(model.system, (0.0, 0.0, 0.0))
    d0 = float(np.nanmax(np.linalg.norm(model.bushing.tangential_displacement_m(), axis=1)))
    settle = settle_after_ramp_s(params)
    total = RAMP_S + settle + STILL_WINDOW_S
    run = run_gravity_ramp(
        model,
        gravity_vector(params),
        gravity_ramp,
        total,
        fine_from_s=RAMP_S + settle,
        hold_deadline_s=RAMP_S,
    )
    stats = slope_window_stats(
        run.series,
        st.normal_world,
        mean_from_s=total - MEAN_WINDOW_S,
        still_from_s=RAMP_S + settle,
    )
    checks, _info = v12_checks(
        params,
        refs,
        case,
        st.normal_world,
        stats,
        slip_total_m=model.bushing.slip_total_m,
        start_deformation_m=d0,
        start_gap_m=st.sphere_gap_m,
    )
    checks += slope_v13_checks(refs, case, stats)
    checks += hold_checks(
        case,
        release_t_s=model.bushing.hold_release_t_s,
        max_tangential_N=model.bushing.hold_max_tangential_N,
        ramp_end_s=RAMP_S,
        friction=params.contact.rigid_floor.friction,
        touch_threshold_N=model.bushing.touch_threshold_N,
    )
    assert run.events == []
    assert not _failed(checks)
    # plan rev. 10 diagnosis: the difference is the ball-centre bushing + P-delta
    assert not _failed(v12_plan_a_diagnosis(refs, case, stats.reaction_world_mean_N))
