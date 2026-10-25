"""S9 SCM model pieces (``outrigger_sim.chrono.scm_model``; ``dynamics_model.md`` 3.11.2, 5.32.4,
5.33.4, 5.33.7).

* soil sets: table values, the elastic_K clamp pre-check, the bprime SCM call (c = phi = 0);
* anchor values against the 5.33.4 table (k_t,S9 per pad type and soil);
* crawler C boxes against the 3.11.2 table (ramp end heights 16.9 / 23.9 mm);
* a short machine build-and-step smoke (4 cm grid): finite state, SCM shear exactly 0 (bprime),
  the swivel stabilisers absent with the pads in the air.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.scm_model import (  # noqa: E402
    FRONT_RAMP_X_M,
    REAR_RAMP_X_M,
    S9Model,
    SoilParameterError,
    crawler_box_specs,
    load_soil_set,
    pad_tangential_values,
    scm_call_values,
    track_tangential_values,
)
from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta  # noqa: E402
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def params_b():
    return apply_pad_variant(load_params(level="top", model="L2b_NSC"), "dwg_rear250")


def test_soil_set_and_clamp_check() -> None:
    g1 = load_soil_set("G1")
    assert g1.chrono["elastic_K"] == 3.5e8 and g1.crawler_contact_area_m2 == pytest.approx(1.49)
    assert len(g1.table_sha256) == 64
    with pytest.raises(SoilParameterError):
        load_soil_set("G1", overrides={"elastic_K": 1.5e8})  # = Kphi, n = 1 -> Chrono clamp
    assert scm_call_values(g1, "bprime")[3:5] == (0.0, 0.0)
    j1 = load_soil_set("J1")
    assert scm_call_values(j1, "native")[3:5] == (68950.0, 34.0)


@pytest.mark.parametrize(
    ("soil", "variant", "expected_MN_m"),
    [("G1", "dwg_rear250", (5.88, 5.88, 3.07, 3.07)), ("J1", "dwg_rear250", (5.13, 5.13, 2.71, 2.71)),
     ("J1", "cad330", (5.13, 5.13, 3.08, 3.08))],
)
def test_pad_stiffness_matches_dynamics_table(soil, variant, expected_MN_m) -> None:
    params = apply_pad_variant(load_params(level="top", model="L2b_NSC"), variant)
    pv = pad_variant_meta(variant, params=params)
    areas = [pv["pad_bottom_area_m2"][leg] for leg in LEG_ORDER]
    v = pad_tangential_values(params, load_soil_set(soil), areas)
    for got, exp in zip(v.stiffness_N_m, expected_MN_m, strict=True):
        assert got / 1e6 == pytest.approx(exp, abs=0.006)  # 5.33.4 table, 2 decimals
    assert v.friction == pytest.approx(math.tan(math.radians(load_soil_set(soil).friction_deg)))
    assert v.adhesion_N[0] == pytest.approx(load_soil_set(soil).cohesion_Pa * areas[0])
    # same damping ratio: c / sqrt(k) constant per leg
    l1 = params.contact.rigid_floor.L1
    for i in range(4):
        assert v.damping_actual_N_s_m[i] / math.sqrt(v.stiffness_N_m[i]) == pytest.approx(
            l1.ct_per_pad_N_s_m[i] / math.sqrt(l1.bushing_stiffness_per_pad_N_m[i]), rel=1e-12)
        assert v.damping_input_N_s_m[i] == 0.5 * v.damping_actual_N_s_m[i]
    upper = pad_tangential_values(params, load_soil_set(soil), areas, stiffness_mode="l1_kt")
    lower = pad_tangential_values(params, load_soil_set(soil), areas, stiffness_mode="janosi")
    assert all(lo < s < up for lo, s, up in zip(lower.stiffness_N_m, v.stiffness_N_m, upper.stiffness_N_m,
                                                 strict=True))


def test_track_values(params_b) -> None:
    t = track_tangential_values(params_b, load_soil_set("G1"))
    assert t.k_rollers_N_m == pytest.approx(1.165e7, rel=0.01)  # 5.33.7 #7
    assert t.k_soil_N_m == pytest.approx(0.8 * 3.5e8 * 1.49 / 2)
    assert t.friction == pytest.approx(math.tan(math.radians(40.0)))


def test_crawler_boxes(params_b) -> None:
    boxes = crawler_box_specs(params_b)
    assert len(boxes) == 6
    z0 = params_b.ground.crawler_bottom_z_m + 0.004
    for b in boxes:
        a = b["angle_y_rad"]
        length, _, t = b["size"]
        c = np.asarray(b["centre"])
        n_up = np.array([math.sin(a), 0.0, math.cos(a)])
        x_ax = np.array([math.cos(a), 0.0, -math.sin(a)])
        bottom = c - n_up * t / 2
        ends = [bottom - x_ax * length / 2, bottom + x_ax * length / 2]
        if b["name"].endswith("flat"):
            assert all(abs(e[2] - z0) < 1e-12 for e in ends)
        elif b["name"].endswith("front"):
            assert ends[0][0] == pytest.approx(FRONT_RAMP_X_M[0], abs=1e-9)
            assert ends[0][2] == pytest.approx(z0, abs=1e-9)
            assert (ends[1][2] - z0) * 1e3 == pytest.approx(16.9, abs=0.05)  # 3.11.2: +16.9 mm
        else:
            assert ends[1][0] == pytest.approx(REAR_RAMP_X_M[1], abs=1e-9)
            assert ends[1][2] == pytest.approx(z0, abs=1e-9)
            assert (ends[0][2] - z0) * 1e3 == pytest.approx(23.9, abs=0.05)  # 3.11.2: +23.9 mm


def test_machine_build_and_step(params_b) -> None:
    pv = pad_variant_meta("dwg_rear250", params=params_b)
    model = S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04)
    for _ in range(100):
        model.step()
    sup = model.forces.sup_force_N
    assert np.all(np.isfinite(sup)) and sup[2] > 0.0
    assert sup[0] == 0.0 and sup[1] == 0.0  # SCM shear off (bprime): tau = 0 exactly
    assert not model.swivel.active.any()  # pads in the air
    assert model.crawler_bushing is not None and model.crawler_bushing.in_contact.all()
    meta = model.meta()
    assert meta["scm"]["scm_shear"] == "off (tangential by anchor bushings)"
    assert meta["scm"]["soil"]["key"] == "G1" and meta["c2_soil"] is None
    row = model.s9_record()
    # control spec 287 cad row: crawler patch force sum, pad sinkage, clearance above the rut
    for key in ("scm_crawler_normal_N", "scm_crawler_force_world_N", "scm_contact_patches", "pad_sinkage_geometric_m",
                "rut_clearance_m", "pad_tilt_max_deg", "body_omega_world_rad_s"):
        assert key in row


def test_gravity_ramp_and_polygon_helpers() -> None:
    from outrigger_sim.chrono.scm_model import convex_hull_2d, gravity_ramp_factor, inside_convex_polygon

    assert gravity_ramp_factor(0.0, 3.0) == 0.0 and gravity_ramp_factor(3.0, 3.0) == 1.0
    assert gravity_ramp_factor(1.5, 3.0) == pytest.approx(0.5)  # Poly345 is symmetric about u = 0.5
    assert gravity_ramp_factor(1.0, 2.0, "linear") == 0.5 and gravity_ramp_factor(0.0, 3.0, "step") == 1.0
    with pytest.raises(ValueError):
        gravity_ramp_factor(0.0, 1.0, "cosine")
    sq = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.5, 0.5], [0.5, 0.0]])
    idx = convex_hull_2d(sq)
    assert sorted(idx.tolist()) == [0, 1, 2, 3]
    inside = inside_convex_polygon(sq[idx], [[0.5, 0.5], [1.0, 0.5], [1.5, 0.5]])
    assert inside.tolist() == [True, False, False]  # edge points excluded


def _ray_dev_mm(model, cs, res, x, y, z_nom):
    import pychrono as ch

    cs.RayHit(ch.ChVector3d(x, y, z_nom - 0.3), ch.ChVector3d(x, y, z_nom + 0.02), res)
    assert res.hit
    return (res.abs_hitPoint.z - z_nom) * 1e3


def test_ray_mesh_bottoms_exact_and_zero_first_step_force(params_b) -> None:
    """P1-V0 (i) / (ii) in small (dynamics 5.34.10): with the default static triangle meshes the
    SCM rays hit the crawler block bottom and the pad bottoms within 0.05 mm, and the zero-gravity
    first step gives no SCM force; the former convex shapes hit up to about 10 mm low."""
    import pychrono as ch

    pv = pad_variant_meta("dwg_rear250", params=params_b)
    model = S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04)
    assert model.ray_shape == "mesh" and model.meta()["ray_shape"]["mode"] == "mesh"
    model.set_gravity_factor(0.0)
    model.step()
    assert np.abs(model.forces.sup_force_N).max() <= 100.0 and np.abs(model.forces.pad_force_N).max() <= 100.0
    cs, res = model.system.GetCollisionSystem(), ch.ChRayhitResult()
    z0 = params_b.ground.crawler_bottom_z_m + 0.004
    devs = [_ray_dev_mm(model, cs, res, float(x), float(y), z0)
            for x in np.linspace(-0.9, 0.85, 15) for y in np.linspace(0.82, 1.27, 7)]
    for i, pad in enumerate(model.pads):
        c = np.asarray(model.pad_bottom_local_pad_m[i])
        for dx in (-0.08, 0.0, 0.07):
            for dy in (-0.08, 0.0, 0.06):
                p = pad.TransformPointLocalToParent(ch.ChVector3d(*(float(v) for v in c + [dx, dy, 0.0])))
                devs.append(_ray_dev_mm(model, cs, res, p.x, p.y, p.z))
    assert np.abs(devs).max() <= 0.05
    assert model.num_ray_hits() > 0  # the block bottom touches the plane (zero sinkage, zero force)


def test_force_reader_sums_terrains(params_b) -> None:
    """ScmForceReader over several terrains = sum of the per-terrain reads; one terrain = that read."""
    from outrigger_sim.chrono.scm_model import ScmForceReader

    pv = pad_variant_meta("dwg_rear250", params=params_b)
    model = S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04, crawler_grid_m=0.04)
    assert model.dual_terrain and len(model.terrains) == 2 and model.terrain is model.pad_terrain
    for _ in range(20):
        model.step()
    one = [ScmForceReader(t, model.pads, model.superstructure) for t in model.terrains]
    for r in one:
        r.refresh()
    assert np.array_equal(model.forces.sup_force_N, one[0].sup_force_N + one[1].sup_force_N)
    assert np.array_equal(model.forces.pad_force_N, one[0].pad_force_N + one[1].pad_force_N)
    assert one[0].sup_force_N[2] == 0.0 and one[1].sup_force_N[2] > 0.0  # tracks on the crawler terrain
    meta = model.meta()
    assert meta["terrain_layout"] == {"dual": True, "pad_grid_m": 0.04, "crawler_grid_m": 0.04}
    assert meta["scm"]["layout"].startswith("dual") and meta["scm"]["crawler_terrain"]["grid_m"] == 0.04
    stats = model.pad_node_stats()
    assert len(stats) == 4 and all(s["n_inside"] > 0 and s["n_contact"] == 0 for s in stats)  # pads in the air


def test_engine_truth_and_measurements(params_b) -> None:
    from outrigger_sim.chrono.scm_engine import S9Engine

    pv = pad_variant_meta("dwg_rear250", params=params_b)
    model = S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04)
    engine = S9Engine(model, imu_method="chrono_point")
    for _ in range(50):
        engine.step()
    truth = engine.truth()
    w = (params_b.superstructure.mass_properties.mass_kg
         + sum(leg.moving_part.mass_kg for leg in params_b.legs)) * 9.80665
    # SCM crawler force reaches the truth (GetContactForce would read 0); 5 ms after the start the
    # machine is still settling into the soil, so only a sizeable positive load is required
    assert 0.05 * w < truth.F_crawler_N[2] < 3.0 * w
    assert np.all(truth.F_contact_n_N == 0.0)  # pads in the air
    meas = engine.measure()
    assert np.all(np.isfinite(meas.head_pressure_Pa))
    assert engine.info.model == "S9_SCM"
    engine.close()


def test_settle_dashpot_heave_roll_pitch_only(params_b) -> None:
    """Settle dashpot (5.35.4 (a), U-S9P-1): force along the plane normal opposing the COG normal
    velocity, torque about the plane x / y axes only (yaw free), fade 3 -> 5 s, zero after."""
    from outrigger_sim.chrono.scm_model import SettleDashpot

    pv = pad_variant_meta("dwg_rear250", params=params_b)
    model = S9Model(params_b, load_soil_set("G1"), pv, grid_m=0.04)
    dp = SettleDashpot(model)
    assert model.settle_dashpot is dp and model.load_hooks[-1] == dp.hook
    assert (dp.c_z, dp.c_pitch, dp.c_roll, dp.fade_s) == (2.0e6, 3.4e6, 2.2e6, (3.0, 5.0))
    assert dp.factor(0.0) == 1.0 and dp.factor(3.0) == 1.0 and dp.factor(4.0) == pytest.approx(0.5)
    assert dp.factor(5.0) == 0.0 and dp.factor(7.0) == 0.0
    sup = model.superstructure
    for _ in range(200):
        model.step()
        v = np.array([sup.GetPosDt().x, sup.GetPosDt().y, sup.GetPosDt().z])
        w = np.array([sup.GetAngVelParent().x, sup.GetAngVelParent().y, sup.GetAngVelParent().z])
        f, t = dp.force_world_N, dp.torque_world_Nm
        assert f[0] == 0.0 and f[1] == 0.0  # level plane: normal = world z, in-plane free
        assert f[2] == pytest.approx(-2.0e6 * v[2], rel=1e-12, abs=1e-9)
        assert t[2] == 0.0  # yaw free
        assert t[0] == pytest.approx(-2.2e6 * w[0], rel=1e-12, abs=1e-9)
        assert t[1] == pytest.approx(-3.4e6 * w[1], rel=1e-12, abs=1e-9)
    assert dp.force_abs_max_N > 0.0 and dp.energy_J >= 0.0
    meta = model.meta()["settle_dashpot"]
    assert meta["c_z_N_s_m"] == 2.0e6 and meta["fade_s"] == [3.0, 5.0]
    dp.fade_s = (0.0, 0.0)  # past the fade: zero force and torque
    model.step()
    assert not dp.force_world_N.any() and not dp.torque_world_Nm.any() and dp.off_since_s is not None
    with pytest.raises(ValueError):
        SettleDashpot(model, fade_s=(5.0, 3.0))


def test_runner_settle_defaults() -> None:
    """run_S9 settle: dashpot default 3 + 5 s; --settle-dashpot none = former 3 + 2 s."""
    import importlib
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"
    sys.path.insert(0, str(scripts))
    try:
        run_s9 = importlib.import_module("run_S9")
    finally:
        sys.path.remove(str(scripts))
    import argparse

    p = argparse.ArgumentParser()
    run_s9._gravity_ramp_args(p)
    a = p.parse_args([])
    assert a.settle_dashpot == "zrp" and run_s9.settle_time_s(a) == 8.0
    assert run_s9.gravity_schedule_meta(a)["hold_s"] == 5.0
    b = p.parse_args(["--settle-dashpot", "none"])
    assert run_s9.settle_time_s(b) == 5.0
    c = p.parse_args(["--settle-dashpot", "none", "--gravity-hold", "17"])
    assert run_s9.settle_time_s(c) == 20.0
