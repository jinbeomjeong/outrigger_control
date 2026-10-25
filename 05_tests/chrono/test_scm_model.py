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
    for key in ("scm_crawler_normal_N", "scm_contact_patches", "pad_sinkage_geometric_m", "rut_clearance_m"):
        assert key in row


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
