"""Ground bushing initial hold (S2a V12 gravity ramp) and the tilted-floor L1 build.

The pad spheres start exactly on the 2 deg slope with zero force and gravity is ramped from 0
(``scenarios/slope``). Without the hold the SMC contact reads N = 0 for about 30 ms, the
anchor follows the pad (yield steps) and every bushing is removed after t_lift and re-created
at N > N_th (events); with the hold the t = 0 bushings stay, no yield, no event.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.ground_bushing import OPTIONAL_STATE_KEYS  # noqa: E402
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.chrono.runs import run_gravity_ramp  # noqa: E402
from outrigger_sim.chrono.system import gravity_vector, set_gravity  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.scenarios.slope import gravity_ramp, slope_start  # noqa: E402
from outrigger_sim.verify.reference import SLOPE_V12_CASES, load_references  # noqa: E402

RUN_S = 0.12


def _slope_model(hold: bool) -> L1Model:
    params = load_params(level="top")
    st = slope_start(params, load_references(), SLOPE_V12_CASES[0])
    model = L1Model(
        params,
        pose=BodyPose(st.body_origin_m),
        extensions_m=st.extensions_m,
        attach_bushings=False,
        floor_pose=BodyPose(st.floor_pos_m, st.floor_quat_wxyz),
    )
    model.bushing.attach(hold_until_loaded=hold)
    set_gravity(model.system, (0.0, 0.0, 0.0))
    return model


@pytest.mark.chrono
def test_tilted_floor_start_has_zero_bushing_deformation() -> None:
    model = _slope_model(hold=True)
    d = model.bushing.tangential_displacement_m()
    assert np.nanmax(np.linalg.norm(d, axis=1)) < 1e-12
    assert np.allclose(
        model.bushing.normal_world(),
        [math.sin(math.radians(2.0)), 0.0, math.cos(math.radians(2.0))],
    )
    assert model.bushing.hold.all()


@pytest.mark.chrono
def test_initial_hold_keeps_the_t0_bushings_through_the_zero_load_start() -> None:
    model = _slope_model(hold=True)
    g = gravity_vector(model.params)
    run = run_gravity_ramp(model, g, gravity_ramp, RUN_S, fine_from_s=RUN_S)
    assert run.events == []
    assert model.bushing.yield_steps.tolist() == [0, 0, 0, 0]
    release = model.bushing.hold_release_t_s
    assert np.all(np.isfinite(release)) and np.all(release < RUN_S)
    assert not model.bushing.hold.any()


@pytest.mark.chrono
def test_without_hold_the_zero_load_start_removes_the_bushings() -> None:
    model = _slope_model(hold=False)
    g = gravity_vector(model.params)
    run = run_gravity_ramp(model, g, gravity_ramp, RUN_S, fine_from_s=RUN_S)
    kinds = sorted({e.kind for e in run.events})
    assert kinds == [1, 2]  # removed after t_lift, re-created at N > N_th
    assert (model.bushing.yield_steps > 0).all()


@pytest.mark.chrono
def test_restore_without_the_optional_hold_keys() -> None:
    model = _slope_model(hold=True)
    arrays = model.bushing.state_arrays()
    assert set(OPTIONAL_STATE_KEYS) <= set(arrays)
    old = {k: v for k, v in arrays.items() if k not in OPTIONAL_STATE_KEYS}
    model.bushing.restore_state(old)
    model.bushing.finish_restore()
    assert not model.bushing.hold.any()
    assert np.isnan(model.bushing.hold_release_t_s).all()
    model.bushing.restore_state(arrays)
    model.bushing.finish_restore()
    assert model.bushing.hold.all()
