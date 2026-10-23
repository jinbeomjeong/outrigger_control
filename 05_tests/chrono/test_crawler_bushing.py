"""Q12 crawler anchor bushings (chrono/crawler_bushing) and the sloped-floor crawler pose
(scenarios/crawler_slope); stage-2 snapshot restore."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_snapshot  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import crawler_static_pose  # noqa: E402
from outrigger_sim.scenarios.crawler_slope import crawler_slope_pose  # noqa: E402

pytestmark = pytest.mark.chrono
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def test_values_and_scale(params) -> None:
    v = crawler_bushing_values(params)
    # rule: mean over the legs of the YAML pad kt / kn (Q12). With the REXOME35 per-leg YAML
    # (2026-10-22) the mean is 0.2331 (front 0.2761, rear 0.1901) and the nominal crawler kt is
    # 1.942e6 N/m per sphere, the value the S6 fdown32 batches used (dynamics_model.md 5.19.7,
    # "보유 크롤러 kt = 공칭 1.942x10^6 N/m"); 0.402 was the pre-REXOME35 common-leg value.
    kn = params.get("contact.rigid_floor.L1.kn_per_pad_N_m")
    kt = params.get("contact.rigid_floor.L1.kt_per_pad_N_m")
    ratio = float(np.mean([float(kt[k]) / float(kn[k]) for k in kn]))
    assert v.kt_over_kn_pad == pytest.approx(ratio, rel=1e-12)
    assert v.kt_over_kn_pad == pytest.approx(0.2331, abs=0.0005)
    assert v.kt_N_m == pytest.approx(1.942e6, rel=1e-3)
    assert v.kt_N_m == pytest.approx(v.kt_over_kn_pad * 8333333.33, rel=1e-6)
    assert v.damping_input_N_s_m == pytest.approx(0.5 * v.ct_N_s_m)
    v3 = crawler_bushing_values(params, 3.0)
    assert v3.kt_N_m == pytest.approx(3.0 * v.kt_N_m)
    assert v3.ct_N_s_m == pytest.approx(math.sqrt(3.0) * v.ct_N_s_m)


def test_flat_slope_pose_equals_level_pose(params) -> None:
    a = crawler_slope_pose(params, 0.0, 0.0)
    b = crawler_static_pose(params)
    assert np.allclose(a.origin_m, b.origin_m, atol=1e-9)
    assert np.allclose(a.sphere_force_N, b.sphere_force_N, atol=1e-3)
    assert a.body_pitch_deg == pytest.approx(b.pitch_deg, abs=1e-7)


def test_slope_pose_balance(params) -> None:
    p = crawler_slope_pose(params, 0.0, 3.5)
    w = p.weight_N
    assert p.sphere_force_N.sum() == pytest.approx(w * math.cos(math.radians(3.5)), rel=1e-6)
    assert p.body_pitch_deg > 3.5  # crawler compliance adds to the floor slope


def test_stage2_snapshot_restores_and_holds(params) -> None:
    # The current stage-2 snapshots are the bundle-B (L1-R on) ones in 07_results/states_L1R,
    # built with the REXOME35 YAML (run_S6.py snaps2 with OUTRIGGER_ROD_SIDE_MECHANICS=
    # one_sided_parallel; S6 verdicts are on bundle B). 07_results/states/S6_crawler_* are the
    # pre-REXOME35 bundle-A states (copies in 07_results/history_pre_rexome35_2026-10-22/states).
    states = ROOT / "07_results" / "states_L1R"
    name = "S6_crawler_top_fup3.5"
    if not (states / f"{name}.npz").exists():
        pytest.skip("stage-2 snapshots not built (run_S6.py snaps2, L1-R on)")
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import s6_stage2

    model, _ = s6_stage2.build_crawler_model(
        params, "fup3.5", attach=False, rod_side_mechanics="one_sided_parallel"
    )
    model.restore(load_snapshot(name, params_sha256=params.sha256, directory=states))
    cb = model.crawler_bushing
    n0 = int(cb.in_contact.sum())
    y0 = int(cb.yield_steps.sum())
    for _ in range(500):
        model.step()
    assert int(cb.in_contact.sum()) == n0 > 0
    assert int(cb.yield_steps.sum()) == y0
    w = crawler_slope_pose(params, 0.0, -3.5).weight_N
    assert sum(model.crawler_normals()) == pytest.approx(w * math.cos(math.radians(3.5)), rel=2e-3)


def test_default_model_has_no_crawler_bushing(params) -> None:
    from outrigger_sim.chrono.model import L1Model

    model = L1Model(params, crawler=True, attach_bushings=False)
    assert model.crawler_bushing is None
    assert model.meta()["crawler_bushings"] is None
