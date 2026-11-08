"""Mixed ground (outrigger_sim.chrono.rigid_base): spec parsing, values, model build (no step)."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.rigid_base import RigidBaseSpec  # noqa: E402


def test_parse() -> None:
    assert RigidBaseSpec.parse("rigid").scm_legs == ()
    assert RigidBaseSpec.parse("-").scm_legs == ()
    assert RigidBaseSpec.parse("FR").scm_legs == ("FR",)
    s = RigidBaseSpec.parse("fr+RL", 3.0)
    assert s.scm_legs == ("FR", "RL") and s.crawler_kn_scale == 3.0
    assert s.rigid_legs == ("FL", "RR")
    assert s.tag() == "rigid+FR+RL_K3"
    with pytest.raises(ValueError):
        RigidBaseSpec(("XX",))
    with pytest.raises(ValueError):
        RigidBaseSpec(("FR", "FR"))
    with pytest.raises(ValueError):
        RigidBaseSpec((), 0.0)


@pytest.fixture(scope="module")
def inputs():
    from outrigger_sim.chrono.scm_model import load_soil_set
    from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta
    from outrigger_sim.params import load_params

    params = apply_pad_variant(load_params(level="top", model="L2b_NSC"), "dwg_rear250")
    return params, pad_variant_meta("dwg_rear250", params=params), load_soil_set("J1")


def test_values(inputs) -> None:
    from outrigger_sim.chrono.rigid_base import rigid_crawler_values, rigid_pad_values

    params = inputs[0]
    pv = rigid_pad_values(params, [100.0] * 4)
    assert pv.kn_N_m == (float(params.get("contact.rigid_floor.concrete.k_N_m")),) * 4
    assert pv.friction == pytest.approx(0.5)
    c1, c3 = rigid_crawler_values(params, 1.0), rigid_crawler_values(params, 3.0)
    assert c3.kn_per_sphere_N_m == pytest.approx(3.0 * c1.kn_per_sphere_N_m)
    assert c3.gn_per_sphere_1_s == pytest.approx(math.sqrt(3.0) * c1.gn_per_sphere_1_s)
    assert c1.track_k_N_m == c3.track_k_N_m


def test_build_mixed_and_default(inputs) -> None:
    from outrigger_sim.chrono.scm_model import S9Model

    params, pv, soil = inputs
    m = S9Model(params, soil, pv, grid_m=0.02, rigid_base=RigidBaseSpec(("FR",), 3.0))
    assert len(m.terrains) == 1 and m.soil_patch_leg == "FR" and m.rigid_contacts is not None
    assert m.pad_terrain_by_leg[1] is m.terrain and m.pad_terrain_by_leg[0] is None
    assert m.plane_point_world_m[2] == pytest.approx(float(params.ground.crawler_bottom_z_m))
    meta = m.meta()
    assert meta["terrain_layout"]["layout"] == "rigid_base" and meta["rigid_base"]["crawler_kn_scale"] == 3.0
    m0 = S9Model(params, soil, pv, grid_m=0.02, rigid_base=RigidBaseSpec(()))
    assert m0.terrains == () and m0.terrain is None
    d = S9Model(params, soil, pv, grid_m=0.02, crawler_grid_m=0.04)
    assert d.rigid_base is None and d.rigid_contacts is None and d.forces.rigid is None and len(d.terrains) == 2
    assert "rigid_base" not in d.meta()
    with pytest.raises(ValueError):
        S9Model(params, soil, pv, crawler_grid_m=0.04, rigid_base=RigidBaseSpec(("FR",)))
